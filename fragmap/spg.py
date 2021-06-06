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

import dataclasses
from dataclasses import dataclass
from math import inf
from pprint import pformat
from typing import Dict, List, Union

import pygit2

from fragmap.load_commits import is_nullfile
from fragmap.span import Span
from fragmap.list_dict import StableListDict


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
        (0, 0) if is_nullfile(diff_delta.old_file) else (1, 1),
        (0, 0) if is_nullfile(diff_delta.new_file) else (1, 1)
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
class FileId:
  commit: int
  path: str

  def tuple(self):
    return tuple([self.path, self.commit])


@dataclass
class CommitNodes:
  nodes: List[Node]


SOURCE = Node.inactive((0, 0), (0, inf), -1)
SINK = Node.inactive((0, inf), (0, 0), inf)


@dataclass
class SPG:
  graph: Dict[Node, List[Node]]
  downstream_from_active: Dict[Node, bool] = \
    dataclasses.field(default_factory=lambda: {})

  @staticmethod
  def empty() -> SPG:
    return SPG({
      SOURCE: [SINK],
    }, downstream_from_active={
      SOURCE: False
    })

  def register(self, prev_node, node):
    if prev_node not in self.graph.keys():
      self.graph[prev_node] = []
    self.graph[prev_node] = [item for item in self.graph[prev_node]
                             if item != SINK]
    self.graph[prev_node].append(node)
    self.propagate_active(prev_node, node)

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

  def commits(self) -> Dict[int, CommitNodes]:
    nodes_by_commit = StableListDict()
    for node in self.nodes():
      nodes_by_commit.add(node.generation, node)
    sorted_by_generation = sorted(nodes_by_commit.items(), key=lambda kv: kv[0])
    return {generation: CommitNodes(nodes)
            for generation, nodes in sorted_by_generation}

  def to_dot(self, file_id: FileId):
    def name(node):
      if node == SOURCE:
        return "s"
      if node == SINK:
        return "t"

      prefix = ""
      if node.active:
        prefix += "A"
      if self.downstream_from_active[node]:
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
                      for start, ends in self.items()
                      for end in ends]) + \
           """
      s [shape=Mdiamond];
      t [shape=Msquare];
    }
  """

  def pformat(self):
    attributes = '\n'.join([
      f"{key}:\n{pformat(value, indent=3)}" for key, value in
      self.__dict__.items()])
    return f"SPG({attributes})\n{self.to_dot(FileId(0, 'unknown'))}"
