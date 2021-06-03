#!/usr/bin/env python
# encoding: utf-8

import mock
import pytest

from fragmap.load_commits import CommitSelectionError


def run(args):
  with mock.patch('sys.argv',
                  ['dummypath/main.py'] + args):
    import fragmap.main
    try:
      fragmap.main.main()
    except CommitSelectionError:
      pytest.skip("Invalid commit selection")


def test_invalid_arg():
  with pytest.raises(SystemExit):
    run(['--notvalidarg=45654'])


def test_empty_arg():
  run([])


def test_arg_n():
  run(['-n', '2'])


def test_arg_s():
  run(['-s', 'HEAD~4'])


def test_r15():
  run(['-s', 'HEAD~15', '-u', 'HEAD~13'])


def test_no_color():
  run(['--no-color'])


def test_full():
  run(['--full'])


def test_n_no_color_full():
  run(['-n', '2', '--no-color', '--full'])
