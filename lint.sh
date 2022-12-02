#!/bin/sh

set -e

usage_msg="Usage: $0 [-f|--autoformat]"

case "$1" in
-h|--help|help)
  echo "$usage_msg"
  exit
  ;;
-f|--autoformat)
  ;;
*)
  # just check if no options are provided
  black_flags="--check"
  isort_flags="--check"
  ;;
esac

echo "Formatting..."
black . $black_flags
isort . $isort_flags
pylint pytealext
