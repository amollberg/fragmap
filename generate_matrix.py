#!/usr/bin/env python

from parse_patch import *
from update_fragments import *
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


DEBUG_GRID = False


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
  if DEBUG_GRID:
    print "Matrix size: rows, cols: ", n_rows, n_cols
  matrix = [['.' for i in xrange(n_cols)] for j in xrange(n_rows)]
  for r in range(n_rows):
    diff_i = r
    inside_fragment = False
    for c in range(n_cols):
      node_line_group = grouped_node_lines[c]
      if DEBUG_GRID:
        print "%d,%d: %s" %(r, c, node_line_group)
      if True: #earliest_diff(node_line_group) <= diff_i:
        for node_line in node_line_group:
          # If node belongs in on this row
          if node_line._startdiff_i == diff_i:
            inside_fragment = (node_line._kind == FragmentBoundNode.START)
            if DEBUG_GRID:
              print "Setting inside_fragment =", inside_fragment
            # If it was updated to False:
            if not inside_fragment:
              # False overrides True so that if start and end from same diff
              # appear in same group we don't get stuck at True
              break
        if DEBUG_GRID:
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
