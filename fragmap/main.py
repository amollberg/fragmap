#!/usr/bin/env python
# encoding: utf-8
from __future__ import print_function

from fragmap.generate_matrix import Fragmap, Cell, BriefFragmap, ConnectedFragmap
from fragmap.list_hunks import get_diff
from fragmap.parse_patch import PatchParser
from fragmap.web_ui import open_fragmap_page
from fragmap.console_ui import print_fragmap
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
  inspecarg.add_argument('-r', '--range', metavar='COMMITS', action='store', required=False, dest='range_',
                         help='Any range(s) of commits to show. See documentation for git rev-list.')
  inspecarg.add_argument('-n', metavar='NUMBER_OF_COMMITS', action='store',
                         help='How many previous commits to show. Uncommitted changes are shown in addition to these.')
  inspecarg.add_argument('-s', metavar='START_COMMIT', action='store',
                         help='Which commit to start showing from, exclusive.')
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

  args = argparser.parse_args()
  # Parse diffs
  pp = PatchParser()
  if args.import_ and (args.s or args.n or args.range_):
    print('Error: --import/-i cannot be used at the same time as other input specifiers')
    exit(1)
  if args.range_ and (args.s or args.n or args.import_):
    print('Error: --range/-r cannot be used at the same time as other input specifiers')
    exit(1)
  max_count = args.n
  if not (args.range_ or args.s or args.n or args.import_):
    max_count = '3'
  if args.import_:
    lines = [l.rstrip() for l in fileinput.input(args.import_)]
  else:
    lines = get_diff(range_=args.range_, max_count=max_count, start=args.s)
  if lines is None:
    exit(1)
  is_full = args.full or args.web
  debug.get('console').debug(lines)
  diff_list = pp.parse(lines)
  if args.export:
    args.export.write('\n'.join(lines))
  debug.get('console').debug(diff_list)
  fragmap = make_fragmap(diff_list, not is_full, False)
  if args.web:
    open_fragmap_page(fragmap)
  else:
    print_fragmap(fragmap, do_color = not args.no_color)

if __name__ == '__main__':
  main()
