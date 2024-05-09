#!/usr/bin/env python3
"""Process an Apple LLVM (Xcode) git repository for diagnostic groups."""
import os
import re
import shutil
import sys

import git
from process_clang_git import create_diffs, create_readme, parse_clang_info

DIR = os.path.dirname(os.path.realpath(__file__))

VERSION_RE = re.compile("[0-9]{8}")

README_TEMPLATE = """
# Apple clang (Xcode) diagnostic flags

Apple's fork of clang (as shipped with Xcode) is _based on_ the LLVM project but
is not a 100% match in the warning and remark flags supported; some are added,
others are removed, and the versioning scheme is different. The official Xcode
releases are built from an Apple-internal repository, so the exact list of flags
is not truly knowable without experimentation.

That said, [Apple's public fork of LLVM](https://github.com/apple/llvm-project)
has `apple/stable/*` and `stable/*` branches which are a close approximation of
the Xcode sources especially with regard to available compiler warnings. For
example, the delta between `apple/stable/20200108` and Xcode 12.2 is about ten
flags.

Warnings available in each branch are as follows:

{% for prev, current in versions %}
* {{current}} [all](warnings-{{current}}.txt)
  • [top level](warnings-top-level-{{current}}.txt)
  • [messages](warnings-messages-{{current}}.txt)
  • [unique](warnings-unique-{{current}}.txt)
{%- if prev %}
  • [diff](warnings-diff-{{prev}}-{{current}}.txt)
{%- endif %}
{%- endfor %}
"""


def main() -> None:
    """Entry point."""
    GIT_DIR = sys.argv[1]
    repo = git.Repo(GIT_DIR)

    target_dir = f"{DIR}/../xcode"
    shutil.rmtree(target_dir, ignore_errors=True)
    os.mkdir(target_dir)

    # Parse all apple/stable/ and stable/ branches as well as apple/main
    branches = sorted(
        ref.name
        for ref in repo.refs  # type: ignore[attr-defined]
        if ref.name.startswith("origin/apple/stable/")
        or ref.name.startswith("origin/stable/")
    )
    versions = [(branch.split("/")[-1], branch) for branch in branches]
    versions = [
        (version, branch)
        for (version, branch) in versions
        if VERSION_RE.fullmatch(version)
    ]
    versions += [("NEXT", "origin/apple/main")]

    os.makedirs(target_dir, exist_ok=True)

    for version, ref in versions:
        print(f"Processing {version=}")
        repo.git.checkout(ref)
        parse_clang_info(version, target_dir, f"{GIT_DIR}/clang/include/clang/Basic")

    # Generate diffs
    version_numbers = [version for version, _ in versions]
    create_diffs(target_dir, [version for version, _ in versions])

    # Generate index (README.md) except for NEXT
    create_readme(target_dir, version_numbers[:-1], README_TEMPLATE)


if __name__ == "__main__":
    main()
