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
            "foolscrate=foolscrate.cmdline:cmdline",
            # the following target is actually employed from the installed environment,
            # since it's location independent.
            "run_all_tests=foolscrate.test.run:run_all_tests",
            # this is used during development because it makes it easier to selectively choose
            # which tests we should run
            "unit=unittest.__main__:main",
        ]
    }
)
