#!/usr/bin/env python

from .update_fragments import *
from . import debug
from .console_color import *

import collections

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
  grid = [['.' for i in range(N)] for j in range(N)]
  for r in range(N):
    for c in range(N):
      if node_lines[r] == node_lines[c]:
        grid[r][c] = '='
  for row in grid:
    print(''.join(row))

def decorate_matrix(m):
  debug.get('grid').debug("decorate_matrix")
  n_rows = len(m)
  if n_rows == 0:
    return m
  n_cols = len(m[0])
  # Mark dots between conflicts
  last_patch = [-1] * n_cols
  for r in range(n_rows):
    for c in range(n_cols):
      cell = m[r][c]
      if cell.kind == Cell.CHANGE:
        debug.get('grid').debug("last_patch %s %s %s", last_patch[c], c, r)
        if last_patch[c] >= 0:
          # Mark the cells inbetween
          start = last_patch[c]
          end = r
          for i in range(start, end + 1):
            # If not yet decorated
            if m[i][c].kind == Cell.NO_CHANGE:
              m[i][c].kind = Cell.BETWEEN_CHANGES
        last_patch[c] = r

# Properties:
#   Each node line is present in every diff from its introduction to the latest diff
#   If node line a <= b on diff i then a <= b on diff i+n with equality implying equality
#   If node line a, b are in the same file on diff i then they are in the same file on all diffs
# Establish a partitioning over equivalence ~ such that a ~ b <=> they belong on the same column
# <=> a == b on every diff on which they both occur

# Divide up by file (across history)
# order node lines (separate start and end) by their line enumber in the latest diff
#   end  >= start
#   ones that are on the same line, recursively order by line number in previous diff, or stop
def new_group_fragment_bound_lines(nodelines):
  """
  Return {file: [set([nodeline, nodeline]), ...], ...}
  """
  def group_fragment_bound_lines_same_file(lines, diff_i):
    """
    Return [set([nodeline, ...]), ...]
    """
    def kind_of_line(line):
      return next(iter(line._nodehistory.values()))._kind
    linegroups = {}
    later_startlines = set([])
    later_endlines = set([])
    for line in lines:
      if diff_i in line._nodehistory:
        line_number = line._nodehistory[diff_i]._line
        add_or_create(linegroups, line, line_number)
      elif kind_of_line(line) == FragmentBoundNode.START:
        later_startlines.add(line)
      elif kind_of_line(line) == FragmentBoundNode.END:
        later_endlines.add(line)
    ordered_linegroups = [lines for linenumber, lines in sorted(linegroups.items(), key=lambda kv: kv[0])]
    if ordered_linegroups:
      # "Round down" the end lines to the lowest group
      ordered_linegroups[0] |= later_endlines
      # "Round up" the start lines to the highest group
      ordered_linegroups[-1] |= later_startlines
    else:
      if later_endlines:
        ordered_linegroups.append(later_endlines)
      if later_startlines:
        ordered_linegroups.append(later_startlines)
    import tests.prettyprint
    print("endlines:",later_endlines)
    print("startlines:",later_startlines)
    print ('  '*diff_i, "line groups at diff", diff_i, tests.prettyprint.Formatter()(ordered_linegroups))
    if diff_i > 0:
      # Refine each group into groups according to previous diff
      ordered_linegroups = [refined_group
                            for group in ordered_linegroups
                            for refined_group in group_fragment_bound_lines_same_file(group, diff_i - 1)]
    return ordered_linegroups
  return {f: group_fragment_bound_lines_same_file(lines, n_patches(lines)-1)
          for f, lines in group_by_file(nodelines).items()}

def add_or_create(itemmap, item, key):
  if key not in itemmap:
    itemmap[key] = set([])
  if item not in itemmap[key]:
    itemmap[key].add(item)
def test_add_or_create():
  m = {1: set(['e']), 2: set([])}
  add_or_create(m, 'a', 2)
  assert m[2] == set(['a'])
  add_or_create(m, 'b', 1)
  assert m[1] == set(['e', 'b'])
  add_or_create(m, 'c', 3)
  assert m[3] == set(['c'])
test_add_or_create()

# Additionally group lines that are consecutive

# Each line
#  check all previously grouped lines:
#    get first common diff
#    same filename there?
# == OR
# Each diff index
#   get lines that are present there
#   put into groups by the (first diff index, filename)
#     if the filename has not group, create it, otherwise add to it
#   evolve the filenames to the next diff i by taking any line from each group and looking at the new filename(if nonnull)
#     (i, oldname) => (i+1, newname if nonnull otherwise oldname)
# Experiment results:
#   Today, renames do not create nodes, they are encoded in the filenames of the affected nodes
#   Moving a modifying commit back before a renaming commit does not cause conflict. The new filename gets the modification, the latter file with the old name does not.
#   => the later modification must NOT be on the same column as the renaming
#   Moving a modifying commit back before a deleting commit causes modify/delete conflict, cannot apply the deleting commit
#   => the later modification must be on the same column as the removing
#   => if the modify commit applied cleanly (i.e. was made for the same filename after restoration) then it must be as the SAME file (not just same name on a later commit, but the identically same) as the deleted file
#   ! diffs before and after a rename must ALSO share column
#     More important than matching restored files
#     Conflicting?
#       1. Create A,
#       2. Rename A to B,
#       3. Remove B
#       4. Create A
#       5. Modify A
#     5 MIGHT apply cleanly between 1 and 2 but that will cause conflict in 3 (modify/delete)
#       3 and 5 must be in the same column (modify/delete)
#       3 and 2 must not be in the same column (renames are transparent) -> Done already
# 1. old/new renamed file in the same column
# 2. same filename as before rename in the same column
# 3. commits applying cleanly iff non colliding in presence of modify/delete
# 1+2: If we move the later commit in between the commits when renamed. Conflict? If so, forget about handling modify/delete
#  the later commit is in the same column as what?!
# => Do NOT treat files with same filename as some previous file that was renamed/deleted. Line numbers cannot find correspondance
# => Map files by (earliest start index of containing node lines, filename)
def group_by_file(lines):
  def add_or_create(filemap, line, filekey):
    if filekey not in filemap:
      files[filekey] = []
    if line not in filemap[filekey]:
      files[filekey].append(line)
  def last_nonnull(line):
    for diff_i in reversed(sorted(line._nodehistory.keys())):
      filename = line._nodehistory[diff_i]._filename
      if filename in ['/dev/null', None]:
        continue
      return diff_i, filename
    return None, filename
  files = {}
  for line in lines:
    filekey = last_nonnull(line)
    add_or_create(files, line, filekey)
  return files


def n_patches(lines):
  return max([max(line._nodehistory.keys()) + 1 for line in lines])

# Group node lines that are equal, i.e. that at the first
# common diff are at the same position and of the same kind.
# As a note, at any subsequent diffs they will consequently be the same too.
def old_group_fragment_bound_lines(node_lines):
  node_lines = sorted(node_lines)
  if debug.is_logging('grouping'):
    print_node_line_relation_table(node_lines)
  debug.get('dco').debug("Sorted lines: %s", node_lines)
  groups = []
  for node_line in node_lines:
    added = False
    for group in groups:
      if node_line == group[0]:
        inter_diff_collision = False
        for member in group:
          if member._startdiff_i == node_line._startdiff_i \
          and member._kind != node_line._kind:
            print("Collision with", member)
            inter_diff_collision = True
            break
        if not inter_diff_collision:
          # Append to group
          debug.get('dco').debug("Adding %s to %s", node_line, group)
          group += [node_line]
          added = True
          break
    if not added:
      # Create new group
      debug.get('dco').debug("Adding new group with %s", node_line)
      groups += [[node_line]]
  return groups


class Cell(object):

  NO_CHANGE=100
  CHANGE=101
  BETWEEN_CHANGES=102

  def __init__(self, kind, node=None):
    self.kind = kind
    self.node = node

  def __repr__(self):
    return "<Cell kind=%s node=%s>" %(self.kind, self.node)

  def __eq__(self, other):
    if other is None:
      return False
    if self.kind == other.kind:
      if self.kind == Cell.NO_CHANGE:
        return True
      if self.node == other.node:
        return True
    return False

  def __ne__(self, other):
    return not (self == other)


class ConnectionStatus(object):
  EMPTY = 1
  INFILL = 2
  CONNECTION = 3


Status9Neighborhood = collections.namedtuple('Status9Neighborhood',
                                             ['up_left', 'up', 'up_right',
                                              'left', 'center', 'right',
                                              'down_left', 'down', 'down_right'])

class ConnectedCell(Cell):

  def __init__(self, base_cell, change_neighborhood):
    self.base = base_cell
    self.changes = change_neighborhood

  def __repr__(self):
    return "<ConnectedCell base=%s changes=%s>" %(self.base, self.changes)

  def __eq__(self, other):
    if other is None:
      return False
    if self.base != other.base:
      return False
    return self.changes == other.changes

  def __ne__(self, other):
    return not (self == other)


class ColumnItem(object):

  def __init__(self, node_line, inside):
    self.node_line = node_line
    self.inside = inside

  def __repr__(self):
    return "<Cell inside=%s node_line=%s>" %(self.inside, self.node_line)

def to_separate_lines(dual_bound_lines):
  return \
    [single_node_line
     for bound_line in dual_bound_lines
     for single_node_line in bound_line.to_single_bound_lines()]

class Fragmap():

  def __init__(self, patches, grouped_node_lines_filemap):
    # Ungroup by file, make a flat list of node line groups
    # TODO: Do something useful with the file grouping, like parallelization
    print("Creating Fragmap with grouped_node_lines=", grouped_node_lines_filemap)
    self.patches = patches
    self.grouped_node_lines_filemap = grouped_node_lines_filemap
    debug.get('matrix').debug("Patches: %s", patches)

  @staticmethod
  def from_diffs(diffs):
    dual_node_lines = update_all_positions_to_latest(diffs)
    for dual_node_line in dual_node_lines:
      dual_node_line.increment_end()
    grouped_lines = new_group_fragment_bound_lines(to_separate_lines(dual_node_lines))
    return Fragmap(diffs, grouped_lines)

  def get_n_patches(self):
    return len(self.patches)

  def get_patch(self, n):
    return self.patches[n]

  def generate_column(self, col_index, prev_column=None):
    c = col_index
    n_rows = self.get_n_patches()
    node_line_group = self.grouped_node_lines[c]
    debug.get('dco').debug("grouped_node_lines at col %d: %s", c, node_line_group)
    # Initialize inside_fragment
    inside_fragment = prev_column
    if prev_column is None:
      if col_index <= 0:
        inside_fragment = [None] * n_rows
      else:
        inside_fragment = self.generate_column(col_index - 1)
    # For each row in the column
    for r in range(n_rows):
      diff_i = r
      debug.get('grid').debug("%d,%d: %s", r, c, node_line_group)
      if True: #earliest_diff(node_line_group) <= diff_i:
        for node_line in node_line_group:
          # If node belongs in on this row
          if node_line._startdiff_i == diff_i:
            inside_fragment[r] = ColumnItem(node_line, node_line._kind == FragmentBoundNode.START)
            debug.get('grid').debug("Setting inside_fragment = %s", inside_fragment)
            # If it was updated to False:
            if not inside_fragment[r].inside:
              # False overrides True so that if start and end from same diff
              # appear in same group we don't get stuck at True
              #break
              pass
        debug.get('grid').debug("%d,%d: %d", r, c, inside_fragment[r])
    return inside_fragment


  # Iterate over the list, placing markers at column i row j if i >= a start node of revision j and i < end node of same revision
  def generate_matrix(self):
    #debug.get('matrix').debug("Grouped lines: %s", self.grouped_node_lines)
    n_rows = self.get_n_patches()
    def generate_file_matrix(grouped_node_lines_onefile):
      def find_end(start_node_line, grouped_node_lines_onefile):
        for end_i, end_group in enumerate(grouped_node_lines_onefile):
          for end_node_line in end_group:
            if end_node_line._kind != FragmentBoundNode.END:
              continue
            if start_node_line.same_dual_line(end_node_line):
              return end_i
        # There should always be an end line to a start line
        assert(False)
      def fill_inside(matrix, start_i, end_i, dual_line):
        r = dual_line._startdiff_i
        # TODO: Even including end_i below does not work because if
        # the fragment is empty then end is in the group BEFORE start!
        # The line-level interval mode of "start-inclusive, end-inclusive"
        # leaks into - and is counter to - the node line group-level interval mode
        # of "start-inclusive, end-exclusive"
        # Two options:
        #  (1) increment end before grouping it, so as to isolate the line-level interval mode
        #  (2) force the start_i to be included always
        for c in range(start_i, end_i):
          matrix[r][c] = Cell(Cell.CHANGE, dual_line._nodehistory[r])
      n_cols = len(grouped_node_lines_onefile)
      debug.get('dco').debug("Matrix size: rows, cols: %d %d", n_rows, n_cols)
      matrix = [[Cell(Cell.NO_CHANGE) for _ in range(n_cols)] for _ in range(n_rows)]
      for start_i, start_group in enumerate(grouped_node_lines_onefile):
        for start_node_line in start_group:
          if start_node_line._kind != FragmentBoundNode.START:
            continue
          end_i = find_end(start_node_line, grouped_node_lines_onefile)
          print("Filling", start_i, "to", end_i, "with", start_node_line)
          fill_inside(matrix, start_i, end_i, start_node_line._dual_line)
          print(matrix)
      # Remove the last line because that is never inside a bound
      matrix = [row[0:-1] for row in matrix]
      print(matrix)
      return matrix
    def append_file_matrix(matrix, file_matrix):
      assert(len(matrix) == len(file_matrix))
      for r in range(len(matrix)):
        matrix[r] += file_matrix[r]
    matrix = [[] for i in range(n_rows)]
    for _, grouped_node_lines_onefile in self.grouped_node_lines_filemap.items():
      file_matrix = generate_file_matrix(grouped_node_lines_onefile)
      append_file_matrix(matrix, file_matrix)
    decorate_matrix(matrix)
    return matrix

  def render_for_console(self, colorize):
    return self._render_for_console(self.generate_matrix(), colorize)

  def _render_for_console(self, matrix, colorize):
    n_rows = len(matrix)
    if n_rows == 0:
      return []
    n_cols = len(matrix[0])
    m = [['.' for _ in range(n_cols)] for _ in range(n_rows)]

    def render_cell(cell):
      if cell.kind == Cell.CHANGE:
        if colorize:
          # Make background white
          return ANSI_BG_WHITE + ' ' + ANSI_RESET
        else:
          return '#'
      if cell.kind == Cell.BETWEEN_CHANGES:
        if colorize:
          # Make background red
          return ANSI_BG_RED + ' ' + ANSI_RESET
        else:
          return '.'
      if cell.kind == Cell.NO_CHANGE:
        return '.'
      assert False, "Unexpected cell kind: %s" %(cell.kind)

    for r in range(n_rows):
      for c in range(n_cols):
        m[r][c] = render_cell(matrix[r][c])
    return m

  def str(self):
    matrix = self.generate_matrix()
    return '\n'.join([''.join(row) for row in matrix])

class BriefFragmap(object):

  def __init__(self, fragmap, connections, key_index):
    assert isinstance(fragmap, Fragmap)
    self.fragmap = fragmap
    self.connections = connections
    self.key_index = key_index
    self.patches = fragmap.patches

  @staticmethod
  def group_by_patch_connection(fragmap):
    def patch_connection_key(column):
      inside = [it.inside if it is not None else False for it in column]
      if inside == [False] * fragmap.get_n_patches():
        # Skip empty columns
        return False, None
      # Convert from list of True,False to string of 1,0
      return True, ''.join(['1' if b else '0' for b in inside])
    return BriefFragmap(fragmap, *BriefFragmap._group_columns_by(fragmap, patch_connection_key))

  @staticmethod
  def group_by_fragment_connection(fragmap):
    ## TODO: group all columns that have the same information, i.e. same diffs as well as same fragments
    pass

  @staticmethod
  def _group_columns_by(fragmap, keyfunc):
    groups = fragmap.grouped_node_lines
    # connections : '01001000..010' -> [node, node, ..]
    # The key strings are formatted such that
    # character i is 1 if the node line group has a node with start from patch i, and
    #                0 otherwise.
    connections = {}
    connections_key_index = []
    prev_column = None
    debug.get('matrix').debug("Group by connection: Before: %s", groups)
    for c in range(len(groups)):
      group = groups[c]
      column = fragmap.generate_column(c, prev_column)
      prev_column = column
      valid, key = keyfunc(column)
      if not valid:
        continue
      debug.get('matrix').debug('key: %s', key)
      if key in list(connections.keys()):
        # Append to existing dict entry
        connections[key] |= group
      else:
        # Make a new entry in the dict
        connections[key] = group
        connections_key_index.append(key)
    debug.get('matrix').debug("Group by connection: After: %s", connections)
    return connections, connections_key_index

  def generate_matrix(self):
    n_rows = self.fragmap.get_n_patches()
    n_cols = len(self.connections)
    debug.get('grid').debug("Matrix size: rows, cols: %s %s", n_rows, n_cols)
    matrix = [[Cell(Cell.NO_CHANGE) for _ in range(n_cols)] for _ in range(n_rows)]
    for c in range(n_cols):
      key = self.key_index[c]
      for r in range(n_rows):
        matrix[r][c].kind = Cell.CHANGE if key[r] == '1' else Cell.NO_CHANGE
    decorate_matrix(matrix)
    return matrix

  def render_for_console(self, colorize):
    return self.fragmap._render_for_console(self.generate_matrix(), colorize)

def n_columns(matrix):
  if len(matrix) == 0:
    return 0
  return len(matrix[0])


def n_rows(matrix):
  return len(matrix)

def in_range(matrix, r, c):
  if r < 0 or r >= n_rows(matrix):
    return False
  if c < 0 or c >= n_columns(matrix):
    return False
  return True

def equal_left_column(matrix, r, c):
  if not in_range(matrix, r, c) or not in_range(matrix, r, c-1):
    return False
  return matrix[r][c-1].node == matrix[r][c].node


def equal_right_column(matrix, r, c):
  if not in_range(matrix, r, c) or not in_range(matrix, r, c+1):
    return False
  return matrix[r][c+1].node == matrix[r][c].node

def change_at(matrix, r, c):
  if not in_range(matrix, r, c):
    return False
  return matrix[r][c].kind == Cell.CHANGE

def no_change_at(matrix, r, c):
  if not in_range(matrix, r, c):
    return True
  return matrix[r][c].kind == Cell.NO_CHANGE


def lzip(*args):
  """
  zip(...) but returns list of lists instead of list of tuples
  """
  return [list(el) for el in zip(*args)]

def flatten(list_of_lists):
  """
  Flatten list of lists into a list
  """
  return [el for inner in list_of_lists for el in inner]


class ConnectedFragmap(object):

  def __init__(self, fragmap):
    self.fragmap = fragmap
    self.patches = fragmap.patches

  def generate_matrix(self):
    def status(connection=False, infill=False):
      if connection:
        return ConnectionStatus.CONNECTION
      if infill:
        return ConnectionStatus.INFILL
      return ConnectionStatus.EMPTY
    def create_cell(matrix, r, c):
      base_cell = matrix[r][c]
      change_center = not no_change_at(matrix, r, c)
      change_up = not no_change_at(matrix, r-1, c)
      change_down = not no_change_at(matrix, r+1, c)
      change_left = change_at(matrix, r, c-1)
      change_right = change_at(matrix, r, c+1)
      equal_left = equal_left_column(matrix, r, c)
      equal_right = equal_right_column(matrix, r, c)
      infill_up_left = equal_left and not no_change_at(matrix, r, c-1) and change_up and not no_change_at(matrix, r-1, c-1) and change_center
      infill_up_right = equal_right and not no_change_at(matrix, r, c+1) and change_up and not no_change_at(matrix, r-1, c+1) and change_center
      infill_down_left = equal_left and not no_change_at(matrix, r, c-1) and change_down and not no_change_at(matrix, r+1, c-1) and change_center
      infill_down_right = equal_right and not no_change_at(matrix, r, c+1) and change_down and not no_change_at(matrix, r+1, c+1) and change_center
      change_neigh = Status9Neighborhood(up_left = status(infill=infill_up_left),
                                         up = status(connection=change_up and change_center),
                                         up_right = status(infill=infill_up_right),
                                         left = status(connection=equal_left and change_center and change_left, infill=infill_up_left),
                                         center = status(connection=change_at(matrix, r, c), infill=matrix[r][c].kind == Cell.BETWEEN_CHANGES),
                                         right = status(connection=equal_right and change_center and change_right, infill=infill_up_right),
                                         down_left = status(infill=infill_down_left),
                                         down = status(connection=change_down and change_center),
                                         down_right = status(infill=infill_down_right),
      )
      return ConnectedCell(base_cell, change_neigh)
    base_matrix = self.fragmap.generate_matrix()
    cols = n_columns(base_matrix)
    rows = n_rows(base_matrix)
    return [[create_cell(base_matrix, r, c) for c in range(cols)] for r in range(rows)]

  def render_for_console(self, colorize):
    connection_matrix = self.generate_matrix()
    def create_cell_description(cell):
      def character(position, status):
        if status == ConnectionStatus.EMPTY:
          return ' '
        if status == ConnectionStatus.INFILL:
          if colorize:
            return ANSI_BG_RED + '^' + ANSI_RESET
          return '^'
        if position in ['up_left', 'up_right', 'down_left', 'down_right']:
          if status == ConnectionStatus.CONNECTION:
            # Should not happen
            #assert False
            return '!'
        if position in ['up', 'down']:
          if status == ConnectionStatus.CONNECTION:
            if colorize:
              return ANSI_BG_RED + '|' + ANSI_RESET
            return "|"
        if position in ['left', 'right']:
          if status == ConnectionStatus.CONNECTION:
            if colorize:
              return ANSI_BG_MAGENTA + '-' + ANSI_RESET
            else:
              return "-"
        if position == 'center':
          if status == ConnectionStatus.CONNECTION:
            if isinstance(cell.base.node, str):
              if colorize:
                return ANSI_BG_WHITE + ANSI_FG_BLUE + cell.base.node + ANSI_RESET
              else:
                return cell.base.node
            else:
              if colorize:
                return ANSI_BG_WHITE + ' ' + ANSI_RESET
              else:
                return '#'
        #assert False
        # Should not happen
        return '!'
      return [[character('up_left', cell.changes.up_left),
               character('up', cell.changes.up),
               character('up_right', cell.changes.up_right)],
              [character('left', cell.changes.left),
               character('center', cell.changes.center),
               character('right', cell.changes.right)],
              [character('down_left', cell.changes.down_left),
               character('down', cell.changes.down),
               character('down_right', cell.changes.down_right)]]

    return flatten([[flatten(v) for v in lzip(*[create_cell_description(cell) for cell in row])]
                    for row in connection_matrix])
