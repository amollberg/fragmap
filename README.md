# git hunkogram - better commit visualization for git


# Requirements

npyscreen, which requires curses. For Windows curses can be obtained precompiled from http://www.lfd.uci.edu/~gohlke/pythonlibs/#curses
Install using pip, example:

    pip install curses-2.2-cp27-none-win_amd64.whl

Npyscreen itself has to be built from the included npyscreen/ directory, as we
require some non-standard functionality that has been patched into this directory.
Simply do:

    cd npyscreen/
    python setup.py install