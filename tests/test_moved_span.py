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
import unittest
from math import inf

from fragmap.update import moved_span
from fragmap.span import Span
from fragmap.spg import DiffHunk, Node, CommitNodes


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
