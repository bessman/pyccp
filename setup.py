#!/bin/env python

from setuptools import setup, find_packages


setup(
    name="pyccp",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-can",
        "cantools",
    ],
    description="CAN Calibration Protocol for Python",
    author="Alexander Bessman",
    author_email="alexander.bessman@gmail.com",
    url="http://github.com/bessman/pyccp",
    python_requires=">=3.6",
    license="LGPLv3",
)
