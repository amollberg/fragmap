#!/usr/bin/env python
# encoding: utf-8

from backports.shutil_get_terminal_size import get_terminal_size

from fragmap.common_ui import first_line
from fragmap.generate_matrix import ConnectedFragmap
from .console_color import *
from .datastructure_util import lzip


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
    return 0, 0
  matrix_width = len(matrix[0])
  hash_width = 8
  padded_matrix_width = matrix_width
  reported_terminal_column_size = get_terminal_size().columns
  if reported_terminal_column_size == 0:
    # Fall back to a default value
    reported_terminal_column_size = 80
  # Note: Subtracting two because ConEmu/Cmder line wraps two columns before
  terminal_column_size = reported_terminal_column_size - 2
  max_actual_commit_width = max([len(first_line(p.header.message))
                                 for p in fragmap.patches()])
  max_commit_width = max(0, min(max_actual_commit_width + 1,
                                int(terminal_column_size / 2),
                                terminal_column_size - (
                                          hash_width + 1 + 1 + padded_matrix_width)))
  actual_total_width = hash_width + 1 + max_commit_width + 1 + padded_matrix_width

  def infill_layout(matrix, print_text_action, print_matrix_action):
    r = 0
    for i in range(len(matrix)):
      r = i / 3
      if i % 3 == 1:
        print_text_action(r)
      else:
        print(''.ljust(hash_width + 1 + max_commit_width), end='')
      print_matrix_action(i)

  def normal_layout(matrix, print_text_action, print_matrix_action):
    for r in range(len(matrix)):
      print_text_action(r)
      print_matrix_action(r)

  # Draw the text and matrix
  def print_line(r):
    cur_patch = fragmap.patches()[r].header
    commit_msg = first_line(cur_patch.message)
    hash = cur_patch.hex
    # Pad short commit messages
    commit_msg = commit_msg.ljust(max_commit_width, ' ')
    # Truncate long commit messages
    commit_msg = commit_msg[0:min(max_commit_width, len(commit_msg))]
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
  return lines_printed, actual_total_width
