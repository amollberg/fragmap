import unittest
from math import inf

from fragmap.span import Span
from fragmap.spg import DiffHunk, Node, CommitNodes
from fragmap.graph import moved_span


class MovedSpanTest(unittest.TestCase):
  def test_initial_insertion(self):
    changes = CommitNodes([
      node(True, Span(1, 1), Span(1, 2))
    ])
    self.assertEqual([Span(0, 1),
                      Span(2, inf)],
                     moved_span(changes, Span(0, inf)))

  def test_offset_earlier_change(self):
    changes = CommitNodes([
      node(True, Span(10, 10), Span(10, 25))
    ])
    self.assertEqual([Span(28, 29)],
                     moved_span(changes, Span(13, 14)))


def node(active: bool, old: Span, new: Span):
  if active:
    return Node.active(DiffHunk.from_tup(old.to_git(), new.to_git()), 99)
  else:
    return Node.inactive(old.to_git(), new.to_git(), 99)


if __name__ == '__main__':
  unittest.main()
