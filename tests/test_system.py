#!/usr/bin/env python

import pytest
import mock


def run(args):
  with mock.patch('sys.argv',
                  ['dummypath/main.py'] + args):
    import common
    import fragmap.main
    fragmap.main.main()

def test_invalid_arg():
  with pytest.raises(SystemExit):
    run(['--notvalidarg=45654'])

def test_empty_arg():
  run([])

def test_arg_n():
  run(['-n', '2'])

def test_arg_s():
  run(['-s', 'master'])

def test_r15():
  run(['-r', 'HEAD~15..HEAD~13'])

def test_no_color():
  run(['--no-color'])

def test_full():
  run(['--full'])

def test_import_export():
  import tempfile
  import os.path
  tempfilename = os.path.join(tempfile.gettempdir(), "fragmap-test-import-export.txt")
  run(['-o', tempfilename])
  run(['-i', tempfilename])

def test_n_no_color_full():
  run(['-n', '2', '--no-color', '--full'])
