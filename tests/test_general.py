#!/usr/bin/env python

from fragmap.commitdiff import CommitDiff
from fragmap.load_commits import CommitLoader, ExplicitCommitSelection
from fragmap.update_fragments import update_inherited_bound, update_new_bound, update_positions, update_all_positions_to_latest
from fragmap.update_fragments import update_inherited_bound, update_new_bound, update_normal_line, update_positions, update_all_positions_to_latest
from fragmap.update_fragments import FragmentBoundNode, FragmentDualBoundNode, FragmentBoundLine
from fragmap.generate_matrix import Cell, Fragmap, BriefFragmap, group_by_file, new_group_fragment_bound_lines, to_separate_lines
from infrastructure import find_commit_with_message, stage_all_changes, reset_hard
import fragmap.debug as debug

import unittest
from mock import Mock
import os
import pprint

TEST_DIR = os.path.dirname(os.path.realpath(__file__))
DIFF_DIR = os.path.join(TEST_DIR, 'diffs')

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
    if cell.kind == Cell.CHANGE:
      return '#'
    if cell.kind == Cell.BETWEEN_CHANGES:
      return '^'
    if cell.kind == Cell.NO_CHANGE:
      return '.'
    assert False, "Unexpected cell kind: %s" %(cell.kind)

  for r in range(n_rows):
    for c in range(n_cols):
      m[r][c] = render_cell(matrix[r][c])
  return m

START = FragmentBoundNode.START
END = FragmentBoundNode.END

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

class FakeFileNode():
  def __init__(self, diff_i, filename):
    self._diff_i = diff_i
    self._filename = filename
  def __repr__(self):
    return str((self._diff_i, self._filename))

class FakeNode():
  def __init__(self, diff_i, line, kind):
    self._diff_i = diff_i
    self._filename = 'dummy'
    self._line = line
    self._kind = kind
  def __repr__(self):
    return str(('FakeNode', self._diff_i, self._filename,
                self._line, self._kind))
class FakeLine():
  def __init__(self, *nodes):
    self._nodehistory = {node._diff_i : node
                         for node in nodes}
  def __repr__(self):
    return str(('FakeLine', self._nodehistory))



class Test(unittest.TestCase):

  # Append instead of replace default assertion failure message
  longMessage = True

  def test_update_normal_line_create_at_beginning(self):
    fragment = MockDiffHunk((0,0), (1,1), [])

    # Subsequent lines shifted
    self.assertEqual(update_normal_line(1, FragmentBoundNode.START, fragment), 2)
    self.assertEqual(update_normal_line(1, FragmentBoundNode.END, fragment), 2)


  def test_update_normal_line_create_at_middle(self):
    fragment =  MockDiffHunk((3,0), (4,1), [])

    # Previous lines unaffected
    self.assertEqual(update_normal_line(3, FragmentBoundNode.START, fragment), 3)
    self.assertEqual(update_normal_line(3, FragmentBoundNode.END, fragment), 3)
    # Subsequent lines shifted
    self.assertEqual(update_normal_line(10, FragmentBoundNode.START, fragment), 11)
    self.assertEqual(update_normal_line(13, FragmentBoundNode.END, fragment), 14)

  def test_update_normal_line_expand_at_middle(self):
    fragment = MockDiffHunk((4,2), (4,4), [])

    # Previous lines unaffected
    self.assertEqual(update_normal_line(3, FragmentBoundNode.START, fragment), 3)
    self.assertEqual(update_normal_line(3, FragmentBoundNode.END, fragment), 3)
    # Contained fragments expanded
    self.assertEqual(update_normal_line(5, FragmentBoundNode.START, fragment), 4)
    self.assertEqual(update_normal_line(5, FragmentBoundNode.END, fragment), 7)
    # Subsequent lines shifted
    self.assertEqual(update_normal_line(10, FragmentBoundNode.START, fragment), 12)
    self.assertEqual(update_normal_line(13, FragmentBoundNode.END, fragment), 15)

  # TODO: test_update_inherited_bound_....
  def test_update_inherited_bound_addition(self):
    # Adds 5 lines, pushing the content on line 4 to line 9 etc.
    filepatch = MockPatch(MockDiffDelta("dummy", "dummy"), [
      MockDiffHunk((3,0), (4,5), [])])
    # nonempty, end +1 < start
    self.assertEqual(update_inherited_bound(1, 2, filepatch), (1, 2))
    # empty, end +1 < start
    self.assertEqual(update_inherited_bound(1, 0, filepatch), (1, 0))
    # nonempty, end +1 = start
    self.assertEqual(update_inherited_bound(1, 3, filepatch), (1, 3))
    # empty bound, start = start
    self.assertEqual(update_inherited_bound(4, 3, filepatch), (4, 8))
    # nonempty, start = start
    self.assertEqual(update_inherited_bound(4, 4, filepatch), (9, 9))
    # nonempty, start > end
    self.assertEqual(update_inherited_bound(5, 6, filepatch), (10, 11))
    # empty, start > end
    self.assertEqual(update_inherited_bound(5, 4, filepatch), (10, 9))

  def test_update_new_bound(self):
    #filepatch = FilePatch(FilePatchHeader("dummy", "dummy"), [
    #    Fragment(FragmentHeader(Range(4,2), Range(4,4)))])
    #fragment = Fragment(FragmentHeader(Range(4,2), Range(4,4)))

    filepatch = MockPatch(MockDiffDelta("dummy", "dummy"), [
      MockDiffHunk((4,2), (4,4), [])])
    fragment = MockDiffHunk((4,2), (4,4), [])

    # Related bounds updated
    self.assertEqual(update_new_bound(fragment), (4, 7))

  def test_update_positions(self):
    #filepatch = FilePatch(FilePatchHeader("dummy", "dummy"), [
    #    Fragment(FragmentHeader(Range(4,2), Range(4,4)))])
    #patch = Patch([filepatch],
    #              PatchHeader("aaabbaaabbaaabbaaabbaaabbaaabbaaabbaaabb",
    #                          "dummy message"))
    filepatch = MockPatch(MockDiffDelta("dummy", "dummy"), [ # TODO: set to newdummy
      MockDiffHunk((4,2), (4,4), [])])
    patch = CommitDiff(MockCommit("aaabbaaabbaaabbaaabbaaabbaaabbaaabbaaabb",
                                  "dummy message"),
                       [filepatch])
    node_line = FragmentBoundLine(FragmentDualBoundNode(0, filepatch, 0,
                                                        FragmentBoundNode("dummy", 2, FragmentBoundNode.START),
                                                        FragmentBoundNode("dummy", 4, FragmentBoundNode.END)))

    update_positions([node_line], patch, 0)
    # Since both the node line and the diff is from the same index, the bound is overwritten by the diff
    self.assertEqual(node_line.last()._filename, "dummy")
    self.assertEqual(node_line.last().start._filename, "dummy")
    self.assertEqual(node_line.last().start._line, 4)
    self.assertEqual(node_line.last().end._filename, "dummy")
    self.assertEqual(node_line.last().end._line, 7)

  def test_group_by_file(self):
    line_f0_f1_f1 = FakeLine(FakeFileNode(0, 'f0'),
                             FakeFileNode(1, 'f1'),
                             FakeFileNode(2, 'f1'))
    self.assertEqual(
      {(2, 'f1'): [line_f0_f1_f1]},
      group_by_file([line_f0_f1_f1]))

    line_x_f0_f0 = FakeLine(FakeFileNode(1, 'f0'),
                            FakeFileNode(2, 'f0'))
    self.assertEqual(
      {(2, 'f1'): [line_f0_f1_f1],
       (2, 'f0'): [line_x_f0_f0]},
      group_by_file([line_f0_f1_f1, line_x_f0_f0]))

    # Deleted file
    line_f0_x_x = FakeLine(FakeFileNode(0, 'f0'),
                           FakeFileNode(1, '/dev/null'),
                           FakeFileNode(2, '/dev/null'))
    self.assertEqual(
      {(0, 'f0'): [line_f0_x_x],
       (2, 'f0'): [line_x_f0_f0]},
      group_by_file([line_f0_x_x, line_x_f0_f0]))

    line_x_f0_f0 = FakeLine(FakeFileNode(1, 'f0'),
                            FakeFileNode(2, 'f0'))
    line_x_f1_f1 = FakeLine(FakeFileNode(1, 'f1'),
                            FakeFileNode(2, 'f1'))
    self.assertEqual(
    {(2, 'f0'): [line_x_f0_f0],
     (2, 'f1'): [line_f0_f1_f1, line_x_f1_f1]},
      group_by_file([line_f0_f1_f1,
                     line_x_f0_f0,
                     line_x_f1_f1]))

  def test_new_group_fragment_bound_lines_insertion(self):
    start_0_0 = FakeLine(FakeNode(0, 0, START),
                         FakeNode(1, 0, START))
    self.assertEqual(
      {(1, 'dummy'):
       [set([start_0_0])]},
      new_group_fragment_bound_lines([start_0_0]))

    end_0_1 = FakeLine(FakeNode(0, 0, END),
                       FakeNode(1, 1, END))
    self.assertEqual(
      {(1, 'dummy'):
       [set([start_0_0]), set([end_0_1])]},
      new_group_fragment_bound_lines([start_0_0,
                                      end_0_1]))

  def test_new_group_fragment_bound_lines_two_insertions_same_start(self):
    start_0_0_0 = FakeLine(FakeNode(0, 0, START),
                           FakeNode(1, 0, START),
                           FakeNode(2, 0, START))
    start_x_0_0 = FakeLine(FakeNode(1, 0, START),
                           FakeNode(2, 0, START))

    end_0_1_3 = FakeLine(FakeNode(0, 0, END),
                         FakeNode(1, 1, END),
                         FakeNode(2, 3, END))
    end_x_1_3 = FakeLine(FakeNode(1, 1, END),
                         FakeNode(2, 3, END))
    self.eq(
      {(2, 'dummy'):
       [set([start_0_0_0, start_x_0_0]), set([end_x_1_3, end_0_1_3])]},
      new_group_fragment_bound_lines([start_0_0_0,
                                      start_x_0_0,
                                      end_0_1_3,
                                      end_x_1_3]))

    self.eq(
      {(2, 'dummy'):
       [set([end_x_1_3, end_0_1_3])]},
      new_group_fragment_bound_lines([end_0_1_3,
                                      end_x_1_3]))

  def test_new_group_fragment_bound_lines_partial_overlap(self):
    # 123456789
    #  ####
    #    #####
    start_2_2_2 = FakeLine(FakeNode(0, 2, START),
                           FakeNode(1, 2, START),
                           FakeNode(2, 2, START))
    start_x_4_4 = FakeLine(FakeNode(1, 4, START),
                           FakeNode(2, 4, START))
    end_5_5_8 = FakeLine(FakeNode(0, 5, END),
                         FakeNode(1, 5, END),
                         FakeNode(2, 8, END))
    end_x_8_8 = FakeLine(FakeNode(1, 8, END),
                         FakeNode(2, 8, END))
    self.eq(
      {(2, 'dummy'):
        [set([start_2_2_2]), set([start_x_4_4]), set([end_5_5_8]), set([end_x_8_8])]},
      new_group_fragment_bound_lines([start_2_2_2, start_x_4_4, end_5_5_8, end_x_8_8]))



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

  def test_003_004_groups(self):
    files = ['003-add-one-line-to-empty-file',
             '004-remove-one-line-empty-file']
    self.check_node_group_kinds(files, [[START,START], [END,END]]) # ((h))


  def test_011(self):
    self.check_diff('011-add-x-to-A-and-N', ['##'])

  def test_012(self):
    self.check_diff('012-add-x-to-A-C', ['#'])

  def test_011_012(self):
    self.check_diffs(['011-add-x-to-A-and-N',
                      '012-add-x-to-A-C'],
                     ['#.#',
                      '##.'])
  def test_011_012_groups(self):
    self.check_node_group_kinds(['011-add-x-to-A-and-N',
                                 '012-add-x-to-A-C'],
                                [[START, START],[END],[END],[START],[END]]) # ((a)bc)..(n)


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
  def test_030_032_groups(self):
    self.check_node_group_kinds(['030-addmod-create-with-ab',
                                 '031-addmod-add-c',
                                 '032-addmod-change-bc-to-xy'],
                                [[START],[START],[END,START],[END,END]]) # (a((xy)))


  def test_030_033(self):
    self.check_diffs(['030-addmod-create-with-ab',
                      '031-addmod-add-c',
                      '032-addmod-change-bc-to-xy',
                      '033-addmod-add-z-between-xy'],
                     ['##...',
                      '.^###',
                      '.####',
                      '...#.'])


  def test_030_033_groups(self):
    self.check_node_group_kinds(['030-addmod-create-with-ab',
                                 '031-addmod-add-c',
                                 '032-addmod-change-bc-to-xy',
                                 '033-addmod-add-z-between-xy'],
                                # 5a3.54x2z2y43
                                [[START],[START],[END,START],[START],[END],[END,END]])


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
                           ['##..',
                            '.^##',
                            '.###',
                            '...#'])

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

  def test_110_111_brief(self):
    self.check_diffs_brief(['110-realdiff-newfilebug-addfile',
                            '111-realdiff-newfilebug-modfile'],
                           ['##',
                            '.#'])

  def test_dco1_brief(self):
    self.check_diffs_brief(['3c707a3d921 WIP: Failing test of diverting',
                            'e330243c1b544 WIP: Refactor cursormove',
                            '59718d27a WIP: Prepare for divertable',
                            '76c3fa0690213 WIP: divertable failing',
                            '2872a758eb7 WIP: Fix: Copy input table'],
                           ['.........##.',
                            '.#.###....^.',
                            '..#^##.##.#.',
                            '...^.####..#',
                            '#..#........'])

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

  # === Helper functions ===

  def eq(self, expected, actual):
    def jprint(v):
      import prettyprint
      pretty = prettyprint.Formatter()
      print(pretty(v, htchar='  '))
    print('expected:', end='')
    jprint(expected)
    print('actual:', end='')
    jprint(actual)
    self.assertEqual(expected, actual)


  def unstaged_change(self, filename, lines):
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    file_path = os.path.join(repo_path, filename)
    with open(file_path, 'w', newline='\n') as f:
      for line in lines:
        print ("to file", file_path, "writing '", line, "'")
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

  def get_node_lines(self, diff_filenames):
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    commit_hexes = [find_commit_with_message(repo_path, diff_filename)
                    for diff_filename in diff_filenames]
    cl = CommitLoader()
    diffs = cl.load(repo_path, ExplicitCommitSelection(commit_hexes))
    return update_all_positions_to_latest(diffs)

  def check_node_group_kinds(self, diff_filenames, kinds):
    def histogram_kinds(kinds):
      hist = []
      for group in kinds:
        group_hist = {START : 0, END : 0}
        debug.get('test').debug(group_hist)
        for node_line_kind in group:
          group_hist[node_line_kind] += 1
        hist += [(group_hist[START], group_hist[END])]
      return hist

    def stringify_kinds_list(l):
      return [{START:'start', END:'end'}[e] for e in l]
    kinds_hist = histogram_kinds(kinds)
    kinds = list(map(stringify_kinds_list, kinds))
    dual_node_lines = self.get_node_lines(diff_filenames)
    for dual_node_line in dual_node_lines:
      dual_node_line.increment_end()
    node_lines = to_separate_lines(dual_node_lines)
    if debug.is_logging('test'):
      print_node_line_relation_table(node_lines)
    grouped_node_lines = new_group_fragment_bound_lines(node_lines)
    grouped_node_lines = [node_line_group
                          for f, node_line_groups in grouped_node_lines.items()
                          for node_line_group in node_line_groups]
    error_string = "Required starts and ends in groups: \n %s\nActual: %s" %(
      kinds, grouped_node_lines)
    self.assertEqual(len(grouped_node_lines), len(kinds_hist), "Wrong length; " + error_string)
    i = 0
    actual_kinds_hist = [None]*len(grouped_node_lines)
    for group in grouped_node_lines:
      n_start = 0
      n_end = 0
      for node_line in group:
        if node_line._kind == FragmentBoundNode.START:
          n_start += 1
        elif node_line._kind == FragmentBoundNode.END:
          n_end += 1

      actual_kinds_hist[i] = (n_start, n_end)
      #self.assertEqual(n_start, kinds[i][START], "Wrong number of starts in group %d: %s" % (i, grouped_node_lines))
      #self.assertEqual(n_end, kinds[i][END], "Wrong number of ends in group %d: %s" % (i, grouped_node_lines))
      i += 1
    self.assertListEqual(actual_kinds_hist, kinds_hist, error_string)


  def check_diff(self, diff_filename, matrix):
    cl = CommitLoader()
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    commit_hex = find_commit_with_message(repo_path, diff_filename)
    diffs = cl.load(repo_path, ExplicitCommitSelection([commit_hex]))
    h = Fragmap.from_diffs(diffs)
    actual_matrix = h.generate_matrix()
    self.check_matrix(render_matrix_for_test(actual_matrix), matrix)

  def check_diff_brief(self, diff_filename, matrix):
    cl = CommitLoader()
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    commit_hex = find_commit_with_message(repo_path, diff_filename)
    diffs = cl.load(repo_path, ExplicitCommitSelection([commit_hex]))
    h = BriefFragmap.group_by_patch_connection(Fragmap.from_diffs(diffs))
    actual_matrix = h.generate_matrix()
    self.check_matrix(render_matrix_for_test(actual_matrix), matrix)

  def check_diffs(self, diff_filenames, matrix):
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    commit_hexes = [find_commit_with_message(repo_path, diff_filename)
                    for diff_filename in diff_filenames]
    cl = CommitLoader()
    diffs = cl.load(repo_path, ExplicitCommitSelection(commit_hexes))
    h = Fragmap.from_diffs(diffs)
    actual_matrix = h.generate_matrix()
    self.check_matrix(render_matrix_for_test(actual_matrix), matrix)


  def check_diffs_brief(self, diff_filenames, matrix):
    test_name = self.id().split('.')[-1]
    repo_path = os.path.join(DIFF_DIR, "build", test_name)
    commit_hexes = [find_commit_with_message(repo_path, diff_filename)
                    for diff_filename in diff_filenames]
    cl = CommitLoader()
    diffs = cl.load(repo_path, ExplicitCommitSelection(commit_hexes))
    h = BriefFragmap.group_by_patch_connection(Fragmap.from_diffs(diffs))
    actual_matrix = h.generate_matrix()
    self.check_matrix(render_matrix_for_test(actual_matrix), matrix)

  def check_matrix(self, matrix, reference):
    joined_matrix = '\n'.join([''.join(row) for row in matrix])
    reference = '\n'.join(reference)
    debug.get('test').debug("Actual: \n%s \nReference: \n%s", joined_matrix, reference)
    self.assertEqual(joined_matrix, reference)
