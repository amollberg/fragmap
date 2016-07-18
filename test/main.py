#!/usr/bin/env python


import unittest
import os
import sys
TEST_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(TEST_DIR, '..'))
from parse_patch import *
from generate_matrix import *

def read_diff(filename):
  filepath = os.path.join(TEST_DIR, 'diffs', filename)
  with open(filepath) as f:
    lines = [line.rstrip() for line in f]
    return lines


class Test(unittest.TestCase):

  def test_003(self):
    self.check_diff('003-add-one-line-to-empty-file.diff', ['#.'])

  def test_004(self):
    self.check_diff('004-remove-one-line-empty-file.diff', ['.'])

  def test_003_004(self):
    self.check_diffs(['003-add-one-line-to-empty-file.diff',
                      '004-remove-one-line-empty-file.diff'], 
                     ['#.',
                      '..'])

  def test_011(self):
    self.check_diff('011-add-x-to-A-and-N.diff', ['#.#.'])

  def test_012(self):
    self.check_diff('012-add-x-to-A-C.diff', ['#.'])

  def test_011_012(self):
    self.check_diffs(['011-add-x-to-A-and-N.diff', 
                      '012-add-x-to-A-C.diff'],
                     ['#..#.', 
                      '##...'])
    

  def check_diff(self, diff_filename, matrix):
    diff = read_diff(diff_filename)
    pp = PatchParser()
    actual_matrix = generate_matrix(pp.parse(diff))
    self.check_matrix(actual_matrix, matrix)

  def check_diffs(self, diff_filenames, matrix):
    diff = []
    for fn in diff_filenames:
      diff += read_diff(fn)
    pp = PatchParser()
    actual_matrix = generate_matrix(pp.parse(diff))
    self.check_matrix(actual_matrix, matrix)

    
  def check_matrix(self, matrix, reference):
    joined_matrix = [''.join(row) for row in matrix]
    self.assertEqual(joined_matrix, reference)

            
if __name__ == '__main__':
  unittest.main()
