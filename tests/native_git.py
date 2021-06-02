#!/usr/bin/env python
# encoding: utf-8
""" For interacting with git via the shell. Requires git to be in PATH """

import subprocess

DEFAULT_GIT_CONFIG_STRING = ["-c", "user.name='Foo Bar'", "-c",
                             "user.email='foo@example.com'"]
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
