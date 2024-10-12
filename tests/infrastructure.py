#!/usr/bin/env python
# encoding: utf-8
# Copyright 2016-2021 Alexander Mollberg
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import shutil
import stat
from os.path import basename

import native_git
import pygit2

from fragmap.common_ui import first_line
from fragmap.load_commits import UNSTAGED_HEX, STAGED_HEX

try:
  # Ownership check may flag directories in network drive mounts
  # so disable it for tests
  pygit2.option(pygit2.enums.Option.SET_OWNER_VALIDATION, False)
except AttributeError:
  pass


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
  print("Removing", args[0])

  def on_readonly(action, name, exc):
    os.chmod(name, stat.S_IWRITE)
    os.remove(name)

  shutil.rmtree(*args, onerror=on_readonly, **kwargs)


def create_bundles(test_dir):
  # for each subdir called "test_*"
  # run git bundle create test_*.bundle --all in test_dir
  test_subdirs = [subdir for subdir in subdirs(test_dir)
                  if basename(subdir).startswith('test_')]
  print(test_subdirs)
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
    dir_name = os.path.join(test_dir, test_name)
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
    ref_names = [ref for ref in repo.references]
    known_commit_ids = set([])
    for ref_name in ref_names:
      tip_commit = repo.references[ref_name].target
      for commit in repo.walk(tip_commit, pygit2.GIT_SORT_TOPOLOGICAL):
        if commit.id in known_commit_ids:
          break
        known_commit_ids.add(commit.id)
        yield commit

  if message == 'STAGED':
    return STAGED_HEX
  if message == 'UNSTAGED':
    return UNSTAGED_HEX
  repo = pygit2.Repository(repo_path)
  for commit in all_commits(repo):
    if first_line(commit.message) == message:
      return str(commit.id)
  raise RuntimeError(
    "No commit with message '%s' in repo %s" % (message, repo_path))


def stage_all_changes(repo_path):
  repo = pygit2.Repository(repo_path)
  repo.index.add_all()
  repo.index.write()


def reset_hard(repo_path):
  repo = pygit2.Repository(repo_path)
  repo.reset(repo.head.target, pygit2.GIT_RESET_HARD)
