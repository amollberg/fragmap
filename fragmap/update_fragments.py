#!/usr/bin/env python
import copy
from parse_patch import *


class FragmentBoundNode():
  # References back into the diffs
  _diff_i = None
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

  def __init__(self, diff_i, file_patch, fragment_i, fragment_range, kind):
    self._diff_i = diff_i
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
    return "<Node: (%s, %d), (%s, %d), %s>" %(self._diff_i, self._fragment_i, self._filename, self._line, kind_str)

class FragmentBoundLine():
  _nodehistory = None
  _startdiff_i = None
  _kind = None

  # Note: This ordering is not transitive so bound line sorting may be inconsistent
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
        debug.log(debug.sorting, "file %s < %s at diff %d" %(a_file, b_file, diff_i))
        return True
      if a_file == b_file and a_line < b_line:
        debug.log(debug.sorting, "line %d < %d at diff %d" %(a_line, b_line, diff_i))
        return True
      return False
    debug.log(debug.sorting, "<<<<< Comparing %s and %s" %(a,b))
    common_diffs = a._nodehistory.viewkeys() & b._nodehistory.viewkeys()
    common_diffs -= {a._startdiff_i-1, b._startdiff_i-1}
    first_common_diff_i = min(common_diffs)
    prev_diff_i = first_common_diff_i - 1
    # Order by filename at latest diff and then by
    # line at earliest common diff
    debug.log(debug.sorting, "First_common=", first_common_diff_i)

    if lt_at_diff(a, b, prev_diff_i):
      debug.log(debug.sorting, "Lines are < at prev diff", prev_diff_i)
      return True
    if lt_at_diff(a, b, first_common_diff_i):
      debug.log(debug.sorting, "Lines are < at first diff", first_common_diff_i)
      return True
    else:
      debug.log(debug.sorting, "Lines are !<")
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
        debug.log(debug.grouping, "file %s != %s at diff %d" %(a_file, b_file, diff_i))
        return False
      if a_line != b_line:
        debug.log(debug.grouping, "line %d != %d at diff %d" %(a_line, b_line, diff_i))
        return False
      return True

    debug.log(debug.grouping, "===== Comparing %s and %s" %(a,b))
    common_diffs = a._nodehistory.viewkeys() & b._nodehistory.viewkeys()
    common_diffs -= {a._startdiff_i-1, b._startdiff_i-1}
    first_common_diff_i = min(common_diffs)
    prev_diff_i = first_common_diff_i - 1

    # If a start and an end does not share a startdiff then it is safe to
    # group them even though their kinds differ because it will still be
    # possible to distinguish the bounds.
    if a._kind != b._kind and a._startdiff_i == b._startdiff_i:
      debug.log(debug.grouping, "kind %d != %d and same startdiff %d" %(a._kind, b._kind, a._startdiff_i))
    if eq_at_diff(a, b, first_common_diff_i) \
        and eq_at_diff(a, b, prev_diff_i) \
        and (a._kind == b._kind or
             a._startdiff_i != b._startdiff_i):
      debug.log(debug.grouping, "Lines are ==")
      return True
    else:
      debug.log(debug.grouping, "Lines are !=")
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

  def update_unchanged(self, diff_i):
    """
    Update the node line with no changes. Simply clones
    the latest node, adds it to the history and returns it.
    """
    # Shallow copy previous
    if diff_i < 0:
      diff_i = 0
    updated_node = copy.copy(self._nodehistory[diff_i-1])
    self._nodehistory[diff_i] = updated_node
    return updated_node

  def update(self, diff_i, filename, line):
    # Copy previous node without changing anything
    updated_node = self.update_unchanged(diff_i)
    debug.log(debug.update, "Updating %s with (%d, %s, %d)" %(self, diff_i, filename, line))
    # Apply changes to new node
    updated_node._diff_i = diff_i
    updated_node._filename = filename
    updated_node._line = line


def update_new_bound(fragment, bound_kind):
  """
  Update a bound that belongs to the current diff. Simply apply whatever
  fragment it belongs to.
  """
  line = 0
  marker = fragment._header
  if bound_kind == FragmentBoundNode.START:
    line = marker._newrange._start
    debug.log(debug.update, "Setting new start line to", line)
  elif bound_kind == FragmentBoundNode.END:
    line = marker._newrange._end
    debug.log(debug.update, "Setting new end line to", line)
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
  debug.log(debug.update, "Update_line:", line, bound_kind, file_patch)
  debug.log(debug.update, "Marker:", marker)
  # TODO: Fix sorting of node line groups after this.
  if marker is not None:
    if line <= marker._oldrange._end:
      # line is inside the range
      debug.log(debug.update, "Line %d is inside range %s" %(line, marker._oldrange))
      if bound_kind == FragmentBoundNode.START:
        line = marker._newrange._start
        debug.log(debug.update, "Setting start line to", line)
      elif bound_kind == FragmentBoundNode.END:
        line = marker._newrange._end
        debug.log(debug.update, "Setting end line to", line)
    else:
      # line is after the range
      debug.log(debug.update, "Line %d is after range %s; shifting %d" % (
        line, marker._oldrange, marker._newrange._end - marker._oldrange._end))
      line += marker._newrange._end - marker._oldrange._end
  else:
    # line is before any fragment; no update required
    pass
  return line


def update_line(line, bound_kind, fragment, startdiff_i, diff_i, file_patch):
  # If the current diff is the start diff of the
  # affected node line:
  if diff_i == startdiff_i:
    # The bound is new
    return update_new_bound(fragment, bound_kind)
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
    debug.log(debug.update, "Node before:", node_line.last())
    node_line.update(diff_i, file_patch._header._newfile,
                     update_line(node_line.last()._line,
                                 node_line.last()._kind,
                                 node_line.last()._fragment,
                                 node_line._startdiff_i,
                                 diff_i,
                                 file_patch))
    debug.log(debug.update, "Node after:", node_line.last())


def update_positions(node_lines, patch, diff_i):
  """
  Update all node lines with a multi-file patch.
  """
  if len(patch._filepatches) > 0:
    for file_patch in patch._filepatches:
      oldfile = file_patch._header._oldfile
      file_node_lines = []
      for nl in node_lines:
        debug.log(debug.update, "last:", nl.last()._filename)
        if nl.last()._filename == oldfile:
          file_node_lines += [nl]
        else:
          nl.update_unchanged(diff_i)
      debug.log(debug.update, "Updating file:", oldfile)
      debug.log(debug.update, "Node lines:", file_node_lines)
      update_file_positions(file_node_lines, file_patch, diff_i)
      debug.log(debug.update, "Updated node lines:", file_node_lines)
  else:
    # No fragments in patch
    debug.log(debug.update, "No fragments in patch")
    for nl in node_lines:
      debug.log(debug.update, "last:", nl.last()._filename)
      nl.update_unchanged(diff_i)
  return node_lines


def extract_nodes(diff, diff_i):
  node_list = []
  for file_patch in diff._filepatches:
    for fragment_i in range(len(file_patch._fragments)):
      fragment = file_patch._fragments[fragment_i]
      node_list += [
        FragmentBoundNode(diff_i, file_patch, fragment_i, fragment._header._oldrange,
                          FragmentBoundNode.START),
        FragmentBoundNode(diff_i, file_patch, fragment_i, fragment._header._oldrange,
                          FragmentBoundNode.END),
        ]
  return node_list


def extract_node_lines(diff, diff_i):
  return map(FragmentBoundLine, extract_nodes(diff, diff_i))


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
  debug.log(debug.update, "update_all_positions:", diff_list)
  node_line_list = []
  for i in range(len(diff_list)):
    node_line_list += extract_node_lines(diff_list[i], i)
    debug.log(debug.update, "= All to latest: All extracted:", i, node_line_list)
    update_positions(node_line_list, diff_list[i], i)
    debug.log(debug.update, "= All to latest: All updated:", node_line_list)
  return node_line_list
