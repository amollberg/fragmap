#!/usr/bin/env python
# encoding: utf-8
#import os
from parse_patch import *
from generate_matrix import *
from list_hunks import get_diff, get_rev_range_from_args
import debug
import argparse
import copy

NPYSCREEN_AVAILABLE = False
try:
  from curses_ui import *
  NPYSCREEN_AVAILABLE = True
except ImportError:
  print "Curses unavailable; using plain text."

CONSOLE_WIDTH = 80

def make_hunkogram(diff_list, brief=False):
  hunkogram = Hunkogram.from_ast(diff_list)
  if brief:
    hunkogram = hunkogram.group_by_patch_connection()
  return hunkogram

ANSI_ESC = '\033'
ANSI_FG_RED = ANSI_ESC + '[31m'
ANSI_BG_RED = ANSI_ESC + '[41m'
ANSI_BG_WHITE = ANSI_ESC + '[47m'
ANSI_FG_CYAN = ANSI_ESC + '[36m'
ANSI_RESET = ANSI_ESC + '[0m'

def decorate_matrix(matrix):
  m = copy.deepcopy(matrix)
  n_rows = len(m)
  if n_rows == 0:
    return m
  n_cols = len(m[0])

  # Mark dots between conflicts
  last_patch = [-1] * n_cols
  for r in range(n_rows):
    for c in range(n_cols):
      cell = m[r][c]
      if cell == '#':
        if last_patch[c] >= 0:
          # Mark the cells inbetween
          start = last_patch[c]
          end = r
          for i in range(start, end + 1):
            # If not yet decorated
            if m[i][c] == '.':
              # Make background red
              m[i][c] = ANSI_BG_RED + ' ' + ANSI_RESET
        last_patch[c] = r
  # Turn # into white squares
  for r in range(n_rows):
    for c in range(n_cols):
      cell = m[r][c]
      if cell == '#':
        # Make background white
        m[r][c] = ANSI_BG_WHITE + ' ' + ANSI_RESET
  return m


# TODO: Change name?
def print_hunkogram(hunkogram, do_decorate=False):
  matrix = hunkogram.generate_matrix()
  matrix_width = len(matrix[0])
  hash_width = 8
  padded_matrix_width = min(CONSOLE_WIDTH/2, matrix_width)
  max_commit_width = min(CONSOLE_WIDTH/2, CONSOLE_WIDTH - (hash_width + 1 + 1 + padded_matrix_width))
  if do_decorate:
    # Colorize the matrix
    matrix = decorate_matrix(matrix)
  # Draw the text and matrix
  for r in range(len(matrix)):
    cur_patch = hunkogram.patches[r]._header
    commit_msg = cur_patch._message[0] # First row of message
    hash = cur_patch._hash
    # Pad short commit messages
    commit_msg = commit_msg.ljust(max_commit_width, ' ')
    # Truncate long commit messages
    commit_msg = commit_msg[0:min(max_commit_width,len(commit_msg))]
    # Print hash, commit, matrix row
    hash = hash[0:hash_width]
    print ANSI_FG_CYAN + hash + ANSI_RESET, commit_msg, ''.join(matrix[r])

def display_hunkogram_screen(hunkogram):
  hash_width = 8
  App = HunkogramApp()
  App._hunkogram = hunkogram
  App._console_width = CONSOLE_WIDTH
  App._hash_width = hash_width
  App.run()

def main(parent_argparser):
  # Parse command line arguments
  argparser = argparse.ArgumentParser(parents=[parent_argparser])
  argparser.add_argument('-p', '--plain', action='store_true', required=False)
  argparser.add_argument('-b', '--brief', action='store_true', required=False)
  argparser.add_argument('--no-decoration', action='store_true', required=False)
  args, unknown_args = argparser.parse_known_args()
  # Parse diffs
  pp = PatchParser()
  lines = get_diff(get_rev_range_from_args())
  debug.log(debug.console, lines)
  diff_list = pp.parse(lines)
  debug.log(debug.console, diff_list)
  hunkogram = make_hunkogram(diff_list, args.brief)
  if not args.plain and NPYSCREEN_AVAILABLE:
    display_hunkogram_screen(hunkogram)
  else:
    print_hunkogram(hunkogram, do_decorate = not args.no_decoration)

if __name__ == '__main__':
  debug_parser = debug.parse_args(extendable=True)
  main(debug_parser)
