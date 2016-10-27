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

def get_diff(max_count_str):
  if not is_git_available():
    print "Error: git cannot be found. Has it been installed?"
    return None
  output = []
  try:
    print '... Retrieving uncommitted changes\r',
    output += get_output_lines([GIT, 'diff', '-U0', '--no-color'])
    print '... Finding revisions             \r',
    rev_list = get_output_lines([GIT, 'rev-list', '--reverse', '--max-count', max_count_str, 'HEAD'])
    if rev_list:
      print '... Retrieving fragments          \r',
      output += get_output_lines([GIT, 'show', '-U0', '--no-color'] + rev_list)
    return output
  except subprocess.CalledProcessError, e:
    if e.returncode == 129:
      print 'Error: Working directory is not a git repository.'
    elif e.output is not None:
      print 'fragmap: Unknown error while executing ', e.cmd, ", git exit code:", e.returncode
    return None

if __name__ == '__main__':
  def pr(s):
    print s
  map(pr, get_diff(get_rev_range_from_args()))
