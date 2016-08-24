# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='dorkbox',
    version='0.1.dev0',
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
            "dorkbox=dorkbox.cmdline:cmdline"
        ]
    }
)
