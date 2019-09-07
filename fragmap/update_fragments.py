#!/usr/bin/env python
import copy
from .load_commits import BinaryHunk, nonnull_file, oldrange, newrange
from . import debug


class FragmentBoundNode():
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

  def __init__(self, filename, line, kind):
    self._filename = filename
    self._line = line
    self._kind = kind

  def __repr__(self):
    kind_str = "START"
    if self._kind == FragmentBoundNode.END:
      kind_str = "END"
    return "<Node: (%s, %d), %s>" %(self._filename, self._line, kind_str)

class FragmentDualBoundNode():
  # References back into the diffs
  _diff_i = None
  _fragment = None

  # Info to sort on
  _filename = None

  # FragmentBoundNodes
  start = None
  end = None

  def __lt__(a, b):
    return a.start < b.start or (
      a.start == b.start and a.end < b.end)

  def __init__(self, diff_i, file_patch, fragment_i, start_line, end_line):
    self._diff_i = diff_i
    self._file_patch = file_patch
    if file_patch.delta.is_binary:
      self._fragment = BinaryHunk(file_patch)
    else:
      self._fragment = file_patch.hunks[fragment_i]
    self._fragment_i = fragment_i
    self._filename = nonnull_file(file_patch.delta)
    self.start = FragmentBoundNode(self._filename, start_line, FragmentBoundNode.START)
    self.end = FragmentBoundNode(self._filename, end_line, FragmentBoundNode.END)

  def set_filename(self, new_filename):
    self._filename = new_filename
    self.start._filename = new_filename
    self.end._filename = new_filename

  def with_incremented_end(self):
    dualnode = FragmentDualBoundNode(self._diff_i,
                                     self._file_patch,
                                     self._fragment_i,
                                     self.start._line,
                                     self.end._line + 1)
    # Some fields not in the constructor get updated afterwards
    dualnode._fragment = self._fragment
    dualnode.set_filename(self._filename)
    return dualnode


  def __repr__(self):
    return "<DualNode: (%s, %d), (%s, %s)>" %(self._diff_i, self._fragment_i, self.start, self.end)

class FragmentBoundLine():
  _nodehistory = None
  _startdiff_i = None
  _kind = None

  # Note: This ordering is not transitive so bound line sorting may be inconsistent
  def __lt__(a, b):
    def lt_at_diff(a, b, diff_i):
      return a._nodehistory[diff_i].with_incremented_end() < b._nodehistory[diff_i].with_incremented_end()

    debug.get('sorting').debug("<<<<< Comparing %s and %s", a,b)
    common_diffs = set(a._nodehistory.keys()) & set(b._nodehistory.keys())
    common_diffs -= {a._startdiff_i-1, b._startdiff_i-1}
    first_common_diff_i = min(common_diffs)
    prev_diff_i = first_common_diff_i - 1
    # Order by filename at latest diff and then by
    # line at earliest common diff
    debug.get('sorting').debug("First_common=%d", first_common_diff_i)

    if lt_at_diff(a, b, prev_diff_i):
      debug.get('sorting').debug("Lines are < at prev diff %d", prev_diff_i)
      return True
    if lt_at_diff(a, b, first_common_diff_i):
      debug.get('sorting').debug("Lines are < at first diff %d", first_common_diff_i)
      return True
    else:
      debug.get('sorting').debug("Lines are !<")
      return False


  # Helper function for __eq__
  def eq_at_diff(a, b, diff_i):
    def comparison_element(node):
      return (node._filename, node.start._line, node.end._line)
    return (comparison_element(a._nodehistory[diff_i].with_incremented_end()) ==
            comparison_element(b._nodehistory[diff_i].with_incremented_end()))


  def __eq__(a, b):
    # # If a start and an end share a startdiff then it is not safe to
    # # group them even though their kinds differ because it will not be
    # # possible to distinguish the bounds.
    # if a._kind != b._kind and a._startdiff_i == b._startdiff_i:
    #   debug.get('grouping').debug("kind %d != %d and same startdiff %d", a._kind, b._kind, a._startdiff_i)
    #   return False

    debug.get('grouping').debug("===== Comparing %s and %s", a, b)
    common_diffs = set(a._nodehistory.keys()) & set(b._nodehistory.keys())
    common_diffs -= {a._startdiff_i-1, b._startdiff_i-1}
    first_common_diff_i = min(common_diffs)
    prev_diff_i = first_common_diff_i - 1

    # If a start and an end does NOT share a startdiff then it is safe to
    # group them.
    if a.eq_at_diff(b, first_common_diff_i) \
        and a.eq_at_diff(b, prev_diff_i) \
        and a._startdiff_i != b._startdiff_i:
      debug.get('grouping').debug("Lines are ==")
      return True
    else:
      debug.get('grouping').debug("Lines are !=")
      return False


  def __init__(self, dual_node):
    self._startdiff_i = dual_node._diff_i
    # Initialize history with a base node that was created
    # by some previous diff (startdiff - 1) so that
    # when this node gets updated with startdiff it will be in sync.
    self._nodehistory = {self._startdiff_i-1 : dual_node}

  def __repr__(self):
    return " \n<FragmentBoundLine: %d, %s>" % (
      self._startdiff_i,
      ''.join(["\n %d: %s" %(key, val)
              for key,val in sorted(self._nodehistory.items())]))

  def last(self):
    return self._nodehistory[max(self._nodehistory.keys())]

  def update_unchanged(self, diff_i):
    """
    Update the node line with no changes. Simply clones
    the latest node, adds it to the history and returns it.
    """
    if diff_i not in self._nodehistory:
      # Shallow copy previous
      if diff_i < 0:
        diff_i = 0
      updated_node = copy.copy(self._nodehistory[diff_i-1])
      self._nodehistory[diff_i] = updated_node
    return self._nodehistory[diff_i]

  def update(self, diff_i, filename, start_line, end_line):
    # Copy previous node without changing anything
    updated_node = self.update_unchanged(diff_i)
    debug.get('update').debug("Updating %s with (%d, %s, (%d, %d))", self, diff_i, filename, start_line, end_line)
    # Apply changes to new node
    updated_node._diff_i = diff_i
    updated_node._filename = filename
    updated_node.start._line = start_line
    updated_node.end._line = end_line

def update_new_bound(fragment):
  """
  Update a bound that belongs to the current diff. Simply apply whatever
  fragment it belongs to.
  """
  marker = newrange(fragment)
  start_line = marker._start
  debug.get('update').debug("Setting new start line to %d", start_line)
  end_line = marker._end
  debug.get('update').debug("Setting new end line to %d", end_line)
  return start_line, end_line

def update_normal_line(line, bound_kind, fragment): # 4, START, (4,3) -> (4,8)
  if line <= oldrange(fragment)._end:
    if line >= oldrange(fragment)._start:
      print(line, "inside", oldrange(fragment))
      # line is inside the range
      debug.get('update').debug("Line %d is inside range %s", line, oldrange(fragment))
      if bound_kind == FragmentBoundNode.START:
        line = newrange(fragment)._start
        debug.get('update').debug("Setting start line to %d", line)
      elif bound_kind == FragmentBoundNode.END:
        line = newrange(fragment)._end
        debug.get('update').debug("Setting end line to %d", line)
  else:
    # line is after the range
    debug.get('update').debug("Line %d is after range %s; shifting %d" % (
      line, oldrange(fragment), newrange(fragment)._end - oldrange(fragment)._end))
    line += newrange(fragment)._end - oldrange(fragment)._end
  return line

def update_inherited_bound(start_line, end_line, file_patch):
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
  for patch_fragment in file_patch.hunks:
    if oldrange(patch_fragment)._start <= start_line:
      marker = patch_fragment
    else:
      break
  if marker is None and file_patch.delta.is_binary:
    marker = BinaryHunk(file_patch)
  debug.get('update').debug("Update_inherited_bound: (%d, %d) %s", start_line, end_line, file_patch)
  debug.get('update').debug("Marker: %s", marker)
  # TODO: Fix sorting of node line groups after this.
  if marker is not None:
    if end_line < start_line and oldrange(marker)._start == start_line:
      start_line = start_line
      # Note that we pass start_line to make sure that end_line is updated as if it was inside the marker range
      end_line = newrange(marker)._end #update_normal_line(start_line, FragmentBoundNode.END, marker)
    else:
      start_line = update_normal_line(start_line, FragmentBoundNode.START, marker)
      end_line = update_normal_line(end_line, FragmentBoundNode.END, marker)
  else:
    # line is before any fragment; no update required
    pass
  return start_line, end_line


def update_bound(dual_node, fragment, startdiff_i, diff_i, file_patch):
  # If the current diff is the start diff of the
  # affected node line:
  if diff_i == startdiff_i:
    # The bound is new
    return update_new_bound(fragment)
  else:
    # The bound is inherited
    return update_inherited_bound(dual_node.start._line, dual_node.end._line, file_patch)


def update_file_positions(file_node_lines, file_patch, diff_i):
  """
  Update all the nodes belonging in a file with a file patch.
  """
  # TODO: Verify that filenames are the same
  # TODO Ensure sorted fragments
  for node_line in file_node_lines:
    debug.get('update').debug("Node before: %s", node_line.last())
    node_line.update(diff_i, file_patch.delta.new_file.path,
                     *update_bound(node_line.last(),
                                   node_line.last()._fragment,
                                   node_line._startdiff_i,
                                   diff_i,
                                   file_patch))
    debug.get('update').debug("Node after: %s", node_line.last())


def update_positions(node_lines, patch, diff_i):
  """
  Update all node lines with a multi-file patch.
  """
  if len(patch.filepatches) > 0:
    for file_patch in patch.filepatches:
      oldfile = file_patch.delta.old_file.path
      file_node_lines = []
      for nl in node_lines:
        debug.get('update').debug("last: %s", nl.last()._filename)
        if nl.last()._filename == oldfile:
          file_node_lines += [nl]
        else:
          nl.update_unchanged(diff_i)
      debug.get('update').debug("Updating file: %s", oldfile)
      debug.get('update').debug("Node lines: %s", file_node_lines)
      update_file_positions(file_node_lines, file_patch, diff_i)
      debug.get('update').debug("Updated node lines: %s", file_node_lines)
  else:
    # No fragments in patch
    debug.get('update').debug("No fragments in patch")
    for nl in node_lines:
      debug.get('update').debug("last: %s", nl.last()._filename)
      nl.update_unchanged(diff_i)
  return node_lines


def extract_dual_nodes(diff, diff_i):
  dual_node_list = []
  for file_patch in diff.filepatches:
    for fragment_i in range(len(file_patch.hunks)):
      fragment = file_patch.hunks[fragment_i]
      dual_node_list += [FragmentDualBoundNode(diff_i, file_patch, fragment_i, oldrange(fragment)._start, oldrange(fragment)._end)]
    if file_patch.delta.is_binary:
      binary_fragment = BinaryHunk(file_patch)
      dual_node_list += [FragmentDualBoundNode(diff_i, file_patch, -1, oldrange(binary_fragment)._start, oldrange(binary_fragment)._end)]
  return dual_node_list


def extract_node_lines(diff, diff_i):
  return list(map(FragmentBoundLine, extract_dual_nodes(diff, diff_i)))


# For each commit: project fragment positions iteratively up past the latest commit
#  => a list of dual nodes, each pointing to commit and start and end of fragment

def update_all_positions_to_latest(diff_list):
  """
  Update all diffs to the latest patch, letting
  newer diffs act as patches for older diffs.
  Assumes diff_list is sorted in ascending time.
  """
  debug.get('update').debug("update_all_positions: %s", diff_list)
  node_line_list = []
  for i in range(len(diff_list)):
    node_line_list += extract_node_lines(diff_list[i], i)
    debug.get('update').debug("= All to latest: All extracted: %d %s", i, node_line_list)
    update_positions(node_line_list, diff_list[i], i)
    debug.get('update').debug("= All to latest: All updated: %s", node_line_list)
  return node_line_list
