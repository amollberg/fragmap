#!/usr/bin/env python

import copy
from parse_patch import *
# Hierarchy:
# AST
#  Patch
#   PatchHeader
#    _hash
#   FilePatch
#     FilePatchHeader
#      _oldfile
#      _newfile
#     Fragment
#      FragmentHeader
#       Range _oldrange
#        _start
#        _end
#       Range _newrange
#        _start
#        _end
# FragmentNodeLine
#  FragmentNode
#  _startdiff_i

DEBUG_SORTING = True
DEBUG_GROUPING = False


# TODO:
# Generate nodes as we update the diff list, not just after every one
# Each update has to also update each node and sort new nodes into the
# list of existing. We may be able to work recursively, patching older
# diffs and adding new nodes. We probably will never remove nodes as to
# signal that fragments have been joined together. They still need to
# be represented at the last level as separate (?).

def nonnull_file(file_patch_header):
  if not is_nullfile(file_patch_header._oldfile):
    return file_patch_header._oldfile
  if not is_nullfile(file_patch_header._newfile):
    return file_patch_header._newfile
  # Both files are null files
  return None


def update_new_bound(fragment_i, bound_kind, file_patch):
  """
  Update a bound that belongs to the current diff. Simply apply whatever
  fragment it belongs to.
  """
  line = 0
  marker = file_patch._fragments[fragment_i]._header
  if bound_kind == FragmentBoundNode.START:
    line = marker._newrange._start
    print "Setting new start line to", line
  elif bound_kind == FragmentBoundNode.END:
    line = marker._newrange._end
    print "Setting new end line to", line
  return line


def update_inherited_bound(line, bound_kind, file_patch):
  """
  Update a bound inherited from an older patch. Must never be
  called for bounds belonging to the newest patch. Use
  update_new_bound for them.
  """
  # patch fragment +a,b -c,d means the map [a,b[ -> [c,d[
  # previous lines are unaffected, mapping e -> e
  # start lines inside fragment map e -> c
  # end lines inside fragment map e -> d
  # subsequent lines map as e -> e-b+d
  marker = None
  for patch_fragment in file_patch._fragments:
    if patch_fragment._header._oldrange._start <= line:
      marker = patch_fragment._header
    else:
      break
  print "Update_line:", line, bound_kind, file_patch
  print "Marker:", marker
  # TODO: Fix sorting of node line groups after this.
  if marker is not None:
    if line <= marker._oldrange._end:
      # line is inside the range
      print "Line %d is inside range %s" %(line, marker._oldrange)
      if bound_kind == FragmentBoundNode.START:
        line = marker._newrange._start
        print "Setting start line to", line
      elif bound_kind == FragmentBoundNode.END:
        line = marker._newrange._end
        print "Setting end line to", line
    else:
      # line is after the range
      print "Line %d is after range %s; shifting %d" % (
        line, marker._oldrange, marker._newrange._end - marker._oldrange._end)
      line += marker._newrange._end - marker._oldrange._end
  else:
    # line is before any fragment; no update required
    pass
  return line

def update_line(line, bound_kind, fragment_i, startdiff_i, diff_i, file_patch):
  # If the current diff is the start diff of the
  # affected node line:
  if diff_i == startdiff_i:
    # The bound is new
    return update_new_bound(fragment_i, bound_kind, file_patch)
  else:
    # The bound is inherited
    return update_inherited_bound(line, bound_kind, file_patch)

def update_file_positions(file_node_lines, file_patch, diff_i):
  """
  Update all the nodes belonging in a file with a file patch.
  """
  # TODO: Verify that filenames are the same
  # TODO Ensure sorted fragments
  for node_line in file_node_lines:
    print "Node before:", node_line.last()
    node_line.update(diff_i, file_patch._header._newfile,
                     update_line(node_line.last()._line,
                                 node_line.last()._kind,
                                 node_line.last()._fragment_i,
                                 node_line._startdiff_i,
                                 diff_i,
                                 file_patch))
    print "Node after:", node_line.last()


def extract_nodes(diff, diff_i):
  node_list = []
  for file_patch in diff._filepatches:
    for fragment_i in range(len(file_patch._fragments)):
      fragment = file_patch._fragments[fragment_i]
      node_list += [
        FragmentBoundNode(diff, diff_i, file_patch, fragment_i, fragment._header._oldrange,
                          FragmentBoundNode.START),
        FragmentBoundNode(diff, diff_i, file_patch, fragment_i, fragment._header._oldrange,
                          FragmentBoundNode.END),
        ]
  return node_list


def extract_node_lines(diff, diff_i):
  return map(FragmentBoundLine, extract_nodes(diff, diff_i))


def update_positions(node_lines, patch, diff_i):
  """
  Update all node lines with a multi-file patch.
  """
  for file_patch in patch._filepatches:
    oldfile = file_patch._header._oldfile
    #file_node_lines = [nl for nl in node_lines if nl.last()._file == oldfile]
    file_node_lines = []
    for nl in node_lines:
      print "last:", nl.last()._filename
      if nl.last()._filename == oldfile:
        file_node_lines += [nl]
    print "Updating file:", oldfile
    print "Node lines:", file_node_lines
    update_file_positions(file_node_lines, file_patch, diff_i)
    print "Updated node lines:", file_node_lines


#def update_positions_to_latest(node_lines, patch_list):
#  """
#  Update the positions of the AST old_ast through every patch
#  in patch_list that is more recent than it.
#  """
#  for patch in patch_list:
#    # TODO: Sort and filter by timestamp
#    update_positions(node_lines, patch)



# For each commit: project fragment positions iteratively up past the latest commit
#  => a list of nodes, each pointing to commit and kind (start or end of fragment)
# Need to generate the nodes as we iterate through. What order?
# * Starting diff : new to old, propagation: old to new
# * Starting diff : old to new, propagation: old to new
#   + Can get all nodes from a patch in one go

def update_all_positions_to_latest(diff_list):
  """
  Update all diffs to the latest patch, letting
  newer diffs act as patches for older diffs.
  Assumes diff_list is sorted in ascending time.
  """
  print "update_all_positions:", diff_list
  node_line_list = []
  for i in range(len(diff_list)):
    #update_positions_to_latest(diff_list[i], diff_list[i+1:])
    node_line_list += extract_node_lines(diff_list[i], i)
    print "All extracted:", i, node_line_list
    update_positions(node_line_list, diff_list[i], i)
    #print "All updated:", node_line_list
  return node_line_list

class FragmentBoundNode():
  # References back into the diffs
  _diff = None
  _diff_i = None
  _file = None
  _fragment = None

  # Info to sort on
  _filename = None
  _line = None

  # Other attributes
  _kind = None
  # Two kinds of fragment bounds:
  START = 1
  END = 2

  # Sort by filename then by line
  def __lt__(a, b):
    return a._filename < b._filename or (
           a._filename == b._filename and a._line < b._line)

  def __init__(self, diff, diff_i, file_patch, fragment_i, fragment_range, kind):
    self._diff = diff
    self._diff_i = diff_i
    self._file = file_patch
    self._fragment = file_patch._fragments[fragment_i]
    self._fragment_i = fragment_i
    self._filename = nonnull_file(file_patch._header)
    if kind == FragmentBoundNode.START:
      self._line = fragment_range._start
    elif kind == FragmentBoundNode.END:
      self._line = fragment_range._end
    self._kind = kind

  def __repr__(self):
    kind_str = "START"
    if self._kind == FragmentBoundNode.END:
      kind_str = "END"
    return "<Node: %s, (%s, %d), %s>" %(self._diff_i, self._filename, self._line, kind_str)

class FragmentBoundLine():
  _nodehistory = None
  _startdiff_i = None
  _kind = None

  # Note: This ordering is not transitive so bound lines cannot be sorted!
  def __lt__(a, b):
    def lt_at_diff(a, b, diff_i):
      a_file = a._nodehistory[diff_i]._filename
      b_file = b._nodehistory[diff_i]._filename
      a_line = a._nodehistory[diff_i]._line
      b_line = b._nodehistory[diff_i]._line
      if a._kind == FragmentBoundNode.END:
        a_line += 1
      if b._kind == FragmentBoundNode.END:
        b_line += 1
      if a_file < b_file:
        if DEBUG_SORTING:
          print "file %s < %s at diff %d" %(a_file, b_file, diff_i)
        return True
      if a_file == b_file and a_line < b_line:
        if DEBUG_SORTING:
          print "line %d < %d at diff %d" %(a_line, b_line, diff_i)
        return True
      return False

    common_diffs = a._nodehistory.viewkeys() & b._nodehistory.viewkeys()
    #first_common_diff_i = min(common_diffs)
    common_diffs -= {a._startdiff_i-1, b._startdiff_i-1}
    first_common_diff_i = min(common_diffs)
    prev_diff_i = first_common_diff_i - 1
    # Order by filename at latest diff and then by
    # line at earliest common diff
    if DEBUG_SORTING:
      print "<<<<< Comparing at first_common=%d %s and %s" %(first_common_diff_i, a,b)

    if lt_at_diff(a, b, prev_diff_i):
      if DEBUG_SORTING:
        print "Lines are < at prev diff", prev_diff_i
      return True
    if lt_at_diff(a, b, first_common_diff_i):
      if DEBUG_SORTING:
        print "Lines are < at first diff", first_common_diff_i
      return True
    else:
      if DEBUG_SORTING:
        print "Lines are !<"
      return False


  def __eq__(a, b):
    def eq_at_diff(a, b, diff_i):
      a_file = a._nodehistory[diff_i]._filename
      b_file = b._nodehistory[diff_i]._filename
      a_line = a._nodehistory[diff_i]._line
      b_line = b._nodehistory[diff_i]._line
      if a._kind == FragmentBoundNode.END:
        a_line += 1
      if b._kind == FragmentBoundNode.END:
        b_line += 1
      if a_file != b_file:
        if DEBUG_GROUPING:
          print "file %s != %s at diff %d" %(a_file, b_file, diff_i)
        return False
      if a_line != b_line:
        if DEBUG_GROUPING:
          print "line %d != %d at diff %d" %(a_line, b_line, diff_i)
        return False
      #return a_file == b_file and a_line == b_line
      return True

    if DEBUG_GROUPING:
      print "===== Comparing %s and %s" %(a,b)
    common_diffs = a._nodehistory.viewkeys() & b._nodehistory.viewkeys()
    common_diffs -= {a._startdiff_i-1, b._startdiff_i-1}
    first_common_diff_i = min(common_diffs)
    prev_diff_i = first_common_diff_i - 1

    #print "Comparing (common diff %d) %s and %s" %(first_common_diff_i, a, b)
    #print "Keys:", (a_file, a_line, a._kind, a._startdiff_i), "==", (b_file, b_line, b._kind, b._startdiff_i)
    # If a start and an end does not share a startdiff then it is safe to
    # group them even though their kinds differ because it will still be
    # possible to distinguish the bounds.
    if a._kind != b._kind and a._startdiff_i == b._startdiff_i:
      if DEBUG_GROUPING:
        print "kind %d != %d and same startdiff %d" %(a._kind, b._kind, a._startdiff_i)
    if eq_at_diff(a, b, first_common_diff_i) \
        and eq_at_diff(a, b, prev_diff_i) \
        and (a._kind == b._kind or
             a._startdiff_i != b._startdiff_i):
      if DEBUG_GROUPING:
        print "Lines are =="
      return True
    else:
      if DEBUG_GROUPING:
        print "Lines are !="
      return False


  def __init__(self, node):
    self._startdiff_i = node._diff_i
    # Initialize history with a base node that was created
    # by some previous diff (startdiff - 1) so that
    # when this node gets updated with startdiff it will be in sync.
    self._nodehistory = {self._startdiff_i-1 : node}
    self._kind = node._kind

  def __repr__(self):
    return " \n<FragmentBoundLine: %d, %s>" % (
      self._startdiff_i,
      ''.join(["\n %d: %s" %(key, val)
              for key,val in sorted(self._nodehistory.iteritems())]))

  def last(self):
    return self._nodehistory[max(self._nodehistory.viewkeys())]

  def update(self, diff_i, filename, line):
    # Shallow copy previous
    if diff_i < 0:
      diff_i = 0
    print "Updating %s with (%d, %s, %d)" %(self, diff_i, filename, line)
    updated_node = copy.copy(self._nodehistory[diff_i-1])

    updated_node._diff_i = diff_i
    updated_node._file = filename
    updated_node._line = line
    self._nodehistory[diff_i] = updated_node


def earliest_diff(node_lines):
  return min([nl._startdiff_i for nl in node_lines])

def print_node_line_relation_table(node_lines):
  """
  Print a grid of '=' indicating which node_line
  is equal to which.
  """
  N = len(node_lines)
  grid = [['.' for i in xrange(N)] for j in xrange(N)]
  for r in range(N):
    for c in range(N):
      if node_lines[r] == node_lines[c]:
        grid[r][c] = '='
  for row in grid:
    print ''.join(row)



# TODO: Convert to just grouping. Howto group nodes in node lines?
# Group node lines that are equal, i.e. that at the first
# common diff are at the same position and of the same kind.
# As a note, at any subsequent diffs they will consequently be the same too.
def group_fragment_bound_lines(node_lines):
  """
  Takes a list of up-to date list of bound node lines.
  Returns a list with ordered bound node lines
  grouped by position (file, line) at first common diff.
  """
  node_lines = sorted(node_lines)
  if DEBUG_SORTING:
    print "Sorted lines:", node_lines
  groups = []
  for node_line in node_lines:
    added = False
    for group in groups:
      inter_diff_collision = False
      for member in group:
        if member._startdiff_i == node_line._startdiff_i \
        and member._kind != node_line._kind:
          inter_diff_collision = True
          break
      if node_line == group[0] and not inter_diff_collision:
        # Append to group
        group += [node_line]
        added = True
        break
    if not added:
      # Create new group
      #print "New group for", node_line
      groups += [[node_line]]
  return groups


# Iterate over the list, placing markers at column i row j if i >= a start node of revision j and i < end node of same revision

def generate_matrix(ast):
  print "AST:", ast
  node_lines = update_all_positions_to_latest(ast._patches)
  if DEBUG_GROUPING:
    print_node_line_relation_table(node_lines)
  print "Node lines:", node_lines

  grouped_node_lines = group_fragment_bound_lines(node_lines)
  print "Grouped lines:", grouped_node_lines
  #bound_list = generate_fragment_bound_list(ast)

  n_rows = len(ast._patches)
  n_cols = len(grouped_node_lines)
  print "Matrix size: rows, cols: ", n_rows, n_cols
  matrix = [['.' for i in xrange(n_cols)] for j in xrange(n_rows)]
  for r in range(n_rows):
    diff_i = r
    inside_fragment = False
    for c in range(n_cols):
      node_line_group = grouped_node_lines[c]
      print "%d,%d: %s" %(r, c, node_line_group)
      if True: #earliest_diff(node_line_group) <= diff_i:
        for node_line in node_line_group:
          # If node belongs in on this row
          if node_line._startdiff_i == diff_i:
            inside_fragment = (node_line._kind == FragmentBoundNode.START)
            print "Setting inside_fragment =", inside_fragment
            # If it was updated to False:
            if not inside_fragment:
              # False overrides True so that if start and end from same diff
              # appear in same group we don't get stuck at True
              break
        print "%d,%d: %d" %(r, c, inside_fragment)
        if inside_fragment:
          matrix[r][c] = '#'
  return matrix

def main():
  pp = PatchParser()
  lines = [line.rstrip() for line in sys.stdin]
  diff_list =  pp.parse(lines)
  print diff_list
  matrix = generate_matrix(diff_list)
  for row in matrix:
    print ''.join(row)


if __name__ == '__main__':
  main()
