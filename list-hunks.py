#!/usr/bin/env python

import subprocess

GIT='git'

def get_diff(rev_range_str):
  output = []

  p = subprocess.Popen([GIT, 'diff', '-U0', '--no-color'], stdout=subprocess.PIPE)
  output_unstaged, _ = p.communicate()

  output += [s.rstrip() for s in output_unstaged.splitlines(True)]

  p = subprocess.Popen([GIT, 'rev-list', '--reverse', rev_range_str], stdout=subprocess.PIPE)
  output_rev_list, _ = p.communicate()
  for rev in output_rev_list.splitlines():
    rev = rev.rstrip()
    if rev != '':
      p = subprocess.Popen([GIT, 'show', '-U0', '--no-color', rev], stdout=subprocess.PIPE)
      output_rev, _ = p.communicate()
      output += [s.rstrip() for s in output_rev.splitlines()]
  return output

if __name__ == '__main__':
  def pr(s):
    print s
  map(pr, get_diff('HEAD~4..HEAD'))
