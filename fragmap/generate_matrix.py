#!/usr/bin/env python

from parse_patch import *
from update_fragments import *
import debug
# Hierarchy:
# AST
#  Patch
#   PatchHeader
#    _hash
#    _message
#   FilePatch
#     FilePatchHeader
#      _oldfile
#      _newfile
#     Fragment
#      _content
#      FragmentHeader
#       Range _oldrange
#        _start
#        _end
#       Range _newrange
#        _start
#        _end
# FragmentBoundLine
#  _startdiff_i
#  FragmentBoundNode
#   _diff_i
#   _filename
#   _line
#   _kind
#   Fragment
#     (see above)



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
  node_lines = sorted(node_lines)
  if debug.is_logging(debug.grouping):
    print_node_line_relation_table(node_lines)
  debug.log(debug.sorting, "Sorted lines:", node_lines)
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


class Fragmap():

  def __init__(self, patches, grouped_node_lines):
    self.patches = patches
    self.grouped_node_lines = grouped_node_lines
    debug.log(debug.matrix, "Patches:", patches)

  @staticmethod
  def from_ast(ast):
    node_lines = update_all_positions_to_latest(ast._patches)
    grouped_lines = group_fragment_bound_lines(node_lines)
    return Fragmap(ast._patches, grouped_lines)

  def group_by_patch_connection(self):
    groups = self.grouped_node_lines
    # connections : '01001000..010' -> [node, node, ..]
    # The key strings are formatted such that
    # character i is 1 if the node line group has a node with start from patch i, and
    #                0 otherwise.
    connections = {}
    connections_key_index = []
    debug.log(debug.matrix, "Group by connection: Before:", groups)
    for c in range(len(groups)):
      group = groups[c]
      column = self.generate_column(c) # TODO: Pass previous column
      if column == [False] * self.get_n_patches():
        # Skip empty columns
        continue
      # Convert from list of True,False to string of 1,0
      key = ''.join(map(lambda b: '1' if b else '0', column))
      debug.log(debug.matrix, 'key:', key)
      if key in connections.keys():
        # Append to existing dict entry
        connections[key].extend(group)
      else:
        # Make a new entry in the dict
        connections[key] = group
        connections_key_index.append(key)
    debug.log(debug.matrix, "Group by connection: After:", connections)
    # Generate matrix
    n_rows = self.get_n_patches()
    n_cols = len(connections)
    debug.log(debug.grid, "Matrix size: rows, cols: ", n_rows, n_cols)
    matrix = [['.' for i in xrange(n_cols)] for j in xrange(n_rows)]
    for c in range(n_cols):
      key = connections_key_index[c]
      for r in range(n_rows):
        matrix[r][c] = '#' if key[r] == '1' else '.'
    bh = BriefFragmap(self.patches, connections.values())
    bh._prerendered_matrix = matrix
    return bh

  def get_n_patches(self):
    return len(self.patches)

  def get_patch(self, n):
    return self.patches[n]

  def generate_column(self, col_index, prev_column=None):
    c = col_index
    n_rows = self.get_n_patches()
    node_line_group = self.grouped_node_lines[c]
    # Initialize inside_fragment
    inside_fragment = prev_column
    if prev_column is None:
      if col_index <= 0:
        inside_fragment = [False] * n_rows
      else:
        inside_fragment = self.generate_column(col_index - 1)
    # For each row in the column
    for r in range(n_rows):
      diff_i = r
      debug.log(debug.grid, "%d,%d: %s" %(r, c, node_line_group))
      if True: #earliest_diff(node_line_group) <= diff_i:
        for node_line in node_line_group:
          # If node belongs in on this row
          if node_line._startdiff_i == diff_i:
            inside_fragment[r] = (node_line._kind == FragmentBoundNode.START)
            debug.log(debug.grid, "Setting inside_fragment =", inside_fragment)
            # If it was updated to False:
            if not inside_fragment[r]:
              # False overrides True so that if start and end from same diff
              # appear in same group we don't get stuck at True
              break
        debug.log(debug.grid, "%d,%d: %d" %(r, c, inside_fragment[r]))
    return inside_fragment

  # Iterate over the list, placing markers at column i row j if i >= a start node of revision j and i < end node of same revision
  def generate_matrix(self):
    debug.log(debug.matrix, "Grouped lines:", self.grouped_node_lines)

    n_rows = self.get_n_patches()
    n_cols = len(self.grouped_node_lines)
    debug.log(debug.grid, "Matrix size: rows, cols: ", n_rows, n_cols)
    matrix = [['.' for i in xrange(n_cols)] for j in xrange(n_rows)]
    prev_col = None
    for c in range(n_cols):
      column = self.generate_column(c, prev_col)
      for r in range(n_rows):
        if column[r]:
          matrix[r][c] = '#'
      prev_col = column
    return matrix

  def str(self):
    matrix = self.generate_matrix()
    return '\n'.join([''.join(row) for row in matrix])

class BriefFragmap(Fragmap):

  _prerendered_matrix = None

  def generate_matrix(self):
    return self._prerendered_matrix

def main():
  pp = PatchParser()
  lines = [line.rstrip() for line in sys.stdin]
  ast = pp.parse(lines)
  debug.log(debug.matrix, diff_list)
  h = Fragmap.from_ast(ast)
  print h.str()


if __name__ == '__main__':
  debug.parse_args()
  main()
