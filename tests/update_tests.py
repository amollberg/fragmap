#!/usr/bin/env python
# encoding: utf-8

from infrastructure import unbundle_development_test_repos, update_repos

import os

DIFF_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'diffs')

def main():
  print ("Test dir:", DIFF_DIR)
  unbundle_development_test_repos(DIFF_DIR, skip_existing=True)
  print("Updating repos")
  update_repos(DIFF_DIR)

if __name__ == '__main__':
  main()
