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
from dataclasses import dataclass
from pathlib import PurePath, Path
from typing import Dict, List, Union

from fragmap.list_dict import ListDict
from fragmap.spg import FileId


def file_matches(path: PurePath, pattern: PurePath):
  if path.parent == path:
    return path == pattern
  else:
    return path == pattern or file_matches(path.parent, pattern)


@dataclass
class FilePatterns:
  patterns: Union[List[PurePath], None]

  @staticmethod
  def from_files_arg(files_arg: Union[List[str], None], cwd: str = '.'):
    return FilePatterns(None if files_arg is None
                        else [PurePath(cwd, p)
                              for p in files_arg])

  def matches(self, absolute_file: str):
    if self.patterns is None:
      return True
    abs_file = Path(absolute_file)
    return any([file_matches(abs_file, pattern)
                for pattern in self.patterns])


@dataclass
class FileSelection:
  patterns: FilePatterns

  # Note: Defined after the class definition
  ALL = None

  @staticmethod
  def from_files_arg(files_arg: Union[List[str], None]):
    return FileSelection(FilePatterns.from_files_arg(files_arg))

  def contains(self,
               file_id: FileId,
               to_earlier_file: Dict[FileId, FileId]):
    if self.patterns.patterns is None:
      return True
    grouped_by_orig_file = ListDict()
    for key in to_earlier_file.keys():
      grouped_by_orig_file.add(to_earlier_file[key], key)

    group = grouped_by_orig_file.kv_map[to_earlier_file[file_id]]
    assert file_id in group
    return any([self.patterns.matches(f.path)
                for f in group])


FileSelection.ALL = FileSelection.from_files_arg(None)
