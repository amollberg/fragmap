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
from typing import List


def lzip(*args):
  """
  zip(...) but returns list of lists instead of list of tuples
  """
  return [list(el) for el in zip(*args)]


def flatten(list_of_lists):
  """
  Flatten list of lists into a list
  """
  return [el for inner in list_of_lists for el in inner]


def up_to_and_including(l: List, matcher) -> List:
  """
  Cut the list after the first matching element.
  """
  def generate():
    for element in l:
      yield element
      if matcher(element):
        break
  return list(generate())
