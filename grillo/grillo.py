import time
from enum import Enum
from pathlib import Path

import fire
import pyperclip

from grillo.modem import Modem, MessageTooLongException


class MessageKind(Enum):
    """
    Kinds of messages that Grillo can send and receive.
    """
    TEXT = "t"
    CLIPBOARD = "c"
    FILE = "f"


class Grillo:
    """
    Tool to send data to a different computer or receive it, just using audio and mic.
    """
    HEADER_SEPARATOR = b"|"
    FILE_NAME_SEPARATOR = b"<NAME>"

    def __init__(self, with_confirmation=True):
        self.modem = Modem(with_confirmation)
        self.listening = False
        self.with_confirmation = with_confirmation

    def send_text(self, text):
        """
        Send text via audio.
        """
        self._send_message(MessageKind.TEXT, str(text).encode("utf-8"))

    def send_clipboard(self):
        """
        Send clipboard contents via audio.
        """
        self._send_message(MessageKind.CLIPBOARD, pyperclip.paste().encode("utf-8"))

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

        self._send_message(MessageKind.FILE, payload)

    def _send_message(self, kind, payload):
        """
        Build a serialized message to send over audio.
        """
        message = kind.value.encode("utf-8") + Grillo.HEADER_SEPARATOR + payload

        self.modem.send_message(message)

    def listen(self, forever=False):
        """
        Receive whatever data is being sent from the source computer.
        """
        if forever:
            self.modem.listen_for_messages(self._receive_message)

            while True:
                time.sleep(0.5)
        else:
            message = self.modem.receive_message()
            self._receive_message(message)


    def _receive_message(self, message):
        """
        Process an incoming message.
        """
        kind, payload = self._parse_message(message)
        if kind == MessageKind.TEXT:
            self._receive_text(payload)
        elif kind == MessageKind.CLIPBOARD:
            self._receive_clipboard(payload)
        elif kind == MessageKind.FILE:
            self._receive_file(payload)

    def _parse_message(self, message):
        """
        Parce message received over audio.
        """
        parts = message.split(Grillo.HEADER_SEPARATOR)

        kind = MessageKind(parts[0].decode("utf-8"))
        payload = Grillo.HEADER_SEPARATOR.join(parts[1:])

        return kind, payload

    def _receive_text(self, payload):
        """
        Receive text via audio.
        """
        text = payload.decode("utf-8")
        print("Received text:")
        print(text)

    def _receive_clipboard(self, payload):
        """
        Receive clipboard contents via audio.
        """
        clipboard_contents = payload.decode("utf-8")
        pyperclip.copy(clipboard_contents)
        print("Received clipboard contents, copied to your own clipboard :)")

    def _receive_file(self, payload):
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


class GrilloCli(object):
    """
    Cli tool to use Grillo from the command line.

    brave: bool
        The default mode waits/sends ack messages to retry missing packets if needed.
        "Brave" mode disables those acks, assuming all the message arrive perfectly all the time.
        If you use brave and a packet is lost, the whole message won't be received.
    """
    def __init__(self, brave=False):
        self._with_confirmation = not brave

    def text(self, text):
        """
        Send a text.
        """
        grillo = Grillo(self._with_confirmation)
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
        grillo = Grillo(self._with_confirmation)
        try:
            grillo.send_clipboard()
        except MessageTooLongException:
            print("Clipboard contents are too big to be sent.")

    def file(self, file_path):
        """
        Send a file.
        """
        grillo = Grillo(self._with_confirmation)
        try:
            grillo.send_file(file_path)
        except MessageTooLongException:
            print("File is too big to be sent.")

    def listen(self, forever=False):
        """
        Receive whatever data is being sent from the source computer.
        """
        grillo = Grillo(self._with_confirmation)
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
