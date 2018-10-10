#!/usr/bin/env python
# encoding: utf-8

from yattag import Doc
from generate_matrix import Cell, BriefFragmap


import os


def open_fragmap_page(fragmap):
  is_brief = isinstance(fragmap, BriefFragmap)
  matrix = fragmap.generate_matrix()

  def colorized_line(line):
    if line == '':
      return
    if line[0] == '-':
      with tag('pre', klass='codeline codeline_removed'):
        text(line)
    if line[0] == '+':
      with tag('pre', klass='codeline codeline_added'):
        text(line)

  def render_cell(cell):
    classes = ['matrix_cell']
    if cell.kind == Cell.CHANGE:
      classes.append('cell_change')
    elif cell.kind == Cell.BETWEEN_CHANGES:
      classes.append('cell_between_changes')
    elif cell.kind == Cell.NO_CHANGE:
      classes.append('cell_no_change')
    with tag('td', klass=' '.join(classes), onclick="javascript:show(this)"):
      with tag('div', klass='code'):
        if cell.node:
          for line in cell.node._fragment._content:
            colorized_line(line)

  doc, tag, text = Doc().tagtext()
  def get_html():
    doc.asis('<!DOCTYPE html>')
    with tag('html'):
      with tag('head'):
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
              with tag('td'):
                with tag('span', klass='commit_message'):
                  text(commit_msg)
              for c in range(len(matrix[r])):
                render_cell(matrix[r][c])
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
      }
      prev_source = source;
      source.id = "selected_cell";
      document.getElementById('code_window').innerHTML = source.childNodes[0].innerHTML;
      console.log(source, source.childNodes[0].innerHTML);
    }
    """

def css():
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
      background-color: rgba(120, 120, 120, 0.4);
    }
    td {
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
    .matrix_cell > .code {
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
    """
