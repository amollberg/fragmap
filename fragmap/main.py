#!/usr/bin/env python
# encoding: utf-8
from __future__ import print_function

from fragmap.generate_matrix import Fragmap, Cell, BriefFragmap, ConnectedFragmap
from fragmap.list_hunks import get_diff
from fragmap.parse_patch import PatchParser
from fragmap.web_ui import open_fragmap_page
from fragmap.console_ui import print_fragmap, display_fragmap_screen, NPYSCREEN_AVAILABLE
import debug

import argparse
import copy
import os
import fileinput

def make_fragmap(diff_list, brief=False, infill=False):
  fragmap = Fragmap.from_ast(diff_list)
  if brief:
    fragmap = BriefFragmap.group_by_patch_connection(fragmap)
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
  argparser.add_argument('-n', metavar='NUMBER_OF_REVS', action='store',
                         help='How many previous revisions to show. Uncommitted changes are shown in addition to these.')
  argparser.add_argument('-s', metavar='START_REV', action='store',
                         help='Which revision to start showing from.')
  inspecarg.add_argument('-i', '--import', metavar='FILENAME', action='store', required=False, dest='import_',
                         help='Import the patch contents from a file or stdin (-)')
  argparser.add_argument('--no-color', action='store_true', required=False,
                         help='Disable color coding of the output.')
  argparser.add_argument('-o', '--export', metavar='FILENAME', type=argparse.FileType('w'), action='store', required=False,
                         help='Export the contents of the current selection of commits to the selected file')
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
  if args.import_ and (args.s or args.n):
    print('Error: --import/-i cannot be used at the same time as other input specifiers')
    exit(1)
  if args.import_:
    lines = [l.rstrip() for l in fileinput.input(args.import_)]
  else:
    lines = get_diff(max_count=args.n, start=args.s)
  if lines is None:
    exit(1)
  is_full = args.full or args.web or args.infilled
  debug.get('console').debug(lines)
  diff_list = pp.parse(lines)
  if args.export:
    args.export.write('\n'.join(lines))
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
