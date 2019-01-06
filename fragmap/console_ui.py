#!/usr/bin/env python
# encoding: utf-8
from __future__ import print_function
from backports.shutil_get_terminal_size import get_terminal_size

from fragmap.generate_matrix import ConnectedFragmap
from console_color import *



def lzip(*args):
  """
  zip(...) but returns list of lists instead of list of tuples
  """
  return [list(el) for el in zip(*args)]


def filter_consecutive_equal_columns(char_matrix):
  transposed_matrix = lzip(*char_matrix)
  filtered_matrix = []
  for col in transposed_matrix:
    if filtered_matrix == []:
      filtered_matrix.append(col)
    if filtered_matrix[-1] == col:
      continue
    if (''.join(col)).strip('. ') == '':
      continue
    filtered_matrix.append(col)
  return lzip(*filtered_matrix)


def print_fragmap(fragmap, do_color):
  matrix = fragmap.render_for_console(do_color)
  matrix = filter_consecutive_equal_columns(matrix)
  if len(matrix) == 0:
    return
  matrix_width = len(matrix[0])
  hash_width = 8
  padded_matrix_width = matrix_width
  terminal_column_size = get_terminal_size().columns
  if terminal_column_size == 0:
    # Fall back to a default value
    terminal_column_size = 80
  max_actual_commit_width = max([len(p._header._message[0]) for p in fragmap.patches])
  max_commit_width = max(0, min(max_actual_commit_width + 1,
                                terminal_column_size/2,
                                terminal_column_size - (hash_width + 1 + 1 + padded_matrix_width)))
  def infill_layout(matrix, print_text_action, print_matrix_action):
    r = 0
    for i in xrange(len(matrix)):
      r = i / 3
      if i % 3 == 1:
        print_text_action(r)
      else:
        print(''.ljust(hash_width + 1 + max_commit_width), end='')
      print_matrix_action(i)
  def normal_layout(matrix, print_text_action, print_matrix_action):
    for r in xrange(len(matrix)):
      print_text_action(r)
      print_matrix_action(r)
  # Draw the text and matrix
  def print_line(r):
    cur_patch = fragmap.patches[r]._header
    commit_msg = cur_patch._message[0] # First row of message
    hash = cur_patch._hash
    # Pad short commit messages
    commit_msg = commit_msg.ljust(max_commit_width, ' ')
    # Truncate long commit messages
    commit_msg = commit_msg[0:min(max_commit_width,len(commit_msg))]
    # Print hash, commit, matrix row
    hash = hash[0:hash_width]
    if do_color:
      hash = ANSI_FG_CYAN + hash + ANSI_RESET
    print(hash, commit_msg, end='')

  def print_matrix(r):
    print(''.join(matrix[r]), ' ')

  if isinstance(fragmap, ConnectedFragmap):
    infill_layout(matrix, print_line, print_matrix)
  else:
    normal_layout(matrix, print_line, print_matrix)
  lines_printed = len(matrix)
  return lines_printed
