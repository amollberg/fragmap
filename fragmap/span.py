#!/usr/bin/env python
# To be able to use the enclosing class type in class method type hints
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from pygit2._pygit2 import DiffHunk


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
