#!/usr/bin/env python
# encoding: utf-8

from yattag import Doc
from generate_matrix import Cell, BriefFragmap, ConnectedFragmap, ConnectedCell, ConnectionStatus


import os
import re


def nop():
  pass


def render_cell_graphics(tag, connected_cell, inner):
  kind = connected_cell.base.kind
  changes = connected_cell.changes
  def etag(*args, **kwargs):
    with tag(*args, **kwargs):
      pass
  def hideempty(status):
    if status == ConnectionStatus.EMPTY:
      return "invisible"
    return ""
  def passinfill(status):
    if status == ConnectionStatus.INFILL:
      return "visibility:hidden"
    return ""

  if kind != Cell.NO_CHANGE:
    inner()
    with tag('div', klass="cell"):
      etag('div', klass="fullquadrant up_left " + hideempty(changes.up_left))
      etag('div', klass="fullquadrant up_right " + hideempty(changes.up_right))
      etag('div', klass="fullquadrant down_left " + hideempty(changes.down_left))
      etag('div', klass="fullquadrant down_right " + hideempty(changes.down_right))

      etag('div', klass="top " + hideempty(changes.up))
      etag('div', klass="left " + hideempty(changes.left), style=passinfill(changes.left))
      with tag('div', klass="inner", style=(passinfill(changes.center))):
        etag('div', klass="dot")
      etag('div', klass="right " + hideempty(changes.right), style=passinfill(changes.right))
      etag('div', klass="bottom " + hideempty(changes.down))
      etag('div', klass="quadrant up_left " + hideempty(changes.up_left))
      etag('div', klass="quadrant up_right " + hideempty(changes.up_right))
      etag('div', klass="quadrant down_left " + hideempty(changes.down_left))
      etag('div', klass="quadrant down_right " + hideempty(changes.down_right))


def open_fragmap_page(fragmap):
  is_brief = isinstance(fragmap, BriefFragmap)
  matrix = ConnectedFragmap(fragmap).generate_matrix()

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
    with tag('td', onclick="javascript:show(this)"):
      def inner():
        with tag('div', klass='code'):
          if cell.base.node:
            text(str(cell.base.node))
            for line in cell.base.node._fragment._content:
              colorized_line(line)
      render_cell_graphics(tag, cell, inner)


  def get_html():
    doc.asis('<!DOCTYPE html>')
    with tag('html'):
      with tag('head'):
        with tag('title'):
          text('Fragmap - ' + os.getcwd())
        with tag('style', type='text/css'):
          doc.asis(css())
      with tag('body'):
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
        background: #c0c0c0;
        border-radius: {{70}}px;
        height: {{180}}px;
        width: {{180}}px;
        padding: {{10}}px;
        position: absolute;
        left: {{80}}px;
        top: {{80}}px;
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
        height: {{200}}px;
        width: {{80}}px;
        z-index: -2;
        position: absolute;
        top: {{80}}px;
    }
    .right {
        right: 0px;
    }
    .left {
        left: 0px;
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
