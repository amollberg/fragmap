#!/usr/bin/env python

# Hierarchy:
# AST
#  ._patches : Patch          .commitdiffs[] : CommitDiff (diff of one commit and its parent + metadata)
#   PatchHeader                 .header : Commit
#    _hash                        .hex
#   FilePatch                   .filepatches[] : Patch
#     FilePatchHeader             .delta : DiffDelta
#      _oldfile                     .old_file.path
#      _newfile                     .new_file.path
#     Fragment                    .hunks[] : DiffHunk
#      _content                     .lines
#      FragmentHeader
#       Range _oldrange
#        _start                     .old_start
#        _end                       .old_start + .old_lines
#       Range _newrange
#        _start                     .new_start
#        _end                       .new_start + .new_lines

import sys
import re
import pygit2
import json
import os

import fragmap.debug as debug
from fragmap.commitdiff import CommitDiff

def is_nullfile(fn):
  return fn == '/dev/null'

def nonnull_file(delta):
  if not is_nullfile(delta.old_file.path):
    return delta.old_file.path
  if not is_nullfile(delta.new_file.path):
    return delta.new_file.path
  # Both files are null files
  return None


class Range(object):
  _start = 0
  _end = 0

  def __init__(self, start, length):
    # Fix for inconvenient notation of empty lines
    # This eliminates the need for special cases in
    # some calculations.
    if length == 0:
      start += 1

    self._start = start
    self._end = start + length - 1

  def __repr__(self):
    return "<Range: %d to %d>" % (self._start, self._end,)

  def update_positions(self, start_delta, end_delta):
    self._start += start_delta
    self._end += end_delta

def oldrange(fragment):
  return Range(fragment.old_start, fragment.old_lines)

def newrange(fragment):
  return Range(fragment.new_start, fragment.new_lines)

def get_diff(repo, commit, find_similar=True):
  if isinstance(commit, pygit2.Commit):
    diff = repo.diff(commit.parents[0], commit, context_lines=0, interhunk_lines=0)
  else:
    diff = commit.get_diff(repo, context_lines=0, interhunk_lines=0)
  if find_similar:
    diff.find_similar()
  return diff

class FakeCommit(object):
  def __init__(self, hex):
    self.hex = hex
    self.message = ''
    # Add more fields here as required

class Unstaged(FakeCommit):
  def __init__(self):
    super(Unstaged, self).__init__('0000000000000000000000000000000000000000')
    self.message = ' (unstaged changes)'

  def get_diff(self, repo, **kwargs):
    return repo.diff(None, None, cached=False, **kwargs)

class Staged(FakeCommit):
  def __init__(self):
    super(Staged, self).__init__('0000000000000000000000000000000000000001')
    self.message = ' (staged changes)'

  def get_diff(self, repo, **kwargs):
    # This does NOT compare staged to HEAD
    # repo.diff(None, None, cached=True)
    return repo.index.diff_to_tree(repo.head.peel().tree, **kwargs)

class CommitSelection(object):
  def __init__(self, since_ref, until_ref, max_count, include_staged, include_unstaged):
    self.start = since_ref
    self.end = until_ref
    self.include_staged = include_staged
    self.include_unstaged = include_unstaged
    self.max_count = max_count

  def get_items(self, repo):
    walker = repo.walk(repo.head.target,
                       pygit2.GIT_SORT_TOPOLOGICAL | pygit2.GIT_SORT_REVERSE)
    if self.end:
      walker.push(repo.revparse_single(self.end).hex)
    if self.start:
      walker.hide(repo.revparse_single(self.start).hex)
    if not (self.start or self.end):
      walker.hide(repo.revparse_single('HEAD~' + str(self.max_count)).hex)
    # Collect all selected commits
    commits = [commit for commit in walker]
    if self.max_count:
      # Limit the number of commits
      commits = commits[0:(self.max_count + 1)]

    if self.include_staged:
      commits.append(Staged())
    if self.include_unstaged:
      commits.append(Unstaged())
    return commits

class ExplicitCommitSelection(object):
  def __init__(self, commit_hex_list):
    self.commit_hexes = commit_hex_list

  def get_items(self, repo):
    return [repo[hex] for hex in self.commit_hexes]

class CommitLoader(object):
  @staticmethod
  def load(repo_dir, commit_selection):
    repo = pygit2.Repository(pygit2.discover_repository(repo_dir))
    commits = commit_selection.get_items(repo)
    commitdiffs = [CommitDiff(commit, get_diff(repo, commit)) for commit in commits]
    return commitdiffs

class DictCoersionEncoder(json.JSONEncoder):
  def default(self, obj):
    try:
      return json.JSONEncoder.default(self, obj)
    except TypeError:
      return vars(obj)

def main():
  cl = CommitLoader()
  print CommitLoader.load(os.getcwd(), CommitSelection('HEAD~4', None, 4, True, True))

if __name__ == '__main__':
  debug.parse_args()
  main()
