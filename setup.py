# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
from os import environ

# this smells, but I don't know how to do better than this right now.
VERSION=environ.get("VERSION") or "0.99.dev0"

setup(
    name='foolscrate',
    version=VERSION,
    packages=find_packages(),
    license='Apache License 2.0',
    long_description="Stupid git-based file synchronized",
    install_requires=[
        "configobj",
        "filelock",
        "click"
    ],
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "unit=unittest.__main__:main",
            "foolscrate=foolscrate.cmdline:cmdline"
        ]
    }
)
