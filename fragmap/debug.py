#!/usr/bin/env python

import argparse
import sys
import logging

_logging_categories = ["curses", "grid", "sorting", "grouping", "parser", "update", "console", "test", "matrix"]
# Fill out map of flags
_enable_logging = {category: False for category in _logging_categories}
logging.basicConfig()
for cat in _logging_categories:
  l = logging.getLogger(cat)
  l.setLevel(logging.CRITICAL)


def is_logging(category):
  return _enable_logging[category]

def enable_logging(category):
  if category in _logging_categories:
    get(category).setLevel(logging.DEBUG)
    _enable_logging[category] = True
  else:
    print "WARNING: Unknown logging category '%s'" %(category,)

def get(category):
  return logging.getLogger(category)


def parse_args(extendable=False):
  # Parse command line arguments
  p = argparse.ArgumentParser(add_help = not extendable)
  p.add_argument("--log", nargs="+",
                 choices=['all'] + _logging_categories,
                 metavar="CATEGORY",
                 help="Which categories of log messages to send to standard output: %(choices)s")
  args, unknown_args = p.parse_known_args()
  if args.log:
    # Resolve 'all' into all logging categories
    if args.log[0] == 'all':
      args.log = _logging_categories
    # Enable all selected categories
    for cat in args.log:
      if cat == 'all':
        continue
      enable_logging(cat)
  # Remove the above known args from subsequent parsers e.g. unittest.
  sys.argv[1:] = unknown_args
  if extendable:
    return p
  return None
