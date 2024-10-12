#!/usr/bin/env python
# encoding: utf-8
# Copyright 2016-2021 Alexander Mollberg
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import os
import sys

from fragmap.console_color import ANSI_UP
from fragmap.console_ui import print_fragmap
from fragmap.file_selection import FileSelection
from fragmap.generate_matrix import ConnectedFragmap, Fragmap, BriefFragmap
from fragmap.load_commits import CommitSelection, CommitLoader
from fragmap.web_ui import open_fragmap_page, start_fragmap_server
from getch.getch import getch
from . import debug


def make_fragmap(diff_list, files_arg, brief=False, infill=False) -> Fragmap:
  fragmap = Fragmap.from_diffs(diff_list, files_arg)
  # with open('fragmap_ast.json', 'wb') as f:
  #   json.dump(fragmap.patches, f, cls=DictCoersionEncoder)
  if brief:
    fragmap = BriefFragmap(fragmap)
  if infill:
    fragmap = ConnectedFragmap(fragmap)
  return fragmap

def disable_owner_validation():
  import pygit2
  try:
    pygit2.option(pygit2.enums.Option.SET_OWNER_VALIDATION, False)
  except AttributeError:
    pass

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
  inspecarg = argparser.add_argument_group('input',
                                           'Specify the input commits or patch file')
  inspecarg.add_argument('-u', '--until', metavar='END_COMMIT', action='store',
                         required=False, dest='until',
                         help='Which commit to show until, inclusive.')
  inspecarg.add_argument('-n', metavar='NUMBER_OF_COMMITS', action='store',
                         help='How many previous commits to show. Uncommitted changes are shown in addition to these.')
  inspecarg.add_argument('-s', '--since', metavar='START_COMMIT',
                         action='store',
                         help='Which commit to start showing from, exclusive.')
  argparser.add_argument('--no-color', action='store_true', required=False,
                         help='Disable color coding of the output.')
  argparser.add_argument('-d','--no-owner-validation', action='store_true', required=False,
                         help='Disable checking that the repository is owned by the current user.')
  argparser.add_argument('-l', '--live', action='store_true', required=False,
                         help='Keep running and enable refreshing of the displayed fragmap')
  outformatarg = argparser.add_mutually_exclusive_group(required=False)
  argparser.add_argument('-f', '--full', action='store_true', required=False,
                         help='Show the full fragmap, disabling deduplication of the columns.')
  outformatarg.add_argument('-w', '--web', action='store_true', required=False,
                            help='Generate and open an HTML document instead of printing to console. Implies -f')
  argparser.add_argument('-i', '--files', metavar='FILE',
                         nargs='+', action='store', required=False,
                         dest='files', help="Which files to show changes "
                                            "from. The default is all files.")

  args = argparser.parse_args()
  if args.no_owner_validation:
    disable_owner_validation()

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
    print('... Generating fragmap\r', end='')
    fm = make_fragmap(diff_list, args.files, not is_full, False)
    print('                      \r', end='')
    # Erase each line and move cursor up to overwrite previous fragmap
    erase_current_line()
    for i in range(lines_printed[0]):
      print(ANSI_UP, end='')
      erase_current_line()
    return fm

  fragmap = serve()
  if args.web:
    if args.live:
      start_fragmap_server(serve)
    else:
      open_fragmap_page(fragmap, args.live)
  else:
    lines_printed[0], columns_printed[0] = print_fragmap(fragmap,
                                                         do_color=not args.no_color)
    if args.live:
      while True:
        print('Press Enter to refresh', end='')
        sys.stdout.flush()
        key = getch()
        if ord(key) != 0xd:
          break
        fragmap = serve()
        lines_printed[0], columns_printed[0] = print_fragmap(fragmap,
                                                             do_color=not args.no_color)
      print('')


if __name__ == '__main__':
  main()
