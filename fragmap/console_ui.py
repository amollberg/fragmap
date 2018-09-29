#!/usr/bin/env python
# encoding: utf-8

from fragmap.generate_matrix import Fragmap
from fragmap.list_hunks import get_diff
from fragmap.parse_patch import PatchParser
from fragmap.web_ui import open_fragmap_page
import debug

import argparse
import copy
import os

NPYSCREEN_AVAILABLE = False
try:
  from fragmap.curses_ui import FragmapApp
  NPYSCREEN_AVAILABLE = True
except ImportError:
  pass

CONSOLE_WIDTH = 80

def make_fragmap(diff_list, brief=False):
  fragmap = Fragmap.from_ast(diff_list)
  if brief:
    fragmap = fragmap.group_by_patch_connection()
  return fragmap

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
def print_fragmap(fragmap, do_decorate=False):
  matrix = fragmap.generate_matrix()
  matrix_width = len(matrix[0])
  hash_width = 8
  padded_matrix_width = matrix_width
  max_commit_width = min(CONSOLE_WIDTH/2, CONSOLE_WIDTH - (hash_width + 1 + 1 + padded_matrix_width))
  if do_decorate:
    # Colorize the matrix
    matrix = decorate_matrix(matrix)
  # Draw the text and matrix
  for r in range(len(matrix)):
    cur_patch = fragmap.patches[r]._header
    commit_msg = cur_patch._message[0] # First row of message
    hash = cur_patch._hash
    # Pad short commit messages
    commit_msg = commit_msg.ljust(max_commit_width, ' ')
    # Truncate long commit messages
    commit_msg = commit_msg[0:min(max_commit_width,len(commit_msg))]
    # Print hash, commit, matrix row
    hash = hash[0:hash_width]
    if do_decorate:
      hash = ANSI_FG_CYAN + hash + ANSI_RESET
    print hash, commit_msg, ''.join(matrix[r])

def display_fragmap_screen(fragmap):
  hash_width = 8
  App = FragmapApp()
  App._fragmap = fragmap
  App._console_width = CONSOLE_WIDTH
  App._hash_width = hash_width
  App.run()

def main():
  if 'FRAGMAP_DEBUG' in os.environ:
    debug_parser = debug.parse_args(extendable=True)
    parent_parsers = [debug_parser]
  else:
    parent_parsers = []

  # Parse command line arguments
  argparser = argparse.ArgumentParser(prog='fragmap',
                                      description='Visualize a timeline of Git commit changes on a grid',
                                      parents=parent_parsers)
  argparser.add_argument('-n', metavar='NUMBER_OF_REVS', action='store',
                         help='How many previous revisions to show. Uncommitted changes are shown in addition to these.')
  argparser.add_argument('-s', metavar='START_REV', action='store',
                         help='Which revision to start showing from.')
  argparser.add_argument('-f', '--full', action='store_true', required=False,
                         help='Show the full fragmap, disabling deduplication of the columns.')
  argparser.add_argument('--no-decoration', action='store_true', required=False,
                         help='Disable color coding of the output.')
  outformatarg = argparser.add_mutually_exclusive_group(required=False)
  outformatarg.add_argument('-w', '--web', action='store_true', required=False,
                            help='Generate and open an HTML document instead of printing to console')
  outformatarg.add_argument('-c', '--curses-ui', action='store_true', required=False,
                            help='Show an interactive curses-based interface instead of plain text.')

  args = argparser.parse_args()
  # Parse diffs
  pp = PatchParser()
  lines = get_diff(max_count=args.n, start=args.s)
  if lines is None:
    exit(1)
  debug.get('console').debug(lines)
  diff_list = pp.parse(lines)
  debug.get('console').debug(diff_list)
  fragmap = make_fragmap(diff_list, not args.full)
  if args.curses_ui:
    if NPYSCREEN_AVAILABLE:
      display_fragmap_screen(fragmap)
    else:
      print "Curses unavailable; using plain text."
      print_fragmap(fragmap, do_decorate = not args.no_decoration)
  elif args.web:
    open_fragmap_page(fragmap)
  else:
    print_fragmap(fragmap, do_decorate = not args.no_decoration)

if __name__ == '__main__':
  main()
