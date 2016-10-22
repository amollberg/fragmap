#!/usr/bin/env python
# encoding: utf-8

import debug
import npyscreen


def get_uncommitted_changes_indices(matrix):
    return [i for i in range(len(matrix[0])) if matrix[-1][i] == '#']


def has_hunks_conflicting_with_uncommitted(row_i, matrix):
    for uncommitted_col_i in get_uncommitted_changes_indices(matrix):
        if matrix[row_i][uncommitted_col_i] == '#':
            return True
    return False


class FragmapGrid(npyscreen.SimpleGrid):
    _fragmap = None
    _matrix = None # TODO: Keep in sync with _fragmap
    _start_row = None
    _start_col = None
    _cursor_event_callback = None

    def when_cursor_moved(self):
        cursor_row = self.edit_cell[0] - self._start_row
        cursor_col = self.edit_cell[1] - self._start_col
        if cursor_row < 0 or cursor_col < 0:
            return
        self._cursor_event_callback(cursor_row, cursor_col)


    def custom_print_cell(self, actual_cell, cell_display_value):
        index = actual_cell.grid_current_value_index
        if index != -1:
            row_i, col_i = index
            row_i -= self._start_row
            col_i -= self._start_col
            if col_i < 0:
                # We are in the hash or commit message column
                if has_hunks_conflicting_with_uncommitted(row_i, self._matrix):
                    actual_cell.color = 'WARNING'
            elif cell_display_value == '#':
                if col_i in get_uncommitted_changes_indices(self._matrix):
                    actual_cell.color = 'WARNING'


class FragmapApp(npyscreen.NPSApp):
    _hash_width = None
    _console_width = None
    _fragmap = None

    # UI components
    _grid = None
    _text_field = None

    def on_cursor_event(self, cursor_row, cursor_col):
        # Look up fragments from matrix cells
        diff_i = cursor_row
        found_node_line = None
        for node_line in self._fragmap.grouped_node_lines[cursor_col]:
            if node_line._startdiff_i == diff_i:
                found_node_line = node_line
                break
        text_content = ""
        if found_node_line is not None:
            text_content = '\n'.join(found_node_line.last()._fragment._content)
        # Write contents of found_node_line.last()._fragment
        # to the text field
        self._text_field.value = text_content
        self._text_field.update()


    def main(self):
        matrix = self._fragmap.generate_matrix()
        patches = self._fragmap.patches
        n_matrix_cols = len(matrix[0])
        n_cols = 2 + n_matrix_cols
        n_rows = len(matrix)
        hash_width = self._hash_width
        grid_width = (2 + hash_width + 1 + 2*n_matrix_cols + 2)
        msg_width = 30
        total_width = msg_width + 1 + grid_width
        debug.log(debug.curses, matrix, patches, n_matrix_cols, n_cols, n_rows, hash_width, msg_width)
        grid = [[''] * n_cols ]* n_rows

        for r in range(n_rows):
            hash = patches[r]._header._hash[0:hash_width]
            commit_msg = patches[r]._header._message[0] # First row of message
            grid_column_widths = [hash_width, msg_width] + [2]*len(matrix[0])
            debug.log(debug.curses, hash, commit_msg, grid_column_widths)
            grid[r] = [hash, commit_msg] + matrix[r]
        # Create the form and populate it with widgets
        F = npyscreen.ActionFormWithMenus(name = "Fragmap", minimum_columns = total_width)
        self._text_field = F.add(npyscreen.MultiLineEdit, value="""sdfsdf\nsdfsdf""", max_height=3, rely=9)

        g = F.add(FragmapGrid, values=grid, name="simple grid",
                  column_width=grid_column_widths, col_margin=0)
        g._matrix = matrix
        g._fragmap = self._fragmap
        g._start_row = 0
        g._start_col = 2
        g._cursor_event_callback = self.on_cursor_event
        self._grid = g

        F.edit()
