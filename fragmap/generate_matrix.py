#!/usr/bin/env python
# encoding: utf-8
# Copyright 2016-2021 Alexander Mollberg
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import collections
from dataclasses import dataclass
from enum import Enum
from pprint import pformat, pprint
from typing import List, Dict, TypeVar, Generic, Sequence, Tuple

from . import debug
from .commitdiff import CommitDiff
from .console_color import *
from .datastructure_util import flatten, lzip
from .enumerate_paths import all_paths
from .file_selection import FileSelection
from .list_dict import StableListDict
from .spg import Node
from .update import FileId, update_commit_diff


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
    if len(list(set([len(col) for col in self]))) > 1:
      debug.get('matrix').critical(f"All rows/columns are not equally long: \n"
                                   f"{pformat(self)}")
      assert (False)
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
  NO_CHANGE = 100
  CHANGE = 101
  BETWEEN_CHANGES = 102
  BETWEEN_SQUASHABLE = 103


@dataclass
class Cell:
  kind: CellKind


@dataclass
class SingleNodeCell(Cell):
  file_id: FileId
  node: Node = None

  def __eq__(self, other):
    if other is None:
      return False
    if self.kind != other.kind:
      return False
    if self.file_id != other.file_id:
      return False
    if self.kind == CellKind.NO_CHANGE:
      return True
    if self.node != other.node:
      return False
    return True

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


def changes_at_row(m: RowMajorMatrix[Cell], r: int):
  n_rows = len(m)
  if n_rows == 0:
    return []
  n_cols = len(m[0])
  return set([c for c in range(n_cols)
              if m[r][c].kind == CellKind.CHANGE])


def collisions_between(m: RowMajorMatrix[Cell],
                       row: int,
                       earlier_row: int):
  changed_at_end_row = changes_at_row(m, row)
  for row_i in range(earlier_row + 1, row):
    if changes_at_row(m, row_i) & changed_at_end_row:
      return True
  return False


def is_subset_of_earlier(m: RowMajorMatrix[Cell], row: int, earlier_row: int):
  changed_at_end_row = changes_at_row(m, row)
  changed_at_earlier_row = changes_at_row(m, earlier_row)
  return not (changed_at_end_row - changed_at_earlier_row)


def find_squashable(m: RowMajorMatrix[Cell]) -> Sequence[Tuple[int, int]]:
  """
  Find pairs of squashable commits.
  Squashable in this case means:
    * that there are no collisions between the commits, and
    * that the lines that changes in the later commit are a subset of
      the lines that changes in the earlier commit.
  Assumes the matrix has already been decorated with BETWEEN_CHANGES.
  """
  n_rows = len(m)
  for r in range(n_rows):
    for earlier_r in reversed(range(r)):
      if collisions_between(m, r, earlier_r):
        break
      if is_subset_of_earlier(m, r, earlier_r):
        yield tuple([earlier_r, r])


def mark_squashable(m: RowMajorMatrix[Cell],
                    squashable_tuples: Sequence[Tuple[int, int]]):
  """
  Mark cells between squashable changes.
  See :py:func: find_squashable
  """
  for earlier_r, r in squashable_tuples:
    changes = changes_at_row(m, r)
    for r_to_mark in range(earlier_r + 1, r):
      for c in changes:
        if m[r_to_mark][c].kind == CellKind.BETWEEN_CHANGES:
          m[r_to_mark][c].kind = CellKind.BETWEEN_SQUASHABLE


def mark_cells_between_changes(m: RowMajorMatrix[Cell]):
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


def decorate_matrix(m: RowMajorMatrix[Cell]):
  debug.get('grid').debug("decorate_matrix")
  mark_cells_between_changes(m)
  mark_squashable(m, find_squashable(m))


class ConnectionStatus(object):
  EMPTY = 1
  INFILL = 2
  CONNECTION = 3


Status9Neighborhood = collections.namedtuple('Status9Neighborhood',
                                             ['up_left', 'up', 'up_right',
                                              'left', 'center', 'right',
                                              'down_left', 'down',
                                              'down_right'])


class ConnectedCell(Cell):

  def __init__(self, base_cell, change_neighborhood):
    self.base = base_cell
    self.changes = change_neighborhood

  def __repr__(self):
    return "<ConnectedCell base=%s changes=%s>" % (self.base, self.changes)

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
    return "<Cell inside=%s node_line=%s>" % (self.inside, self.node_line)


@dataclass
class GraphPath:
  nodes: List[Node]
  file_id: FileId


@dataclass
class Fragmap:
  _patches: List[CommitDiff]
  spgs: Dict[FileId, Dict[Node, List[Node]]]

  @staticmethod
  def from_diffs(diffs: List[CommitDiff], files_arg: List[str] = None):
    files = {}
    spgs = {}
    for i, diff in enumerate(diffs):
      update_commit_diff(spgs, files, diff, i)
      if debug.is_logging('update'):
        for file_id, spg in spgs.items():
          debug.get('update').debug(spg.to_dot(file_id))
        debug.get('update').debug("-------")

    selected_files = FileSelection.from_files_arg(files_arg)
    selected_file_spgs = {file_id: spg
                          for file_id, spg in spgs.items()
                          if selected_files.contains(file_id, files)}
    return Fragmap(diffs, selected_file_spgs)

  def patches(self):
    return self._patches

  def paths(self) -> List[GraphPath]:
    return [
      GraphPath(path, file_id)
      # Sort by file
      for file_id, spg in
      sorted(self.spgs.items(), key=lambda kv: kv[0].tuple())
      for path in all_paths(spg)
    ]

  def _generate_columns(self) -> ColumnMajorMatrix:
    paths = self.paths()
    # Remove empty columns
    paths = [path
             for path in paths
             if any([node.active for node in path.nodes])]
    if paths:
      # All columns should be equally long
      if 1 != len(list(set([len(col.nodes) for col in paths]))):
        debug.get('matrix').critical(f"All columns are not equally long: \n"
                                     f"{pformat(paths)}")
        assert False
    return ColumnMajorMatrix([
      [SingleNodeCell(CellKind.CHANGE if node.active else CellKind.NO_CHANGE,
                      path.file_id,
                      node)
       for node in path.nodes]
      for path in paths
    ])

  def generate_matrix(self) -> RowMajorMatrix:
    columns = self._generate_columns()
    rows = columns.row_major()
    m = RowMajorMatrix(rows[1:-1])
    decorate_matrix(m)
    return m

  def render_for_console(self, colorize) -> RowMajorMatrix[str]:
    return self._render_for_console(self.generate_matrix(), colorize)

  def _render_for_console(self, matrix: RowMajorMatrix[Cell], colorize: bool) \
          -> RowMajorMatrix[str]:
    n_rows = len(matrix)
    if n_rows == 0:
      return []
    n_cols = len(matrix[0])
    m = RowMajorMatrix([['.' for _ in range(n_cols)] for _ in range(n_rows)])

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
          return '|'
      if cell.kind == CellKind.BETWEEN_SQUASHABLE:
        if colorize:
          # Make background yellow
          return ANSI_BG_DARK_YELLOW + ' ' + ANSI_RESET
        else:
          return '^'
      if cell.kind == CellKind.NO_CHANGE:
        return '.'
      assert False, "Unexpected cell kind: %s" % (cell.kind)

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

  def render_for_console(self, colorize) -> RowMajorMatrix[str]:
    return self._render_for_console(self.generate_matrix(), colorize)

  def _render_for_console(self, matrix, colorize) -> RowMajorMatrix[str]:
    n_rows = len(matrix)
    if n_rows == 0:
      return []
    n_cols = len(matrix[0])
    m = RowMajorMatrix([['.' for _ in range(n_cols)] for _ in range(n_rows)])

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
          return '|'
      if cell.kind == CellKind.BETWEEN_SQUASHABLE:
        if colorize:
          # Make background yellow
          return ANSI_BG_DARK_YELLOW + ' ' + ANSI_RESET
        else:
          return '^'
      if cell.kind == CellKind.NO_CHANGE:
        return '.'
      assert False, "Unexpected cell kind: %s" % (cell.kind)

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
  if not in_range(matrix, r, c) or not in_range(matrix, r, c - 1):
    return False
  return matrix[r][c - 1].node == matrix[r][c].node


def equal_right_column(matrix, r, c):
  if not in_range(matrix, r, c) or not in_range(matrix, r, c + 1):
    return False
  return matrix[r][c + 1].node == matrix[r][c].node


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
      change_up = not no_change_at(matrix, r - 1, c)
      change_down = not no_change_at(matrix, r + 1, c)
      change_left = change_at(matrix, r, c - 1)
      change_right = change_at(matrix, r, c + 1)
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
            # assert False
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
        # assert False
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

    return flatten([[flatten(v) for v in
                     lzip(*[create_cell_description(cell) for cell in row])]
                    for row in connection_matrix])
