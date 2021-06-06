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
from pprint import pformat
from typing import List

from fragmap import debug
from fragmap.spg import SPG, SOURCE, Node, SINK
from fragmap.update import node_by_new

def _all_paths_without_deduplication(
        spg: SPG,
        source: Node) -> List[List[Node]]:
  if source == SINK:
    return [[SINK]]
  paths = [[source] + path
           for end in sorted(spg.graph[source], key=node_by_new)
           for path in _all_paths_without_deduplication(spg, end)]
  if debug.is_logging('grouping'):
    debug.get('grouping').debug(f"paths: \n{pformat(paths)}")
  return paths


def all_paths(spg: SPG, source=SOURCE) -> List[List[Node]]:
  """
  Enumerates all paths through the SPG. All inactive nodes are treated as
  idential and identical paths are skipped, so all returned paths will have a
  unique set of visited active nodes.
  """
  def path_key_ignoring_inactive(path: List[Node]):
    return tuple([tuple([node.generation, node_by_new(node)])
            if node.active else tuple()
            for node in path])
  paths = _all_paths_without_deduplication(spg, source)
  known_keys = set()
  for path in paths:
    k = path_key_ignoring_inactive(path)
    if k not in known_keys:
      known_keys.add(k)
      yield path
