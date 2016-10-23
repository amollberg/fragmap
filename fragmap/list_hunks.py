#!/usr/bin/env python

import subprocess
import argparse
import distutils.spawn
import os

GIT='git'

# For suppressing subprocess output
NULLFILE = open(os.devnull, 'w')

def is_git_available():
  return (distutils.spawn.find_executable(GIT) is not None)

def get_output_lines(args):
  out_str = subprocess.check_output(args, stderr=NULLFILE)
  return [s.rstrip() for s in out_str.splitlines(True)]

def get_diff(rev_range_str):
  if not is_git_available():
    print "Error: git cannot be found. Has it been installed?"
    return None
  output = []
  try:
    output += get_output_lines([GIT, 'diff', '-U0', '--no-color'])
    for rev in get_output_lines([GIT, 'rev-list', '--reverse', rev_range_str]):
      if rev != '':
        output += get_output_lines([GIT, 'show', '-U0', '--no-color', rev])
    return output
  except subprocess.CalledProcessError, e:
    if e.returncode == 129:
      print 'Error: Working directory is not a git repository.'
    elif e.output is not None:
      print 'fragmap: Unknown error while executing ', e.cmd, ", git exit code:", e.returncode
    return None

def get_rev_range_str(n_revs):
  try:
    if n_revs:
      n_revs = int(n_revs)
    else:
      n_revs = 2
  except ValueError:
    return None
  return 'HEAD~%d..HEAD' %(n_revs,)

if __name__ == '__main__':
  def pr(s):
    print s
  map(pr, get_diff(get_rev_range_from_args()))
