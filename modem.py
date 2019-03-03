"""
An audio modem, able to encode and decode data from/to audio. Internally uses chirp for
the modulation/demodulation, and unireedsolomon for error correction.
"""

from chirpsdk import ChirpConnect, CallbackSet
from grillo import config


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
    def _build_chirp_modem(self):
        chirp = ChirpConnect(
            key=config.CHIRP_APP_KEY,
            secret=config.CHIRP_APP_SECRET,
            config=config.CHIRP_APP_CONFIG,
        )

        return chirp

    def _build_chirp_modem_for_receive(self, callback):
        chirp = self._build_chirp_modem()
        chirp.set_callbacks(ChirpCallbacks(callback))
        chirp.start(receive=True)

        return chirp

    def _build_chirp_modem_for_send(self):
        chirp = self._build_chirp_modem()
        chirp.start(send=True)

        return chirp

    def send(self, message, blocking=True):
        modem = self._build_chirp_modem_for_send()
        modem.send(message, blocking)

    def listen(self, on_received_callback):
        modem = self._build_chirp_modem_for_receive(on_received_callback)
