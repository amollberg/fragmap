from pprint import pformat
from typing import List

from fragmap import debug
from fragmap.spg import SPG, SOURCE, Node, SINK
from fragmap.update import node_by_new


def all_paths(spg: SPG, source=SOURCE) -> List[List[Node]]:
  if source == SINK:
    return [[SINK]]
  paths = [[source] + path
           for end in sorted(spg.graph[source], key=node_by_new)
           for path in all_paths(spg, end)]
  if debug.is_logging('grouping'):
    debug.get('grouping').debug(f"paths: \n{pformat(paths)}")
  return paths
