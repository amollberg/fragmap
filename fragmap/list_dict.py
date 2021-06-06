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
from dataclasses import dataclass, field


@dataclass
class ListDict:
  """
  A dictionary of appendable lists
  """
  kv_map: dict = field(default_factory=lambda: {})

  def add(self, key, value):
    if key not in self.kv_map.keys():
      self.kv_map[key] = []
    self.kv_map[key].append(value)

  def items(self):
    for key in self.kv_map.keys():
      yield key, self.kv_map[key]


@dataclass
class StableListDict:
  """
  A dictionary of appendable lists that return the keys in the same
  order as they were inserted.
  """
  kv_map: dict = field(default_factory=lambda: {})
  keys: list = field(default_factory=lambda: [])

  def add(self, key, value):
    if key not in self.keys:
      self.keys.append(key)
      self.kv_map[key] = []
    self.kv_map[key].append(value)

  def items(self):
    for key in self.keys:
      yield key, self.kv_map[key]
