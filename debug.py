#!/usr/bin/env python

import argparse
import sys

curses = 0
grid = 1
sorting = 2
grouping = 3
parser = 4
update = 5
console = 6
test = 7
matrix = 8
# Fill out map of flags. The keys must correpsond to the constants above!
_enable_logging = {category: False for category in range(0,9)}

def is_logging(category):
  return _enable_logging[category]

def enable_logging(category_list):
  for category in category_list:
    _enable_logging[category] = True

def log(category, *args):
  if _enable_logging[category]:
    for arg in args:
      print arg,


def parse_args():
  # Parse command line arguments
  p = argparse.ArgumentParser(description="")
  p.add_argument("--log", nargs="+",
                 choices=["all", "curses", "grid", "sorting", "grouping", "parser", "update", "console", "test", "matrix"],
                 help="Which categories of log messages to send to standard output.")
  args = p.parse_known_args()
  if args[0].log:
    # Translate textual arguments to numeric constants to be passed to enable_logging
    category_constants = []
    for cat in args[0].log:
      if cat == "all" or cat == "curses":
        category_constants += [curses]
      if cat == "all" or cat == "grid":
        category_constants += [grid]
      if cat == "all" or cat == "sorting":
        category_constants += [sorting]
      if cat == "all" or cat == "grouping":
        category_constants += [grouping]
      if cat == "all" or cat == "parser":
        category_constants += [parser]
      if cat == "all" or cat == "update":
        category_constants += [update]
      if cat == "all" or cat == "console":
        category_constants += [console]
      if cat == "all" or cat == "test":
        category_constants += [test]
      if cat == "all" or cat == "matrix":
        category_constants += [matrix]
    enable_logging(category_constants)
  # Remove the above known args from subsequent parsers e.g. unittest.
  sys.argv[1:] = args[1]
