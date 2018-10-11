#!/usr/bin/env python
# encoding: utf-8

from yattag import Doc
from generate_matrix import Cell, BriefFragmap


import collections
import os
import re


def nop():
  pass


def n_columns(matrix):
  if len(matrix) == 0:
    return 0
  return len(matrix[0])


def n_rows(matrix):
  return len(matrix)

def in_range(matrix, r, c):
  if r < 0 or r >= n_rows(matrix):
    return False
  if c < 0 or c >= n_columns(matrix):
    return False
  return True


def equal_left_column(matrix, r, c):
  if not in_range(matrix, r, c) or not in_range(matrix, r, c-1):
    return False
  return matrix[r][c-1].node == matrix[r][c].node


def equal_right_column(matrix, r, c):
  if not in_range(matrix, r, c) or not in_range(matrix, r, c+1):
    return False
  return matrix[r][c+1].node == matrix[r][c].node


def change_at(matrix, r, c):
  if not in_range(matrix, r, c):
    return False
  return matrix[r][c].kind != Cell.NO_CHANGE

Bool8Neighborhood = collections.namedtuple('Bool8Beighborhood',
                                           ['up_left', 'up', 'up_right', 'left', 'right', 'down_left', 'down', 'down_right'])


def render_cell_graphics(tag, kind, changes, inner):
  def etag(*args, **kwargs):
    with tag(*args, **kwargs):
      pass
  def visif(cond):
    if cond:
      return ""
    return "invisible"
  if kind != Cell.NO_CHANGE:
    inner()
    with tag('div', klass="cell"):
      etag('div', klass="fullquadrant up_left " + visif(changes.up_left))
      etag('div', klass="fullquadrant up_right " + visif(changes.up_right))
      etag('div', klass="fullquadrant down_left " + visif(changes.down_left))
      etag('div', klass="fullquadrant down_right " + visif(changes.down_right))

      etag('div', klass="top " + visif(changes.up))
      etag('div', klass="left " + visif(changes.left), style=("visibility:hidden;" if kind != Cell.CHANGE else ""))
      with tag('div', klass="inner", style=("visibility:hidden;" if kind != Cell.CHANGE else "")):
        etag('div', klass="dot")
      etag('div', klass="right " + visif(changes.right), style=("visibility:hidden;" if kind != Cell.CHANGE else ""))
      etag('div', klass="bottom " + visif(changes.down))
      etag('div', klass="quadrant up_left " + visif(changes.up_left))
      etag('div', klass="quadrant up_right " + visif(changes.up_right))
      etag('div', klass="quadrant down_left " + visif(changes.down_left))
      etag('div', klass="quadrant down_right " + visif(changes.down_right))


def open_fragmap_page(fragmap):
  is_brief = isinstance(fragmap, BriefFragmap)
  matrix = fragmap.generate_matrix()

  doc, tag, text = Doc().tagtext()

  def colorized_line(line):
    if line == '':
      return
    if line[0] == '-':
      with tag('pre', klass='codeline codeline_removed'):
        text(line)
    if line[0] == '+':
      with tag('pre', klass='codeline codeline_added'):
        text(line)

  def etag(*args, **kwargs):
    """
    Generate a tag with empty content
    """
    with tag(*args, **kwargs):
      pass



  def render_cell(cell, r, c):
    self_is_change = cell.kind == Cell.CHANGE
    change_up = change_at(matrix, r-1, c)
    change_down = change_at(matrix, r+1, c)
    change_left = change_at(matrix, r, c-1)
    change_right = change_at(matrix, r, c+1)
    equal_left = equal_left_column(matrix, r, c)
    equal_right = equal_right_column(matrix, r, c)
    change_neigh = Bool8Neighborhood(up_left = change_left and change_up and change_at(matrix, r-1, c-1),
                                     up = change_up,
                                     up_right = change_right and change_up and change_at(matrix, r-1, c+1),
                                     left = equal_left,
                                     right = equal_right,
                                     down_left = change_left and change_down and change_at(matrix, r+1, c-1),
                                     down = change_down,
                                     down_right = change_right and change_down and change_at(matrix, r+1, c+1),
                                     )



    with tag('td', onclick="javascript:show(this)"):
      def inner():
        with tag('div', klass='code'):
          if cell.node:
            text(str(cell.node))
            text(equal_left_column(matrix, r, c))
            text(equal_right_column(matrix, r, c))
            for line in cell.node._fragment._content:
              colorized_line(line)
      render_cell_graphics(tag, cell.kind, change_neigh, inner)


  def get_html():
    doc.asis('<!DOCTYPE html>')
    with tag('html'):
      with tag('head'):
        with tag('title'):
          text('Fragmap - ' + os.getcwd())
        with tag('style', type='text/css'):
          doc.asis(css())
      with tag('body'):
        render_cell_graphics(tag, Cell.CHANGE, Bool8Neighborhood(False, True, False, True, True, True, True, True), nop)
        with tag('table'):
          with tag('tr'):
            with tag('th'):
              text('Hash')
            with tag('th'):
              text('Message')
            with tag('th'):
              text(' ')
          for r in range(len(matrix)):
            cur_patch = fragmap.patches[r]._header
            commit_msg = cur_patch._message[0] # First row of message
            hash = cur_patch._hash
            with tag('tr'):
              with tag('td'):
                with tag('span', klass='commit_hash'):
                  text(hash[0:8])
              with tag('td', klass="message_td"):
                with tag('span', klass='commit_message'):
                  text(commit_msg)
              for c in range(len(matrix[r])):
                render_cell(matrix[r][c], r, c)
        with tag('div', id='code_window'):
          text('')
        with tag('script'):
          doc.asis(javascript())
    return doc.getvalue()



  with open('fragmap.html', 'w') as f:
    f.write(get_html())
    os.startfile(f.name)


def javascript():
  return \
    """
    prev_source = null;
    function show(source) {
      if (prev_source) {
        prev_source.id = "";
        prev_source.parentElement.id = "";
      }
      prev_source = source;
      source.id = "selected_cell";
      source.parentElement.id = "selected_row";
      document.getElementById('code_window').innerHTML = source.childNodes[0].innerHTML;
      console.log(source, source.childNodes[0].innerHTML);
    }
    """



def css():
  cellwidth=25
  scale=cellwidth/360.0
  def scale_number(m):
    return str(int(m.group(1)) * scale)
  return re.sub(r'{{(\d+)}}', scale_number, raw_css())

def raw_css():
  return \
    """
    body {
      background: black;
      color: #e5e5e5;
    }
    table {
      border-collapse: collapse;
    }
    tr:nth-child(even) {
      background-color: rgba(70, 70, 70, 0.4);
    }
    tr:nth-child(odd) {
      background-color: rgba(90, 90, 90, 0.4);
    }
    td {
      text-align: left;
      vertical-align: bottom;
      padding: 0;
    }
    .message_td {
      white-space: nowrap;
    }
    .commit_hash {
      font-family: monospace;
      margin-right: 10pt;
    }
    .commit_message {
      margin-right: 10pt;
    }
    .matrix_cell {
      font-family: monospace;
      width: 8pt;
    }
    .cell_change {
      background-color: white;
    }
    .cell_between_changes {
      background-color: red;
    }
    .matrix_cell#selected_cell {
      box-shadow: 0px 0px 3px 2px #6F67E0 inset;
    }
    tr#selected_row {
      background-color: rgba(160, 160, 160, 0.4);
    }
    .code {
      display: none;
    }
    #code_window {
      font-family: monospace;
    }
    .codeline {
      margin: 0 auto;
    }
    .codeline_added {
      color: green;
    }
    .codeline_removed {
      color: red;
    }
    .invisible, .invisible::before {
        background: inherit;
    }
    .cell {
        background: black;
        position: relative;
        width: {{360}}px;
        height: {{360}}px;
        float: left;
        z-index: -3;
    }
    .inner {
        margin: {{40}}px;
        background: #c0c0c0;
        border-radius: {{70}}px;
        margin: {{80}}px 0px;
        float: left;
        height: {{180}}px;
        width: {{180}}px;
        padding: {{10}}px;
    }
    .dot {
        background: #a00080;
        border-radius: {{60}}px; /* dot.border_radius = inner.border_radius - inner.padding */
        box-shadow: {{2}}px {{2}}px {{10}}px {{4}}px rgba(0,0,0,0.3) inset;
        display: block;
        width: 100%;
        height: 100%;
    }
    .left:not(.invisible), .right:not(.invisible) {
        background: #c0c0c0;
    }
    .left, .right {
        border-radius: {{20}}px;
        border-radius: 0;
        float: left;
        margin: {{80}}px 0px;
        height: {{200}}px;
        width: {{80}}px;
        z-index: -2;
        position: relative;
    }
    .left.invisible, .right.invisible {
       visibility: hidden;
    }
    .top:not(.invisible), .bottom:not(.invisible) {
        background: red;
    }
    .top, .bottom {
        display: block;
        position: absolute;
        width: {{60}}px;
        height: {{180}}px;
        left: {{150}}px; /* top.left = cell.width/2 - top.width/2  */
        z-index: -1;
    }
    .top {
        top: 0px;
    }
    .bottom {
        bottom: 0px;
    }
    .quadrant:not(.invisible)::before {
        background: tomato;
    }
    .quadrant:not(.invisible) {
        background: tomato;
    }
    .fullquadrant:not(.invisible) {
        background: tomato;
    }
    .fullquadrant {
        display:block;
        position: absolute;
        height: {{180}}px;
        width: {{180}}px;
        z-index: -2;
    }
    .quadrant {
        display: block;
        position: absolute;
        height: {{150}}px;
        width: {{150}}px;
        z-index: -1;
    }
    .quadrant:before {
        content: "";
        display: block;
        position: absolute;
        height: {{80}}px;
        width: {{80}}px;
    }
    .up_left {
        top: 0px;
        left: 0px;
    }
    .up_left:before {
        border-radius: 0 0 15% 0;
        bottom: -{{20}}px;
    }
    .up_right {
        top: 0px;
        right: 0px;
    }
    .up_right:before {
        border-radius: 0 0 0 15%;
        right: 0px;
        bottom: -{{20}}px;
    }
    .down_left {
        bottom: 0px;
        left: 0px;
    }
    .down_left:before {
        border-radius: 0 15% 0 0;
        top: -{{20}}px; /* bottom pos = before.height + after.height - left.height */
    }
    .down_right {
        bottom: 0px;
        right: 0px;
    }
    .down_right:before {
        border-radius: 15% 0 0 0;
        top: -{{20}}px; /* bottom pos = before.height + after.height - left.height */
        right: 0px;
    }
    """
