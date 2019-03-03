"""
An audio modem, able to encode and decode data from/to audio. Internally uses chirp for
the modulation/demodulation, and unireedsolomon for error correction.
"""

from chirpsdk import ChirpConnect, CallbackSet
from grillo import config


class MessageTooLongException(Exception):
    """
    Error raised when a message is too long to be sent.
    """
    pass


class MessagePartsLostException(Exception):
    pass


class ChirpCallbacks(CallbackSet):
    """
    Callbacks container that chirp expects to get.
    """
    def __init__(self, callback):
        self.callback = callback
        self.partial_message = None

    def on_received(self, payload, channel):
        """
        Executed when chirp receives data.
        """
        if payload is not None:
            total_parts = payload[0]
            part_number = payload[1]
            message_part = payload[2:]

            if self.partial_message is None:
                # first part received!

                if part_number != 0:
                    # but we missed the real first part
                    raise MessagePartsLostException("Missed the begining of the message.")

                self.partial_message = PartialMessage(total_parts)
            else:
                # middle or last part received

                if part_number != self.partial_message.parts[-1][0] + 1:
                    # but we missed some part in between
                    raise MessagePartsLostException("Missed parts of the message.")

            self.partial_message.parts.append((part_number, message_part))

            # finished receiving all the parts?
            if self.partial_message.finished():
                final_message = self.partial_message.combine()
                self.partial_message = None
                self.callback(final_message)
        else:
            print('Decode failed')
            self.partial_message = None


class PartialMessage:
    """
    Status of a reception process, in which we must concatenate multiple parts together to get
    the full message.
    """
    def __init__(self, total_parts):
        self.total_parts = total_parts
        self.parts = []

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
        for i in range(chain_len):
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

    def listen(self, on_received_callback):
        modem = self._build_chirp_modem_for_listening(on_received_callback)

    def _build_chirp_modem_for_listening(self, on_received_callback):
        chirp = self._build_chirp_modem()
        chirp.set_callbacks(ChirpCallbacks(on_received_callback))
        chirp.start(receive=True, send=False)

        return chirp

    def _build_chirp_modem(self):
        chirp = ChirpConnect(
            key=config.CHIRP_APP_KEY,
            secret=config.CHIRP_APP_SECRET,
            config=config.CHIRP_APP_CONFIG,
        )

        return chirp
