"""
An audio modem, able to encode and decode data from/to audio. Internally uses chirp for
the modulation/demodulation, and unireedsolomon for error correction.
"""
import time
from datetime import datetime, timedelta

from chirpsdk import ChirpConnect, CallbackSet
from grillo import config


class MessageTooLongException(Exception):
    """
    Error raised when a message is too long to be sent.
    """
    pass


class MessageAckIsBroken(Exception):
    """
    Error raised when the ack packet isn't received correctly.
    """
    pass


class NoCallbacks(CallbackSet):
    """
    There's no way of removing callbacks in chirp, you can only replace the callback set with a
    new one. So we need this "empty" callback set.
    """
    pass


class SinglePacketReceiver(CallbackSet):
    """
    A thing that can receive a single chirp packet, and stores it as an instance variable. It can
    also call a callback when the packet is received.
    """
    def __init__(self, callback=None):
        self.callback = callback
        self.packet = None

    def on_received(self, payload, channel):
        """
        Executed when chirp receives data.
        """
        self.packet = payload
        if self.callback is not None:
            self.callback(payload)


class Modem:
    """
    An audio modem able to encode and decode data from/to audio. Internally uses chirp for
    the modulation/demodulation and error correction, but adding a layer that allows for messages
    longer than 32 bytes (sending multiple chirp messages for every grillo message).
    """
    DATA_LEN = 30
    PACKET_DURATION = timedelta(seconds=4.66)

    def __init__(self, with_confirmation=False):
        self.chirp = ChirpConnect(
            key=config.CHIRP_APP_KEY,
            secret=config.CHIRP_APP_SECRET,
            config=config.CHIRP_APP_CONFIG,
        )
        self.chirp.start(send=True, receive=True)

        self.with_confirmation = with_confirmation
        self.reset_chained_status()

    def reset_chained_status(self):
        """
        Reset the status of the chained message that is being received.
        """
        self.chained_total_parts = None
        self.chained_parts = {}

    def send_message(self, message):
        """
        Send a message as multiple packets.
        """
        chain_len = self._get_chain_len(len(message))
        if chain_len > 255:
            raise MessageTooLongException()

        packets_to_send = range(chain_len)
        while len(packets_to_send) > 0:
            self._send_packets(message, packets_to_send, chain_len)
            if self.with_confirmation:
                packets_to_send = self._get_packets_to_retry()
            else:
                break

    def _get_packets_to_retry(self):
        """
        Wait for the other end to inform which parts of a message it didn't receive.
        """
        packets_to_retry = []
        ack_msg = self.receive_packet(self.PACKET_DURATION * 2)
        if ack_msg is None:
            return []

        header = ack_msg[0]
        if header == 0:
            packets_to_retry = ack_msg[1:]
            return packets_to_retry
        else:
            raise MessageAckIsBroken()

    def _send_packets(self, message, packet_list, chain_len):
        """
        Send a message as multiple packets, one after the other.
        """
        for i in packet_list:
            packet = (
                bytes([chain_len, i])
                + message[self.DATA_LEN * i:self.DATA_LEN * (i + 1)])
            self.send_packet(packet)

    def send_packet(self, packet):
        """
        Send a single packet.
        """
        self.chirp.send(packet, blocking=True)

    def send_ack(self, missing_parts=None):
        """
        Send a packet informing the missing parts of a chained message.
        """
        if missing_parts is None:
            missing_parts = []

        self.send_packet(bytes([0] + missing_parts))

    def _get_chain_len(self, size):
        return size // self.DATA_LEN + 1

    def receive_packet(self, timeout=None):
        """
        Wait (blocking) for a single packet, and return it when received.
        """
        receiver = SinglePacketReceiver()
        self.chirp.set_callbacks(receiver)

        start = datetime.now()

        while receiver.packet is None:
            time.sleep(0.1)

            if timeout:
                now = datetime.now()
                if now - start > timeout:
                    break

        self.stop_listening()
        return receiver.packet

    def receive_message(self, timeout=300):
        """
        Wait (blocking) for a single message, and return it when received.
        """
        self.reset_chained_status()

        receiver = SinglePacketReceiver(callback=self.on_chained_part_received)
        self.chirp.set_callbacks(receiver)

        self.timeout_start = datetime.now()
        if timeout:
            self.timeout_delta = timedelta(seconds=timeout)

        chained_message = None
        last_expected_part = None

        while chained_message is None:
            time.sleep(0.1)

            if self.chained_total_parts is not None:
                if last_expected_part is None:
                    last_expected_part = self.chained_total_parts - 1

                if last_expected_part in self.chained_parts or self._timeout_expired():
                    # finished receiving all the parts or should have finished and we didn't
                    missing_parts = self.chained_missing_parts()

                    if missing_parts:
                        # we didn't get all the parts, ask for the missing ones
                        parts_to_resend = missing_parts[:self.DATA_LEN]
                        last_expected_part = parts_to_resend[-1]
                        self.send_ack(parts_to_resend)
                        self._reset_timeout()
                    else:
                        # stop the chained building loop, we got all the parts
                        chained_message = self.chained_combine()
                        self.send_ack()
                        break

            if timeout and self._timeout_expired():
                break

        self.stop_listening()
        self.reset_chained_status()

        return chained_message

    def _timeout_expired(self):
        now = datetime.now()
        return (now - self.timeout_start) > self.timeout_delta

    def on_chained_part_received(self, packet):
        """
        Executed when chirp receives data that is part of a chained message.
        """
        if packet is not None:
            total_parts = packet[0]
            part_number = packet[1]
            message_part = packet[2:]

            if self.chained_total_parts is None:
                # first part received!
                self.chained_total_parts = total_parts

            self.chained_parts[part_number] = message_part
            self._reset_timeout()

    def _reset_timeout(self):
        self.timeout_delta = self.PACKET_DURATION * 1.5
        self.timeout_start = datetime.now()

    def chained_missing_parts(self):
        """
        Which parts of the message are missing?
        """
        return [part_number for part_number in range(self.chained_total_parts)
                if part_number not in self.chained_parts]

    def chained_combine(self):
        """
        Concatenate all the message parts.
        """
        return b''.join(self.chained_parts[part_number]
                        for part_number in range(self.chained_total_parts))

    def listen_for_packets(self, callback):
        """
        Start listening for packets, calling a callback whenever a packet is received.
        """
        receiver = SinglePacketReceiver(callback)
        self.chirp.set_callbacks(receiver)

    def listen_for_messages(self, callback):
        """
        Start listening for messages, calling a callback whenever a packet is received.
        """
        while True:
            message = self.receive_message()
            callback(message)
            self.reset_chained_status()

    def stop_listening(self):
        """
        Stop using chirp to listen for packets.
        """
        self.chirp.set_callbacks(NoCallbacks())
