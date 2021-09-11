#!/usr/bin/env python3
"""Process an Apple LLVM (Xcode) git repository for diagnostic groups."""
import os
import subprocess  # noqa: S404
import sys

from process_clang_git import format_json, shell

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
                f"{target_dir}/warnings-xcode-unique-{current_ver}.txt",
                f"{target_dir}/warnings-xcode-unique-{next_ver}.txt",
            ],
            f"{target_dir}/warnings-xcode-diff-{current_ver}-{next_ver}.txt",
        )


def parse_clang_info(version: str, target_dir: str, input_dir: str) -> None:
    """
    Parse clang diagnostic groups for the given version (in input_dir) to target_dir.

    :param version: Version number to use in output filenames
    :param target_dir: Directory to write outputs
    :param input_dir: Directory containing Diagnostic.td file
    """
    json_file = f"{target_dir}/warnings-xcode-{version}.json"

    shell(
        ["llvm-tblgen", "-dump-json", "-I", input_dir, f"{input_dir}/Diagnostic.td"],
        json_file,
    )
    format_json(json_file)

    shell(
        [f"{DIR}/parse-clang-diagnostic-groups.py", json_file],
        f"{target_dir}/warnings-xcode-{version}.txt",
    )
    shell(
        [f"{DIR}/parse-clang-diagnostic-groups.py", "--unique", json_file],
        f"{target_dir}/warnings-xcode-unique-{version}.txt",
    )
    shell(
        [f"{DIR}/parse-clang-diagnostic-groups.py", "--top-level", json_file],
        f"{target_dir}/warnings-xcode-top-level-{version}.txt",
    )
    shell(
        [f"{DIR}/parse-clang-diagnostic-groups.py", "--top-level", "--text", json_file],
        f"{target_dir}/warnings-xcode-messages-{version}.txt",
    )


def main() -> None:
    """Entry point."""
    GIT_DIR = sys.argv[1]

    target_dir = f"{DIR}/../xcode"

    # Parse all apple/stable branches
    cmd = ["git", "-C", GIT_DIR, "branch", "--list", "-r", "origin/apple/stable/*"]
    result = subprocess.run(cmd, capture_output=True, check=True)  # noqa: S603

    versions = [branch.split("/")[-1] for branch in result.stdout.decode().splitlines()]
    result.stdout.decode().splitlines()

    os.makedirs(target_dir, exist_ok=True)

    for version in versions:
        print(f"Processing {version=}")
        shell(["git", "-C", GIT_DIR, "checkout", f"origin/apple/stable/{version}"])
        parse_clang_info(version, target_dir, f"{GIT_DIR}/clang/include/clang/Basic")

    # Parse NEXT (apple/main)
    versions.append("NEXT")

    print("Processing apple/main")
    shell(["git", "-C", GIT_DIR, "checkout", "origin/apple/main"])
    parse_clang_info("NEXT", target_dir, f"{GIT_DIR}/clang/include/clang/Basic")

    # Generate diffs
    create_diffs(target_dir, versions)


if __name__ == "__main__":
    main()
