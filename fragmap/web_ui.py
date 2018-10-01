#!/usr/bin/env python
# encoding: utf-8

from yattag import Doc
from generate_matrix import Cell

import os


def open_fragmap_page(fragmap):
  matrix = fragmap.generate_matrix()
  print(matrix)

  def render_cell(cell):
    classes = ['matrix_cell']
    if cell.kind == Cell.CHANGE:
      classes.append('cell_change')
      cell_text = '#'
    elif cell.kind == Cell.BETWEEN_CHANGES:
      classes.append('cell_between_changes')
      cell_text = '^'
    elif cell.kind == Cell.NO_CHANGE:
      classes.append('cell_no_change')
      cell_text = '.'
    with tag('div', **{'class': ' '.join(classes)}):
      text(cell_text)


  doc, tag, text = Doc().tagtext()
  def get_html():
    with tag('html'):
      with tag('head'):
        with tag('style', type='text/css'):
          text("""
               table {
                 border-collapse: collapse;
               }
               th {
                 text-align: left;
                 vertical-align: bottom;
                 padding: 0;
               }
               .commit_hash {
                 font-family: monospace;
                 margin-right: 10pt;
               }
               .commit_message {
                 margin-right: 10pt;
               }
               .matrix_cell, .matrix_cell > div {
                 font-family: monospace;
                 width: 100%;
                 height: 100%;
                 padding: 0;
               }
               .cell_change {
                 background-color: yellow;
               }
               .cell_between_changes {
                 background-color: red;
               }
               .cell_no_change {
                 background-color: green;
               }""")
      with tag('body'):
        with tag('table'):
          for r in range(len(matrix)):
            cur_patch = fragmap.patches[r]._header
            commit_msg = cur_patch._message[0] # First row of message
            hash = cur_patch._hash
            with tag('tr'):
              with tag('th'):
                with tag('span', **{'class': 'commit_hash'}):
                  text(hash[0:8])
              with tag('th'):
                with tag('span', **{'class': 'commit_message'}):
                  text(commit_msg)
              for c in matrix[r]:
                with tag('th'):
                  render_cell(c)
    return doc.getvalue()
  with open('fragmap.html', 'w') as f:
    f.write(get_html())
    os.startfile(f.name)
