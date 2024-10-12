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
""" For interacting with git via the shell. Requires git to be in PATH """

import subprocess

DEFAULT_GIT_CONFIG_STRING = ["-c", "user.name='Foo Bar'", "-c",
                             "user.email='foo@example.com'",
                             "-c", "safe.directory=*"]
DEFAULT_GIT_ENV = {'GIT_COMMITTER_NAME': 'Foo Bar',
                   'GIT_COMMITTER_EMAIL': 'foo@example.com',
                   'GIT_CONFIG_NOSYSTEM': '1'}


def bundle(repo_path, bundle_abspath):
  print("Bundling", repo_path, "to", bundle_abspath)
  subprocess.check_call(['git'] + DEFAULT_GIT_CONFIG_STRING +
                        ['bundle', 'create', bundle_abspath, '--all'],
                        cwd=repo_path, env=DEFAULT_GIT_ENV)


def clone(url, repo_path, *clone_args):
  subprocess.check_call(['git'] + DEFAULT_GIT_CONFIG_STRING +
                        ['clone'] + DEFAULT_GIT_CONFIG_STRING +
                        list(clone_args) + ['--', url, repo_path])


def add_remote(repo_path, remote):
  subprocess.call(['git'] + DEFAULT_GIT_CONFIG_STRING +
                  ['remote', 'add', 'origin', remote])
  # In case origin already exists but has a different URL
  subprocess.check_call(['git'] + DEFAULT_GIT_CONFIG_STRING +
                        ['remote', 'set-url', 'origin', remote])
