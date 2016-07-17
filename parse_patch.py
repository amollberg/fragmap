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
    if lines[0][0:11] != 'diff --git ':
      return None, lines
    lines = lines[1:]
    while lines[0] != '' and lines[0][0:4] != '--- ':
      lines = lines[1:]
      
    if lines[0][0:4] != '--- ':
      return None, lines
    
    match = re.match('^--- (?:a/|b/)?(.*)$', lines[0])
    if match is None:
      return None, lines
    oldfile = match.group(1)
    
    match = re.match('^\+\+\+ (?:a/|b/)?(.*)$', lines[1])
    if match is not None:
      newfile = match.group(1)
    return FilePatchHeader(oldfile, newfile), lines[2:]

  
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

class PatchHeader():
  _hash = None

  def __init__(self, hash):
    self._hash = hash

  def __repr__(self):
    return "[PatchHeader: %s]" %(self._hash,)

  @staticmethod
  def parse(lines):
    print "PatchHeader?", lines[0]
    match = re.match("^([0-9a-f]{40})", lines[0][0:40])
    if match is not None:
      lines = lines[1:]

    match = re.match("^commit ([0-9a-f]{40})", lines[0])
    if match is None:
      return None, lines
    hash = match.group(1)

    if lines[1][0:8] != 'Author: ':
      print "'%s'!='Author: '" %(lines[1][0:8],)
      return None, lines
    if lines[2][0:6] != 'Date: ':
      print "##2"
      return None, lines
    lines = lines[3:]
    while lines[0] == '' or lines[0][0] == ' ':
      print "in PatchHeader:", lines[0]
      lines = lines[1:]
    return PatchHeader(hash), lines
        
class Patch():
  _header = None
  _filepatches = None

  def __init__(self, filepatches):
    self._filepatches = filepatches

  def __repr__(self):
    return "[Patch: %s]" % (self._filepatches,)

  def find_patch_by_old_file(self, old_file_name):
    for file_patch in self._filepatches:
      if file_patch._header._oldfile == old_file_name:
        return file_patch
    return None

  @staticmethod
  def parse(lines):
    print "Patch?", lines[0]
    header, lines = PatchHeader.parse(lines)
    print "PatchHeader: ", header
    if header is None:
      return None, lines
    filepatches = []
    while len(lines) > 0:
      filepatch, lines = FilePatch.parse(lines)
      print "FilePatch:", filepatch
      if filepatch is not None:
        filepatches += [filepatch]
      else:
        # No more parsable filepatches; return
        break
    return Patch(filepatches), lines
  
class AST():
  _patches = None
  def __init__(self, patches):
    self._patches = patches

  def __repr__(self):
    return "[AST: %s]" % (self._patches,)

  @staticmethod
  def parse(lines):
    patches = []
    while len(lines) > 0:
      patch, lines = Patch.parse(lines)
      print "Patch: ", patch
      if patch is not None:
        patches += [patch]
      else:
        # Remove a line and retry parsing
        lines = lines[1:]
        continue
    return AST(patches), lines
  
class PatchParser():
  _ast = None

  @staticmethod
  def parse(lines):
    ast, lines_after = AST.parse(lines)
    if len(lines_after) == len(lines):
      print "No lines parsed!"
    if len(lines_after) > 0:
      print "Unparsable content left at end of file."
    return ast

def main():
  pp = PatchParser()
  lines = [line.rstrip() for line in sys.stdin]
  print  pp.parse(lines)

if __name__ == '__main__':
  main()
