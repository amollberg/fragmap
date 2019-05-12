# git fragmap - better commit visualization for git

# Install
After installing the requirements (see below), simply run:

    pip install fragmap

# Requirements

- Git

- Python 2.7

# Develop fragmap

- Uninstall any existing versions of fragmap

- Clone this repo

- Run `pip install -r requirements.txt` to install all requirements

- Run `pip install -r requirements-dev.txt` to be able to run the test suite

- Run `python setup.py develop`

- Run `python update_tests.py`. This also needs to be run if you make changes to any repo under `tests/diffs/`

- (Optional) Define the environment variable `FRAGMAP_DEBUG` to get access to the `--log` argument.

# Autocompletion

- Clone this repo

- Source `bash_completion.sh` in the cloned directory
