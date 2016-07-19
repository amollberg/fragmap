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

def nonnull_file(file_patch_header):
  def is_null(fn):
    return fn == '/dev/null'
  if not is_null(file_patch_header._newfile):
    return file_patch_header._newfile
  if not is_null(file_patch_header._oldfile):
    return file_patch_header._oldfile
  # Both files are null files
  return None

def update_positions(old_diff, patch):
  def update_file_positions(file_ast, file_patch):
    """
    Update the AST to how it should look after the patch has been applied.
    """
    def update_range(fragment_range, file_patch):
      # patch fragment +a,b -c,d means the map [a,b[ -> [c,d[
      # previous lines are unaffected, mapping e -> e
      # start lines inside fragment map e -> c
      # end lines inside fragment map e -> d
      # subsequent lines map as e -> e-b+d
      marker = None
      for patch_fragment in file_patch._fragments:
        if patch_fragment._header._oldrange._start <= fragment_range._start:
          marker = patch_fragment._header
        else:
          break
      if marker is None:
        # No fragments before the given range
        return
      if fragment_range._start < marker._oldrange._end:
        fragment_range._start = marker._newrange._start
      else:
        fragment_range._start += marker._newrange._end - marker._oldrange._end
      if fragment_range._end < marker._oldrange._end:
        fragment_range._end = marker._newrange._end
      else:
        fragment_range._end += marker._newrange._end - marker._oldrange._end
      
    # TODO: Verify that filenames are the same
    # TODO Ensure sorted fragments
    for ast_fragment in file_ast._fragments:
      print "Header before:", ast_fragment._header
      update_range(ast_fragment._header._oldrange, file_patch)
      update_range(ast_fragment._header._newrange, file_patch)
      print "Patch:", file_patch
      print "Header after:", ast_fragment._header

  for file_patch in patch._filepatches:
    for file_ast in old_diff._filepatches:
      if nonnull_file(file_ast._header) == file_patch._header._oldfile:
        update_file_positions(file_ast, file_patch)
        file_ast._header._oldfile = file_patch._header._newfile
        file_ast._header._newfile = file_patch._header._newfile
          

def update_positions_to_latest(old_diff, patch_list):
  """
  Update the positions of the AST old_ast through every patch
  in patch_list that is more recent than it.
  """
  for patch in patch_list:
    # TODO: Sort and filter by timestamp
    update_positions(old_diff, patch)
  
# For each commit: project fragment positions iteratively up past the latest commit
#  => a list of nodes, each pointing to commit and kind (start or end of fragment)

def update_all_positions_to_latest(diff_list):
  """
  Update all diffs to the latest patch, letting
  newer diffs act as patches for older diffs.
  Assumes diff_list is sorted in ascending time.
  """
  # For all diffs except the last which is already up to date.
  for i in range(len(diff_list) - 1):
    update_positions_to_latest(diff_list[i], diff_list[i+1:])
  return diff_list

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
    return "\n<Node: %s, (%s, %d), %d>" %(self._diff_i, self._filename, self._line, self._kind)
    

def extract_fragments(ast):
  fragment_list = []
  diff_list = ast._patches
  diff_i = 0
  for diff in diff_list:
    for file_patch in diff._filepatches:
      for fragment in file_patch._fragments:
        fragment_list += [
          FragmentBoundNode(diff, diff_i, file_patch, fragment, fragment._header._oldrange,
                            file_patch._header._oldfile, FragmentBoundNode.START),
          FragmentBoundNode(diff, diff_i, file_patch, fragment, fragment._header._oldrange,
                            file_patch._header._oldfile, FragmentBoundNode.END),
          FragmentBoundNode(diff, diff_i, file_patch, fragment, fragment._header._newrange,
                            file_patch._header._newfile, FragmentBoundNode.START),
          FragmentBoundNode(diff, diff_i, file_patch, fragment, fragment._header._newrange,
                            file_patch._header._newfile, FragmentBoundNode.END)
        ]
    diff_i += 1
  return fragment_list

def generate_fragment_bound_list(ast):
  """
  Takes an up-to date list of diffs.
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
  ast._patches = update_all_positions_to_latest(ast._patches)
  print "AST after update:", ast
  bound_list = generate_fragment_bound_list(ast)
  print "bound list:", bound_list
  n_rows = len(ast._patches)
  n_cols = len(bound_list)
  print "Matrix size: rows, cols: ", n_rows, n_cols
  matrix = [['.' for i in xrange(n_cols)] for j in xrange(n_rows)]
  for r in range(n_rows):
    inside_fragment = False
    item_i = 0
    for c in range(n_cols):
      for node in bound_list[c]:
        # If node belongs in on this row
        if node._diff_i == r:
          inside_fragment = (node._kind == FragmentBoundNode.START)
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
