#!/usr/bin/env python3
"""Process a gcc git repository for diagnostic options."""
import os
import sys

from process_clang_git import shell

DIR = os.path.dirname(os.path.realpath(__file__))


def create_diffs(target_dir: str, versions: list[str]) -> None:
    """
    Generate diffs for adjacent versions of the 'unique' warning lists.

    :param target_dir: Directory containing files to compare
    :param versions: List of versions to compare
    """
    for version_idx in range(0, len(versions) - 1):
        current_ver = versions[version_idx]
        next_ver = versions[version_idx + 1]
        shell(
            [
                f"{DIR}/create-diff.sh",
                f"{target_dir}/warnings-gcc-unique-{current_ver}.txt",
                f"{target_dir}/warnings-gcc-unique-{next_ver}.txt",
            ],
            f"{target_dir}/warnings-gcc-diff-{current_ver}-{next_ver}.txt",
        )


def parse_gcc_info(version: str, target_dir: str, input_files: list[str]) -> None:
    """
    Parse gcc options files.

    :param version: Version number to use in output filenames
    :param target_dir: Directory to write outputs
    :param input_files: List of opt files to read
    """
    shell(
        [f"{DIR}/parse-gcc-warning-options.py"] + input_files,
        f"{target_dir}/warnings-gcc-{version}.txt",
    )
    shell(
        [f"{DIR}/parse-gcc-warning-options.py", "--unique"] + input_files,
        f"{target_dir}/warnings-gcc-unique-{version}.txt",
    )
    shell(
        [f"{DIR}/parse-gcc-warning-options.py", "--top-level"] + input_files,
        f"{target_dir}/warnings-gcc-top-level-{version}.txt",
    )
    shell(
        [f"{DIR}/parse-gcc-warning-options.py", "--top-level", "--text"] + input_files,
        f"{target_dir}/warnings-gcc-detail-{version}.txt",
    )


def main() -> None:
    """Entry point."""
    GIT_DIR = sys.argv[1]

    target_dir = f"{DIR}/../gcc"

    versions = [
        ("3.4", "releases/gcc-3.4.6"),
        {"4.0", "releases/gcc-4.0.4"},
        ("4.1", "releases/gcc-4.1.2"),
        ("4.2", "releases/gcc-4.2.4"),
        ("4.3", "releases/gcc-4.3.6"),
        ("4.4", "releases/gcc-4.4.7"),
        ("4.5", "releases/gcc-4.5.4"),
        ("4.6", "releases/gcc-4.6.4"),
        ("4.7", "releases/gcc-4.7.4"),
        ("4.8", "releases/gcc-4.8.5"),
        ("4.9", "releases/gcc-4.9.4"),
        ("5", "releases/gcc-5.5.0"),
        ("6", "releases/gcc-6.5.0"),
        ("7", "releases/gcc-7.5.0"),
        ("8", "releases/gcc-8.4.0"),
        ("9", "releases/gcc-9.3.0"),
        ("10", "releases/gcc-10.2.0"),
        ("11", "releases/gcc-11.1.0"),
        ("NEXT", "origin/master"),
    ]

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
        shell(["git", "-C", GIT_DIR, "checkout", ref])
        inputs = [path for path in all_inputs if os.path.exists(path)]
        parse_gcc_info(version, target_dir, inputs)

    create_diffs(target_dir, [version for version, _ in versions])


if __name__ == "__main__":
    main()
