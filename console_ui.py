from parse_patch import *
from generate_matrix import *

CONSOLE_WIDTH = 80

# TODO: Change name?
def print_hunkogram(diff_list):
  matrix = generate_matrix(diff_list)
  matrix_width = len(matrix[0])
  hash_width = 8
  padded_matrix_width = max(CONSOLE_WIDTH/2, matrix_width)
  max_commit_width = min(CONSOLE_WIDTH/2, CONSOLE_WIDTH - (hash_width + 1 + 1 + padded_matrix_width))
  for r in range(len(matrix)):
    commit_msg = "Test"
    hash = diff_list._patches[r]._header._hash
    # Pad short commit messages
    commit_msg = commit_msg.ljust(max_commit_width, ' ')
    # Truncate long commit messages
    commit_msg = commit_msg[0:min(max_commit_width,len(commit_msg))]
    # Print hash, commit, matrix row
    hash = hash[0:hash_width]
    print hash, commit_msg, ''.join(matrix[r])

def main():
  pp = PatchParser()
  lines = [line.rstrip() for line in sys.stdin]
  print lines
  diff_list = pp.parse(lines)
  print_hunkogram(diff_list)



if __name__ == '__main__':
  main()
