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
