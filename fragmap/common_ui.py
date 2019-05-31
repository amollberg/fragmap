#!/usr/bin/env python
# encoding: utf-8

def first_line(string_with_newlines):
  return string_with_newlines.split('\n', 1)[0]
assert(first_line('abcd\ne') == 'abcd')
assert(first_line('ab') == 'ab')
assert(first_line('') == '')
