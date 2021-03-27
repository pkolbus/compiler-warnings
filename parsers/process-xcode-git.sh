#!/bin/bash
set -euo pipefail

DIR=$(dirname "$(readlink -f "$0")")

function parse_clang_info()
{
    local version=$1
    local target_dir=$2
    local input_dir=$3

    local json_file="$target_dir"/warnings-xcode-"$version".json

    llvm-tblgen -dump-json -I "${input_dir}" \
          "${input_dir}/Diagnostic.td" \
          | python3 -mjson.tool \
          > "${json_file}"
    "$DIR"/parse-clang-diagnostic-groups.py "${json_file}" \
          > "$target_dir"/warnings-xcode-"$version".txt
    "$DIR"/parse-clang-diagnostic-groups.py --unique "${json_file}" \
          > "$target_dir"/warnings-xcode-unique-"$version".txt
    "$DIR"/parse-clang-diagnostic-groups.py --top-level "${json_file}" \
          > "$target_dir"/warnings-xcode-top-level-"$version".txt
    "$DIR"/parse-clang-diagnostic-groups.py --top-level --text "${json_file}" \
          > "$target_dir"/warnings-xcode-messages-"$version".txt
}

GIT_DIR=$1

target_dir=$DIR/../xcode

# Parse all apple/stable branches
mapfile -t versions < <( git -C "$GIT_DIR" branch --list -r "origin/apple/stable/*" | cut -f4 -d"/")

mkdir -p "$target_dir"

for v in "${versions[@]}"; do
    git -C "$GIT_DIR" checkout "origin/apple/stable/${v}"
    parse_clang_info "${v}" "$target_dir" "$GIT_DIR"/clang/include/clang/Basic
done

# Parse NEXT (apple/main)
versions=( "${versions[@]}" "NEXT" )

git -C "$GIT_DIR" checkout origin/apple/main
parse_clang_info NEXT "$target_dir" "$GIT_DIR"/clang/include/clang/Basic

# Generate diffs
seq 2 "${#versions[@]}" | while read -r version_idx; do
    current=${versions[$(( version_idx - 2 ))]}
    next=${versions[$(( version_idx - 1 ))]}
    "$DIR"/create-diff.sh \
          "${target_dir}/warnings-xcode-unique-${current}.txt" \
          "${target_dir}/warnings-xcode-unique-${next}.txt" \
          > "${target_dir}/warnings-xcode-diff-${current}-${next}.txt"
done
