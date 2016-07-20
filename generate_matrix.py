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

# TODO:
# Generate nodes as we update the diff list, not just after every one 
# Each update has to also update each node and sort new nodes into the
# list of existing. We may be able to work recursively, patching older 
# diffs and adding new nodes. We probably will never remove nodes as to
# signal that fragments have been joined together. They still need to
# be represented at the last level as separate (?).

def nonnull_file(file_patch_header):
  def is_null(fn):
    return fn == '/dev/null'
  if not is_null(file_patch_header._newfile):
    return file_patch_header._newfile
  if not is_null(file_patch_header._oldfile):
    return file_patch_header._oldfile
  # Both files are null files
  return None

def update_line(line, bound_kind, file_patch):
  """
  Update one line in a file with a file patch.
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
  if marker is not None:
    is_creation = (marker._oldrange._start == marker._oldrange._end)
    if line < marker._oldrange._end or (
      is_creation and line == marker._oldrange._end):

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
  return line


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
                                 file_patch))
    print "Node after:", node_line.last()


def extract_nodes(diff, diff_i):
  node_list = []
  for file_patch in diff._filepatches:
    for fragment in file_patch._fragments:
      node_list += [
        FragmentBoundNode(diff, diff_i, file_patch, fragment, fragment._header._oldrange,
                          file_patch._header._oldfile, FragmentBoundNode.START),
        FragmentBoundNode(diff, diff_i, file_patch, fragment, fragment._header._oldrange,
                          file_patch._header._oldfile, FragmentBoundNode.END),
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


  def __init__(self, diff, diff_i, file_patch, fragment, fragment_range, filename, kind):
    self._diff = diff
    self._diff_i = diff_i
    self._file = file_patch
    self._fragment = fragment
    self._filename = filename
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

  def __lt__(a, b):
    common_diffs = a._nodehistory.viewkeys() & b._nodehistory.viewkeys()
    first_common_diff_i = min(common_diffs)
    last_common_diff_i = max(common_diffs)
    # Order by filename at latest diff and then by
    # line at earliest common diff
    a_file = a._nodehistory[last_common_diff_i]._filename
    b_file = b._nodehistory[last_common_diff_i]._filename
    a_line = a._nodehistory[first_common_diff_i]._line
    b_line = b._nodehistory[first_common_diff_i]._line
    return a_file < b_file or (a_file == b_file and a_line < b_line)

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
              for key,val in self._nodehistory.iteritems()]))

  def last(self):
    return self._nodehistory[max(self._nodehistory.viewkeys())]

  def update(self, diff_i, filename, line):
    # Shallow copy previous
    if diff_i < 0:
      diff_i = 0
    updated_node = copy.copy(self._nodehistory[diff_i-1])

    updated_node._diff_i = diff_i
    updated_node._file = filename
    updated_node._line = line
    self._nodehistory[diff_i] = updated_node


# TODO: Convert to just grouping. Howto group nodes in node lines?
def generate_fragment_bound_list(ast):
  """
  Takes a list of  up-to date list of diffs.
  Returns a list with ordered fragment bounds
  grouped by position (file, line).
  """
  node_list = sorted(extract_fragments(ast))
  grouped_list = [[]]
  last_key = None
  last_i = 0
  for node in node_list:
    if node._line == 0:
      continue
    key = (node._filename, node._line)
    if last_key is None:
      last_key = key
    if key != last_key:
      last_i += 1
      # Append new sublist
      grouped_list += [[]]
    # Append to sublist at index last_i
    grouped_list[last_i] += [node]
    last_key = key
  return grouped_list

      
# Iterate over the list, placing markers at column i row j if i >= a start node of revision j and i < end node of same revision

def generate_matrix(ast):
  print "AST:", ast
  node_lines = update_all_positions_to_latest(ast._patches)
  print "Node lines:", node_lines
  #bound_list = generate_fragment_bound_list(ast)
  n_rows = len(ast._patches)
  n_cols = len(node_lines) # TODO: Reduce this after they have been grouped
  print "Matrix size: rows, cols: ", n_rows, n_cols
  matrix = [['.' for i in xrange(n_cols)] for j in xrange(n_rows)]
  for r in range(n_rows):
    diff_i = r
    inside_fragment = False
    item_i = 0
    for c in range(n_cols):
      node_line = node_lines[c]
      print "%d,%d: %s" %(r,c, node_line)
      # If node belongs in on this row
      if node_line._startdiff_i == diff_i:
        inside_fragment = (node_line._kind == FragmentBoundNode.START)
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
