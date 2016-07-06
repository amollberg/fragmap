#!/usr/bin/env python

# Read patch from stdin, write list of files and hunks to stdout

# AST -> Patch

import sys
import re

class Range():
  _start = 0
  _length = 0

  def __init__(self, start, length):
    self._start = start
    self._length = length

  def __repr__(self):
    return "[Range: %d, %d]" % (self._start, self._length,)

class FragmentHeader():
  _oldrange = None
  _newrange = None
  def __init__(self, oldrange, newrange):
    self._oldrange = oldrange
    self._newrange = newrange

  def __repr__(self):
    return "[FragmentHeader: %s, %s]" % (self._oldrange, self._newrange,)

  @staticmethod
  def parse(lines):
    print "FragmentHeader? ", lines[0]
    if lines[0][0:4] == '@@ -':
      match = re.match('^@@ -(\d+)(?:,(\d+)) \+(\d+)(?:,(\d+)) @@', lines[0])
      if match is not None:
        oldlength = 1
        if match.group(2):
          oldlength = int(match.group(2))
        newlength = 1
        if match.group(4):
          newlength = int(match.group(4))
        return FragmentHeader(Range(int(match.group(1)), oldlength),
                              Range(int(match.group(3)), newlength)), 1
    print "Not fragment header"
    return None, 0
    
    
class Fragment():
  _header = None
  def __init__(self, header):
    self._header = header

  def __repr__(self):
    return "[Fragment: %s]" % (self._header,)

  @staticmethod
  def parse(lines):
    print "Fragment? ", lines[0]
    header, i = FragmentHeader.parse(lines)
    # Consume lines according to FragmentHeader
    #print "Header:", header
    lines = lines[i:]
    #print i
    if header is not None:
      for line in lines:
        #print "line: '%s', length: %d" % (line, len(line))
        if len(line) == 0 or line[0] in {' ', '+', '-', '\\'}:
          #print "in fragment '%s'" % line, i
          i += 1
        else:
          #print "not in fragment: '%s'" % line, i
          break
      return Fragment(header), i
    print "Not fragment"
    return None, 0

class FilePatchHeader():
  _oldfile = None
  _newfile = None
  def __init__(self, oldfile, newfile):
    self._oldfile = oldfile
    self._newfile = newfile

  def __repr__(self):
    return "[FilePatchHeader: %s -> %s]" % (self._oldfile, self._newfile,)

  @staticmethod
  def parse(lines):
    print "FilePatchHeader? ", lines[0]
    if lines[0][0:4] == '--- ':
      match = re.match('^--- (?:a/|b/)?(.*)$', lines[0])
      if match is not None:
        oldfile = match.group(1)
        match = re.match('^\+\+\+ (?:a/|b/)?(.*)$', lines[1])
        if match is not None:
          newfile = match.group(1)
          return FilePatchHeader(oldfile, newfile), 2
    return None, 0

  
class FilePatch():
  _fragments = None
  _header = None
  
  def __init__(self, header, fragments):
    self._header = header
    self._fragments = fragments

  def __repr__(self):
    return "[FilePatch: %s]" % (self._fragments,)

  @staticmethod
  def parse(lines):
    print "FilePatch? ", lines[0]
    i = 0
    header, j = FilePatchHeader.parse(lines)
    # Consume lines
    lines = lines[j:]
    i += j
    if header is not None:
      fragments = []
      while len(lines) > 0:
        #print i,j, lines
        fragment, j = Fragment.parse(lines)
        print "Fragment: ", fragment, j
        # Consume lines
        #print len(lines)
        lines = lines[j:]
        #print "After:",len(lines)
        i += j
        if fragment is None:
          # No more fragments; return
          return FilePatch(header, fragments), i
        fragments += [fragment]
    return None, 0

  
class AST():
  _filePatches = None
  def __init__(self, filePatches):
    self._filePatches = filePatches

  def __repr__(self):
    return "[AST: %s]" % (self._filePatches,)

  @staticmethod
  def parse(lines):
    i = 0
    filePatches = []
    while len(lines) > 0:
      filePatch, lines_consumed = FilePatch.parse(lines)
      print "Filepatch: ", filePatch
      if lines_consumed > 0:
        # Consume lines
        lines = lines[lines_consumed:]
        i += lines_consumed
        if filePatch is None:
          # No more file patches; return
          return AST(filePatches), i
        filePatches += [filePatch]
      else:
        # Remove a line and retry parsing
        lines = lines[1:]
        i += 1
        continue
    return None, 0
  
class PatchParser():
  _ast = None

  @staticmethod
  def parse(lines):
    ast, lines_consumed = AST.parse(lines)
    if lines_consumed == 0:
      print "No lines consumed!"
    if lines_consumed < len(lines):
      print "Unparsable content left at end of file."
    return ast

def main():
  pp = PatchParser()
  lines = [line.rstrip() for line in sys.stdin]
  print  pp.parse(lines)

if __name__ == '__main__':
  main()
