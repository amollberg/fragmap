#!/usr/bin/env python
# encoding: utf-8

class CommitDiff(object):
  def __init__(self, pygit_commit, pygit_diff):
    self.header = pygit_commit
    self.filepatches = [patch for patch in pygit_diff]

  def __repr__(self):
    return "<CommitDiff: %s %s>" %(self.header, self.filepatches)
