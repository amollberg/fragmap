#!/usr/bin/env python
# encoding: utf-8
from __future__ import print_function

from fragmap.generate_matrix import Fragmap, Cell, BriefFragmap, ConnectedFragmap
from fragmap.list_hunks import get_diff
from fragmap.parse_patch import PatchParser
from fragmap.web_ui import open_fragmap_page
from console_color import *
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

def make_fragmap(diff_list, brief=False, infill=False):
  fragmap = Fragmap.from_ast(diff_list)
  if brief:
    fragmap = BriefFragmap.group_by_patch_connection(fragmap)
  if infill:
    fragmap = ConnectedFragmap(fragmap)
  return fragmap

# TODO: Change name?
def print_fragmap(fragmap, do_color):
  matrix = fragmap.generate_matrix()
  matrix = fragmap.render_for_console(do_color)
  matrix_width = len(matrix[0])
  hash_width = 8
  padded_matrix_width = matrix_width
  max_commit_width = min(CONSOLE_WIDTH/2, CONSOLE_WIDTH - (hash_width + 1 + 1 + padded_matrix_width))
  def infill_r(matrix, print_text_action, print_matrix_action):
    r = 0
    for i in xrange(len(matrix)):
      r = i / 3
      if i % 3 == 1:
        print_text_action(r)
      else:
        print(''.ljust(hash_width + 1 + max_commit_width + 1), end='')
      print_matrix_action(i)
  def normal_r(matrix, print_text_action, print_matrix_action):
    for r in xrange(len(matrix)):
      print_text_action(r)
      print_matrix_action(r)
  # Draw the text and matrix
  def print_line(r):
    cur_patch = fragmap.patches[r]._header
    commit_msg = cur_patch._message[0] # First row of message
    hash = cur_patch._hash
    # Pad short commit messages
    commit_msg = commit_msg.ljust(max_commit_width, ' ')
    # Truncate long commit messages
    commit_msg = commit_msg[0:min(max_commit_width,len(commit_msg))]
    # Print hash, commit, matrix row
    hash = hash[0:hash_width]
    if do_color:
      hash = ANSI_FG_CYAN + hash + ANSI_RESET
    print(hash, commit_msg, end='')

  def print_matrix(r):
    print(''.join(matrix[r]))

  if isinstance(fragmap, ConnectedFragmap):
    infill_r(matrix, print_line, print_matrix)
  else:
    normal_r(matrix, print_line, print_matrix)


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
  argparser.add_argument('--no-color', action='store_true', required=False,
                         help='Disable color coding of the output.')
  outformatarg = argparser.add_mutually_exclusive_group(required=False)
  argparser.add_argument('-f', '--full', action='store_true', required=False,
                         help='Show the full fragmap, disabling deduplication of the columns.')
  outformatarg.add_argument('-w', '--web', action='store_true', required=False,
                            help='Generate and open an HTML document instead of printing to console. Implies -f')
  outformatarg.add_argument('-c', '--curses-ui', action='store_true', required=False,
                            help='Show an interactive curses-based interface instead of plain text.')
  outformatarg.add_argument('-l', '--infilled', action='store_true', required=False,
                            help='Show an infilled version as plain text on console. Looks like the HTML version. Implies -f')

  args = argparser.parse_args()
  # Parse diffs
  pp = PatchParser()
  lines = get_diff(max_count=args.n, start=args.s)
  if lines is None:
    exit(1)
  is_full = args.full or args.web or args.infilled
  debug.get('console').debug(lines)
  diff_list = pp.parse(lines)
  debug.get('console').debug(diff_list)
  fragmap = make_fragmap(diff_list, not is_full, args.infilled)
  if args.curses_ui:
    if NPYSCREEN_AVAILABLE:
      display_fragmap_screen(fragmap)
    else:
      print("Curses unavailable; using plain text.")
      print_fragmap(fragmap, do_color = not args.no_color)
  elif args.web:
    open_fragmap_page(fragmap)
  else:
    print_fragmap(fragmap, do_color = not args.no_color)

if __name__ == '__main__':
  main()
