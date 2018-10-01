#!/usr/bin/env python
# encoding: utf-8

from yattag import Doc
from generate_matrix import Cell

import os


def open_fragmap_page(fragmap):
  matrix = fragmap.generate_matrix()
  print(matrix)

  def render_cell(cell):
    with tag('span', **{'class': 'matrix_cell'}):
      if cell.kind == Cell.CHANGE:
        text('#')
      if cell.kind == Cell.BETWEEN_CHANGES:
        text('^')
      if cell.kind == Cell.NO_CHANGE:
        text('.')

  doc, tag, text = Doc().tagtext()
  def get_html():
    with tag('html'):
      with tag('head'):
        with tag('style', type='text/css'):
          text('th { text-align: left; }')
          text('.matrix_cell { font-family: monospace; }')
      with tag('body'):
        with tag('table'):
          for r in range(len(matrix)):
            cur_patch = fragmap.patches[r]._header
            commit_msg = cur_patch._message[0] # First row of message
            hash = cur_patch._hash
            with tag('tr'):
              with tag('th'):
                text(commit_msg)
              with tag('th'):
                text(hash)
              for c in matrix[r]:
                with tag('th'):
                  render_cell(c)
    return doc.getvalue()
  with open('fragmap.html', 'w') as f:
    f.write(get_html())
    os.startfile(f.name)
