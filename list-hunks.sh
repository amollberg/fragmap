#!/bin/env bash

while read -r rev; do
    echo $rev
    #git diff "$rev~1" "$rev"  --
    git diff -U0 --no-color
    git show -U0 --no-color "$rev"  -- # | grep "^[@+-]"

done < <(git rev-list --reverse "$1")

# TODO: Integrate with interactive rebase, edit buffer or something
#git rebase -i "$1"
#cat .git/rebase-merge/git-rebase-todo
