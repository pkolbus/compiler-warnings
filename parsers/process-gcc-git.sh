#!/bin/bash

set -euo pipefail

DIR=$(dirname "$(readlink -f "$0")")

function parse_gcc_info()
{
    local version=$1
    local target_dir=$2
    shift 2
    local input_files=("$@")
    "${DIR}/parse-gcc-warning-options.py" "${input_files[@]}" \
          > "${target_dir}/warnings-gcc-${version}.txt"
    "${DIR}/parse-gcc-warning-options.py" --unique "${input_files[@]}" \
          > "${target_dir}/warnings-gcc-unique-${version}.txt"
    "${DIR}/parse-gcc-warning-options.py" --top-level "${input_files[@]}" \
          > "${target_dir}/warnings-gcc-top-level-${version}.txt"
    "${DIR}/parse-gcc-warning-options.py" --top-level --text "${input_files[@]}" \
          > "${target_dir}/warnings-gcc-detail-${version}.txt"
}

GIT_DIR=$1

target_dir=${DIR}/../gcc

git -C "${GIT_DIR}" checkout releases/gcc-3.4.6
parse_gcc_info 3.4 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-4.0.4
parse_gcc_info 4.0 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-4.1.2
parse_gcc_info 4.1 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-4.2.4
parse_gcc_info 4.2 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-4.3.6
parse_gcc_info 4.3 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-4.4.7
parse_gcc_info 4.4 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-4.5.4
parse_gcc_info 4.5 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-4.6.4
parse_gcc_info 4.6 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c-family/c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-4.7.4
parse_gcc_info 4.7 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c-family/c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-4.8.5
parse_gcc_info 4.8 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c-family/c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-4.9.4
parse_gcc_info 4.9 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c-family/c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-5.5.0
parse_gcc_info 5 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c-family/c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-6.5.0
parse_gcc_info 6 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c-family/c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-7.5.0
parse_gcc_info 7 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c-family/c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-8.4.0
parse_gcc_info 8 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c-family/c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-9.3.0
parse_gcc_info 9 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c-family/c.opt}

git -C "${GIT_DIR}" checkout releases/gcc-10.2.0
parse_gcc_info 10 "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c-family/c.opt,analyzer/analyzer.opt}

git -C "${GIT_DIR}" checkout origin/master
parse_gcc_info NEXT "${target_dir}" "${GIT_DIR}"/gcc/{common.opt,c-family/c.opt,analyzer/analyzer.opt}

versions=(
    3.4
    4.0
    4.1
    4.2
    4.3
    4.4
    4.5
    4.6
    4.7
    4.8
    4.9
    5
    6
    7
    8
    9
    10
    NEXT
)

seq 2 "${#versions[@]}" | while read -r version_idx; do
    current=${versions[$(( version_idx - 2 ))]}
    next=${versions[$(( version_idx - 1 ))]}
    "${DIR}/create-diff.sh" \
          "${target_dir}/warnings-gcc-unique-${current}.txt" \
          "${target_dir}/warnings-gcc-unique-${next}.txt" \
          > "${target_dir}/warnings-gcc-diff-${current}-${next}.txt"
done
