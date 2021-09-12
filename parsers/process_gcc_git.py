#!/usr/bin/env python3
"""Process a gcc git repository for diagnostic options."""
import os
import sys

import git
from process_clang_git import create_diffs, shell

DIR = os.path.dirname(os.path.realpath(__file__))


def parse_gcc_info(version: str, target_dir: str, input_files: list[str]) -> None:
    """
    Parse gcc options files.

    :param version: Version number to use in output filenames
    :param target_dir: Directory to write outputs
    :param input_files: List of opt files to read
    """
    shell(
        [f"{DIR}/parse-gcc-warning-options.py"] + input_files,
        f"{target_dir}/warnings-{version}.txt",
    )
    shell(
        [f"{DIR}/parse-gcc-warning-options.py", "--unique"] + input_files,
        f"{target_dir}/warnings-unique-{version}.txt",
    )
    shell(
        [f"{DIR}/parse-gcc-warning-options.py", "--top-level"] + input_files,
        f"{target_dir}/warnings-top-level-{version}.txt",
    )
    shell(
        [f"{DIR}/parse-gcc-warning-options.py", "--top-level", "--text"] + input_files,
        f"{target_dir}/warnings-detail-{version}.txt",
    )


def tryfloat(number: str) -> float:
    """
    Return number as a float, or zero.

    :param number: The number to convert.
    :returns: The number as a float, or zero if the number cannot be converted.
    """
    try:
        return float(number)
    except ValueError:
        return 0


def main() -> None:
    """Entry point."""
    GIT_DIR = sys.argv[1]
    repo = git.Repo(GIT_DIR)

    target_dir = f"{DIR}/../gcc"

    # Parse all release branches
    branches = [
        ref.name for ref in repo.refs if ref.name.startswith("origin/releases/gcc-")
    ]

    # Remove everything up to the last / as well as the "gcc-"
    versions = [(branch.split("/")[-1][4:], branch) for branch in branches]

    # Filter to 3.4 and later, and sort numerically
    versions = [(version, ref) for version, ref in versions if tryfloat(version) >= 3.4]
    versions = sorted(versions, key=lambda v: float(v[0]))

    # Add the master branch
    versions += [("NEXT", "origin/master")]

    all_inputs = [
        f"{GIT_DIR}/gcc/{path}"
        for path in (
            "common.opt",
            "c.opt",  # gcc 4.5 and earlier
            "c-family/c.opt",  # gcc 4.6 and later
            "analyzer/analyzer.opt",  # gcc 10 and later
        )
    ]

    for version, ref in versions:
        print(f"Processing {version=}")
        repo.git.checkout(ref)
        inputs = [path for path in all_inputs if os.path.exists(path)]
        parse_gcc_info(version, target_dir, inputs)

    create_diffs(target_dir, [version for version, _ in versions])


if __name__ == "__main__":
    main()
