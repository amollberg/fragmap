#!/usr/bin/env python

# Read patch from stdin, write list of files and hunks to stdout

# AST -> Patch

# Hierarchy:
# AST
#  Patch
#   PatchHeader
#    _hash
#   FilePatch
#     FilePatchHeader
#      _oldfile
#      _newfile
#     Fragment
#      FragmentHeader
#       Range _oldrange
#        _start
#        _end
#       Range _newrange
#        _start
#        _end

import sys
import re
import debug


def is_nullfile(fn):
  return fn == '/dev/null'


def nonnull_file(file_patch_header):
  if not is_nullfile(file_patch_header._oldfile):
    return file_patch_header._oldfile
  if not is_nullfile(file_patch_header._newfile):
    return file_patch_header._newfile
  # Both files are null files
  return None


class Range():
  _start = 0
  _end = 0

  def __init__(self, start, length):
    # Fix for inconvenient notation of empty lines
    # This eliminates the need for special cases in
    # some calculations.
    if length == 0:
      start += 1

    self._start = start
    self._end = start + length - 1

  def __repr__(self):
    return "<Range: %d to %d>" % (self._start, self._end,)

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
    return "<FragmentHeader: %s, %s>" % (self._oldrange, self._newrange,)

  @staticmethod
  def parse(lines):
    debug.log(debug.parser, "FragmentHeader? ", lines[0])
    if lines[0][0:4] == '@@ -':
      match = re.match('^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', lines[0])
      if match is not None:
        oldlength = 1
        if match.group(2):
          oldlength = int(match.group(2))
        newlength = 1
        if match.group(4):
          newlength = int(match.group(4))
        return FragmentHeader(Range(int(match.group(1)), oldlength),
                              Range(int(match.group(3)), newlength)), lines[1:]
    debug.log(debug.parser, "Not fragment header")
    return None, lines


class Fragment():
  _header = None
  _content = None
  def __init__(self, header, content=''):
    self._header = header
    self._content = content

  def __repr__(self):
    return "\n   <Fragment: %s %s>" % (self._header, self._content)

  def update_positions(self, start_delta, length_delta):
    self._header._newrange.update_positions(start_delta, length_delta)
    self._header._oldrange.update_positions(start_delta, length_delta)

  @staticmethod
  def parse(lines):
    debug.log(debug.parser, "Fragment? ", lines[0])
    header, lines = FragmentHeader.parse(lines)
    i = 0
    if header is not None:
      content = []
      for line in lines:
        if len(line) == 0 or line[0] in {' ', '+', '-', '\\'}:
          content += [line]
          i += 1
        else:
          break
      return Fragment(header, content), lines[i:]
    debug.log(debug.parser, "Not fragment")
    return None, lines

class FilePatchHeader():
  _oldfile = None
  _newfile = None
  def __init__(self, oldfile, newfile):
    # A fix to avoid special cases for null files
    # TODO: If file creation is important, this needs
    # to be signaled in another way, like _iscreation.
    if is_nullfile(oldfile):
      oldfile = newfile
    elif is_nullfile(newfile):
      newfile = oldfile

    self._oldfile = oldfile
    self._newfile = newfile

  def __repr__(self):
    return "<FilePatchHeader: %s -> %s>" % (self._oldfile, self._newfile,)

  @staticmethod
  def parse(lines):
    def parse_rename_header(lines):
      if lines[0][0:16] == "similarity index":
        lines = lines[1:]
      match = re.match('^rename from (.*)$', lines[0])
      if match is None:
        return None, lines
      oldfile = match.group(1)

      match = re.match('^rename to (.*)$', lines[1])
      if match is None:
        return None, lines
      newfile = match.group(1)

      return FilePatchHeader(oldfile, newfile), lines[2:]

    def parse_diff_header(lines):
      while lines and lines[0] != '' and lines[0][0:4] != '--- ':
        lines = lines[1:]

      if not lines or lines[0][0:4] != '--- ':
        return None, lines

      match = re.match('^--- (?:a/|b/)?(.*)$', lines[0])
      if match is None:
        return None, lines
      oldfile = match.group(1)

      match = re.match('^\+\+\+ (?:a/|b/)?(.*)$', lines[1])
      if match is not None:
        newfile = match.group(1)
      return FilePatchHeader(oldfile, newfile), lines[2:]

    debug.log(debug.parser, "FilePatchHeader? ", lines[0])
    if lines[0][0:11] != 'diff --git ':
      return None, lines
    lines = lines[1:]
    # Try a rename header
    header, lines = parse_rename_header(lines)
    if header is None:
      # Try a regular (diff) header
      header, lines = parse_diff_header(lines)
    return header, lines


class FilePatch():
  _fragments = None
  _header = None

  def __init__(self, header, fragments):
    self._header = header
    self._fragments = fragments

  def __repr__(self):
    return "\n  <FilePatch: %s, %s>" % (self._header, self._fragments,)

  @staticmethod
  def parse(lines):
    debug.log(debug.parser, "FilePatch? ", lines[0])
    header, lines = FilePatchHeader.parse(lines)
    if header is not None:
      fragments = []
      while len(lines) > 0:
        fragment, lines = Fragment.parse(lines)
        if fragment is None:
          # No more fragments; stop
          break
        fragments += [fragment]
      p = FilePatch(header, fragments), lines
      return p
    else:
      return None, lines

class PatchHeader():
  _hash = None
  _message = None

  def __init__(self, hash, message):
    self._hash = hash
    self._message = message

  def __repr__(self):
    return "<PatchHeader: %s\n%s>" %(self._hash, self._message)

  @staticmethod
  def parse(lines):
    debug.log(debug.parser, "PatchHeader?", lines[0])
    match = re.match("^([0-9a-f]{40})", lines[0][0:40])
    if match is not None:
      lines = lines[1:]

    match = re.match("^commit ([0-9a-f]{40})", lines[0])
    if match is None:
      return None, lines
    hash = match.group(1)

    if lines[1][0:8] != 'Author: ':
      debug.log(debug.parser, "'%s'!='Author: '" %(lines[1][0:8],))
      return None, lines
    if lines[2][0:6] != 'Date: ':
      return None, lines
    lines = lines[3:]
    message = []
    while lines[0] == '' or lines[0][0] == ' ':
      debug.log(debug.parser, "in PatchHeader:", lines[0])
      if lines[0] != '':
        # Add line to message list
        message += [lines[0].strip()]
      lines = lines[1:]
    return PatchHeader(hash, message), lines

class Patch():
  _header = None
  _filepatches = None

  def __init__(self, filepatches, header):
    self._filepatches = filepatches
    self._header = header

  def __repr__(self):
    return "\n <Patch: %s %s>" % (self._header, self._filepatches)

  def find_patch_by_old_file(self, old_file_name):
    for file_patch in self._filepatches:
      if file_patch._header._oldfile == old_file_name:
        return file_patch
    return None

  @staticmethod
  def parse(lines):
    debug.log(debug.parser, "Patch?", lines[0])
    header, lines = PatchHeader.parse(lines)
    debug.log(debug.parser, "PatchHeader: ", header)
    if header is None:
      return None, lines
    filepatches = []
    while len(lines) > 0:
      filepatch, lines = FilePatch.parse(lines)
      debug.log(debug.parser, "FilePatch:", filepatch)
      if filepatch is not None:
        filepatches += [filepatch]
      else:
        # No more parsable filepatches; return
        break
    return Patch(filepatches, header), lines

class AST():
  _patches = None
  def __init__(self, patches):
    self._patches = patches

  def __repr__(self):
    return "<AST: %s>" % (self._patches,)

  @staticmethod
  def parse(lines):
    patches = []
    unheadered_filepatches = []
    while len(lines) > 0:
      # Try parsing a Patch
      patch, lines = Patch.parse(lines)
      debug.log(debug.parser, "Patch: ", patch)
      if patch is not None:
        patches += [patch]
      else:
        # Try parsing a FilePatch
        filepatch, lines = FilePatch.parse(lines)
        debug.log(debug.parser, "Filepatch without patch header:", filepatch)
        if filepatch is not None:
          unheadered_filepatches += [filepatch]
        else:
          # Remove a line and retry parsing
          lines = lines[1:]
        continue
    if len(unheadered_filepatches) > 0:
      dummy_patch = Patch(unheadered_filepatches,
                          PatchHeader('0000000000000000000000000000000000000000',
                                      [' (uncommitted changes)']))
      debug.log(debug.parser, "Created dummy Patch:", dummy_patch)
      patches += [dummy_patch]
    return AST(patches), lines

class PatchParser():
  _ast = None

  @staticmethod
  def parse(lines):
    ast, lines_after = AST.parse(lines)
    if len(lines_after) == len(lines):
      debug.log(debug.parser, "No lines parsed!")
    if len(lines_after) > 0:
      debug.log(debug.parser, "Unparsable content left at end of file.")
    return ast





def main():
  pp = PatchParser()
  lines = [line.rstrip() for line in sys.stdin]
  print pp.parse(lines)

if __name__ == '__main__':
  debug.parse_args()
  main()
