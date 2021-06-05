import unittest
from pathlib import PurePath

from fragmap.file_selection import FileSelection, FilePatterns, file_matches
from fragmap.spg import FileId


class FileSelectionTest(unittest.TestCase):
  def test_single_absolute_file(self):
    fp = FilePatterns.from_files_arg(['file.txt'])
    self.assertTrue(fp.matches('file.txt'))
    self.assertFalse(fp.matches('other.txt'))


class FilePatternsTest(unittest.TestCase):
  def test_matches_absolute_file(self):
    self.assertTrue(self.file_matches('f.txt', 'f.txt'))
    self.assertFalse(self.file_matches('f/f.txt', 'f.txt'))
    self.assertFalse(self.file_matches('f.txt', 'f/f.txt'))
    self.assertTrue(self.file_matches('f.txt', './f.txt'))
    self.assertTrue(self.file_matches('./f.txt', 'f.txt'))

  def test_matches_file_from_dir(self):
    self.assertTrue(self.file_matches('d/f.txt', 'd'))
    self.assertTrue(self.file_matches('d/f.txt', 'd/'))
    self.assertTrue(self.file_matches('d/f.txt', './d/'))
    self.assertTrue(self.file_matches('d/s/f.txt', './d/s'))
    self.assertTrue(self.file_matches('d/s/f.txt', 'd'))
    self.assertFalse(self.file_matches('d.txt', 'd'))
    self.assertFalse(self.file_matches('d/s/f.txt', 's'))
    self.assertFalse(self.file_matches('d/s/f.txt', 'f.txt'))

  def file_matches(self, path, pattern):
    return file_matches(PurePath(path), PurePath(pattern))


if __name__ == '__main__':
  unittest.main()
