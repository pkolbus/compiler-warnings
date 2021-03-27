#!/bin/bash

set -eu

diff -Naur "$1" "$2" | grep -E "^[-+]-" | grep -v -- ---
