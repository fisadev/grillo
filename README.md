# grillo

A small tool to easily send data (files, clipboard) between computers with 0 config, just using audio and mic.

On Ubuntu, install it with:


    sudo apt install portaudio19-dev libffi-dev libsndfile1
    pip3 install -e .


# Usage


    machine1> grillo listen

    machine2> grillo text "hello world!"


After hearing some hight pitched sounds, machine1 should print:

    machine1> grillo listen
    Received text:
    hello world!


You can also send files:

    machine2> grillo file /path/to/a_file.txt


Or even update machine1's clipboard with machine2's clipboard contents:

    machine2> grillo clipboard


This is currently under heavy development, that's why it hasn't been published to PyPI.
**The** biggest issue right now: the tool used to communicate, can't send packages more than 32 bytes long. Possible alternative we are working on: replace it with [this](https://github.com/romanz/amodem) other tool.
