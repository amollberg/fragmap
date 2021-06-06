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

# To be able to use the enclosing class type in class method type hints
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from pprint import pformat
from typing import List, Dict, Union, Tuple

import pygit2
from pygit2 import DiffHunk

from fragmap.commitdiff import CommitDiff
from fragmap.datastructure_util import flatten
from fragmap.span import Span, Overlap
from fragmap.spg import SPG, Node, DiffHunk, SINK, FileId, CommitNodes
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
class Patch:
  delta: DiffDelta
  hunks: list[DiffHunk]


class Diff(list):
  pass


@dataclass(frozen=True)
class Commit:
  hex: str
  message: str


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
      spg.register(prev_node, node)
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
      spg.register(prev_node, node)
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
      spg.register(prev_node, node)
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
      spg.register(prev_node, node)
    return do_register

  def add_if_overlap(prev_node):
    prev_range = Span.from_new(prev_node.hunk)
    overlap = cur_range.overlap(prev_range)
    do_register = overlap != Overlap.NO_OVERLAP
    if debug.is_logging('update'):
      debug.get('update').debug(
        f"add_if_overlap on {prev_range}? {do_register}")
    if do_register:
      spg.register(prev_node, node)
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
      some_overlap = some_overlap or \
                     add_unless_point_to_downstream_active(prev_node)

  if not some_overlap:
    for prev_node in nodes_from_previous_commit:
      some_overlap = some_overlap or add_unless_point_to_active(prev_node)

  if not some_overlap:
    for prev_node in nodes_from_previous_commit:
      some_overlap = some_overlap or add_if_to_inactive(prev_node)

  if not some_overlap:
    for prev_node in nodes_from_previous_commit:
      some_overlap = some_overlap or add_if_overlap(prev_node)

  spg.register(node, SINK)
  if not some_overlap:
    debug.get('update').critical(
      '\n'.join([
        "-----------------",
        "SPG:", spg.pformat(),
        "Previous nodes:", pformat(nodes_from_previous_commit),
        "To be added:", str(cur_range), pformat(node)
      ])
    )
  assert some_overlap


@dataclass
class DiffSpan:
  old: Span
  new: Span

  @staticmethod
  def from_hunk(hunk: Union[pygit2.DiffHunk, DiffHunk]):
    return DiffSpan(old=Span.from_old(hunk),
                    new=Span.from_new(hunk))


@dataclass
class RowLutEntry:
  old: int
  new: int
  start_of_change: bool


@dataclass
class RowLut:
  _entries_by_old: Dict[Tuple[int, bool], RowLutEntry]
  # Keep an explicit list to ensure a sorted list of keys is accessible
  _old_keys: List[int]

  @staticmethod
  def from_diff_spans(spans: List[DiffSpan]):
    entries = flatten([
      [RowLutEntry(change.old.start, change.new.start, True),
       RowLutEntry(change.old.end, change.new.end, False)]
      for change in spans])
    return RowLut({(entry.old, entry.start_of_change): entry
                   for entry in entries},
                  [entry.old for entry in entries])

  def lookup_old_start(self, old_row: int):
    key_index = bisect_right(self._old_keys, old_row)
    if key_index == 0:
      return old_row
    else:
      key_index -= 1
      key = (self._old_keys[key_index], False)
      entry = self._entries_by_old[key]
      new_row = old_row - entry.old + entry.new
      return new_row

  def lookup_old_end(self, old_row: int):
    # Note: Since ends of spans are exclusive, we really want the entry
    # affecting the previous row
    key_index = bisect_right(self._old_keys, old_row - 1)
    if key_index == 0:
      return old_row
    else:
      key_index -= 1
      key = (self._old_keys[key_index], False)
      entry = self._entries_by_old[key]
      new_row = old_row - entry.old + entry.new
      return new_row


def moved_span(new_changes: CommitNodes, old: Span) -> List[Span]:
  new_change_spans = [DiffSpan.from_hunk(node.hunk)
                      for node in new_changes.nodes]
  # For lookup from old row to new row
  row_lut = RowLut.from_diff_spans(new_change_spans)

  def overhanging(change: DiffSpan, to_update: Span) -> List[Span]:
    """ Return a list of spans that cover the updated span but not the given
        change.
    """
    # to_update: |       [---]
    # change:    | [---]
    if change.old.end <= to_update.start:
      return [to_update]
    # to_update: |    [---]
    # change:    | [---]
    elif change.old.end <= to_update.end and change.old.start <= to_update.start:
      return [Span(change.old.end, to_update.end)]
    # to_update: |    [---]
    # change:    |     [-]
    elif change.old.end <= to_update.end and change.old.start > to_update.start:
      return [Span(to_update.start, change.old.start),
              Span(change.old.end, to_update.end)]
    # to_update: |    [---]
    # change:    | [--------]
    elif change.old.end >= to_update.end and \
            change.old.start <= to_update.start:
      return []
    # to_update: |    [---]
    # change:    |      [---]
    elif change.old.start <= to_update.end:
      return [Span(to_update.start, change.old.start)]
    elif change.old.start >= to_update.end:
      return [to_update]
    print("unknown case:", change, to_update)
    assert False

  def update(to_update: Span) -> Span:
    new_start = row_lut.lookup_old_start(to_update.start)
    new_end = row_lut.lookup_old_end(to_update.end)
    return Span(new_start, new_end)

  overhang = [old]

  for new_change in new_change_spans:
    overhang = [span
                for resulting_span in overhang
                for span in overhanging(new_change, resulting_span)]
  overhang = [span
              for span in overhang
              if not span.is_empty()]
  updated = [update(span) for span in overhang]
  if debug.is_logging('update'):
    debug.get('update').debug("(ov)-> %s", overhang)
    debug.get('update').debug("moved_span: %s %s", old, new_change_spans)
    debug.get('update').debug("    -> %s", updated)
  return updated


def add_and_propagate(prev_commit: CommitNodes,
                      commit: CommitNodes) -> CommitNodes:
  generation = prev_commit.nodes[0].generation + 1
  prev_commit = CommitNodes([node
                             for node in prev_commit.nodes
                             if not Span.from_new(node.hunk).is_empty()])
  added = commit.nodes

  # 1. empty, add all from commit (supposedly all are active), propagate the
  #    non-overlapping parts of the previous
  # -> row delta computation: start and en separately, common function
  def propagate(prev_node: Node):
    prev_span = Span.from_new(prev_node.hunk)
    new_spans = moved_span(commit, prev_span)
    return [Node.inactive(prev_span.to_git(), new_span.to_git(), generation)
            for new_span in new_spans]

  propagated = [span
                for prev_node in prev_commit.nodes
                for span in propagate(prev_node)]

  new_nodes = sorted(added + propagated, key=node_by_new)
  return CommitNodes(new_nodes)


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
          f" {pformat(prev_node)} {DiffSpan.from_hunk(prev_node.hunk)}")
      file_spg.register(prev_node, propagated)
      file_spg.register(propagated, SINK)


def update_unchanged_file(file_spg: SPG, generation):
  prev_nodes_by_new = \
    sorted([start for start, ends in file_spg.items()
            if SINK in ends],
           key=node_by_new)
  if debug.is_logging('update'):
    debug.get('update').debug(
      f"propagating unchanged to generation {generation}:\n"
      f" {pformat(prev_nodes_by_new)}")
  new_commit = add_and_propagate(CommitNodes(prev_nodes_by_new),
                                 # No changes
                                 CommitNodes([]))
  nodes_by_old = sorted(new_commit.nodes, key=node_by_old)

  if debug.is_logging('update'):
    debug.get('update').debug(
      f"updating unchanged to generation {generation}:\n"
      f" {pformat(nodes_by_old)}")

  for cur_node in nodes_by_old:
    add_on_top_of(file_spg, prev_nodes_by_new, cur_node)

  update_dangling(file_spg, prev_nodes_by_new, generation)


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
    nodes_by_old = [Node.active_binary(filepatch.delta, generation)]
  else:
    nodes_by_old = sorted([Node.active(diff_hunk, generation)
                           for diff_hunk in filepatch.hunks],
                          key=node_by_old)
  prev_nodes_by_new = sorted([start for start, ends in file_spg.items()
                              if SINK in ends],
                             key=node_by_new)
  # Propagate the previous nodes and overwriting with the new ones
  new_commit = add_and_propagate(CommitNodes(prev_nodes_by_new),
                                 CommitNodes(nodes_by_old))
  nodes_by_old = sorted(new_commit.nodes, key=node_by_old)

  if debug.is_logging('update'):
    debug.get('update').debug(
      f"updating changed to generation {generation}:\n"
      f" {pformat(nodes_by_old)}")

  for cur_node in nodes_by_old:
    add_on_top_of(file_spg, prev_nodes_by_new, cur_node)

  # Not too early, this prepagation is too dumb to be applied to proper
  # nodes
  update_dangling(file_spg, prev_nodes_by_new, generation)

  debug.get('update').debug("------------------ done update_file")
  return file_spg


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
    return FileId(diff_i - 1, filepatch.delta.old_file.path)

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
      spgs[original_file_id] = SPG.empty()
      file_spg = spgs[original_file_id]
      # Create nodes for older commits where the file did not exist
      # yet (=unchanged)
      for i in range(diff_i):
        update_unchanged_file(file_spg, i)
    file_spg = spgs[original_file_id]
    update_file(file_spg, filepatch, diff_i)


def node_by_old(node: Node):
  spans = DiffSpan.from_hunk(node.hunk)
  return tuple([spans.old.start,
                spans.new.start,
                spans.old.end,
                spans.new.end])


def node_by_new(node: Node):
  spans = DiffSpan.from_hunk(node.hunk)
  return tuple([spans.new.start,
                spans.old.start,
                spans.new.end,
                spans.old.end])
