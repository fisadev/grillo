"""
An audio modem, able to encode and decode data from/to audio. Internally uses chirp for
the modulation/demodulation, and unireedsolomon for error correction.
"""
import time

from chirpsdk import ChirpConnect, CallbackSet
from grillo import config


class MessageTooLongException(Exception):
    """
    Error raised when a message is too long to be sent.
    """
    pass


class MessagePartsLostException(Exception):
    """
    Error raised when part of a message can't be read.
    """
    pass

class MessageAckIsBroken(Exception):
    pass


class PartialMessageReceiver(CallbackSet):
    """
    A thing that can listen to chirp callbacks and build a message received in parts.
    """
    def __init__(self, callback):
        self.callback = callback
        self.reset_status()

    def reset_status(self):
        """
        Reset reception status.
        """
        self.total_parts = None
        self.parts = []

    def on_received(self, payload, channel):
        """
        Executed when chirp receives data.
        """
        if payload is None:
            self.reset_status()
            raise MessagePartsLostException("A part of the message failed to decode.")
        else:
            total_parts = payload[0]
            part_number = payload[1]
            message_part = payload[2:]

            if self.total_parts is None:
                # first part received!

                if part_number != 0:
                    # but we missed the real first part
                    self.reset_status()
                    raise MessagePartsLostException("Missed the begining of the message.")

                self.total_parts = total_parts
            else:
                # middle or last part received

                if part_number != self.parts[-1][0] + 1:
                    # but we missed some part in between
                    self.reset_status()
                    raise MessagePartsLostException("Missed parts of the message.")

            self.parts.append((part_number, message_part))

            # finished receiving all the parts?
            if self.finished():
                final_message = self.combine()
                self.reset_status()
                self.callback(final_message)

    def finished(self):
        """
        Is the message complete?
        """
        return len(self.parts) == self.total_parts

    def combine(self):
        """
        Concatenate all the message parts.
        """
        return b''.join(message_part
                        for part_number, message_part in self.parts)


class Modem:
    """
    An audio modem able to encode and decode data from/to audio. Internally uses chirp for
    the modulation/demodulation and error correction, but adding a layer that allows for messages
    longer than 32 bytes (sending multiple chirp messages for every grillo message).
    """
    DATA_LEN = 30

    def send(self, message, blocking=True):
        chain_len = self._get_chain_len(len(message))
        if chain_len > 255:
            raise MessageTooLongException()

        modem = self._build_chirp_modem_for_send()
        packets_to_send = range(chain_len)
        while len(packets_to_send) > 0:
            self._send_packets(modem, message, packets_to_send, chain_len, blocking)
# TODO           packets_to_send = self._get_packets_to_retry()
            packets_to_send = []

    def _get_packets_to_retry(self):
        packets_to_retry = []
        receiver = SinglePacketReceiver()
        self.listen(receiver)
        ack_msg = receiver.get_packet(5)
        header = ack_msg[0]
        if header == 0:
            packets_to_retry = ack_msg[1:]
            return packets_to_retry
        else:
            raise MessageAckIsBroken()

    def _send_packets(self, modem, message, packet_list, chain_len, blocking):
        for i in packet_list:
            packet = (
                bytes([chain_len, i])
                + message[self.DATA_LEN * i:self.DATA_LEN * (i + 1)])
            modem.send(packet, blocking)

    def _get_chain_len(self, size):
        return size // self.DATA_LEN + 1

    def _build_chirp_modem_for_send(self):
        chirp = self._build_chirp_modem()
        chirp.start(send=True, receive=False)

        return chirp

    def listen(self, on_received_callback, kill_after_seconds=None):
        modem = self._build_chirp_modem_for_listening(on_received_callback)

        if kill_after_seconds:
            time.sleep(kill_after_seconds)
            modem.stop()

    def _build_chirp_modem_for_listening(self, on_received_callback):
        chirp = self._build_chirp_modem()
        chirp.set_callbacks(PartialMessageReceiver(on_received_callback))
        chirp.start(receive=True, send=False)

        return chirp

    def _build_chirp_modem(self):
        chirp = ChirpConnect(
            key=config.CHIRP_APP_KEY,
            secret=config.CHIRP_APP_SECRET,
            config=config.CHIRP_APP_CONFIG,
        )

        return chirp
