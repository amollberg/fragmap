#!/usr/bin/env python
# encoding: utf-8
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
