Grillo
======

A small tool to easily send data (files, clipboard) between computers with 0 config, just using audio and mic.

Installation
============

On Ubuntu, install it by running:


.. code::

    sudo apt install portaudio19-dev libffi-dev libsndfile1 xclip
    pip3 install grillomodem --user


Usage
=====


.. code::

    machine1> grillo listen

    machine2> grillo text "hello world!"


After hearing some hight pitched sounds, machine1 should print:


.. code::

    machine1> grillo listen
    Received text:
    hello world!


You can also send files:

.. code::

    machine2> grillo file /path/to/a_file.txt


Or even update machine1's clipboard with machine2's clipboard contents:

.. code::

    machine2> grillo clipboard


Limitations
===========

This will work with contents of less than 8KB, and the bandwith is fairly low, around 52bps. So use it to send small files (configs, etc), texts (like commands, an email, an url, etc), or copied text from the clipboard. Don't try to send stuff like a video :)

Usage as a lib
==============

You can also use Grillo from your own Python programs, like this:

.. code:: python

    from grillo import Grillo

    g = Grillo()
    g.send_text("hello world")


Brave vs normal mode
====================

In the default mode, Grillo will use an ACK message to request any packets of a message that haven't been successfully received. 
This helps working in noisy environments. If you are super confident in your quiet environment, or your receiver can't emit 
sounds, you can use ``--brave`` to disable that feature.
