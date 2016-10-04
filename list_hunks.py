#!/usr/bin/env python

import subprocess
import argparse

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

def get_rev_range_from_args():
  p = argparse.ArgumentParser(description='')
  p.add_argument('-n', metavar='NUMBER_OF_REVS', action='store')
  args = p.parse_known_args()[0]
  n_revs = 2
  try:
    if args.n:
      n_revs = int(args.n)
  except ValueError:
    return None
  return 'HEAD~%d..HEAD' %(n_revs,)

if __name__ == '__main__':
  def pr(s):
    print s
  map(pr, get_diff(get_rev_range_from_args()))
