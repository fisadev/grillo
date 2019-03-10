#!/usr/bin/env python3
import os.path
from setuptools import setup, find_packages


setup(
    name="GrilloModem",
    version='1.2.3',
    author="Juan Pedro Fisanotti",
    author_email="fisadev@gmail.com",
    license="GPLv3",
    description=("A small tool to easily send data (files, clipboard) between computers with 0 "
                 "config, just using audio and mic."),
    long_description=open("README.rst").read(),
    keywords=["audio", "modem", "clipboard", "transfer"],
    packages=find_packages(exclude=["tests"]),
    url="https://github.com/fisadev/grillo",
    entry_points={
        'console_scripts': ['grillo=grillo.cli:main'],
    },
    install_requires=[
        "chirpsdk",
        "pyperclip",
        "docopt",
        "termcolor",
        "traitlets",  # dependency of chirp, but missing in their requirements
    ],
)
