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

from fragmap.generate_matrix import *


# Test helpers

def create_base_cell(character):
  if character == ' ':
    return SingleNodeCell(CellKind.NO_CHANGE, None, None)
  if character == '^':
    return SingleNodeCell(CellKind.BETWEEN_CHANGES, None, '^')
  return SingleNodeCell(CellKind.CHANGE, None, str(character))


def create_node_matrix_from_description(desc_matrix):
  return [[create_base_cell(cell) for cell in row] for row in desc_matrix]


assert [[SingleNodeCell(CellKind.CHANGE, None, '3'),
         SingleNodeCell(CellKind.NO_CHANGE, None, None)]] == \
       create_node_matrix_from_description(['3 '])


def create_connection_matrix_from_description(desc_matrix):
  def create_connected_cell(up_row, mid_row, down_row):
    up_left, up, up_right = up_row
    left, center, right = mid_row
    down_left, down, down_right = down_row

    def connection_status(character):
      if character == ' ':
        return ConnectionStatus.EMPTY
      if character == '^':
        return ConnectionStatus.INFILL
      return ConnectionStatus.CONNECTION

    return ConnectedCell(create_base_cell(center),
                         Status9Neighborhood(up_left=connection_status(up_left),
                                             up=connection_status(up),
                                             up_right=connection_status(
                                               up_right),
                                             left=connection_status(left),
                                             center=connection_status(center),
                                             right=connection_status(right),
                                             down_left=connection_status(
                                               down_left),
                                             down=connection_status(down),
                                             down_right=connection_status(
                                               down_right)))

  n_rows = len(desc_matrix) / 3
  n_cols = len(desc_matrix[0])
  return [[create_connected_cell(desc_matrix[3 * r][c],
                                 desc_matrix[3 * r + 1][c],
                                 desc_matrix[3 * r + 2][c])
           for c in range(n_cols)] for r in range(n_rows)]


class FakeFragmap(object):

  def __init__(self, matrix):
    self.matrix = matrix
    self.patches = []

  def generate_matrix(self):
    return self.matrix


class ConnectionTest(unittest.TestCase):

  def test_1(self):
    self.check_matrix([['   '],
                       [' 1 '],
                       ['   ']], ['1'])

  def test_2(self):
    self.check_matrix([['   ', '   '],
                       [' 1 ', ' 2 '],
                       ['   ', '   ']],
                      ['12'])

  def test_3(self):
    self.check_matrix([['   ', '   '],
                       [' 1-', '-1 '],
                       ['   ', '   ']],
                      ['11'])

  def test_4(self):
    self.check_matrix([['   '],
                       [' 1 '],
                       [' | '],
                       [' | '],
                       [' 1 '],
                       ['   ']],
                      ['1',
                       '1'])

  def test_5(self):
    self.check_matrix([['   '],
                       [' 1 '],
                       [' | '],

                       [' | '],
                       [' ^ '],
                       [' | '],

                       [' | '],
                       [' 1 '],
                       ['   ']],
                      ['1',
                       '^',
                       '1'])

  def test_5b(self):
    self.check_matrix([['   '],
                       [' 1 '],
                       [' | '],

                       [' | '],
                       [' ^ '],
                       [' | '],

                       [' | '],
                       [' ^ '],
                       [' | '],

                       [' | '],
                       [' 1 '],
                       ['   ']],
                      ['1',
                       '^',
                       '^',
                       '1'])

  def test_6(self):
    self.check_matrix([['   ', '   '],
                       ['   ', ' 2 '],
                       ['   ', '   '],

                       ['   ', '   '],
                       [' 1 ', '   '],
                       ['   ', '   ']],
                      [' 2',
                       '1 '])

  def test_7(self):
    self.check_matrix([['   ', '   '],
                       [' 1-', '-1 '],
                       [' | ', '   '],

                       [' | ', '   '],
                       [' 1 ', '   '],
                       ['   ', '   ']],
                      ['11',
                       '1 '])

  def test_7b(self):
    self.check_matrix([['   ', '   '],
                       [' 1-', '-1 '],
                       [' | ', '   '],

                       [' | ', '   '],
                       [' ^ ', '   '],
                       [' | ', '   '],

                       [' | ', '   '],
                       [' 1 ', '   '],
                       ['   ', '   ']],
                      ['11',
                       '^ ',
                       '1 '])

  def test_8(self):
    self.check_matrix([['   ', '   ', '   '],
                       [' 1 ', '   ', '   '],
                       ['   ', '   ', '   '],

                       ['   ', '   ', '   '],
                       ['   ', ' 2 ', '   '],
                       ['   ', '   ', '   '],

                       ['   ', '   ', '   '],
                       ['   ', '   ', ' 3 '],
                       ['   ', '   ', '   ']],
                      ['1  ',
                       ' 2 ',
                       '  3'])

  def test_9(self):
    self.check_matrix([['   ', '   '],
                       [' 1 ', ' 2 '],
                       [' | ', ' | '],

                       [' |^', '^| '],
                       # TODO: Weird behavior, come up with useful and consistent style
                       [' 1-', '-1 '],
                       ['   ', '   ']],
                      ['12',
                       '11 '])

  def check_matrix(self, expected_connection_matrix, node_matrix):
    matrix = create_node_matrix_from_description(node_matrix)
    connected_fragmap = ConnectedFragmap(FakeFragmap(matrix))
    actual_description = connected_fragmap.render_for_console(False)

    def assert_same_description(actual, expected):
      def join_rows(matrix_description):
        return [''.join(row) for row in matrix_description]

      def match_fail_string(actual, expected, row, col):
        s = []

        def line(string):
          s.append(string)

        assert expected[row][col] != actual[row][col]
        line('Match fail at row %s, column %s' % (row, col))
        for r in range(row):
          line('[%s]' % (actual[r],))
        line('[%s]' % (actual[row],))
        line("%s^ expected '%s'" % (' ' * (col + 1), expected[row][col]))
        for r in range(row + 1, len(actual)):
          line('[%s]' % (actual[r],))
        line('----')
        return '\n'.join(s)

      def check_description(actual, expected):
        self.assertEqual(len(actual), len(expected))
        for r in range(len(actual)):
          self.assertEqual(len(actual[r]), len(expected[r]))
          for c in range(len(actual[r])):
            if actual[r][c] != expected[r][c]:
              self.fail(match_fail_string(actual, expected, r, c))

      check_description(join_rows(actual), join_rows(expected))

    assert_same_description(actual_description, expected_connection_matrix)
