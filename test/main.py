#!/usr/bin/env python


import unittest
import os
import sys
TEST_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(TEST_DIR, '..'))
from parse_patch import *
from generate_matrix import *
import debug

def read_diff(filename):
  filepath = os.path.join(TEST_DIR, 'diffs', filename)
  with open(filepath) as f:
    lines = [line.rstrip() for line in f]
    return lines

START = 0
END = 1

class Test(unittest.TestCase):

  # Append instead of replace default assertion failure message
  longMessage = True

  def test_update_inherited_bound_create_at_beginning(self):
    filepatch = FilePatch(FilePatchHeader("dummy", "dummy"), [
        Fragment(FragmentHeader(Range(0,0), Range(1,1)))])

    # Subsequent lines shifted
    self.assertEqual(update_inherited_bound(1, FragmentBoundNode.START, filepatch), 2)
    self.assertEqual(update_inherited_bound(1, FragmentBoundNode.END, filepatch), 2)


  def test_update_inherited_bound_create_at_middle(self):
    filepatch = FilePatch(FilePatchHeader("dummy", "dummy"), [
        Fragment(FragmentHeader(Range(3,0), Range(4,1)))])

    # Previous lines unaffected
    self.assertEqual(update_inherited_bound(3, FragmentBoundNode.START, filepatch), 3)
    self.assertEqual(update_inherited_bound(3, FragmentBoundNode.END, filepatch), 3)
    # Subsequent lines shifted
    self.assertEqual(update_inherited_bound(10, FragmentBoundNode.START, filepatch), 11)
    self.assertEqual(update_inherited_bound(13, FragmentBoundNode.END, filepatch), 14)

  def test_update_inherited_bound_expand_at_middle(self):
    filepatch = FilePatch(FilePatchHeader("dummy", "dummy"), [
        Fragment(FragmentHeader(Range(4,2), Range(4,4)))])

    # Previous lines unaffected
    self.assertEqual(update_inherited_bound(3, FragmentBoundNode.START, filepatch), 3)
    self.assertEqual(update_inherited_bound(3, FragmentBoundNode.END, filepatch), 3)
    # Contained fragments expanded
    self.assertEqual(update_inherited_bound(5, FragmentBoundNode.START, filepatch), 4)
    self.assertEqual(update_inherited_bound(5, FragmentBoundNode.END, filepatch), 7)
    # Subsequent lines shifted
    self.assertEqual(update_inherited_bound(10, FragmentBoundNode.START, filepatch), 12)
    self.assertEqual(update_inherited_bound(13, FragmentBoundNode.END, filepatch), 15)

  def test_update_new_bound(self):
    filepatch = FilePatch(FilePatchHeader("dummy", "dummy"), [
        Fragment(FragmentHeader(Range(4,2), Range(4,4)))])
    fragment = Fragment(FragmentHeader(Range(4,2), Range(4,4)))

    # Related bounds updated
    self.assertEqual(update_new_bound(fragment, FragmentBoundNode.START), 4)
    self.assertEqual(update_new_bound(fragment, FragmentBoundNode.END), 7)

  def test_update_positions(self):
    filepatch = FilePatch(FilePatchHeader("dummy", "dummy"), [
        Fragment(FragmentHeader(Range(4,2), Range(4,4)))])
    patch = Patch([filepatch],
                  PatchHeader("aaabbaaabbaaabbaaabbaaabbaaabbaaabbaaabb",
                              "dummy message"))
    node_lines = [FragmentBoundLine(FragmentBoundNode(0, filepatch, 0, Range(4,2), FragmentBoundNode.END))]
    update_positions(node_lines, patch, 0)
    self.assertEqual(node_lines[0].last()._filename, "dummy")
    self.assertEqual(node_lines[0].last()._line, 7)



  def test_016_004(self):
    self.check_diffs(['016-add-one-line-to-empty.txt.diff',
                      '002-rename-empty-file.diff',
                      '004-remove-one-line-empty-file.diff'],
                     ['#.',
                      '..',
                      '#.'])

  def test_003(self):
    self.check_diff('003-add-one-line-to-empty-file.diff', ['#.'])

  def test_004(self):
    self.check_diff('004-remove-one-line-empty-file.diff', ['#.'])

  def test_003_004(self):
    files = ['003-add-one-line-to-empty-file.diff',
             '004-remove-one-line-empty-file.diff']
    self.check_diffs(files,
                     ['#.',
                      '#.'])

  def test_003_004_groups(self):
    files = ['003-add-one-line-to-empty-file.diff',
             '004-remove-one-line-empty-file.diff']
    self.check_node_group_kinds(files, [[START,START], [END,END]]) # ((h))


  def test_011(self):
    self.check_diff('011-add-x-to-A-and-N.diff', ['#.#.'])

  def test_012(self):
    self.check_diff('012-add-x-to-A-C.diff', ['#.'])

  def test_011_012(self):
    self.check_diffs(['011-add-x-to-A-and-N.diff',
                      '012-add-x-to-A-C.diff'],
                     ['#..#.',
                      '##...'])
  def test_011_012_groups(self):
    self.check_node_group_kinds(['011-add-x-to-A-and-N.diff',
                                 '012-add-x-to-A-C.diff'],
                                [[START, START],[END],[END],[START],[END]]) # ((a)bc)..(n)


  def test_020(self):
    self.check_diff('020-modfile-create.diff', ['#.'])

  def test_021(self):
    self.check_diff('021-modfile-remove-first-line.diff', ['#.'])

  def test_020_021(self):
    self.check_diffs(['020-modfile-create.diff',
                      '021-modfile-remove-first-line.diff'],
                     ['##.',
                      '#..'])

  def test_022_023(self):
    self.check_diffs(['022-modfile-mod-second-line.diff',
                      '023-modfile-readd-first-line.diff'],
                     ['.#.',
                      '#..'])


  def test_030(self):
    self.check_diff('030-addmod-create-with-ab.diff', ['#.'])

  def test_030_031(self):
    self.check_diffs(['030-addmod-create-with-ab.diff',
                      '031-addmod-add-c.diff'],
                     ['#..',
                      '.#.'])

  def test_030_032(self):
    self.check_diffs(['030-addmod-create-with-ab.diff',
                      '031-addmod-add-c.diff',
                      '032-addmod-change-bc-to-xy.diff'],
                     ['##..',
                      '..#.',
                      '.##.'])
  def test_030_032_groups(self):
    self.check_node_group_kinds(['030-addmod-create-with-ab.diff',
                                 '031-addmod-add-c.diff',
                                 '032-addmod-change-bc-to-xy.diff'],
                                [[START],[START],[END,START],[END,END]]) # (a((xy)))


  def test_030_033(self):
    self.check_diffs(['030-addmod-create-with-ab.diff',
                      '031-addmod-add-c.diff',
                      '032-addmod-change-bc-to-xy.diff',
                      '033-addmod-add-z-between-xy.diff'],
                     ['##....',
                      '..###.',
                      '.####.',
                      '...#..'])


  def test_030_033_groups(self):
    self.check_node_group_kinds(['030-addmod-create-with-ab.diff',
                                 '031-addmod-add-c.diff',
                                 '032-addmod-change-bc-to-xy.diff',
                                 '033-addmod-add-z-between-xy.diff'],
                                # 5a3.54x2z2y43
                                [[START],[START],[END,START],[START],[END],[END,END]])


  def test_041_042_043(self):
    self.check_diffs(['041-successivemod-mod-ab.diff',
                      '042-successivemod-mod-cd.diff',
                      '043-successivemod-mod-ef.diff'],
                     ['#...',
                      '.#..',
                      '..#.'])

  def test_050_054(self):
    self.check_diffs(['050-twofiles-create-a-with-a.diff',
                      '051-twofiles-create-b-with-x.diff',
                      '052-twofiles-add-y-to-b.diff',
                      '053-twofiles-add-z-to-b.diff',
                      '054-twofiles-add-w-to-b.diff'],
                     ['#......',
                      '..#....',
                      '...#...',
                      '....#..',
                      '.....#.'])

  # == Test brief fragmaps ==

  def test_016_004_brief(self):
    self.check_diffs_brief(['016-add-one-line-to-empty.txt.diff',
                            '002-rename-empty-file.diff',
                            '004-remove-one-line-empty-file.diff'],
                           ['#',
                            '.',
                            '#'])

  def test_003_brief(self):
    self.check_diff_brief('003-add-one-line-to-empty-file.diff',
                          ['#'])

  def test_004_brief(self):
    self.check_diff_brief('004-remove-one-line-empty-file.diff',
                          ['#'])

  def test_003_004_brief(self):
    self.check_diffs_brief(['003-add-one-line-to-empty-file.diff',
                            '004-remove-one-line-empty-file.diff'],
                           ['#',
                            '#'])

  def test_011_brief(self):
    self.check_diff_brief('011-add-x-to-A-and-N.diff',
                          ['#'])

  def test_012_brief(self):
    self.check_diff_brief('012-add-x-to-A-C.diff',
                          ['#'])

  def test_011_012_brief(self):
    self.check_diffs_brief(['011-add-x-to-A-and-N.diff',
                            '012-add-x-to-A-C.diff'],
                           ['#.#',
                            '##.'])

  def test_020_brief(self):
    self.check_diff_brief('020-modfile-create.diff',
                          ['#'])

  def test_021_brief(self):
    self.check_diff_brief('021-modfile-remove-first-line.diff',
                          ['#'])

  def test_020_021_brief(self):
    self.check_diffs_brief(['020-modfile-create.diff',
                      '021-modfile-remove-first-line.diff'],
                     ['##',
                      '#.'])

  def test_022_023_brief(self):
    self.check_diffs_brief(['022-modfile-mod-second-line.diff',
                      '023-modfile-readd-first-line.diff'],
                     ['.#',
                      '#.'])


  def test_030_brief(self):
    self.check_diff_brief('030-addmod-create-with-ab.diff',
                          ['#'])

  def test_030_031_brief(self):
    self.check_diffs_brief(['030-addmod-create-with-ab.diff',
                      '031-addmod-add-c.diff'],
                     ['#.',
                      '.#'])

  def test_030_032_brief(self):
    self.check_diffs_brief(['030-addmod-create-with-ab.diff',
                      '031-addmod-add-c.diff',
                      '032-addmod-change-bc-to-xy.diff'],
                     ['##.',
                      '..#',
                      '.##'])

  def test_030_033_brief(self):
    self.check_diffs_brief(['030-addmod-create-with-ab.diff',
                      '031-addmod-add-c.diff',
                      '032-addmod-change-bc-to-xy.diff',
                      '033-addmod-add-z-between-xy.diff'],
                     ['##..',
                      '..##',
                      '.###',
                      '...#'])

  def test_041_042_043_brief(self):
    self.check_diffs_brief(['041-successivemod-mod-ab.diff',
                      '042-successivemod-mod-cd.diff',
                      '043-successivemod-mod-ef.diff'],
                     ['#..',
                      '.#.',
                      '..#'])

  def test_050_054_brief(self):
    self.check_diffs_brief(['050-twofiles-create-a-with-a.diff',
                      '051-twofiles-create-b-with-x.diff',
                      '052-twofiles-add-y-to-b.diff',
                      '053-twofiles-add-z-to-b.diff',
                      '054-twofiles-add-w-to-b.diff'],
                     ['#....',
                      '.#...',
                      '..#..',
                      '...#.',
                      '....#'])

  # == Test command line arguments ==

  def test_args_no_args(self):
    import list_hunks
    old_argv = sys.argv # Backup real value
    # No args -> default to some nonempty set of revs
    sys.argv = [sys.argv[0], '']
    self.assertTrue(list_hunks.get_rev_range_from_args() is not None)
    sys.argv = old_argv # Restore real value

  def test_args_n_arg_valid(self):
    import list_hunks
    old_argv = sys.argv # Backup real value
    # -n 5 given -> should get HEAD~5..HEAD
    sys.argv = [sys.argv[0], '-n', '5']
    self.assertEqual(list_hunks.get_rev_range_from_args(), 'HEAD~5..HEAD')
    sys.argv = old_argv # Restore real value

  def test_args_n_arg_invalid(self):
    import list_hunks
    old_argv = sys.argv # Backup real value
    # -n foo given -> should get None
    sys.argv = [sys.argv[0], '-n', 'foo']
    self.assertEqual(list_hunks.get_rev_range_from_args(), None)
    sys.argv = old_argv # Restore real value


  def get_node_lines(self, diff_filenames):
    diff = []
    for fn in diff_filenames:
      diff += read_diff(fn)
    debug.log(debug.test, diff)
    pp = PatchParser()
    return update_all_positions_to_latest(pp.parse(diff)._patches)

  def check_node_group_kinds(self, diff_filenames, kinds):
    def histogram_kinds(kinds):
      hist = []
      for group in kinds:
        group_hist = {START : 0, END : 0}
        debug.log(debug.test, group_hist)
        for node_line_kind in group:
          group_hist[node_line_kind] += 1
        hist += [(group_hist[START], group_hist[END])]
      return hist

    def stringify_kinds_list(l):
      return map(lambda e: {START:'start', END:'end'}[e], l)
    kinds_hist = histogram_kinds(kinds)
    kinds = map(stringify_kinds_list, kinds)
    node_lines = self.get_node_lines(diff_filenames)
    if debug.is_logging(debug.test):
      print_node_line_relation_table(node_lines)
    grouped_node_lines = group_fragment_bound_lines(node_lines)
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
    diff = read_diff(diff_filename)
    pp = PatchParser()
    h = Fragmap.from_ast(pp.parse(diff))
    actual_matrix = h.generate_matrix()
    self.check_matrix(actual_matrix, matrix)

  def check_diff_brief(self, diff_filename, matrix):
    diff = read_diff(diff_filename)
    pp = PatchParser()
    h = Fragmap.from_ast(pp.parse(diff)).group_by_patch_connection()
    actual_matrix = h.generate_matrix()
    self.check_matrix(actual_matrix, matrix)

  def check_diffs(self, diff_filenames, matrix):
    diff = []
    for fn in diff_filenames:
      diff += read_diff(fn)
    pp = PatchParser()
    h = Fragmap.from_ast(pp.parse(diff))
    actual_matrix = h.generate_matrix()
    self.check_matrix(actual_matrix, matrix)


  def check_diffs_brief(self, diff_filenames, matrix):
    diff = []
    for fn in diff_filenames:
      diff += read_diff(fn)
    pp = PatchParser()
    h = Fragmap.from_ast(pp.parse(diff)).group_by_patch_connection()
    actual_matrix = h.generate_matrix()
    self.check_matrix(actual_matrix, matrix)

  def check_matrix(self, matrix, reference):
    joined_matrix = '\n'.join([''.join(row) for row in matrix])
    reference = '\n'.join(reference)
    debug.log(debug.test, "Actual:\n", joined_matrix, "\nReference:\n", reference)
    self.assertEqual(joined_matrix, reference)




if __name__ == '__main__':
  debug_parser = debug.parse_args(extendable=True)
  unittest.main()
