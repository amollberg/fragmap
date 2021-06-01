#!/usr/bin/env python
import itertools
from dataclasses import dataclass
from enum import Enum
from pprint import pformat, pprint
from typing import List, Dict, Type, TypeVar, Generic

from .commitdiff import CommitDiff
from .datastructure_util import flatten, lzip
from .graph import FileId, update_commit_diff, all_paths
from .spg import Node
from .stable_list_dict import StableListDict
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

CellType = TypeVar('CellType')

class Matrix(Generic[CellType], List[List[CellType]]):
  def _transpose(self):
    if 1 != len(list(set([len(col) for col in self]))):
      debug.get('matrix').critical(f"All rows/columns are not equally long: \n"
                                   f"{pformat(self)}")
      assert(False)
    return list(zip(*self))

  def column_major(self):
    if isinstance(self, ColumnMajorMatrix):
      return self

    if isinstance(self, RowMajorMatrix):
      return ColumnMajorMatrix(self._transpose())

  def row_major(self):
    if isinstance(self, RowMajorMatrix):
      return self

    if isinstance(self, ColumnMajorMatrix):
      return RowMajorMatrix(self._transpose())


class ColumnMajorMatrix(Matrix[CellType]):
  pass


class RowMajorMatrix(Matrix[CellType]):
  pass


class CellKind(Enum):
  NO_CHANGE=100
  CHANGE=101
  BETWEEN_CHANGES=102


@dataclass
class Cell:
  kind: CellKind


@dataclass
class SingleNodeCell(Cell):
  node: Node = None

  def __eq__(self, other):
    if other is None:
      return False
    if self.kind == other.kind:
      if self.kind == CellKind.NO_CHANGE:
        return True
      if self.node == other.node:
        return True
    return False

  def __ne__(self, other):
    return not (self == other)


@dataclass
class MultiNodeCell(Cell):
  nodes: List[object]

  def __eq__(self, other):
    if other is None:
      return False
    if self.kind == other.kind:
      if self.kind == CellKind.NO_CHANGE:
        return True
      if self.nodes == other.nodes:
        return True
    return False

  def __ne__(self, other):
    return not (self == other)


def decorate_matrix(m: RowMajorMatrix[Cell]):
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
      if cell.kind == CellKind.CHANGE:
        if debug.is_logging('grid'):
          debug.get('grid').debug("last_patch %s %s %s", last_patch[c], c, r)
        if last_patch[c] >= 0:
          # Mark the cells inbetween
          start = last_patch[c]
          end = r
          for i in range(start, end + 1):
            # If not yet decorated
            if m[i][c].kind == CellKind.NO_CHANGE:
              m[i][c].kind = CellKind.BETWEEN_CHANGES
        last_patch[c] = r



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

  def __init__(self, node_line, inside: bool):
    self.node_line = node_line
    self.inside = inside

  def __repr__(self):
    return "<Cell inside=%s node_line=%s>" %(self.inside, self.node_line)


@dataclass
class Fragmap:
  _patches: List[CommitDiff]
  spgs: Dict[FileId, Dict[Node, List[Node]]]

  @staticmethod
  def from_diffs(diffs: List[CommitDiff]):
    files = {}
    spgs = {}
    for i, diff in enumerate(diffs):
      update_commit_diff(spgs, files, diff, i)
      if debug.is_logging('update'):
        for file_id, spg in spgs.items():
          debug.get('update').debug(spg.to_dot(file_id))
        debug.get('update').debug("-------")

    return Fragmap(diffs, spgs)

  def patches(self):
    return self._patches

  def paths(self):
    return [
      path
      # Sort by file
      for _, spg in sorted(self.spgs.items(), key=lambda kv:kv[0].tuple())
      for path in all_paths(spg)
    ]

  def _generate_columns(self) -> ColumnMajorMatrix:
    columns = self.paths()
    # Remove empty columns
    columns = [column
               for column in columns
               if any([node.active for node in column])]
    # All columns should be equally long
    if 1 != len(list(set([len(col) for col in columns]))):
      debug.get('matrix').critical(f"All columns are not equally long: \n"
                                   f"{pformat(columns)}")
      assert False
    return ColumnMajorMatrix([
      [SingleNodeCell(CellKind.CHANGE if node.active else CellKind.NO_CHANGE,
                      node)
       for node in column]
      for column in columns
    ])

  def generate_matrix(self) -> RowMajorMatrix:
    columns = self._generate_columns()
    rows = columns.row_major()
    m = RowMajorMatrix(rows[1:-1])
    decorate_matrix(m)
    return m

  def render_for_console(self, colorize):
    return self._render_for_console(self.generate_matrix(), colorize)

  def _render_for_console(self, matrix: RowMajorMatrix[Cell], colorize: bool):
    n_rows = len(matrix)
    if n_rows == 0:
      return []
    n_cols = len(matrix[0])
    m = [['.' for _ in range(n_cols)] for _ in range(n_rows)]

    def render_cell(cell: SingleNodeCell):
      if cell.kind == CellKind.CHANGE:
        if colorize:
          # Make background white
          return ANSI_BG_WHITE + ' ' + ANSI_RESET
        else:
          return '#'
      if cell.kind == CellKind.BETWEEN_CHANGES:
        if colorize:
          # Make background red
          return ANSI_BG_RED + ' ' + ANSI_RESET
        else:
          return '.'
      if cell.kind == CellKind.NO_CHANGE:
        return '.'
      assert False, "Unexpected cell kind: %s" %(cell.kind)

    for r in range(n_rows):
      for c in range(n_cols):
        m[r][c] = render_cell(matrix[r][c])
    return m

  def str(self):
    matrix = self.generate_matrix()
    return '\n'.join([''.join(row) for row in matrix])


@dataclass
class BriefFragmap:
  inner: Fragmap

  def patches(self):
    return self.inner.patches()

  def generate_matrix(self) -> RowMajorMatrix:
    full_matrix = self.inner.generate_matrix()
    return BriefFragmap._group_by_patch_connection(
      full_matrix.column_major()).row_major()

  @staticmethod
  def _group_by_patch_connection(columns: ColumnMajorMatrix[SingleNodeCell]) \
          -> ColumnMajorMatrix:
    def connection(column: List[Cell]):
      return ''.join(['1' if r.kind == CellKind.CHANGE else '0'
                      for r in column])

    def groupby(l: List[List[Cell]], key) -> List[List[List[Cell]]]:
      d = StableListDict()
      for item in l:
        d.add(key(item), item)
      return [values for k, values in d.items()]

    column_groups = ColumnMajorMatrix(groupby(columns, key=connection))
    if debug.is_logging('matrix'):
      debug.get('matrix').debug(f"grouped columns: {pformat(column_groups)}")
    def multi_cell_kind(cells: List[Cell]):
      kinds = list(set([cell.kind for cell in cells]))
      if len(kinds) != 1:
        print("Cells have different kinds:", kinds)
        pprint(cells)
        assert False
      return kinds[0]

    def transpose(list_of_lists):
      return list(zip(*list_of_lists))

    return ColumnMajorMatrix([
      [MultiNodeCell(multi_cell_kind(cell_group),
                     [cell.node for cell in cell_group])
       for cell_group in transpose(column_group)]
      for column_group in column_groups
    ])

  def render_for_console(self, colorize):
    return self._render_for_console(self.generate_matrix(), colorize)

  def _render_for_console(self, matrix, colorize):
    n_rows = len(matrix)
    if n_rows == 0:
      return []
    n_cols = len(matrix[0])
    m = [['.' for _ in range(n_cols)] for _ in range(n_rows)]

    def render_cell(cell: MultiNodeCell):
      if cell.kind == CellKind.CHANGE:
        if colorize:
          # Make background white
          return ANSI_BG_WHITE + ' ' + ANSI_RESET
        else:
          return '#'
      if cell.kind == CellKind.BETWEEN_CHANGES:
        if colorize:
          # Make background red
          return ANSI_BG_RED + ' ' + ANSI_RESET
        else:
          return '.'
      if cell.kind == CellKind.NO_CHANGE:
        return '.'
      assert False, "Unexpected cell kind: %s" %(cell.kind)

    for r in range(n_rows):
      for c in range(n_cols):
        m[r][c] = render_cell(matrix[r][c])
    return m

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
  return matrix[r][c].kind == CellKind.CHANGE

def no_change_at(matrix, r, c):
  if not in_range(matrix, r, c):
    return True
  return matrix[r][c].kind == CellKind.NO_CHANGE


class ConnectedFragmap(object):

  def __init__(self, fragmap):
    self.fragmap = fragmap
    self.patches = fragmap.patches

  def generate_matrix(self) -> RowMajorMatrix:
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
                                         center = status(connection=change_at(matrix, r, c), infill=matrix[r][c].kind == CellKind.BETWEEN_CHANGES),
                                         right = status(connection=equal_right and change_center and change_right, infill=infill_up_right),
                                         down_left = status(infill=infill_down_left),
                                         down = status(connection=change_down and change_center),
                                         down_right = status(infill=infill_down_right),
      )
      return ConnectedCell(base_cell, change_neigh)

    base_matrix = self.fragmap.generate_matrix()
    cols = n_columns(base_matrix)
    rows = n_rows(base_matrix)
    return RowMajorMatrix([
      [create_cell(base_matrix, r, c)
       for c in range(cols)]
      for r in range(rows)
    ])

  def render_for_console(self, colorize):
    connection_matrix = self.generate_matrix()
    def create_cell_description(cell) -> List[List[str]]:
      def character(position, status) -> str:
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
