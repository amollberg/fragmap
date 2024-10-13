#!/usr/bin/env python
# encoding: utf-8

import os

from setuptools import setup, find_packages


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "fragmap",
    version = "0.4.3",
    author = "Alexander Mollberg",
    author_email = "amollberg@users.noreply.github.com",
    description = ("Visualize a timeline of Git commit changes on a grid"),
    license = "BSD",
    keywords = "git visualization console terminal",
    url = "https://github.com/amollberg/fragmap",
    packages=find_packages(),
    long_description=read('README.md'),
    python_requires='>=3.7',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Version Control",
        "Environment :: Console",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
    install_requires=["pygit2>=0.28.1",
                      "yattag==1.10.0",
                      "backports.shutil_get_terminal_size>=1.0.0"],
    tests_require=read("requirements-dev.txt"),
    entry_points={
        'console_scripts': ['fragmap=fragmap.main:main'],
    },
)
