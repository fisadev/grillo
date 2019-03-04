"""Cli tool to use Grillo from the command line.
With the "listen" command you can listen for messages that any other computer sends using grillo.
With the "text", "file" and "clip"/"clipboard" commands, you can send data to any listening
computer.

When sending text, the receiver will just see it printed. When sending your clipboard, the
receiver will have the contents of your clipboard copied into their clipboard. And when sending
files, the file will be saved in the receiver's computer.

Usage:
  grillo listen [--forever] [--brave]
  grillo (clip|clipboard) [--brave]
  grillo text <text> [--brave]
  grillo file <file_path> [--brave]
  grillo (-h | --help)
  grillo --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --brave       The default mode waits/sends ack messages to retry missing packets if needed.
                "Brave" mode disables those acks, assuming all the message arrive perfectly all
                the time.  If you use brave and a packet is lost, the whole message won't be
                received.
  --forever     Keep listening for any messages, don't stop at the first message received.
"""
from docopt import docopt
from termcolor import colored, cprint

from grillo import Grillo
from grillo.modem import MessageTooLongException


def main():
    """
    Entry point when executed via command line.
    """
    arguments = docopt(__doc__)

    with_confirmation = not arguments['--brave']
    grillo = Grillo(with_confirmation)

    if arguments['listen']:
        try:
            grillo.listen(arguments['--forever'])
        except KeyboardInterrupt:
            cprint("Grillo was killed. Poor little grillo.", "yellow")
    else:
        try:
            if arguments['text']:
                grillo.send_text(arguments['<text>'])
            elif arguments['clip'] or arguments['clipboard']:
                grillo.send_clipboard()
            elif arguments['file']:
                grillo.send_file(arguments['<file_path>'])
        except MessageTooLongException:
            cprint("Contents are too long to send, Grillo can't handle them :(", "red")


if __name__ == '__main__':
    main()
