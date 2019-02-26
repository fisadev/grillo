import pickle
import time
from enum import Enum
from pathlib import Path

import fire
import pyperclip
from chirpsdk import ChirpConnect, CallbackSet

from grillo import config


class MessageKind(Enum):
    """
    Kinds of messages that Grillo can send and receive.
    """
    TEXT = "t"
    CLIPBOARD = "c"
    FILE = "f"


class MessageTooLongException(Exception):
    """
    Error raised when a message is too long to be sent.
    """
    pass


class ChirpCallbacks(CallbackSet):
    """
    Callbacks container that chirp expects to get.
    """
    def __init__(self, grillo):
        self.grillo = grillo

    def on_received(self, payload, channel):
        """
        Executed when chirp receives data.
        """
        if payload is not None:
            identifier = payload.decode('utf-8')

            self.grillo.receive_message(payload)
        else:
            print('Decode failed')


class Grillo:
    """
    Tool to send data to a different computer or receive it, just using audio and mic.
    """
    HEADER_SEPARATOR = b"|"
    FILE_NAME_SEPARATOR = b"<NAME>"

    def __init__(self, send=False, receive=False):
        """
        Return an instance of a chirp thingymagic ready to be used.
        """
        self.chirp = ChirpConnect(
            key=config.CHIRP_APP_KEY,
            secret=config.CHIRP_APP_SECRET,
            config=config.CHIRP_APP_CONFIG,
        )

        self.chirp.set_callbacks(ChirpCallbacks(self))
        self.listening = receive
        self.chirp.start(send=send, receive=receive)

    def send_message(self, kind, payload):
        """
        Build a serialized message to send over audio.
        """
        message = kind.value.encode("utf-8") + Grillo.HEADER_SEPARATOR + payload

        if len(message) > 32:
            raise MessageTooLongException()

        self.chirp.send(message, blocking=True)

    def read_message(self, message):
        """
        Read a serialized message received over audio.
        """
        parts = message.split(Grillo.HEADER_SEPARATOR)

        kind = MessageKind(parts[0].decode("utf-8"))
        payload = Grillo.HEADER_SEPARATOR.join(parts[1:])

        return kind, payload

    def send_text(self, text):
        """
        Send text via audio.
        """
        self.send_message(MessageKind.TEXT, text.encode("utf-8"))

    def send_clipboard(self):
        """
        Send clipboard contents via audio.
        """
        self.send_message(MessageKind.CLIPBOARD, pyperclip.paste().encode("utf-8"))

    def send_file(self, file_path):
        """
        Send file contents via audio.
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        with file_path.open('rb') as file:
            file_contents = file.read()

        payload = (
            file_path.name.encode("utf-8") +
            Grillo.FILE_NAME_SEPARATOR +
            file_contents
        )

        self.send_message(MessageKind.FILE, payload)

    def listen(self, forever=False):
        """
        Receive whatever data is being sent from the source computer.
        """
        while self.listening or forever:
            time.sleep(1)

    def receive_message(self, message):
        """
        Process an incoming message.
        """
        kind, payload = self.read_message(message)
        if kind == MessageKind.TEXT:
            self.receive_text(payload)
        elif kind == MessageKind.CLIPBOARD:
            self.receive_clipboard(payload)
        elif kind == MessageKind.FILE:
            self.receive_file(payload)

        self.listening = False

    def receive_text(self, payload):
        """
        Receive text via audio.
        """
        text = payload.decode("utf-8")
        print("Received text:")
        print(text)

    def receive_clipboard(self, payload):
        """
        Receive clipboard contents via audio.
        """
        clipboard_contents = payload.decode("utf-8")
        pyperclip.copy(clipboard_contents)
        print("Received clipboard contents, copied to your own clipboard :)")

    def receive_file(self, payload):
        """
        Receive file contents via audio.
        """
        parts = payload.split(Grillo.FILE_NAME_SEPARATOR)

        name = parts[0].decode("utf-8")
        file_contents = Grillo.FILE_NAME_SEPARATOR.join(parts[1:])

        file_path = Path(".") / name

        copy_counter = 0
        while file_path.exists():
            copy_counter += 1
            file_path = Path(".") / str(copy_counter) + "_" + name

        with file_path.open('wb') as file:
            file.write(file_contents)

        print("Received a file, saved to", str(file_path))


class GrilloCli:
    """
    Cli tool to use Grillo from the command line.
    """
    def text(self, text):
        """
        Send a text.
        """
        grillo = Grillo(send=True)
        try:
            grillo.send_text(text)
        except MessageTooLongException:
            print("Text is too long to be sent.")

    def clip(self):
        """
        Send the contents of the clipboard.
        """
        self.clipboard()

    def clipboard(self):
        """
        Send the contents of the clipboard.
        """
        grillo = Grillo(send=True)
        try:
            grillo.send_clipboard()
        except MessageTooLongException:
            print("Clipboard contents are too big to be sent.")

    def file(self, file_path):
        """
        Send a file.
        """
        grillo = Grillo(send=True)
        try:
            grillo.send_file(file_path)
        except MessageTooLongException:
            print("File is too big to be sent.")

    def listen(self, forever=False):
        """
        Receive whatever data is being sent from the source computer.
        """
        grillo = Grillo(receive=True)
        try:
            grillo.listen(forever)
        except KeyboardInterrupt:
            print("Grillo was killed. Poor little grillo.")


def main():
    """
    Entry point when executed via command line.
    """
    fire.Fire(GrilloCli)


if __name__ == '__main__':
    main()
