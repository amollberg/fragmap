#!/usr/bin/env bash

__fragmap_complete () {
    prev="${COMP_WORDS[COMP_CWORD - 1]}"
    cur="${COMP_WORDS[COMP_CWORD]}"
    case "$prev" in
	-s|-r|--range)
	    # Refs from git
	    __git_complete_refs --cur="$cur"
	    ;;
	-i|--import|-o|--export)
	    # Files in working directory
	    COMPREPLY=( $(compgen -f $cur) )
	    ;;
    esac
    return 0
}

[ -n "$(type -t __git_complete_refs)" ] || echo fragmap: Warning: Bash completion for Git not detected

complete -o bashdefault -o nospace -F __fragmap_complete fragmap
