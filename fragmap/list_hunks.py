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

def _assemble_revlist_command(range_=None, max_count=None, start=None):
  args = [GIT, 'rev-list', '--reverse']
  rev_spec = 'HEAD'
  if range_ is not None:
    rev_spec = range_
  elif start is not None:
    rev_spec = start + '..HEAD'
  if max_count is not None:
    args += ['--max-count', max_count]
  args += [rev_spec]
  return args

def get_rev_list(**kwargs):
  return get_output_lines(_assemble_revlist_command(**kwargs))

def get_diff(staged, unstaged, **kwargs):
  if not is_git_available():
    print "Error: git cannot be found. Has it been installed?"
    return None
  output = []
  try:
    if unstaged:
      print '... Retrieving uncommitted changes\r',
      output += get_output_lines([GIT, 'diff', '-U0', '--no-color', '--raw'])
    if staged:
      print '... Retrieving staged changes     \r',
      output += get_output_lines([GIT, 'diff', '-U0', '--no-color', '--raw', '--staged'])
    print '... Finding commits               \r',
    rev_list = get_rev_list(**kwargs)
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
  finally:
    print '                                  \r',
