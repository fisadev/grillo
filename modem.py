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


class ChirpCallbacks(CallbackSet):
    """
    Callbacks container that chirp expects to get.
    """
    def __init__(self, callback):
        self.callback = callback

    def on_received(self, payload, channel):
        """
        Executed when chirp receives data.
        """
        if payload is not None:
            self.callback(payload)

        else:
            print('Decode failed')


class Modem:
    def send(self, message, blocking=True):
        if len(message) > 32:
            raise MessageTooLongException()

        modem = self._build_chirp_modem_for_send()
        modem.send(message, blocking)

    def _build_chirp_modem_for_send(self):
        chirp = self._build_chirp_modem()
        chirp.start(send=True, receive=False)

        return chirp

    def listen(self, on_received_callback):
        modem = self._build_chirp_modem_for_listening(on_received_callback)

    def _build_chirp_modem_for_listening(self, callback):
        chirp = self._build_chirp_modem()
        chirp.set_callbacks(ChirpCallbacks(callback))
        chirp.start(receive=True, send=False)

        return chirp

    def _build_chirp_modem(self):
        chirp = ChirpConnect(
            key=config.CHIRP_APP_KEY,
            secret=config.CHIRP_APP_SECRET,
            config=config.CHIRP_APP_CONFIG,
        )

        return chirp
