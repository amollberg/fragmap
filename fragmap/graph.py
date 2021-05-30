#!/usr/bin/env python

from dataclasses import dataclass

from math import inf
from typing import List, Dict, Type, Union

import pygit2
from pygit2 import Oid, DiffHunk

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
class Node:
  hunk: Union[pygit2.DiffHunk, DiffHunk]
  generation: int
  active: bool

  @staticmethod
  def active(diff_hunk: pygit2.DiffHunk, generation: int):
    return Node(diff_hunk, generation, active=True)

  @staticmethod
  def inactive(old_start_and_lines, new_start_and_lines, generation: int):
    return Node(
      DiffHunk.from_tup(old_start_and_lines, new_start_and_lines),
      generation,
      active=False)


@dataclass(frozen=True)
class DiffHunk:
  old_start: int
  old_lines: int
  new_start: int
  new_lines: int

  @staticmethod
  def from_tup(old_start_and_lines, new_start_and_lines):
    old_start, old_lines = old_start_and_lines
    new_start, new_lines = new_start_and_lines
    return DiffHunk(old_start=old_start,
                    old_lines=old_lines,
                    new_start=new_start,
                    new_lines=new_lines)


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

SOURCE = Node.inactive((0, 0), (0, inf), -1)
SINK = Node.inactive((0, inf), (0, 0), inf)


def empty_spg():
  return {
    SOURCE: [SINK],
  }


def to_dot(spg: Dict[Node, List[Node]], file_id: FileId):
  def name(node):
    if node == SOURCE:
      return "s"
    if node == SINK:
      return "t"
    prefix = '_A_' if node.active else ''
    return f"{prefix}n{node.generation}_" \
           f"{node.hunk.old_start}_{node.hunk.old_lines}_" \
           f"{node.hunk.new_start}_{node.hunk.new_lines}"

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
        spg: Dict[Node, List[Node]],
        nodes_from_previous_commit: List[Node],
        node: Node):
  cur_range = Span.from_old(node.hunk)
  some_overlap = False
  for prev_node in nodes_from_previous_commit:
    prev_range = Span.from_new(prev_node.hunk)
    if cur_range.overlaps(prev_range):
      spg[prev_node] = [item for item in spg[prev_node]
                        if item != SINK]
      spg[prev_node].append(node)
      some_overlap = True

  spg[node] = [SINK]
  if not some_overlap:
    print("-----------------")
    print("spg:", spg)
    print("prev:", nodes_from_previous_commit)
    print("to add:", node)
  assert some_overlap


def fill_in_between(hunks: list[Node]):
  return [el
          for left, right in zip(hunks, hunks[1:])
          for el in [
            left,
            Node.inactive(
              (left.hunk.old_start + left.hunk.old_lines,
               right.hunk.old_start - left.hunk.old_start - left.hunk.old_lines),
              (left.hunk.new_start + left.hunk.new_lines,
               right.hunk.new_start - left.hunk.new_start - left.hunk.new_lines),
              left.generation)
          ]
  ] + ([hunks[-1]] if hunks else [])


def update_unchanged_file(file_spg: Dict[Node, List[Node]], generation):
  prev_nodes_by_end = sorted(
    [start for start, ends in file_spg.items()
     if SINK in ends],
    key=lambda node: node.hunk.new_start)
  filler = Node.inactive(
    (0, inf),
    (0, inf),
    generation)
  add_on_top_of(file_spg, prev_nodes_by_end, filler)


def update_file(file_spg: Dict[Node, List[Node]],
                filepatch: Patch,
                generation: int):
  def get_first_node(nodes):
    if not nodes:
      return None
    return sorted(nodes, key=lambda node: node.new_start)[0]
  def get_last_node(nodes):
    if not nodes:
      return None
    return sorted(nodes, key=lambda node: node.new_start)[-1]

  hunks_by_start = sorted(filepatch.hunks, key=lambda hunk: hunk.old_start)
  nodes_by_start = [Node.active(diff_hunk, generation)
                    for diff_hunk in hunks_by_start]
  nodes_by_start = fill_in_between(nodes_by_start)
  prev_nodes_by_end = sorted(
    [start for start, ends in file_spg.items()
     if SINK in ends],
    key=lambda node: node.hunk.new_start)

  for cur_node in nodes_by_start:
    add_on_top_of(file_spg, prev_nodes_by_end, cur_node)

  if nodes_by_start and (nodes_by_start[0].hunk.new_start > 0 or
                         nodes_by_start[0].hunk.old_start > 0
  ):
    prev_first = Span.from_old(nodes_by_start[0].hunk)
    cur_first = Span.from_new(nodes_by_start[0].hunk)
    filler = Node.inactive(
      (0, prev_first.start),
      (0, cur_first.start),
      generation)
    add_on_top_of(file_spg, prev_nodes_by_end, filler)

  if nodes_by_start and (nodes_by_start[-1].hunk.new_lines < inf or
                         nodes_by_start[-1].hunk.old_lines < inf
  ):
    prev_last = Span.from_old(nodes_by_start[-1].hunk)
    cur_last = Span.from_new(nodes_by_start[-1].hunk)
    filler = Node.inactive(
      (prev_last.end, inf),
      (cur_last.end, inf),
      generation)
    add_on_top_of(file_spg, prev_nodes_by_end, filler)

  return file_spg


@dataclass(frozen=True)
class FileId:
  commit: int
  path: str


def update_commit_diff(
        spgs: Dict[FileId, Dict[Node, List[Node]]],
        files: Dict[FileId, FileId],
        commit_diff: CommitDiff,
        diff_i: int):
  return update(spgs, files, Diff(commit_diff.filepatches), diff_i)


def update(spgs: Dict[FileId, Dict[Node, List[Node]]],
           files: Dict[FileId, FileId],
           diff: Diff,
           diff_i: int):
  def old_patch_file_id(filepatch):
    return FileId(diff_i-1, filepatch.delta.old_file.path)

  def new_patch_file_id(filepatch):
    return FileId(diff_i, filepatch.delta.new_file.path)

  def update_unchanged_files():
    old_filepaths_of_changed = [filepatch.delta.old_file.path
                                for filepatch in diff]

    # Propagate the old known files that have not changed
    def update_unchanged(file_id: FileId):
      new_file_id = FileId(commit=diff_i, path=file_id.path)
      files[new_file_id] = files[file_id]
      print("mapped", new_file_id, "to", files[file_id])
      return new_file_id

    return [
      update_unchanged(file_id)
      for file_id in list(files.keys())
      if file_id.commit == diff_i - 1 and \
              file_id.path not in old_filepaths_of_changed
    ]

  def update_changed_files():
    # Update the files that have changed (are in the diff)
    def update_changed(filepatch: Patch):
      old_file_id = old_patch_file_id(filepatch)
      # Register previously undiscovered file's old name
      if old_file_id not in files:
        print("mapped undiscovered", old_file_id)
        files[old_file_id] = old_file_id

      # Register file's new name
      new_file_id = new_patch_file_id(filepatch)
      files[new_file_id] = files[old_file_id]
      print("mapping changed", new_file_id, "to", files[old_file_id])
      return files[new_file_id]

    return [
      update_changed(filepatch)
      for filepatch in diff
    ]

  # Update graph of files that have not changed
  for file_id in update_unchanged_files():
    print("unchanged:", file_id, "in commit", diff_i)
    print(files)
    print(list(spgs.keys()))
    original_file_id = files[file_id]
    file_spg = spgs[original_file_id]
    update_unchanged_file(file_spg, diff_i)

  # Update graph of files that have changes (are in the diff)
  update_changed_files()
  for filepatch in diff:
    original_file_id = files[new_patch_file_id(filepatch)]
    if original_file_id not in spgs:
      spgs[original_file_id] = empty_spg()
    file_spg = spgs[original_file_id]
    update_file(file_spg, filepatch, diff_i)


def all_paths(spg, source=SOURCE) -> List[List[Node]]:
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
      Patch(DiffDelta.from_paths("B1", "b1"), [
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
    update(spgs, files, diff, i)
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
