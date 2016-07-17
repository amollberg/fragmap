#!/usr/bin/env python

from parse_patch import *

def update_positions(old_ast, patch):
  ast = copy(old_ast)
  def update_file_positions(file_ast, file_patch):
    """
    Update the AST to how it should look after the patch has been applied.
    """
    # TODO: Remove this return
    # Naive version - no update
    return
    
    # TODO: Verify that filenames are the same
    # patch fragment +a,b -c,d means the map [a,a+b] -> [c,c+d]
    # previous lines are unaffected, mapping e -> e
    # subsequent lines map as e -> e-(a+b)+c+d
    # TODO Ensure sorted fragments
    #for patch_fragment in file_patch._fragments:
    #  for ast_fragment in file_ast:
    #    updated_header = ast_fragment._header
    #    if ast_fragment._header._oldrange._start >= patch_fragment._header._oldrange._start:
    #      if ast_fragment._header._oldrange._start <= patch_fragment._header._oldrange._end:
    #        # Old start is inside patch fragment; absorb to the patch start
    #        updated_header._oldrange._start = patch_fragment._header._newrange._start
    #        # New start has to absorb to patch start as well
    #        updated_header._newrange._start = patch_fragment._header._newrange._start
    #      else:
    #        # Old start is after the patch fragment; shift the starts
  # TODO
  pass
          

def update_positions_to_latest(old_diff, patch_list):
  """
  Update the positions of the AST old_ast through every patch
  in patch_list that is more recent than it.
  """
  # TODO
  pass
  
# For each commit: project fragment positions iteratively up past the latest commit
#  => a list of nodes, each pointing to commit and kind (start or end of fragment)

def update_all_positions_to_latest(ast_list):
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
  _diff_i = None
  _file_i = None
  _fragment_i = None
  
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
    return a._filename < b._filename or a._line < b._line


  def __init__(self, diff_list, diff_i, file_i, fragment_i, kind):
    self._diff_i = diff_i
    self._file_i = file_i
    self._fragment_i = fragment_i
    self._filename = diff_list[diff_i]._filepatches[file_i]._header._oldfile
    fragment_range = diff_list[diff_i]._filepatches[file_i]._fragments[fragment_i]._header._oldrange
    if kind == FragmentBoundNode.START:
      self._line = fragment_range._start
    elif kind == FragmentBoundNode.END:
      self._line = fragment_range._end
    self._kind = kind

  def __repr__(self):
    return "[Node: %d, %d, %d, (%s, %d), %d]" %(self._diff_i, self._file_i, self._fragment_i, self._filename, self._line, self._kind)
    

def extract_fragments(ast):
  fragment_list = []
  diff_list = ast._patches
  for diff_i in range(len(diff_list)):
    for file_i in range(len(diff_list[diff_i]._filepatches)):
      for fragment_i in range(len(diff_list[diff_i]._filepatches[file_i]._fragments)):
        fragment_list += [
          FragmentBoundNode(diff_list, diff_i, file_i, fragment_i, FragmentBoundNode.START),
          FragmentBoundNode(diff_list, diff_i, file_i, fragment_i, FragmentBoundNode.END)
        ]
  return fragment_list

def generate_fragment_bound_list(ast):
  """
  Takes an up-to date list of diffs.
  Returns a list with ordered fragment bounds.
  """
  return sorted(extract_fragments(ast))

      
# Iterate over the list, placing markers at column i row j if i >= a start node of revision j and i < end node of same revision

def generate_matrix(ast):
  bound_list = generate_fragment_bound_list(ast)
  print "bound list:", bound_list
  n_rows = len(ast._patches)
  n_cols = len(bound_list)
  print "Matrix size: rows, cols: ", n_rows, n_cols
  matrix = [['.'] * n_cols] * n_rows
  for r in range(n_rows):
    inside_fragment = False
    item_i = 0
    for c in range(n_cols):
      inside_fragment = (bound_list[r]._kind == FragmentBoundNode.START and bound_list[r]._diff_i == r)
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
