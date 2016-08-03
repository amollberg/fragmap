#!/usr/bin/env python
# encoding: utf-8

DEBUG_CURSES=False

import npyscreen

def get_uncommitted_changes_indices(matrix):
    return [i for i in range(len(matrix[0])) if matrix[-1][i] == '#']


def has_hunks_conflicting_with_uncommitted(row_i, matrix):
    for uncommitted_col_i in get_uncommitted_changes_indices(matrix):
        if matrix[row_i][uncommitted_col_i] == '#':
            return True
    return False


class HunkogramGrid(npyscreen.SimpleGrid):
    _diff_list = None
    _matrix = None
    _grouped_node_lines = None
    _start_row = None
    _start_col = None

    def when_cursor_moved(self):
        cursor_row = self.edit_cell[0] - self._start_row
        cursor_col = self.edit_cell[1] - self._start_col
        # Look up fragments from matrix cells
        diff_i = cursor_row
        found_node_line = None
        for node_line in self._grouped_node_lines[cursor_col]:
            if node_line._startdiff_i == diff_i:
                found_node_line = node_line
                break
        if found_node_line is None:
            return
        # TODO: Write contents of found_node_line.last()._fragment
        # to some text field


    def custom_print_cell(self, actual_cell, cell_display_value):
        index = actual_cell.grid_current_value_index
        if index != -1:
            row_i, col_i = index
            row_i -= self._start_row
            col_i -= self._start_col
            if col_i < 0:
                if has_hunks_conflicting_with_uncommitted(row_i, self._matrix):
                    actual_cell.color = 'WARNING'
            elif cell_display_value == '#':
                if col_i in get_uncommitted_changes_indices(self._matrix):
                    actual_cell.color = 'WARNING'


class HunkogramApp(npyscreen.NPSApp):
    _diff_list = None
    _matrix = None
    _hash_width = None
    _console_width = None
    _grouped_node_lines = None

    def main(self):
        matrix = self._matrix
        diff_list = self._diff_list
        n_matrix_cols = len(matrix[0])
        n_cols = 2 + n_matrix_cols
        n_rows = len(matrix)
        hash_width = self._hash_width
        msg_width = self._console_width - (2 + hash_width + 1 + 2*n_matrix_cols + 2)
        if msg_width < 1:
            F = npyscreen.ActionFormWithMenus(name = "Error: Diagram too wide")
            F.edit()
            return
        if DEBUG_CURSES:
            print matrix, diff_list, n_matrix_cols, n_cols, n_rows, hash_width, msg_width
        grid = [[''] * n_cols ]* n_rows

        for r in range(n_rows):
            hash = diff_list._patches[r]._header._hash[0:hash_width]
            commit_msg = diff_list._patches[r]._header._message[0] # First row of message
            grid_column_widths = [hash_width, msg_width] + [2]*len(matrix[0])
            if DEBUG_CURSES:
                print hash, commit_msg, grid_column_widths
            grid[r] = [hash, commit_msg] + matrix[r]
        # Create the form and populate it with widgets
        F = npyscreen.ActionFormWithMenus(name = "Hunkogram",)
        g = F.add(HunkogramGrid, values=grid, name="simple grid",
                  column_width=grid_column_widths, col_margin=0)
        g._diff_list = self._diff_list
        g._matrix = self._matrix
        g._grouped_node_lines = self._grouped_node_lines
        g._start_row = 0
        g._start_col = 2
        F.edit()
