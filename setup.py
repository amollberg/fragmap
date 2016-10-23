#!/usr/bin/env python
import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "fragmap",
    version = "0.1.1",
    author = "Alexander Mollberg",
    author_email = "amollberg@users.noreply.github.com",
    description = ("Visualize a timeline of Git commit changes on a grid"),
    license = "BSD",
    keywords = "git visualization console terminal",
    url = "https://github.com/amollberg/fragmap",
    packages=['fragmap', 'fragmap/test'],
    long_description=read('README.md'),
    classifiers=[
        "Topic :: Software Development :: Version Control",
        "Environment :: Console",
        "Environment :: Console :: Curses",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
    install_requires=["npyscreen==4.9.1.dev99"],
    dependency_links=[
        "git+https://github.com/amollberg/npyscreen.git@6e219e47c760f060d5dc4209056389c69592ed59#egg=npyscreen-4.9.1.dev99"
    ],
    entry_points={
        'console_scripts': ['fragmap=fragmap.console_ui:main'],
    },
)
