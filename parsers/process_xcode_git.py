#!/usr/bin/env python3
"""Process an Apple LLVM (Xcode) git repository for diagnostic groups."""
import os
import sys

import git
from process_clang_git import create_diffs, parse_clang_info

DIR = os.path.dirname(os.path.realpath(__file__))


def main() -> None:
    """Entry point."""
    GIT_DIR = sys.argv[1]
    repo = git.Repo(GIT_DIR)

    target_dir = f"{DIR}/../xcode"

    # Parse all apple/stable branches as well as apple/main
    branches = sorted(
        ref.name for ref in repo.refs if ref.name.startswith("origin/apple/stable/")
    )
    versions = [(branch.split("/")[-1], branch) for branch in branches]
    versions += [("NEXT", "origin/apple/main")]

    os.makedirs(target_dir, exist_ok=True)

    for version, ref in versions:
        print(f"Processing {version=}")
        repo.git.checkout(ref)
        parse_clang_info(version, target_dir, f"{GIT_DIR}/clang/include/clang/Basic")

    # Generate diffs
    create_diffs(target_dir, [version for version, _ in versions])


if __name__ == "__main__":
    main()
