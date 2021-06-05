#!/usr/bin/env python
# encoding: utf-8

import unittest

from fragmap.update import Overlap
from fragmap.span import Span


class SpanTest(unittest.TestCase):
  def test_overlaps_same_start(self):
    self.assertEqual(Overlap.INTERVAL_OVERLAP,
                     self.overlap(Span(0, 1), Span(0, 2)))

  def test_not_overlaps_adjacent(self):
    self.assertEqual(Overlap.NO_OVERLAP,
                     self.overlap(Span(0, 1), Span(1, 2)))

  def test_overlaps_empty_contained(self):
    self.assertEqual(Overlap.POINT_OVERLAP,
                     self.overlap(Span(0, 2), Span(1, 1)))

  def test_overlaps_same_end(self):
    self.assertEqual(Overlap.INTERVAL_OVERLAP,
                     self.overlap(Span(1, 2), Span(0, 2)))

  def test_overlaps_empty_at_start(self):
    self.assertEqual(Overlap.POINT_OVERLAP,
                     self.overlap(Span(0, 2), Span(0, 0)))

  def test_overlaps_empty_at_end(self):
    self.assertEqual(Overlap.POINT_OVERLAP,
                     self.overlap(Span(0, 2), Span(2, 2)))

  def test_overlaps_empty_at_end2(self):
    self.assertEqual(Overlap.POINT_OVERLAP,
                     self.overlap(Span(1, 3), Span(3, 3)))

  def overlap(self, a, b):
    self.assertEqual(a.overlap(b), b.overlap(a))
    return a.overlap(b)


if __name__ == '__main__':
  unittest.main()
