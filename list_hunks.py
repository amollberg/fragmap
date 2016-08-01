#!/usr/bin/env python

import subprocess

GIT='git'

def get_output_lines(args):
  out_str = subprocess.check_output(args)
  return [s.rstrip() for s in out_str.splitlines(True)]

def get_diff(rev_range_str):
  output = []
  output += get_output_lines([GIT, 'diff', '-U0', '--no-color'])
  for rev in get_output_lines([GIT, 'rev-list', '--reverse', rev_range_str]):
    if rev != '':
      output += get_output_lines([GIT, 'show', '-U0', '--no-color', rev])
  return output

if __name__ == '__main__':
  def pr(s):
    print s
  map(pr, get_diff('HEAD~4..HEAD'))
