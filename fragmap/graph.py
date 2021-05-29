#!/usr/bin/env python

from dataclasses import dataclass

from math import inf
from typing import List, Dict, Type

from pygit2 import Oid

from fragmap.commitdiff import CommitDiff
from fragmap.generate_matrix import Cell


@dataclass(frozen=True)
class DiffFile:
  path: str


@dataclass(frozen=True)
class DiffDelta:
  old_file: DiffFile
  new_file: DiffFile
  is_binary: bool

  @staticmethod
  def from_paths(old_file_path, new_file_path):
    return DiffDelta(old_file=DiffFile(old_file_path),
                     new_file=DiffFile(new_file_path),
                     is_binary=False)


@dataclass(frozen=True)
class DiffLine:
  content: str


@dataclass(frozen=True)
class DiffHunk:
  old_start: int
  old_lines: int
  new_start: int
  new_lines: int
  generation: int = -1
  active: bool = True

  @staticmethod
  def from_tup(old_start_and_lines, new_start_and_lines, generation,
               active=True):
    old_start, old_lines = old_start_and_lines
    new_start, new_lines = new_start_and_lines
    return DiffHunk(old_start=old_start,
                    old_lines=old_lines,
                    new_start=new_start,
                    new_lines=new_lines,
                    generation=generation,
                    active=active)

@dataclass(frozen=True)
class Patch:
  delta: DiffDelta
  hunks: list[DiffHunk]


class Diff(list):
  pass

@dataclass(frozen=True)
class Commit:
  hex: str
  message: str

@dataclass(frozen=True)
class Span:
  # Inclusive
  start: int
  # Exclusive
  end: int

  @staticmethod
  def from_old(diff_hunk: DiffHunk):
    return Span(start=diff_hunk.old_start,
                end=diff_hunk.old_start + diff_hunk.old_lines)

  @staticmethod
  def from_new(diff_hunk: DiffHunk):
    return Span(start=diff_hunk.new_start,
                end=diff_hunk.new_start + diff_hunk.new_lines)

  def overlaps(self, other):
    return (
      self.start == other.start or
      self.end == other.end
    ) or not (
            self.end <= other.start or
            other.end <= self.start
    )

SOURCE = DiffHunk.from_tup((0, 0), (0, inf), -1, False)
SINK = DiffHunk.from_tup((0, inf), (0, 0), inf, False)


def empty_spg():
  return {
    SOURCE: [SINK],
  }


def to_dot(spg, file_id: FileId):
  def name(node):
    if node == SOURCE:
      return "s"
    if node == SINK:
      return "t"
    prefix = '_A_' if node.active else ''
    return f"{prefix}n{node.generation}_" \
           f"{node.old_start}_{node.old_lines}_" \
           f"{node.new_start}_{node.new_lines}"

  return f"""
  # {file_id}
  digraph G {{
""" + \
         '\n'.join([f"{name(start)} -> {name(end)};"
                    for start, ends in spg.items()
                    for end in ends]) + \
         """
    s [shape=Mdiamond];
    t [shape=Msquare];
  }
"""


def add_on_top_of(
        spg,
        hunks_from_previous_commit: list[DiffHunk],
        diff_hunk: DiffHunk):
  cur_range = Span.from_old(diff_hunk)
  some_overlap = False
  for prev_hunk in hunks_from_previous_commit:
    prev_range = Span.from_new(prev_hunk)
    if cur_range.overlaps(prev_range):
      spg[prev_hunk] = [item for item in spg[prev_hunk]
                        if item != SINK]
      spg[prev_hunk].append(diff_hunk)
      some_overlap = True

  spg[diff_hunk] = [SINK]
  if not some_overlap:
    print("-----------------")
    print("spg:", spg)
    print("prev:", hunks_from_previous_commit)
    print("to add:", diff_hunk)
  assert some_overlap


def fill_in_between(hunks: list[DiffHunk]):
  return [el
          for left, right in zip(hunks, hunks[1:])
          for el in [
            left,
            DiffHunk.from_tup((left.old_start + left.old_lines,
                               right.old_start - left.old_start - left.old_lines),
                              (left.new_start + left.new_lines,
                               right.new_start - left.new_start - left.new_lines),
                              left.generation,
                              False)]
  ] + ([hunks[-1]] if hunks else [])


def update_file(file_spg: Dict[DiffHunk, List[DiffHunk]], diff: Patch):
  def get_first_node(nodes):
    if not nodes:
      return None
    return sorted(nodes, key=lambda node: node.new_start)[0]
  def get_last_node(nodes):
    if not nodes:
      return None
    return sorted(nodes, key=lambda node: node.new_start)[-1]

  hunks_by_start = sorted(diff.hunks, key=lambda hunk: hunk.old_start)
  hunks_by_start = fill_in_between(hunks_by_start)
  prev_nodes_by_end = sorted(
    [start for start, ends in file_spg.items()
     if SINK in ends],
    key=lambda hunk: hunk.new_start)

  for cur_hunk in hunks_by_start:
    add_on_top_of(file_spg, prev_nodes_by_end, cur_hunk)

  if hunks_by_start and hunks_by_start[0].new_start > 0:
    prev_first = Span.from_old(hunks_by_start[0])
    cur_first = Span.from_new(hunks_by_start[0])
    filler = DiffHunk.from_tup(
      (0, prev_first.start),
      (0, cur_first.start),
      hunks_by_start[0].generation, False)
    add_on_top_of(file_spg, prev_nodes_by_end, filler)

  if hunks_by_start and hunks_by_start[-1].new_lines < inf:
    prev_last = Span.from_old(hunks_by_start[-1])
    cur_last = Span.from_new(hunks_by_start[-1])
    filler = DiffHunk.from_tup(
      (prev_last.end, inf),
      (cur_last.end, inf),
      hunks_by_start[-1].generation, False)
    add_on_top_of(file_spg, prev_nodes_by_end, filler)

  return file_spg


@dataclass(frozen=True)
class FileId:
  commit: int
  path: str


def update_commit_diff(
        spgs: Dict[FileId, Dict[DiffHunk, List[DiffHunk]]],
        files: Dict[FileId, FileId],
        commit_diff: CommitDiff,
        diff_i: int):
  return update(spgs, files, Diff(commit_diff.filepatches), diff_i)


def update(spgs: Dict[FileId, Dict[DiffHunk, List[DiffHunk]]],
           files: Dict[FileId, FileId],
           diff: Patch,
           diff_i: int):
  def update_files():
    old_file_id = FileId(diff_i-1, diff.delta.old_file.path)
    if old_file_id not in files:
      files[old_file_id] = old_file_id

    new_file_id = FileId(diff_i, diff.delta.new_file.path)
    files[new_file_id] = files[old_file_id]
    return files[new_file_id]

  original_file_id = update_files()
  if original_file_id not in spgs:
    spgs[original_file_id] = empty_spg()
  file_spg = spgs[original_file_id]
  update_file(file_spg, diff)


def all_paths(spg, source=SOURCE) -> List[List[DiffHunk]]:
  if source == SINK:
    return [[SINK]]
  return [[source] + path
    for end in spg[source]
    for path in all_paths(spg, end)]


def print_fragmap(spg):
  paths = all_paths(spg)
  columns = [tuple(node.active
             for node in path)
             for path in paths]
  columns = list(set(columns))
  rows = list(zip(*columns))
  for row in rows[1:-1]:
    print(''.join([
      '#' if cell else '.'
      for cell in row]))


@dataclass
class SpgFragmap:
  spgs: Dict[FileId, Dict[Node, List[Node]]]

  @staticmethod
  def from_diffs(diffs: List[CommitDiff]):
    files = {}
    spgs = {}
    for i, diff in enumerate(diffs):
      update_commit_diff(spgs, files, diff, i)
      for file_id, spg in spgs.items():
        debug.get('update').debug(to_dot(spg, file_id))
      debug.get('update').debug("-------")

    return SpgFragmap(spgs)

  def generate_matrix(self) -> List[List[Cell]]:
    columns = [
      tuple(node.active
             for node in path)
       for spg in self.spgs.values()
       for path in all_paths(spg)
    ]
    columns = list(set(columns))
    rows = list(zip(*columns))
    return [
      [Cell(Cell.CHANGE) if cell else Cell(Cell.NO_CHANGE)
       for cell in row]
      for row in rows[1:-1]
    ]


def main():
  diffs = [
    Diff([
      Patch(DiffDelta.from_paths("F1", "f1"), [
        DiffHunk.from_tup((100, 0), (100, 2), 0),
      ]),
      Patch(DiffDelta.from_paths("f1", "F1"), [
        DiffHunk.from_tup((1, 0), (1, 1), 0),
        DiffHunk.from_tup((4, 0), (5, 2), 0),
      ]),
    ]),
    Diff([
      Patch(DiffDelta.from_paths("F1", "F1"), [
        DiffHunk.from_tup((1, 3), (1, 3), 1),
      ]),
    ]),
  ]
  spgs = {}
  files = {}
  for i, diff in enumerate(diffs):
    for patch in diff:
      update(spgs, files, patch, i)
    for file_id, spg in spgs.items():
      print(to_dot(spg, file_id))
    print("-------")

  from pprint import pprint
  pprint(files)
  for spg in spgs.values():
    pprint(all_paths(spg))
    print_fragmap(spg)




if __name__ == '__main__':
  main()
