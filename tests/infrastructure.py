#!/usr/bin/env python
# encoding: utf-8

import native_git

import os
import pygit2
import shutil
import stat
from os.path import basename

def subdirs(dir_path):
  for e in os.walk(dir_path):
    dirpath, dirnames, filenames = e
    return [os.path.join(dir_path, name) for name in dirnames]

def files(dir_path):
  for e in os.walk(dir_path):
    dirpath, dirnames, filenames = e
    return [os.path.join(dir_path, name) for name in filenames]

def create_dir(dir_path):
  if not os.path.exists(dir_path):
    os.makedirs(dir_path)

def rmtree_readonly(*args, **kwargs):
  print "Removing", args[0]
  def on_readonly(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)
  shutil.rmtree(*args, onerror=on_readonly, **kwargs)

def create_bundles(test_dir):
  # for each subdir called "test_*"
  # run git bundle create test_*.bundle --all in test_dir
  test_subdirs = [subdir for subdir in subdirs(test_dir)
                  if basename(subdir).startswith('test_')]
  print test_subdirs
  for test_subdir in test_subdirs:
    native_git.bundle(test_subdir, os.path.abspath(test_subdir + '.bundle'))

def unbundle_execution_test_repos(test_dir):
  test_bundles = [filename for filename in files(test_dir)
                  if basename(filename).startswith('test_') and
                  filename.endswith('.bundle')]
  for bundle in test_bundles:
    test_name = basename(bundle.replace('.bundle', ''))
    dir_name = os.path.join(test_dir, 'build', test_name)
    native_git.clone(bundle, dir_name, '-n')

def unbundle_development_test_repos(test_dir, skip_existing=False):
  test_bundles = [filename for filename in files(test_dir)
                  if basename(filename).startswith('test_') and
                  filename.endswith('.bundle')]
  for bundle in test_bundles:
    test_name = basename(bundle.replace('.bundle', ''))
    dir_name = os.path.join(test_dir, "build", test_name)
    if not skip_existing or not os.path.exists(dir_name):
      native_git.clone(bundle, dir_name)

def remove_execution_test_repos(test_dir):
  test_subdirs = [subdir for subdir in subdirs(os.path.join(test_dir, "build"))
                  if basename(subdir).startswith('test_')]
  for subdir in test_subdirs:
    rmtree_readonly(subdir)

def update_repos(test_dir):
  create_dir(os.path.join(test_dir, "build"))
  create_bundles(test_dir)
  remove_execution_test_repos(test_dir)
  unbundle_execution_test_repos(test_dir)

def find_commit_with_message(repo_path, message):
  def all_commits(repo):
    branches = repo.references
    known_commit_hexes = set([])
    for branch in branches:
      tip_commit = repo[branch.target]
      for commit in repo.walk(tip_commit, pygit2.GIT_SORT_TOPOLOGICAL):
        if commit.hex in known_commit_hexes:
          break
        known_commit_hexes.add(commit.hex)
        yield commit
  repo = pygit2.Repository(repo_path)
  for commit in all_commits(repo):
    if commit.message == message:
      return commit.hex
  return None
