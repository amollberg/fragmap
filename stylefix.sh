#!/usr/bin/env bash
set -e

items="fragmap/*.py tests/*.py getch/*.py *.py"

black .
isort $items
pylint -j 4 $items
