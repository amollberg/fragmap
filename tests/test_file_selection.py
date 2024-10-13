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
import unittest
from pathlib import PurePath

from fragmap.file_selection import FilePatterns, FileSelection, file_matches
from fragmap.spg import FileId


class FileSelectionTest(unittest.TestCase):
    def test_single_absolute_file(self):
        fp = FilePatterns.from_files_arg(["file.txt"])
        self.assertTrue(fp.matches("file.txt"))
        self.assertFalse(fp.matches("other.txt"))


class FilePatternsTest(unittest.TestCase):
    def test_matches_absolute_file(self):
        self.assertTrue(self.file_matches("f.txt", "f.txt"))
        self.assertFalse(self.file_matches("f/f.txt", "f.txt"))
        self.assertFalse(self.file_matches("f.txt", "f/f.txt"))
        self.assertTrue(self.file_matches("f.txt", "./f.txt"))
        self.assertTrue(self.file_matches("./f.txt", "f.txt"))

    def test_matches_file_from_dir(self):
        self.assertTrue(self.file_matches("d/f.txt", "d"))
        self.assertTrue(self.file_matches("d/f.txt", "d/"))
        self.assertTrue(self.file_matches("d/f.txt", "./d/"))
        self.assertTrue(self.file_matches("d/s/f.txt", "./d/s"))
        self.assertTrue(self.file_matches("d/s/f.txt", "d"))
        self.assertFalse(self.file_matches("d.txt", "d"))
        self.assertFalse(self.file_matches("d/s/f.txt", "s"))
        self.assertFalse(self.file_matches("d/s/f.txt", "f.txt"))

    def file_matches(self, path, pattern):
        return file_matches(PurePath(path), PurePath(pattern))


if __name__ == "__main__":
    unittest.main()
