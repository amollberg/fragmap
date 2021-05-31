#!/usr/bin/env python
# To be able to use the enclosing class type in class method type hints
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import Enum

from math import inf
from typing import List, Dict, Type, Union
from pprint import pprint, pformat

import pygit2
from pygit2 import Oid, DiffHunk

from fragmap.commitdiff import CommitDiff
from fragmap.load_commits import is_nullfile
from . import debug


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
  def active_binary(diff_delta: pygit2.DiffDelta, generation: int):
    return Node(
      DiffHunk.from_tup(
        (0,0) if is_nullfile(diff_delta.old_file) else (1,1),
        (0,0) if is_nullfile(diff_delta.new_file) else (1,1)
      ),
      generation,
      active=True)

  @staticmethod
  def inactive(old_start_and_lines, new_start_and_lines, generation: int):
    return Node(
      DiffHunk.from_tup(old_start_and_lines, new_start_and_lines),
      generation,
      active=False)

  @staticmethod
  def propagated(old_node: Node, generation: int):
    return Node(
      DiffHunk.from_tup(
        (old_node.hunk.new_start, old_node.hunk.new_lines),
        (old_node.hunk.new_start, old_node.hunk.new_lines)),
      generation,
      active=False)


@dataclass(frozen=True)
class DiffHunk:
  old_start: int
  old_lines: int
  new_start: int
  new_lines: int
  lines: str = dataclasses.field(default_factory=lambda: tuple())

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

class Overlap(Enum):
  NO_OVERLAP = 0
  POINT_OVERLAP = 1
  INTERVAL_OVERLAP = 2

@dataclass(frozen=True)
class Span:
  # Inclusive
  start: int
  # Exclusive
  end: int

  @staticmethod
  def from_old(diff_hunk: DiffHunk):
    start = diff_hunk.old_start
    if diff_hunk.old_lines == 0:
      start += 1
    end = start + diff_hunk.old_lines
    return Span(start, end)

  @staticmethod
  def from_new(diff_hunk: DiffHunk):
    start = diff_hunk.new_start
    if diff_hunk.new_lines == 0:
      start += 1
    end = start + diff_hunk.new_lines
    return Span(start, end)

  def is_empty(self):
    return self.start == self.end

  def adjacent_up_to(self, new_end):
    return Span(self.end, new_end)

  def adjacent_down_to(self, new_start):
    return Span(new_start, self.start)

  def to_git(self):
    if self.start == self.end:
      return [self.start - 1, 0]
    return [self.start, self.end - self.start]

  def overlap(self, other: Span) -> Overlap:
    if (
      self.start == other.start or
      self.end == other.end
    ) or not (
            self.end <= other.start or
            other.end <= self.start
    ):
      if self.is_empty() or other.is_empty():
        return Overlap.POINT_OVERLAP
      else:
        return Overlap.INTERVAL_OVERLAP
    else:
      return Overlap.NO_OVERLAP

SOURCE = Node.inactive((0, 0), (0, inf), -1)
SINK = Node.inactive((0, inf), (0, 0), inf)


def empty_spg() -> SPG:
  return SPG({
    SOURCE: [SINK],
  }, downstream_from_active={
    SOURCE: False
  })


def to_dot(spg: SPG, file_id: FileId):
  def name(node):
    if node == SOURCE:
      return "s"
    if node == SINK:
      return "t"

    prefix = ""
    if node.active:
      prefix += "A"
    if spg.downstream_from_active[node]:
      prefix += "d"
    if prefix:
      prefix = f"_{prefix}_"
    old = Span.from_old(node.hunk)
    new = Span.from_new(node.hunk)
    return f"{prefix}n{node.generation}_" \
           f"{old.start}_{old.end}_" \
           f"{new.start}_{new.end}"

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


def register(spg: SPG, prev_node, node):
  if prev_node not in spg.nodes():
    spg.graph[prev_node] = []
  spg.graph[prev_node] = [item for item in spg.graph[prev_node]
                          if item != SINK]
  spg.graph[prev_node].append(node)
  spg.propagate_active(prev_node, node)


@dataclass
class SPG:
  graph: Dict[Node, List[Node]]
  downstream_from_active: Dict[Node, bool] = dataclasses.field(default_factory=lambda: {})

  def propagate_active(self, prev_node, node):
    if not prev_node in self.downstream_from_active:
      self.downstream_from_active[prev_node] = prev_node.active
    if not node in self.downstream_from_active:
      self.downstream_from_active[node] = node.active
    self.downstream_from_active[node] |= self.downstream_from_active[prev_node]

  def nodes(self):
    return self.graph.keys()

  def items(self):
    return self.graph.items()


def add_on_top_of(
        spg: SPG,
        nodes_from_previous_commit: List[Node],
        node: Node):
  cur_range = Span.from_old(node.hunk)
  some_overlap = False

  def overlap_on_border(a: Span, b: Span):
    return a.start == b.start or a.end == b.end

  def add_if_interval_overlap(prev_node):
    prev_range = Span.from_new(prev_node.hunk)
    overlap = cur_range.overlap(prev_range)
    do_register = overlap == Overlap.INTERVAL_OVERLAP
    if debug.is_logging('update'):
      debug.get('update').debug(
        f"add_if_interval_overlap on {prev_range}? {do_register}")
    if do_register:
      register(spg, prev_node, node)
    return do_register

  def add_unless_point_to_downstream_active(prev_node):
    prev_range = Span.from_new(prev_node.hunk)
    overlap = cur_range.overlap(prev_range)
    do_register = overlap != Overlap.NO_OVERLAP \
                  and not (overlap == Overlap.POINT_OVERLAP
                           and overlap_on_border(cur_range, prev_range)
                           and spg.downstream_from_active[prev_node])
    if debug.is_logging('update'):
      debug.get('update').debug(
        f"add_unless_point_to_downstream_active on {prev_range}? {do_register}")
    if do_register:
      register(spg, prev_node, node)
    return do_register

  def add_unless_point_to_active(prev_node):
    prev_range = Span.from_new(prev_node.hunk)
    overlap = cur_range.overlap(prev_range)
    do_register = overlap != Overlap.NO_OVERLAP \
                  and not (overlap == Overlap.POINT_OVERLAP
                           and overlap_on_border(cur_range, prev_range)
                           and prev_node.active)
    if debug.is_logging('update'):
      debug.get('update').debug(
        f"add_unless_point_to_active on {prev_range}? {do_register}")
    if do_register:
      register(spg, prev_node, node)
    return do_register

  def add_if_to_inactive(prev_node):
    prev_range = Span.from_new(prev_node.hunk)
    overlap = cur_range.overlap(prev_range)
    do_register = overlap != Overlap.NO_OVERLAP \
                  and not prev_node.active
    if debug.is_logging('update'):
      debug.get('update').debug(
        f"add_if_to_inactive on {prev_range}? {do_register}")
    if do_register:
      register(spg, prev_node, node)
    return do_register

  def add_if_overlap(prev_node):
    prev_range = Span.from_new(prev_node.hunk)
    overlap = cur_range.overlap(prev_range)
    do_register = overlap != Overlap.NO_OVERLAP
    if debug.is_logging('update'):
      debug.get('update').debug(
        f"add_if_overlap on {prev_range}? {do_register}")
    if do_register:
      register(spg, prev_node, node)
    return do_register

  if debug.is_logging('update'):
    debug.get('update').debug(
      f"Adding {node} {cur_range} on top of previous")
  for prev_node in nodes_from_previous_commit:
    some_overlap = add_if_interval_overlap(prev_node) or some_overlap

  # Note the order of or-ed terms. The function call is put on the right to
  # effectively skip the rest of the nodes after the first overlap
  if not some_overlap:
    for prev_node in nodes_from_previous_commit:
      some_overlap = some_overlap or add_unless_point_to_downstream_active(prev_node)

  if not some_overlap:
    for prev_node in nodes_from_previous_commit:
      some_overlap = some_overlap or add_unless_point_to_active(prev_node)

  if not some_overlap:
    for prev_node in nodes_from_previous_commit:
      some_overlap = some_overlap or add_if_to_inactive(prev_node)

  if not some_overlap:
    for prev_node in nodes_from_previous_commit:
      some_overlap = some_overlap or add_if_overlap(prev_node)

  spg.graph[node] = [SINK]
  if not some_overlap:
    debug.get('update').critical(
      '\n'.join([
        "-----------------",
        "SPG:", pformat(spg),
        "Previous nodes:", pformat(nodes_from_previous_commit),
        "To be added:", cur_range, pformat(node)
      ])
    )
  assert some_overlap


def surround_with_inactive(nodes: List[Node]) -> List[Node]:
  if not nodes:
    return []
  generation = nodes[0].generation
  def top_node_to(right: pygit2.DiffHunk) -> Node:
    old = Span.from_old(right).adjacent_down_to(1).to_git()
    new = Span.from_new(right).adjacent_down_to(1).to_git()
    return Node.inactive(old, new, generation)
  def node_between(left: pygit2.DiffHunk, right: pygit2.DiffHunk) -> Node:
    old_left = Span.from_old(left)
    new_left = Span.from_new(left)
    old_right = Span.from_old(right)
    new_right = Span.from_new(right)
    old = old_left.adjacent_up_to(old_right.start).to_git()
    new = new_left.adjacent_up_to(new_right.start).to_git()
    if debug.is_logging('update'):
      debug.get('update').debug(
        f"creating between: {Node.inactive(old, new, generation)}")
    return Node.inactive(old, new, generation)
  def bottom_node_from(left: pygit2.DiffHunk) -> Node:
    old = Span.from_old(left).adjacent_up_to(inf).to_git()
    new = Span.from_new(left).adjacent_up_to(inf).to_git()
    return Node.inactive(old, new, generation)

  return \
    [top_node_to(nodes[0].hunk)] + \
    [el
     for left, right in zip(nodes, nodes[1:])
     for el in [left, node_between(left.hunk, right.hunk)]
     ] + \
    [nodes[-1]] + \
    [bottom_node_from(nodes[-1].hunk)]


def update_dangling(file_spg: SPG,
                    nodes: List[Node],
                    generation: int):
  for prev_node in nodes:
    if debug.is_logging('update'):
      debug.get('update').debug(f"Checking dangling: {prev_node}: "
                                f"{file_spg.graph[prev_node]}")
    if SINK in file_spg.graph[prev_node]:
      propagated = Node.propagated(prev_node, generation)
      if debug.is_logging('update'):
        debug.get('update').debug(
          f"updating dangling to generation {generation}:\n"
          f" {pformat(prev_node)}")
      register(file_spg, prev_node, propagated)
      register(file_spg, propagated, SINK)


def update_unchanged_file(file_spg: SPG, generation):
  prev_nodes_by_end = sorted(
    [start for start, ends in file_spg.items()
     if SINK in ends],
    key=lambda node: node.hunk.new_start)
  if debug.is_logging('update'):
    debug.get('update').debug(
      f"propagating unchanged to generation {generation}:\n"
      f" {pformat(prev_nodes_by_end)}")
  for prev_node in prev_nodes_by_end:
    propagated = Node.propagated(prev_node, generation)
    add_on_top_of(file_spg, prev_nodes_by_end, propagated)

  update_dangling(file_spg, prev_nodes_by_end, generation)


def update_file(file_spg: SPG,
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

  if filepatch.delta.is_binary:
    nodes_by_start = [Node.active_binary(filepatch.delta, generation)]
  else:
    hunks_by_start = sorted(filepatch.hunks, key=lambda hunk: hunk.old_start)
    nodes_by_start = [Node.active(diff_hunk, generation)
                      for diff_hunk in hunks_by_start]
  nodes_by_start = surround_with_inactive(nodes_by_start)
  if debug.is_logging('update'):
    debug.get('update').debug(
      f"updating changed to generation {generation}:\n"
      f" {pformat(nodes_by_start)}")
  prev_nodes_by_end = sorted(
    [start for start, ends in file_spg.items()
     if SINK in ends],
    key=lambda node: node.hunk.new_start)

  for cur_node in nodes_by_start:
    add_on_top_of(file_spg, prev_nodes_by_end, cur_node)

  # Not too early, this prepagation is too dumb to be applied to proper
  # nodes
  update_dangling(file_spg, prev_nodes_by_end, generation)

  debug.get('update').debug("------------------ done update_file")
  return file_spg


@dataclass(frozen=True)
class FileId:
  commit: int
  path: str

  def tuple(self):
    return tuple([self.path, self.commit])


def update_commit_diff(
        spgs: Dict[FileId, SPG],
        files: Dict[FileId, FileId],
        commit_diff: CommitDiff,
        diff_i: int):
  return update(spgs, files, Diff(commit_diff.filepatches), diff_i)


def update(spgs: Dict[FileId, SPG],
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
      if debug.is_logging('update_files'):
        debug.get('update_files').debug(
          f"mapped unchanged {new_file_id} to original {files[file_id]}")
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
        if debug.is_logging('update_files'):
          debug.get('update_files').debug(
            f"created undiscovered old {old_file_id}")
        files[old_file_id] = old_file_id

      # Register file's new name
      new_file_id = new_patch_file_id(filepatch)
      files[new_file_id] = files[old_file_id]
      if debug.is_logging('update_files'):
        debug.get('update_files').debug(
          f"mapping changed {new_file_id} "
          f"to original {files[old_file_id]} "
          f"via {old_file_id}")
      return files[new_file_id]

    return [
      update_changed(filepatch)
      for filepatch in diff
    ]

  # Update graph of files that have not changed
  for file_id in update_unchanged_files():
    if debug.is_logging('update_files'):
      debug.get('update_files').debug(f"unchanged {file_id} in commit {diff_i}")
    original_file_id = files[file_id]
    file_spg = spgs[original_file_id]
    update_unchanged_file(file_spg, diff_i)

  # Update graph of files that have changes (are in the diff)
  update_changed_files()
  for filepatch in diff:
    original_file_id = files[new_patch_file_id(filepatch)]
    if debug.is_logging('update_files'):
      debug.get('update_files').debug(
        f"changed {new_patch_file_id(filepatch)} in commit {diff_i}")
    if original_file_id not in spgs:
      spgs[original_file_id] = empty_spg()
      file_spg = spgs[original_file_id]
      # Create nodes for older commits where the file did not exist
      # yet (=unchanged)
      for i in range(diff_i):
        update_unchanged_file(file_spg, i)
    file_spg = spgs[original_file_id]
    update_file(file_spg, filepatch, diff_i)


def all_paths(spg: SPG, source=SOURCE) -> List[List[Node]]:
  if source == SINK:
    return [[SINK]]
  paths= [[source] + path
    for end in sorted(spg.graph[source], key=lambda node:
    tuple([node.hunk.old_start,
           node.hunk.new_start,
           node.hunk.old_lines,
           node.hunk.new_lines]))
    for path in all_paths(spg, end)]
  if debug.is_logging('grouping'):
    debug.get('grouping').debug(f"paths: \n{pformat(paths)}")
  return paths


def print_fragmap(spg: SPG):
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

  pprint(files)
  for spg in spgs.values():
    pprint(all_paths(spg))
    print_fragmap(spg)


if __name__ == '__main__':
  main()
