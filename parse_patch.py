#!/usr/bin/env python

# Read patch from stdin, write list of files and hunks to stdout

# AST -> Patch

import sys
import re

class Range():
  _start = 0
  _end = 0

  def __init__(self, start, length):
    self._start = start
    self._end = start + length

  def __repr__(self):
    return "[Range: %d to %d]" % (self._start, self._end,)

  def update_positions(self, start_delta, end_delta):
    self._start += start_delta
    self._end += end_delta


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
                              Range(int(match.group(3)), newlength)), lines[1:]
    print "Not fragment header"
    return None, lines
    
    
class Fragment():
  _header = None
  def __init__(self, header):
    self._header = header

  def __repr__(self):
    return "[Fragment: %s]" % (self._header,)

  def update_positions(self, start_delta, length_delta):
    self._header._newrange.update_positions(start_delta, length_delta)
    self._header._oldrange.update_positions(start_delta, length_delta)

  @staticmethod
  def parse(lines):
    print "Fragment? ", lines[0]
    header, lines = FragmentHeader.parse(lines)
    #print i
    i = 0
    if header is not None:
      for line in lines:
        #print "line: '%s', length: %d" % (line, len(line))
        if len(line) == 0 or line[0] in {' ', '+', '-', '\\'}:
          #print "in fragment '%s'" % line, i
          i += 1
        else:
          #print "not in fragment: '%s'" % line, i
          break
      return Fragment(header), lines[i:]
    print "Not fragment"
    return None, lines

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
        return FilePatchHeader(oldfile, newfile), lines[2:]
    return None, lines

  
class FilePatch():
  _fragments = None
  _header = None
  
  def __init__(self, header, fragments):
    self._header = header
    self._fragments = fragments

  def __repr__(self):
    return "[FilePatch: %s, %s]" % (self._header, self._fragments,)

  @staticmethod
  def parse(lines):
    print "FilePatch? ", lines[0]
    header, lines = FilePatchHeader.parse(lines)
    if header is not None:
      fragments = []
      while len(lines) > 0:
        #print i,j, lines
        fragment, lines = Fragment.parse(lines)
        #print "Fragment: ", fragment
        # Consume lines
        #print len(lines)
        #print "After:",len(lines)
        if fragment is None:
          # No more fragments; stop
          break
        fragments += [fragment]
        #print "Fragments:", fragments
      p = FilePatch(header, fragments), lines
      #print "Returned patch:", p
      return p
    else:
      return None, lines

  
class AST():
  _filePatches = None
  def __init__(self, filePatches):
    self._filePatches = filePatches

  def __repr__(self):
    return "[AST: %s]" % (self._filePatches,)

  def find_patch_by_old_file(self, old_file_name):
    for file_patch in self._filePatches:
      if file_patch._header._oldfile == old_file_name:
        return file_patch
    return None

  @staticmethod
  def parse(lines):
    filePatches = []
    while len(lines) > 0:
      filePatch, lines = FilePatch.parse(lines)
      print "Filepatch: ", filePatch
      if filePatch is not None:
        filePatches += [filePatch]
      else:
        # Remove a line and retry parsing
        lines = lines[1:]
        continue
    return AST(filePatches), lines
  
class PatchParser():
  _ast = None

  @staticmethod
  def parse(lines):
    ast, lines_after = AST.parse(lines)
    if len(lines_after) == len(lines):
      print "No lines parsed!"
    if len(lines_after) > 0:
      print "Unparsable content left at end of file."
    return [ast]

def main():
  pp = PatchParser()
  lines = [line.rstrip() for line in sys.stdin]
  print  pp.parse(lines)

if __name__ == '__main__':
  main()
