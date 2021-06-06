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
import os
import unittest

from infrastructure import find_commit_with_message, stage_all_changes, \
  reset_hard
from mock import Mock

import fragmap.debug as debug
from fragmap.generate_matrix import Fragmap, BriefFragmap, CellKind
from fragmap.load_commits import CommitLoader, ExplicitCommitSelection, \
  CommitSelection
from fragmap.spg import FileId

TEST_DIR = os.path.dirname(os.path.realpath(__file__))
DIFF_DIR = os.path.join(TEST_DIR, 'diffs')

debug.set_logging_categories('all')


def read_diff(filename):
  filepath = os.path.join(TEST_DIR, 'diffs', filename)
  with open(filepath) as f:
    lines = [line.rstrip() for line in f]
    return lines


def render_matrix_for_test(matrix):
  n_rows = len(matrix)
  if n_rows == 0:
    return []
  n_cols = len(matrix[0])
  m = [['.' for _ in range(n_cols)] for _ in range(n_rows)]

  def render_cell(cell):
    if cell.kind == CellKind.CHANGE:
      return '#'
    if cell.kind in [CellKind.BETWEEN_CHANGES, CellKind.BETWEEN_SQUASHABLE]:
      return '^'
    if cell.kind == CellKind.NO_CHANGE:
      return '.'
    assert False, "Unexpected cell kind: %s" % (cell.kind)

  for r in range(n_rows):
    for c in range(n_cols):
      m[r][c] = render_cell(matrix[r][c])
  return m


START = 0
END = 1


def MockDiffFile(path):
  return Mock(path=path)


def MockDiffDelta(old_file_path, new_file_path):
  return Mock(old_file=MockDiffFile(old_file_path),
              new_file=MockDiffFile(new_file_path),
              is_binary=False)


def MockDiffLine(content):
  return Mock(content=content)


def MockDiffHunk(old_start_and_lines, new_start_and_lines, mocklines):
  old_start, old_lines = old_start_and_lines
  new_start, new_lines = new_start_and_lines
  return Mock(lines=mocklines,
              old_start=old_start,
              old_lines=old_lines,
              new_start=new_start,
              new_lines=new_lines)


def MockPatch(mockdelta, mockhunks):
  return Mock(delta=mockdelta, hunks=mockhunks)


def MockCommit(hex, message):
  return Mock(hex=hex, message=message)


class Test(unittest.TestCase):
  # Append instead of replace default assertion failure message
  longMessage = True

  def test_016_004(self):
    self.check_diffs(['016-add-one-line-to-empty.txt',
                      '002-rename-empty-file',
                      '004-remove-one-line-empty-file'],
                     ['#',
                      '^',
                      '#'])

  def test_003(self):
    self.check_diff('003-add-one-line-to-empty-file', ['#'])

  def test_004(self):
    self.check_diff('004-remove-one-line-empty-file', ['#'])

  def test_003_004(self):
    files = ['003-add-one-line-to-empty-file',
             '004-remove-one-line-empty-file']
    self.check_diffs(files,
                     ['#',
                      '#'])

  def test_011(self):
    self.check_diff('011-add-x-to-A-and-N', ['##'])

  def test_012(self):
    self.check_diff('012-add-x-to-A-C', ['#'])

  def test_011_012(self):
    self.check_diffs(['011-add-x-to-A-and-N',
                      '012-add-x-to-A-C'],
                     ['#.#',
                      '##.'])

  def test_020(self):
    self.check_diff('020-modfile-create', ['#'])

  def test_021(self):
    self.check_diff('021-modfile-remove-first-line', ['#'])

  def test_020_021(self):
    self.check_diffs(['020-modfile-create',
                      '021-modfile-remove-first-line'],
                     ['##',
                      '#.'])

  def test_022_023(self):
    self.check_diffs(['022-modfile-mod-second-line',
                      '023-modfile-readd-first-line'],
                     ['.#',
                      '#.'])

  def test_030(self):
    self.check_diff('030-addmod-create-with-ab', ['#'])

  def test_030_031(self):
    self.check_diffs(['030-addmod-create-with-ab',
                      '031-addmod-add-c'],
                     ['#.',
                      '.#'])

  def test_030_032(self):
    self.check_diffs(['030-addmod-create-with-ab',
                      '031-addmod-add-c',
                      '032-addmod-change-bc-to-xy'],
                     ['##.',
                      '.^#',
                      '.##'])

  def test_030_033(self):
    self.check_diffs(['030-addmod-create-with-ab',
                      '031-addmod-add-c',
                      '032-addmod-change-bc-to-xy',
                      '033-addmod-add-z-between-xy'],
                     ['###..',
                      '.^^##',
                      '.####',
                      '..#.#'])

  def test_041_042_043(self):
    self.check_diffs(['041-successivemod-mod-ab',
                      '042-successivemod-mod-cd',
                      '043-successivemod-mod-ef'],
                     ['#..',
                      '.#.',
                      '..#'])

  def test_050_054(self):
    self.check_diffs(['050-twofiles-create-a-with-a',
                      '051-twofiles-create-b-with-x',
                      '052-twofiles-add-y-to-b',
                      '053-twofiles-add-z-to-b',
                      '054-twofiles-add-w-to-b'],
                     ['#....',
                      '.#...',
                      '..#..',
                      '...#.',
                      '....#'])

  def test_060_061(self):
    self.check_diffs(['060-binaryfile-added',
                      '061-binaryfile-changed'],
                     ['#',
                      '#'])

  def test_070_072(self):
    self.check_diffs(['070-add-X-to-D',
                      '071-add-X-to-A',
                      '072-add-X-to-F'],
                     ['.#.',
                      '#..',
                      '..#'])

  def test_080(self):
    self.check_diffs(['080-rename-empty-file'],
                     [''])

  # == Test brief fragmaps ==

  def test_016_004_brief(self):
    self.check_diffs_brief(['016-add-one-line-to-empty.txt',
                            '002-rename-empty-file',
                            '004-remove-one-line-empty-file'],
                           ['#',
                            '^',
                            '#'])

  def test_003_brief(self):
    self.check_diff_brief('003-add-one-line-to-empty-file',
                          ['#'])

  def test_004_brief(self):
    self.check_diff_brief('004-remove-one-line-empty-file',
                          ['#'])

  def test_003_004_brief(self):
    self.check_diffs_brief(['003-add-one-line-to-empty-file',
                            '004-remove-one-line-empty-file'],
                           ['#',
                            '#'])

  def test_011_brief(self):
    self.check_diff_brief('011-add-x-to-A-and-N',
                          ['#'])

  def test_012_brief(self):
    self.check_diff_brief('012-add-x-to-A-C',
                          ['#'])

  def test_011_012_brief(self):
    self.check_diffs_brief(['011-add-x-to-A-and-N',
                            '012-add-x-to-A-C'],
                           ['#.#',
                            '##.'])

  def test_020_brief(self):
    self.check_diff_brief('020-modfile-create',
                          ['#'])

  def test_021_brief(self):
    self.check_diff_brief('021-modfile-remove-first-line',
                          ['#'])

  def test_020_021_brief(self):
    self.check_diffs_brief(['020-modfile-create',
                            '021-modfile-remove-first-line'],
                           ['##',
                            '#.'])

  def test_022_023_brief(self):
    self.check_diffs_brief(['022-modfile-mod-second-line',
                            '023-modfile-readd-first-line'],
                           ['.#',
                            '#.'])

  def test_030_brief(self):
    self.check_diff_brief('030-addmod-create-with-ab',
                          ['#'])

  def test_030_031_brief(self):
    self.check_diffs_brief(['030-addmod-create-with-ab',
                            '031-addmod-add-c'],
                           ['#.',
                            '.#'])

  def test_030_032_brief(self):
    self.check_diffs_brief(['030-addmod-create-with-ab',
                            '031-addmod-add-c',
                            '032-addmod-change-bc-to-xy'],
                           ['##.',
                            '.^#',
                            '.##'])

  def test_030_033_brief(self):
    self.check_diffs_brief(['030-addmod-create-with-ab',
                            '031-addmod-add-c',
                            '032-addmod-change-bc-to-xy',
                            '033-addmod-add-z-between-xy'],
                           ['###..',
                            '.^^##',
                            '.####',
                            '..#.#'])

  def test_041_042_043_brief(self):
    self.check_diffs_brief(['041-successivemod-mod-ab',
                            '042-successivemod-mod-cd',
                            '043-successivemod-mod-ef'],
                           ['#..',
                            '.#.',
                            '..#'])

  def test_050_054_brief(self):
    self.check_diffs_brief(['050-twofiles-create-a-with-a',
                            '051-twofiles-create-b-with-x',
                            '052-twofiles-add-y-to-b',
                            '053-twofiles-add-z-to-b',
                            '054-twofiles-add-w-to-b'],
                           ['#....',
                            '.#...',
                            '..#..',
                            '...#.',
                            '....#'])

  def test_070_072_brief(self):
    self.check_diffs_brief(['070-add-X-to-D',
                            '071-add-X-to-A',
                            '072-add-X-to-F'],
                           ['.#.',
                            '#..',
                            '..#'])

  def test_110_111_brief(self):
    self.check_diffs_brief(['110-realdiff-newfilebug-addfile',
                            '111-realdiff-newfilebug-modfile'],
                           ['##',
                            '.#'])

  def test_staged(self):
    self.reset_hard()
    self.staged_change('file.txt', ['hello', 'world', 'new line'])
    self.check_diffs_brief(['Setup',
                            'STAGED',
                            'UNSTAGED'],
                           ['#.',
                            '.#',
                            '..'])

  def test_unstaged(self):
    self.reset_hard()
    self.unstaged_change('file.txt', ['hello', 'world', 'unstaged'])
    self.check_diffs_brief(['Setup',
                            'STAGED',
                            'UNSTAGED'],
                           ['#.',
                            '..',
                            '.#'])

  def test_staged_and_unstaged(self):
    self.reset_hard()
    self.staged_change('file.txt', ['hello', 'world', 'new line'])
    self.unstaged_change('file.txt', ['hello', 'new line'])
    self.check_diffs_brief(['Setup',
                            'STAGED',
                            'UNSTAGED'],
                           ['##.',
                            '.^#',
                            '.#.'])
    self.unstaged_change('file.txt', [''])
    self.check_diffs_brief(['Setup',
                            'STAGED',
                            'UNSTAGED'],
                           ['#.',
                            '^#',
                            '##'])

  # === Tests of file selection ===

  def test_016_004_files(self):
    start = '0e427042'
    self.check_file_selection({FileId(-1, 'empty.txt')}, ['empty.txt'], start)
    self.check_file_selection({FileId(-1, 'empty.txt')}, ['other.txt'], start)
    self.check_file_selection({FileId(-1, 'empty.txt')}, None, start)
    self.check_file_selection(set(), ['non-existent-file.txt'], start)

  def test_050_054_files(self):
    start = '0e427042'
    self.check_file_selection({FileId(-1, 'file_a.txt')}, ['file_a.txt'], start)
    self.check_file_selection({FileId(0, 'file_b.txt')}, ['file_b.txt'], start)
    self.check_file_selection({FileId(0, 'file_b.txt'),
                               FileId(-1, 'file_a.txt')}, None, start)

  # === Exception tests on more complex commits ===

  def test_1622573011(self):
    self.check_no_exceptions(['Prepare for smarter propagation',
                              'WIP: add_and_propagate',
                              'Format graph.py'])

  # === Helper functions ===

  def unstaged_change(self, filename, lines):
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    file_path = os.path.join(repo_path, filename)
    with open(file_path, 'w', newline='\n') as f:
      for line in lines:
        print("to file", file_path, "writing '", line, "'")
        f.write(line + '\n')

  def staged_change(self, filename, lines):
    self.unstaged_change(filename, lines)
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    stage_all_changes(repo_path)

  def reset_hard(self):
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    reset_hard(repo_path)

  def check_diff(self, commit_message, matrix):
    cl = CommitLoader()
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    commit_hex = find_commit_with_message(repo_path, commit_message)
    diffs = cl.load(repo_path, ExplicitCommitSelection([commit_hex]))
    h = Fragmap.from_diffs(diffs)
    actual_matrix = h.generate_matrix()
    self.check_matrix(render_matrix_for_test(actual_matrix), matrix)

  def check_diff_brief(self, commit_message, matrix):
    cl = CommitLoader()
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    commit_hex = find_commit_with_message(repo_path, commit_message)
    diffs = cl.load(repo_path, ExplicitCommitSelection([commit_hex]))
    h = BriefFragmap(Fragmap.from_diffs(diffs))
    actual_matrix = h.generate_matrix()
    self.check_matrix(render_matrix_for_test(actual_matrix), matrix)

  def check_diffs(self, commit_messages, matrix):
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    commit_hexes = [find_commit_with_message(repo_path, commit_message)
                    for commit_message in commit_messages]
    cl = CommitLoader()
    diffs = cl.load(repo_path, ExplicitCommitSelection(commit_hexes))
    h = Fragmap.from_diffs(diffs)
    actual_matrix = h.generate_matrix()
    self.check_matrix(render_matrix_for_test(actual_matrix), matrix)

  def check_diffs_brief(self, commit_messages, matrix):
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    commit_hexes = [find_commit_with_message(repo_path, commit_message)
                    for commit_message in commit_messages]
    cl = CommitLoader()
    diffs = cl.load(repo_path, ExplicitCommitSelection(commit_hexes))
    h = BriefFragmap(Fragmap.from_diffs(diffs))
    actual_matrix = h.generate_matrix()
    self.check_matrix(render_matrix_for_test(actual_matrix), matrix)

  def check_matrix(self, matrix, reference):
    joined_matrix = '\n'.join([''.join(row) for row in matrix])
    reference = '\n'.join(reference)
    debug.get('test').debug("Actual: \n%s \nReference: \n%s", joined_matrix,
                            reference)
    self.assertEqual(joined_matrix, reference)

  def check_no_exceptions(self, commit_messages):
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    commit_hexes = [find_commit_with_message(repo_path, commit_message)
                    for commit_message in commit_messages]
    cl = CommitLoader()
    diffs = cl.load(repo_path, ExplicitCommitSelection(commit_hexes))
    h = BriefFragmap(Fragmap.from_diffs(diffs))
    h.generate_matrix()

  def check_file_selection(self, expected_ids, file_arg, start_commit):
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    cl = CommitLoader()
    all_commits_in_repo = CommitSelection(start_commit, None, 999, True, True)
    diffs = cl.load(repo_path, all_commits_in_repo)
    h = Fragmap.from_diffs(diffs, file_arg)
    self.assertEqual(set(h.spgs.keys()), expected_ids)
