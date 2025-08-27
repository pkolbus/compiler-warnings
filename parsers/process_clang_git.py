#!/usr/bin/env python3
"""Process a clang git repository for diagnostic groups."""
import difflib
import json
import os
import shutil
import subprocess  # noqa: S404
import sys

import git
import jinja2

DIR = os.path.dirname(os.path.realpath(__file__))

README_TEMPLATE = """
# Clang diagnostic flags

Clang has both warnings (flags starting with `-W`) and remarks (flags starting
with `-R`); both are in these lists for completeness. Clang also has
`-Weverything` and `-Reverything` flags (not shown in these lists), to enable
all warnings or all remarks respectively. Clang documentation also provides a
[reference](https://clang.llvm.org/docs/DiagnosticsReference.html).

{% for prev, current in versions %}
* clang {{current}} [all](warnings-{{current}}.txt)
  • [top level](warnings-top-level-{{current}}.txt)
  • [messages](warnings-messages-{{current}}.txt)
  • [unique](warnings-unique-{{current}}.txt)
{%- if prev %}
  • [diff](warnings-diff-{{prev}}-{{current}}.txt)
{%- endif %}
{%- endfor %}
"""


def is_interesting(line: str) -> bool:
    """
    Return whether line is interesting for a diff.

    :param line: The line to examine.
    :returns: True if the line is interesting for a diff, False otherwise.
    """
    return line.startswith("+-") or line.startswith("--") and not line.startswith("---")


def create_diffs(target_dir: str, versions: list[str]) -> None:
    """
    Generate diffs for adjacent versions of the 'unique' warning lists.

    :param target_dir: Directory containing files to compare
    :param versions: List of versions to compare
    """
    for version_idx in range(0, len(versions) - 1):
        current_ver = versions[version_idx]
        next_ver = versions[version_idx + 1]

        with open(f"{target_dir}/warnings-unique-{current_ver}.txt") as current_file:
            current_lines = current_file.readlines()
        with open(f"{target_dir}/warnings-unique-{next_ver}.txt") as next_file:
            next_lines = next_file.readlines()

        with open(
            f"{target_dir}/warnings-diff-{current_ver}-{next_ver}.txt", "w"
        ) as diff:
            lines = difflib.unified_diff(current_lines, next_lines, n=0)
            lines = filter(is_interesting, lines)
            diff.writelines(lines)


def create_readme(target_dir: str, versions: list[str], readme_template: str) -> None:
    """Write the README.md.

    :param target_dir: The directory to write to.
    :param versions: The list of versions to include in the README.
    :param readme_template: String containing the text of the Jinja2 template.
        In the template, versions is a list of (prev, current) version tuples.
    """
    # Prev/current version pairs. Generate in reverse order, and treat the first
    # as a special case.
    version_pairs: list[tuple[str | None, str]] = [
        (versions[i], versions[i + 1]) for i in range(len(versions) - 2, -1, -1)
    ]
    version_pairs += [(None, versions[0])]

    template = jinja2.Template(readme_template)
    with open(f"{target_dir}/README.md", "w") as index:
        index.write(template.render(versions=version_pairs))


def format_json(json_path: str) -> None:
    """Format the JSON file at json_path.

    :param json_path: The file to reformat.
    """
    obj = json.load(open(json_path))

    with open(json_path, "w") as json_file:
        json.dump(obj, json_file, indent=4)
        json_file.write("\n")  # Add trailing newline that json.dump does not


def parse_clang_info(version: str, target_dir: str, input_dir: str) -> None:
    """
    Parse clang diagnostic groups for the given version (in input_dir) to target_dir.

    :param version: Version number to use in output filenames
    :param target_dir: Directory to write outputs
    :param input_dir: Directory containing Diagnostic.td file
    """
    json_file = f"{target_dir}/warnings-{version}.json"

    shell(
        ["llvm-tblgen", "-dump-json", "-I", input_dir, f"{input_dir}/Diagnostic.td"],
        json_file,
    )
    format_json(json_file)

    shell(
        [sys.executable, f"{DIR}/parse-clang-diagnostic-groups.py", json_file],
        f"{target_dir}/warnings-{version}.txt",
    )
    shell(
        [
            sys.executable,
            f"{DIR}/parse-clang-diagnostic-groups.py",
            "--unique",
            json_file,
        ],
        f"{target_dir}/warnings-unique-{version}.txt",
    )
    shell(
        [
            sys.executable,
            f"{DIR}/parse-clang-diagnostic-groups.py",
            "--top-level",
            json_file,
        ],
        f"{target_dir}/warnings-top-level-{version}.txt",
    )
    shell(
        [
            sys.executable,
            f"{DIR}/parse-clang-diagnostic-groups.py",
            "--top-level",
            "--text",
            json_file,
        ],
        f"{target_dir}/warnings-messages-{version}.txt",
    )


def shell(cmd: list[str], stdout_path: str) -> None:
    """
    Run cmd in a subprocess.

    :param cmd: The command to run.
    :param stdout_path: Optional path to write stdout.
    """
    result = subprocess.run(cmd, stdout=subprocess.PIPE, check=True)  # noqa: S603

    with open(stdout_path, "wb") as stdout_file:
        stdout_file.write(result.stdout)


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

    target_dir = f"{DIR}/../clang"
    shutil.rmtree(target_dir, ignore_errors=True)
    os.mkdir(target_dir)

    # Parse all release branches
    branches = [ref.name for ref in repo.refs if ref.name.startswith("origin/release/")]

    # Remove everything up to the last / as well as the ".x"
    versions = [(branch.split("/")[-1][:-2], branch) for branch in branches]

    # Filter to 3.2 and later, and sort numerically
    versions = [(version, ref) for version, ref in versions if tryfloat(version) >= 3.2]
    versions = sorted(versions, key=lambda v: float(v[0]))

    # Add the main branch
    versions += [("NEXT", "origin/main")]

    for version, ref in versions:
        print(f"Processing {version=}")
        repo.git.checkout(ref)
        parse_clang_info(version, target_dir, f"{GIT_DIR}/clang/include/clang/Basic")

    # Generate diffs
    version_numbers = [version for version, _ in versions]
    create_diffs(target_dir, version_numbers)

    # Generate index (README.md) except for NEXT
    create_readme(target_dir, version_numbers[:-1], README_TEMPLATE)


if __name__ == "__main__":
    main()
