#!/usr/bin/env python
# encoding: utf-8
from pygit2 import Commit, Diff


class CommitDiff(object):
  def __init__(self, pygit_commit: Commit, pygit_diff: Diff):
    self.header = pygit_commit
    self.filepatches = [patch for patch in pygit_diff]

  def __repr__(self):
    return "<CommitDiff: %s %s>" % (self.header, self.filepatches)
