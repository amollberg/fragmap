#!/usr/bin/env python
# encoding: utf-8

from yattag import Doc
from generate_matrix import Cell, BriefFragmap, ConnectedFragmap, ConnectedCell, ConnectionStatus
from http import start_server

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
  def activitymarker(status):
    if status == ConnectionStatus.CONNECTION:
      return "active"
    return ""

  if kind != Cell.NO_CHANGE:
    inner()
    with tag('div', klass="cell " + activitymarker(changes.center)):
      etag('div', klass="top " + hideempty(changes.up))
      etag('div', klass="left " + hideempty(changes.left), style=passinfill(changes.left))
      with tag('div', klass="inner", style=(passinfill(changes.center))):
        etag('div', klass="dot")
      etag('div', klass="right " + hideempty(changes.right), style=passinfill(changes.right))
      etag('div', klass="bottom " + hideempty(changes.down))


def make_fragmap_page(fragmap):
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
    def inner():
      with tag('div', klass='code'):
        if cell.base.node:
          text(str(cell.base.node))
          for line in cell.base.node._fragment._content:
            colorized_line(line)
    render_cell_graphics(tag, cell, inner)

  def get_first_filename(matrix, c):
    for r in xrange(len(matrix)):
      cell = matrix[r][c]
      if cell.base.kind != Cell.NO_CHANGE:
        return cell.base.node._filename
    return None

  def generate_first_filename_spans(matrix):
    filenames = []
    if len(matrix) == 0:
      return filenames
    for c in xrange(len(matrix[0])):
      fn = get_first_filename(matrix, c)
      if len(filenames) == 0:
        filenames.append({'filename': fn, 'span': 1, 'start': c})
        continue
      if filenames[-1]['filename'] == fn or fn is None:
        filenames[-1]['span'] += 1
        continue
      if fn is not None:
        filenames.append({'filename': fn, 'span': 1, 'start': c})
    return filenames

  def render_filename_start_row(filenames):
    for fn in filenames:
      with tag('th', klass='filename_start', colspan=fn['span'], style='vertical-align: top; overflow: hidden'):
        with tag('div', style="position: relative; width: inherit"):
          with tag('div', style="overflow: hidden; position: absolute; right: 10px; width: 10000px; text-align: right"):
            if fn['filename'] is not None:
              text(fn['filename'])

  def filename_header_td_class(filenames, c):
    for fn in filenames:
      if c == fn['start']:
        return 'filename_start '
    return ''


  def get_html():
    doc.asis('<!DOCTYPE html>')
    with tag('html'):
      with tag('head'):
        with tag('title'):
          text('Fragmap - ' + os.getcwd())
        with tag('style', type='text/css'):
          doc.asis(css())
      with tag('body'):
        with tag('div', id='map_window'):
          with tag('table'):
            start_filenames = generate_first_filename_spans(matrix)
            with tag('tr'):
              with tag('th', style="font-weight: bold"):
                text('Hash')
              with tag('th', style="font-weight: bold"):
                text('Message')
              if len(matrix) > 0:
                render_filename_start_row(start_filenames)
            for r in range(len(matrix)):
              cur_patch = fragmap.patches[r]._header
              commit_msg = cur_patch._message[0] # First row of message
              hash = cur_patch._hash
              with tag('tr'):
                with tag('th'):
                  with tag('span', klass='commit_hash'):
                    text(hash[0:8])
                with tag('th', klass="message_cell"):
                  with tag('span', klass='commit_message'):
                    text(commit_msg)
                for c in range(len(matrix[r])):
                  with tag('td', klass=filename_header_td_class(start_filenames, c),
                           onclick="javascript:show(this)"):
                    render_cell(matrix[r][c], r, c)
        with tag('div', id='code_window'):
          text('')
        with tag('script'):
          doc.asis(javascript())
    return doc.getvalue()

  return get_html()

def start_fragmap_server(fragmap_callback):
  def html_callback():
    return make_fragmap_page(fragmap_callback())
  server = start_server(html_callback)
  address = 'http://%s:%s' % server.server_address
  os.startfile(address)
  print 'Serving fragmap at %s' %(address,)
  print "Press 'r' to re-launch the page"
  print 'Press any other key to terminate'
  from getch.getch import getch
  while(ord(getch()) == ord('r')):
      os.startfile(address)
  server.shutdown()


def open_fragmap_page(fragmap, live):
  with open('fragmap.html', 'w') as f:
    f.write(make_fragmap_page(fragmap))
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
    }
    function within(lower, x, upper) {
      return lower <= x && x <= upper;
    }
    function inside(table, row, col) {
      var nRows = table.getElementsByTagName('tr').length;
      var nCols = table.getElementsByTagName('tr')[1].getElementsByTagName('td').length || 0;
      // Note: row minimum is 1 since the first row is the header
      return within(1, row, nRows - 1) && within(0, col, nCols - 1);
    }
    function indexByTagName(haystack, tagName, needleChild) {
      var children = haystack.getElementsByTagName(tagName);
      for (var i = 0;; i++) {
        if (children[i] == needleChild) {
          return i;
        }
      }
      return -1;
    }
    function neighbor(source, rowOffset, colOffset) {
      var row = source.parentElement;
      var colNumber = indexByTagName(row, 'td', source);
      var table = row.parentElement;
      var rowNumber = indexByTagName(table, 'tr', row);
      if (!inside(table, rowNumber + rowOffset, colNumber + colOffset)) {
        return null;
      }
      return table
        .getElementsByTagName('tr')[rowNumber + rowOffset]
        .getElementsByTagName('td')[colNumber + colOffset];
    }
    function neighborWhere(source, rowDirection, colDirection, pred) {
      var cell = source;
      var i = 0;
      for (cell = neighbor(cell, rowDirection, colDirection);
           cell !== null && !pred(cell);
           i++, cell = neighbor(cell, rowDirection, colDirection)) {
        // Empty
      }
      return [cell, i];
    }
    function active_cell(cell) {
      return cell !== null && cell.getElementsByClassName('active').length > 0;
    }
    function handleKeyDown(e) {
      e = e || window.event;
      var rowOffset = 0;
      var colOffset = 0;
      if (e.key == 'ArrowUp') {
        // up arrow
        rowOffset = -1;
      }
      else if (e.key == 'ArrowDown') {
        // down arrow
        rowOffset = 1;
      }
      else if (e.key == 'ArrowLeft') {
        // left arrow
        colOffset = -1;
      }
      else if (e.key == 'ArrowRight') {
        // right arrow
        colOffset = 1;
      }
      else {
        return true;
      }
      var divertable = !e.ctrlKey;
      var source = prev_source;
      var next = source;
      if (!divertable) {
        [next, _] = neighborWhere(source, rowOffset, colOffset, active_cell);
      }
      else {
        neigh = next;
        while(neigh !== null) {
          // Take one step in the desired direction
          neigh = neighbor(neigh, rowOffset, colOffset);
          if (neigh === null) {
            break;
          }
          if (active_cell(neigh)) {
            next = neigh;
            break;
          }
          // Look to both sides
          [nextPos, distPos] = neighborWhere(neigh, colOffset, rowOffset, active_cell);
          [nextNeg, distNeg] = neighborWhere(neigh, -colOffset, -rowOffset, active_cell);
          // Pick whichever was closest and valid
          if (nextPos !== null) {
            next = nextPos;
            if (nextNeg !== null) {
              next = distNeg < distPos ? nextNeg : nextPos;
            }
          }
          else {
            next = nextNeg;
          }
          if (next !== null) {
            break;
          }
        }
      }
      if (next === null) {
        next = source;
      }
      show(next);
      return false;
    }
    document.body.onkeydown = handleKeyDown;
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
    tr:nth-child(even), tr:nth-child(even) th:nth-child(1), tr:nth-child(even) th:nth-child(2) {
      background-color: rgba(28, 28, 28);
    }
    tr:nth-child(odd), tr:nth-child(odd) th:nth-child(1), tr:nth-child(odd) th:nth-child(2){
      background-color: rgba(36, 36, 36);
    }
    tr th:nth-child(1), tr th:nth-child(2) {
      z-index: 2;
    }
    th {
      font-family: sans-serif;
      font-weight: normal;
    }
    td, .message_cell {
      text-align: left;
      vertical-align: bottom;
      padding: 0;
    }
    .message_cell {
      box-shadow: 10px 0px 10px 0px rgba(0,0,0,0.5);
    }
    th:first-child, th:nth-child(2) {
      position: -webkit-sticky;
      position: sticky;
      left: 0;
    }
    .message_cell {
      white-space: nowrap;
      font-family: sans-serif;
    }
    .commit_hash {
      font-family: monospace;
      margin-right: 10pt;
    }
    .commit_message {
      margin-right: 10pt;
    }
    .cell_change {
      background-color: white;
    }
    .cell_between_changes {
      background-color: red;
    }
    #selected_cell .dot {
      background: white;
      box-shadow: 0px 0px 5px 5px;
    }
    tr#selected_row {
      background-color: rgba(160, 160, 160, 0.4);
    }
    .code {
      display: none;
    }
    #map_window {
      overflow-x: auto;
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
    th.filename_start, td.filename_start {
      border-left: 4px solid black;
    }
    .invisible, .invisible::before {
        background: inherit;
    }
    .cell {
        position: relative;
        width: {{360}}px;
        height: {{360}}px;
        float: left;
        z-index: 1;
    }
    .inner {
        border-radius: {{20}}px;
        height: {{140}}px;
        width: {{140}}px;
        padding: {{30}}px;
        position: absolute;
        left: {{80}}px;
        top: {{80}}px;
    }
    .dot {
        background: #0d76c2;
        border-radius: {{60}}px; /* dot.border_radius = inner.border_radius - inner.padding */
        box-shadow: {{15}}px {{15}}px {{3}}px {{3}}px rgba(0,0,0,0.8) inset;
        display: block;
        position: relative;
        z-index: 2;
        width: 100%;
        height: 100%;
    }
    .left:not(.invisible), .right:not(.invisible), .inner {
        background: #35aaff;
    }
    .left, .right {
        border-radius: 0;
        height: {{200}}px;
        width: {{100}}px;
        z-index: 1;
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
        background: #642bff;
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
    """
