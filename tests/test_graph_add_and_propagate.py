#!/usr/bin/env python
# encoding: utf-8

import unittest
from math import inf

from fragmap.update import add_and_propagate
from fragmap.span import Span
from fragmap.spg import DiffHunk, Node, CommitNodes


class GraphAddAndPropagateTest(unittest.TestCase):
  maxDiff = None

  def test_propagate_without_change(self):
    previous = CommitNodes([
      node(False, Span(1, 1), Span(1, 3), 0),
      node(True, Span(1, 1), Span(3, 5), 0),
      node(False, Span(1, 1), Span(5, inf), 0),
    ])
    new = CommitNodes([])
    self.assertEqualCommitNodes(CommitNodes([
      node(False, Span(1, 3), Span(1, 3), 1),
      node(False, Span(3, 5), Span(3, 5), 1),
      node(False, Span(5, inf), Span(5, inf), 1),
    ]), add_and_propagate(previous, new))

  def test_add_active_to_empty(self):
    previous = CommitNodes([
      node(False, Span(1, 1), Span(1, inf), 0),
    ])
    new = CommitNodes([
      node(True, Span(2, 4), Span(2, 4), 1),
    ])
    self.assertEqualCommitNodes(CommitNodes([
      node(False, Span(1, inf), Span(1, 2), 1),
      node(True, Span(2, 4), Span(2, 4), 1),
      node(False, Span(1, inf), Span(4, inf), 1),
    ]), add_and_propagate(previous, new))

  def test_add_partial_overlap_rewrite_active(self):
    previous = CommitNodes([
      node(False, Span(1, 1), Span(1, 3), 0),
      node(True, Span(1, 1), Span(3, 5), 0),
      node(False, Span(1, 1), Span(5, inf), 0),
    ])
    new = CommitNodes([
      node(True, Span(2, 4), Span(2, 4), 1),
    ])
    self.assertEqualCommitNodes(CommitNodes([
      node(False, Span(1, 3), Span(1, 2), 1),
      node(True, Span(2, 4), Span(2, 4), 1),
      node(False, Span(3, 5), Span(4, 5), 1),
      node(False, Span(5, inf), Span(5, inf), 1),
    ]), add_and_propagate(previous, new))

  def test_ignore_old_point_spans(self):
    previous = CommitNodes([
      node(False, Span(1, 3), Span(1, 3), 0),
      node(True, Span(3, 4), Span(3, 3), 0),
      node(False, Span(4, inf), Span(3, inf), 0),
    ])
    new = CommitNodes([])
    self.assertEqualCommitNodes(CommitNodes([
      node(False, Span(1, 3), Span(1, 3), 1),
      node(False, Span(3, inf), Span(3, inf), 1),
    ]), add_and_propagate(previous, new))

  def test_keep_new_point_spans(self):
    previous = CommitNodes([
      node(False, Span(1, inf), Span(1, inf), 0),
    ])
    new = CommitNodes([
      node(True, Span(3, 4), Span(3, 3), 1),
    ])
    self.assertEqualCommitNodes(CommitNodes([
      node(False, Span(1, inf), Span(1, 3), 1),
      node(False, Span(1, inf), Span(3, inf), 1),
      node(True, Span(3, 4), Span(3, 3), 1),
    ]), add_and_propagate(previous, new))

  def test_003_004(self):
    previous = CommitNodes([
      node(False, Span(0, inf), Span(0, 1), 0),
      node(True, Span(1, 1), Span(1, 2), 0),
      node(False, Span(0, inf), Span(2, inf), 0),
    ])
    new = CommitNodes([
      node(True, Span(1, 2), Span(1, 1), 1),
    ])
    self.assertEqualCommitNodes(CommitNodes([
      node(False, Span(0, 1), Span(0, 1), 1),
      node(True, Span(1, 2), Span(1, 1), 1),
      node(False, Span(2, inf), Span(1, inf), 1),
    ]), add_and_propagate(previous, new))

  def assertEqualCommitNodes(self,
                             expected: CommitNodes,
                             actual: CommitNodes):
    self.assertEqual(expected.nodes, actual.nodes)


def node(active: bool, old: Span, new: Span, generation: int):
  if active:
    return Node.active(DiffHunk.from_tup(old.to_git(), new.to_git()),
                       generation)
  else:
    return Node.inactive(old.to_git(), new.to_git(), generation)


if __name__ == '__main__':
  unittest.main()
