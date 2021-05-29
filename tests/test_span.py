import unittest

from fragmap.graph import Span

class SpanTest(unittest.TestCase):
  def test_overlaps_same_start(self):
    self.assertTrue(self.overlap(Span(0, 1), Span(0, 2)))

  def test_not_overlaps_adjacent(self):
    self.assertFalse(self.overlap(Span(0, 1), Span(1, 2)))

  def test_overlaps_empty_contained(self):
    self.assertTrue(self.overlap(Span(0, 2), Span(1, 1)))

  def test_overlaps_same_end(self):
    self.assertTrue(self.overlap(Span(1, 2), Span(0, 2)))

  def test_overlaps_empty_at_start(self):
    self.assertTrue(self.overlap(Span(0, 2), Span(0, 0)))

  def test_overlaps_empty_at_end(self):
    self.assertTrue(self.overlap(Span(0, 2), Span(2, 2)))

  def overlap(self, a, b):
    self.assertEqual(a.overlaps(b), b.overlaps(a))
    return a.overlaps(b)



if __name__ == '__main__':
  unittest.main()
