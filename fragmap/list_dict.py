#!/usr/bin/env python
# encoding: utf-8

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
