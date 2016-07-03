#!/bin/env bash

while read -r rev; do
	echo $rev 
    #git diff "$rev~1" "$rev"  --
	git show "$rev"  -- | grep "^@"
done < <(git rev-list "$1")