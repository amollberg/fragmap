#!/usr/bin/env python
# encoding: utf-8

import argparse
import logging
import sys

_logging_categories = ["grid", "sorting", "grouping", "parser", "update",
                       "update_files", "console", "test", "matrix"]
# Fill out map of flags
_logging_enabled = {category: False for category in _logging_categories}
logging.basicConfig()
for cat in _logging_categories:
  l = logging.getLogger(cat)
  l.setLevel(logging.CRITICAL)


def is_logging(category):
  return _logging_enabled[category]


def _enable_logging(category):
  if category in _logging_categories:
    get(category).setLevel(logging.DEBUG)
    _logging_enabled[category] = True
  else:
    print("WARNING: Unknown logging category '{}'".format(category))


def get(category):
  return logging.getLogger(category)


def set_logging_categories(*categories):
  if categories:
    # Resolve 'all' into all logging categories
    if categories[0] == 'all':
      categories = _logging_categories
    # Enable all selected categories
    for cat in categories:
      if cat == 'all':
        continue
      _enable_logging(cat)


def parse_args(extendable=False):
  # Parse command line arguments
  p = argparse.ArgumentParser(add_help=not extendable)
  p.add_argument("--log", nargs="+", default=[],
                 choices=['all'] + _logging_categories,
                 metavar="CATEGORY",
                 help="Which categories of log messages to send to standard output: %(choices)s")
  args, unknown_args = p.parse_known_args()
  set_logging_categories(*args.log)
  # Remove the above known args from subsequent parsers e.g. unittest.
  sys.argv[1:] = unknown_args
  if extendable:
    return p
  return None
