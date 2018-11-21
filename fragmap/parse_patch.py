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
#      _content
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
import json


def is_nullfile(fn):
  return fn == '/dev/null'


def nonnull_file(file_patch_header):
  if not is_nullfile(file_patch_header._oldfile):
    return file_patch_header._oldfile
  if not is_nullfile(file_patch_header._newfile):
    return file_patch_header._newfile
  # Both files are null files
  return None


class Range(object):
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


class FragmentHeader(object):
  _oldrange = None
  _newrange = None
  def __init__(self, oldrange, newrange):
    self._oldrange = oldrange
    self._newrange = newrange

  def __repr__(self):
    return "<FragmentHeader: %s, %s>" % (self._oldrange, self._newrange,)

  @staticmethod
  def parse(lines):
    debug.get('parser').debug("FragmentHeader? %s", lines[0])
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
    if lines[0][0:6] == 'Binary':
      match = re.match('^Binary files (?:a/|b/)?(.*) and (?:a/|b/)?(.*) differ$', lines[0])
      if match is not None:
        oldlength = 1
        if match.group(1) == '/dev/null':
          oldlength = 0
        newlength = 1
        if match.group(2) == '/dev/null':
          newlength = 0
        return FragmentHeader(Range(0, oldlength),
                              Range(0, newlength)), lines[1:]
    debug.get('parser').debug("Not fragment header")
    return None, lines


class Fragment(object):
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
    debug.get('parser').debug("Fragment? %s", lines[0])
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
    debug.get('parser').debug("Not fragment")
    return None, lines


class FilePatchHeader(object):
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

      filepatchheader = FilePatchHeader(oldfile, newfile)

      lines = lines[2:]
      header_lines = lines
      if len(lines) == 0:
        return filepatchheader, header_lines

      # Try greedily to match optional (and redundant) ---, +++ lines

      lines = skip_index(lines)
      match = re.match('^--- (?:a/|b/)?(.*)$', lines[0])
      if match is not None:
        lines = lines[1:]
      if match is None or oldfile != match.group(1):
        return filepatchheader, header_lines

      match = re.match('^\+\+\+ (?:a/|b/)?(.*)$', lines[0])
      if match is not None:
        lines = lines[1:]
      if match is None or newfile != match.group(1):
        return filepatchheader, header_lines

      return filepatchheader, lines

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

    def parse_binary_header(lines):
      while lines and lines[0] != '' and lines[0][0:6] != 'Binary':
        lines = lines[1:]
      if not lines or lines[0][0:6] != 'Binary':
        return None, lines

      match = re.match('^Binary files (?:a/|b/)?(.*) and (?:a/|b/)?(.*) differ$', lines[0])
      if match is None:
        return None, lines
      oldfile = match.group(1)
      newfile = match.group(2)
      # Returning lines and not lines[1:] here because we need
      # the 'Binary files ... differ' line for the Fragment parsing as well,
      # otherwise the FilePatch will have no fragments.
      return FilePatchHeader(oldfile, newfile), lines

    def skip_index(lines):
      while len(lines) > 0 and lines[0][0:6] == 'index ':
        lines = lines[1:]
      return lines

    debug.get('parser').debug("FilePatchHeader? %s", lines[0])
    if lines[0][0:11] != 'diff --git ':
      return None, lines
    lines = lines[1:]
    # Try a rename header
    header, rlines = parse_rename_header(lines)
    rlines = skip_index(rlines)
    if header is not None:
      debug.get('parser').debug("Parsed rename FilePatchHeader: %s", header)
      return header, rlines
    # Try a regular (diff) header
    header, rlines = parse_diff_header(lines)
    rlines = skip_index(rlines)
    if header is not None:
      debug.get('parser').debug("Parsed diff FilePatchHeader: %s", header)
      return header, rlines
    # Try a binary header
    header, rlines = parse_binary_header(lines)
    rlines = skip_index(rlines)
    if header is not None:
      debug.get('parser').debug("Parsed binary FilePatchHeader: %s", header)
      return header, rlines
    return header, lines


class FilePatch(object):
  _fragments = None
  _header = None

  def __init__(self, header, fragments):
    self._header = header
    self._fragments = fragments

  def __repr__(self):
    return "\n  <FilePatch: %s, %s>" % (self._header, self._fragments,)

  @staticmethod
  def parse(lines):
    debug.get('parser').debug("FilePatch? %s", lines[0])
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


class RawPatchHeader(object):
  _content = None

  def __init__(self, content):
    self._content = content

  def __repr__(self):
    return "<RawPatchHeader: %s>" %(self._content,)

  @staticmethod
  def parse(lines):
    debug.get('parser').debug("RawPatchHeader? %s", lines[0])
    if lines[0][0] != ':':
      return None, lines
    content = []
    while lines[0] == '' or lines[0][0] == ':':
      debug.get('parser').debug("in RawPatchHeader: %s", lines[0])
      if lines[0] != '':
        # Add line to content list
        content += [lines[0].strip()]
      lines = lines[1:]
    return PatchHeader(hash, content), lines



class PatchHeader(object):
  _hash = None
  _message = None

  def __init__(self, hash, message):
    self._hash = hash
    self._message = message

  def __repr__(self):
    return "<PatchHeader: %s\n%s>" %(self._hash, self._message)

  @staticmethod
  def parse(lines):
    debug.get('parser').debug("PatchHeader? %s", lines[0])
    match = re.match("^([0-9a-f]{40})", lines[0][0:40])
    if match is not None:
      lines = lines[1:]

    match = re.match("^commit ([0-9a-f]{40})", lines[0])
    if match is None:
      return None, lines
    hash = match.group(1)

    if lines[1][0:8] != 'Author: ':
      debug.get('parser').debug("'%s'!='Author: '", lines[1][0:8])
      return None, lines
    if lines[2][0:6] != 'Date: ':
      return None, lines
    lines = lines[3:]
    message = []
    while lines[0] == '' or lines[0][0] == ' ':
      debug.get('parser').debug("in PatchHeader: %s", lines[0])
      if lines[0] != '':
        # Add line to message list
        message += [lines[0].strip()]
      lines = lines[1:]
    return PatchHeader(hash, message), lines


class RawPatch(object):
  _header = None
  _filepatches = None

  def __init__(self, filepatches, header):
    self._filepatches = filepatches
    self._header = header

  def __repr__(self):
    return "\n <RawPatch: %s %s" % (self._header, self._filepatches)

  @staticmethod
  def parse(lines):
    debug.get('parser').debug("RawPatch? %s", lines[0])
    header, lines = RawPatchHeader.parse(lines)
    debug.get('parser').debug("RawPatchHeader: %s", header)
    if header is None:
      return None, lines
    filepatches = []
    while len(lines) > 0:
      filepatch, lines = FilePatch.parse(lines)
      debug.get('parser').debug("FilePatch: %s", filepatch)
      if filepatch is not None:
        filepatches += [filepatch]
      else:
        # No more parsable filepatches; return
        break
    return Patch(filepatches, header), lines


class Patch(object):
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
    while lines[0] == '':
      lines = lines[1:]
    debug.get('parser').debug("Patch? %s", lines[0])
    header, lines = PatchHeader.parse(lines)
    debug.get('parser').debug("PatchHeader: %s", header)
    if header is None:
      return None, lines
    filepatches = []
    while len(lines) > 0:
      filepatch, lines = FilePatch.parse(lines)
      debug.get('parser').debug("FilePatch: %s", filepatch)
      if filepatch is not None:
        filepatches += [filepatch]
      else:
        # No more parsable filepatches; return
        break
    return Patch(filepatches, header), lines


class AST(object):
  _patches = None
  def __init__(self, patches):
    self._patches = patches

  def __repr__(self):
    return "<AST: %s>" % (self._patches,)

  @staticmethod
  def parse(lines):
    patches = []
    rawpatches = []
    while len(lines) > 0:
      if lines[0] == '':
        lines = lines[1:]
        continue
      # Try parsing a Patch
      patch, lines = Patch.parse(lines)
      debug.get('parser').debug("Patch: %s", patch)
      if patch is not None:
        patches += [patch]
      else:
        # Try parsing a RawPatch
        rawpatch, lines = RawPatch.parse(lines)
        debug.get('parser').debug("Rawpatch : %s", rawpatch)
        if rawpatch is not None:
          rawpatches += [rawpatch]
        else:
          # Remove a line and retry parsing
          lines = lines[1:]
        continue
    if len(rawpatches) > 1:
      staged_patch = Patch(rawpatches[1]._filepatches,
                           PatchHeader('0000000100000000000000000000000000000000',
                                       [' (staged changes)']))
      debug.get('parser').debug("Created staged Patch: %s", staged_patch)
      patches += [staged_patch]

    if len(rawpatches) > 0:
      uncommitted_patch = Patch(rawpatches[0]._filepatches,
                                PatchHeader('0000000000000000000000000000000000000000',
                                            [' (unstaged changes)']))
      debug.get('parser').debug("Created unstaged Patch: %s", uncommitted_patch)
      patches += [uncommitted_patch]
    return AST(patches), lines


class PatchParser(object):
  _ast = None

  @staticmethod
  def parse(lines):
    ast, lines_after = AST.parse(lines)
    if len(lines_after) == len(lines):
      debug.get('parser').debug("No lines parsed!")
    if len(lines_after) > 0:
      debug.get('parser').debug("Unparsable content left at end of file.")
    return ast

class DictCoersionEncoder(json.JSONEncoder):
  def default(self, obj):
    try:
      return json.JSONEncoder.default(self, obj)
    except TypeError:
      return vars(obj)




def main():
  pp = PatchParser()
  lines = [line.rstrip() for line in sys.stdin]
  print pp.parse(lines)

if __name__ == '__main__':
  debug.parse_args()
  main()
