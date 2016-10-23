# git fragmap - better commit visualization for git

# Install
After installing the requirements (see below), simply run:

    pip install fragmap

# Requirements

- Git

- Python 2.7

- Curses (required by npyscreen). For Windows curses can be obtained precompiled from http://www.lfd.uci.edu/~gohlke/pythonlibs/#curses
Install using pip, example:

    `pip install curses-2.2-cp27-none-win_amd64.whl`

Npyscreen itself will be installed automatically as a dependency by pip. Note that a custom version compiled for this
application is required as we require some non-standard functionality.

# Develop fragmap

- Uninstall any existing versions of fragmap

- Clone this repo

- Run `python setup.py develop`

- (Optional) Define the environment variable `FRAGMAP_DEBUG` to get access to the `--log` argument.
