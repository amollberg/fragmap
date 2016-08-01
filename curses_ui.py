#!/usr/bin/env python
# encoding: utf-8


import npyscreen
class HunkogramApp(npyscreen.NPSApp):
    _diff_list = None
    _matrix = None
    _hash_width = None
    _console_width = None

    def main(self):
        # These lines create the form and populate it with widgets.
        # A fairly complex screen in only 8 or so lines of code - a line for each control.
        F = npyscreen.ActionFormWithMenus(name = "Welcome to Npyscreen",)
        #matrix = [['#','.','#','#','#','.','.'],
        #          ['#','#','.','.','.','#','.'],
        #          ['.','#','.','#','.','.','.']]
        matrix = self._matrix
        diff_list = self._diff_list
        n_matrix_cols = len(matrix[0])
        n_cols = 2 + n_matrix_cols
        n_rows = len(matrix)
        hash_width = self._hash_width
        msg_width = self._console_width - (2 + hash_width + 1 + 2*n_matrix_cols + 2)
        grid = [[''] * n_cols ]* n_rows
        for r in range(n_rows):
            #hash = 'abcd0123'
            hash = diff_list._patches[r]._header._hash[0:hash_width]
            #commit_msg = 'Test commit message about this or that'
            commit_msg = diff_list._patches[r]._header._message[0] # First row of message
            grid[r] = [hash, commit_msg] + matrix[r]
        g = F.add(npyscreen.SimpleGrid, values=grid, name="simple grid",
                  column_width=[hash_width, msg_width] + [2]*len(matrix[0]), col_margin=0)
        F.edit()
