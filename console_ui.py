#!/usr/bin/env python
# encoding: utf-8
#import os
from parse_patch import *
from generate_matrix import *
from list_hunks import get_diff
import debug

NPYSCREEN_AVAILABLE = False
try:
  from curses_ui import *
  NPYSCREEN_AVAILABLE = True
except ImportError:
  print "Curses unavailable; using plain text."

CONSOLE_WIDTH = 80

# TODO: Change name?
def print_hunkogram(diff_list):
  matrix, _ = generate_matrix(diff_list)
  matrix_width = len(matrix[0])
  hash_width = 8
  padded_matrix_width = min(CONSOLE_WIDTH/2, matrix_width)
  max_commit_width = min(CONSOLE_WIDTH/2, CONSOLE_WIDTH - (hash_width + 1 + 1 + padded_matrix_width))
  for r in range(len(matrix)):
    cur_patch = diff_list._patches[r]._header
    commit_msg = cur_patch._message[0] # First row of message
    hash = cur_patch._hash
    # Pad short commit messages
    commit_msg = commit_msg.ljust(max_commit_width, ' ')
    # Truncate long commit messages
    commit_msg = commit_msg[0:min(max_commit_width,len(commit_msg))]
    # Print hash, commit, matrix row
    hash = hash[0:hash_width]
    print hash, commit_msg, ''.join(matrix[r])

def display_hunkogram_screen(diff_list):
  matrix, grouped_node_lines = generate_matrix(diff_list)
  hash_width = 8
  App = HunkogramApp()
  App._diff_list = diff_list
  App._matrix = matrix
  App._grouped_node_lines = grouped_node_lines
  App._console_width = CONSOLE_WIDTH
  App._hash_width = 8
  App.run()


def main():
  pp = PatchParser()
  lines = get_diff('HEAD~4..HEAD')
  debug.log(debug.console, lines)
  diff_list = pp.parse(lines)
  debug.log(debug.console, diff_list)
  if NPYSCREEN_AVAILABLE:
    display_hunkogram_screen(diff_list)
  else:
    print_hunkogram(diff_list)


if __name__ == '__main__':
  debug.parse_args()
  main()
