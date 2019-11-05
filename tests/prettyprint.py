#!/usr/bin/env python

class Formatter(object):
  def __init__(self):
    self.types = {}
    self.htchar = '\t'
    self.lfchar = '\n'
    self.indent = 0
    self.set_formatter(object, self.__class__.format_object)
    self.set_formatter(dict, self.__class__.format_dict)
    self.set_formatter(list, self.__class__.format_list)
    self.set_formatter(tuple, self.__class__.format_tuple)
    self.set_formatter(set, self.__class__.format_set)

  def set_formatter(self, obj, callback):
    self.types[obj] = callback

  def __call__(self, value, **args):
    for key in args:
      setattr(self, key, args[key])
    formatter = self.types[type(value) if type(value) in self.types else object]
    return formatter(self, value, self.indent)

  def format_object(self, value, indent):
    return repr(value)

  def format_dict(self, value, indent):
    items = [
      self.lfchar + self.htchar * (indent + 1) + repr(key) + ': ' +
      (self.types[type(value[key]) if type(value[key]) in self.types else object])(self, value[key], indent + 1)
      for key in value
    ]
    return '{%s}' % (','.join(items) + self.lfchar + self.htchar * indent)

  def format_list(self, value, indent):
    items = [
      self.lfchar + self.htchar * (indent + 1) + (self.types[type(item) if type(item) in self.types else object])(self, item, indent + 1)
      for item in value
    ]
    return '[%s]' % (','.join(items) + self.lfchar + self.htchar * indent)

  def format_tuple(self, value, indent):
    items = [
      self.lfchar + self.htchar * (indent + 1) + (self.types[type(item) if type(item) in self.types else object])(self, item, indent + 1)
      for item in value
    ]
    return '(%s)' % (','.join(items) + self.lfchar + self.htchar * indent)

  def format_set(self, value, indent):
    items = [
      self.lfchar + self.htchar * (indent + 1) + (self.types[type(item) if type(item) in self.types else object])(self, item, indent + 1)
      for item in value
    ]
    return 'set([%s])' % (','.join(items) + self.lfchar + self.htchar * indent)
