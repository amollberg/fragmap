#!/usr/bin/env python
# encoding: utf-8
from dataclasses import dataclass
from typing import Dict, List, Union

from fragmap.list_dict import ListDict
from fragmap.spg import FileId

@dataclass
class FileSelection:
  files: List[str]

  # Note: Defined after the class definition
  ALL = None

  @staticmethod
  def from_files_arg(files_arg: Union[List[str], None]):
    return FileSelection(files_arg)

  def contains(self,
               file_id: FileId,
               to_earlier_file: Dict[FileId, FileId]):
    if self.files is None:
      return True
    grouped_by_orig_file = ListDict()
    for key in to_earlier_file.keys():
      grouped_by_orig_file.add(to_earlier_file[key], key)

    def is_path_in_group(file_path: str, group: List[FileId]):
      return any([f.path == file_path for f in group])

    group = grouped_by_orig_file.kv_map[to_earlier_file[file_id]]
    assert file_id in group
    for path in self.files:
      if is_path_in_group(path, group):
        return True
    return False


FileSelection.ALL = FileSelection.from_files_arg(None)
