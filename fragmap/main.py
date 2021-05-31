#!/usr/bin/env python
# encoding: utf-8


from fragmap.generate_matrix import Fragmap, Cell, BriefFragmap, \
  ConnectedFragmap, Fragmap, BriefFragmap
from fragmap.web_ui import open_fragmap_page, start_fragmap_server
from fragmap.console_ui import print_fragmap
from fragmap.console_color import ANSI_UP
from fragmap.load_commits import CommitSelection, CommitLoader
from . import debug

import argparse
import copy
import os
import fileinput
from getch.getch import getch

import json

def make_fragmap(diff_list, brief=False, infill=False) -> Fragmap:
  fragmap = Fragmap.from_diffs(diff_list)
  # with open('fragmap_ast.json', 'wb') as f:
  #   json.dump(fragmap.patches, f, cls=DictCoersionEncoder)
  if brief:
    fragmap = BriefFragmap(fragmap)
  if infill:
    fragmap = ConnectedFragmap(fragmap)
  return fragmap

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
  inspecarg = argparser.add_argument_group('input', 'Specify the input commits or patch file')
  inspecarg.add_argument('-u', '--until', metavar='END_COMMIT', action='store', required=False, dest='until',
                         help='Which commit to show until, inclusive.')
  inspecarg.add_argument('-n', metavar='NUMBER_OF_COMMITS', action='store',
                         help='How many previous commits to show. Uncommitted changes are shown in addition to these.')
  inspecarg.add_argument('-s', '--since', metavar='START_COMMIT', action='store',
                         help='Which commit to start showing from, exclusive.')
  argparser.add_argument('--no-color', action='store_true', required=False,
                         help='Disable color coding of the output.')
  argparser.add_argument('-l', '--live', action='store_true', required=False,
                         help='Keep running and enable refreshing of the displayed fragmap')
  outformatarg = argparser.add_mutually_exclusive_group(required=False)
  argparser.add_argument('-f', '--full', action='store_true', required=False,
                         help='Show the full fragmap, disabling deduplication of the columns.')
  outformatarg.add_argument('-w', '--web', action='store_true', required=False,
                            help='Generate and open an HTML document instead of printing to console. Implies -f')

  args = argparser.parse_args()
  # Load commits
  cl = CommitLoader()
  if args.until and not args.since:
    print('Error: --since/-s must be used if --until/-u is used')
    exit(1)
  max_count = None
  if args.n:
    max_count = int(args.n)
  if not (args.until or args.since or args.n):
    max_count = 3
  lines_printed = [0]
  columns_printed = [0]
  def serve():
    def erase_current_line():
      print('\r' + ' ' * columns_printed[0] + '\r', end='')
    # Make way for status updates from below operations
    erase_current_line()
    selection = CommitSelection(since_ref=args.since,
                                until_ref=args.until,
                                max_count=max_count,
                                include_staged=not args.until,
                                include_unstaged=not args.until)
    is_full = args.full or args.web
    debug.get('console').debug(selection)
    diff_list = cl.load(os.getcwd(), selection)
    debug.get('console').debug(diff_list)
    # Erase each line and move cursor up to overwrite previous fragmap
    erase_current_line()
    for i in range(lines_printed[0]):
      print(ANSI_UP, end='')
      erase_current_line()
    print('... Generating fragmap\r', end='')
    fm = make_fragmap(diff_list, not is_full, False)
    print('                      \r', end='')
    return fm
  fragmap = serve()
  if args.web:
    if args.live:
      start_fragmap_server(serve)
    else:
      open_fragmap_page(fragmap, args.live)
  else:
    lines_printed[0], columns_printed[0] = print_fragmap(fragmap, do_color = not args.no_color)
    if args.live:
      while True:
        print('Press Enter to refresh', end='')
        import sys
        key = getch()
        if ord(key) != 0xd:
          break
        fragmap = serve()
        lines_printed[0], columns_printed[0] = print_fragmap(fragmap, do_color = not args.no_color)
      print('')




if __name__ == '__main__':
  main()
