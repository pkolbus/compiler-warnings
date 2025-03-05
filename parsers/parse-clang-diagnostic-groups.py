#!/usr/bin/env python3
"""
Parser for clang diagnostic groups.

Parses an extract of clang's Diagnostic.td as formatted by the command
`llvm-tblgen -dump-json`, and identifies relevant information about the
compiler warning options.
"""
from __future__ import annotations

import argparse
from functools import total_ordering
from itertools import chain
import json
import logging
from typing import Any, NotRequired, TypedDict

import common


class ClangTextSubstitution:
    """One clang TextSubstitution."""

    def __init__(self, substitution: str) -> None:
        """
        Construct from substitution text.

        :param substitution: The replacement text.
        """
        self._substitution = substitution

    @classmethod
    def from_json(cls, obj: dict[str, str]) -> ClangTextSubstitution:
        """
        Construct from a TextSubstitution instance (JSON object).

        :param obj: The JSON object containing a Diagnostic instance.
        :return: The TextSubstitution represented by obj.
        """
        return ClangTextSubstitution(obj["Substitution"])

    @property
    def summary(self) -> str:
        """:return: the summary text of the substitution, resolved."""
        return resolve_format_string(self._substitution, {})


# Map from text substitution name to contents.
ClangTextSubstitutions = dict[str, ClangTextSubstitution]  # noqa: T484


def find_argument(message: str, start: int) -> tuple[int, list[str]]:
    """
    Find and return the complete argument.

    :param message: The message to parse.
    :param start: The index of the open brace.
    :return: A tuple of (end_index, arguments) where end_index is the index
        immediately following the close brace. Note that the items in the
        arguments list may contain placeholder text.
    """
    depth = 0
    index = start + 1
    arguments = []

    argument_start = index
    while index < len(message):
        if depth == 0 and message[index] in ("|", "}"):
            arguments.append(message[argument_start:index])
            argument_start = index + 1
        if message[index] == "}":
            if depth == 0:
                break
            depth -= 1
        if message[index] == "%":
            # Possible inner placeholder
            index += 1
            if message[index] == "%":
                # Escaped %
                index += 1
                continue

            # Skip across the modifier
            while message[index] == "-" or message[index].islower():
                index += 1

            # If an argument is present, need the matching close brace
            if message[index] == "{":
                depth += 1
        index += 1

    return index + 1, arguments


def parse_placeholder(
    message: str, start: int
) -> tuple[int, int, str | None, list[str] | None]:
    """Parse the placeholder starting at message[cur_idx].

    message[start:] must be a placeholder for a diagnostic argument.  The format
    for a placeholder is one of "%0", "%modifier0", or "%modifier{arguments}0".
    The digit is a number from 0-9 indicating which argument this comes from.
    The modifier is a string of digits from the set [-a-z]+, arguments is a
    brace enclosed string.

    :param message: The string containing the message to parse.
    :param start: The start index to parse at.
    :return: a 4-tuple of index, argument_index, modifier, arguments. The `modifier`
        and `arguments` are None if not present in the placeholder.
    :raises RuntimeError: if message cannot be parsed.
    """
    cur_idx = start + 1  # Skip over the %

    modifier: str | None = None
    arguments: list[str] | None = None
    if not message[cur_idx].isdigit():
        modifier_start = cur_idx
        while message[cur_idx] == "-" or message[cur_idx].islower():
            cur_idx += 1
        modifier = message[modifier_start:cur_idx]

        if message[cur_idx] == "{":
            cur_idx, arguments = find_argument(message, cur_idx)

        if modifier == "diff":
            cur_idx += 2  # Skip comma and 2nd argument index

    argument_no = message[cur_idx]
    if not argument_no.isdigit():
        raise RuntimeError()

    cur_idx += 1  # Skip digit

    return cur_idx, int(argument_no), modifier, arguments


def format_alternative_list(
    alternatives: list[str], substitutions: ClangTextSubstitutions
) -> str:
    """
    Format a list of alternatives.

    If any alternative is the empty string, present the remaining as an
    optional selection. Otherwise, format as a mandatory selection.

    :param alternatives: List of alternatives to format. Each element may contain
        placeholder text.
    :param substitutions: Collection of TextSubstitution, for `sub`.
    :return: The formatted list.
    """
    # Remove and check for empty items
    filtered_alternatives = list(filter(bool, alternatives))
    is_optional = len(filtered_alternatives) < len(alternatives)

    # Remove duplicates. Python 3.7+ guarantees order is preserved.
    filtered_alternatives = list(dict.fromkeys(filtered_alternatives))
    filtered_alternatives = [
        resolve_format_string(alternative, substitutions)
        for alternative in filtered_alternatives
    ]

    if is_optional:
        return "[{}]".format("|".join(filtered_alternatives))

    return "<{}>".format("|".join(filtered_alternatives))


def format_arguments(
    modifier: str, arguments: list[str], substitutions: ClangTextSubstitutions
) -> str:
    """
    Format modifier and arguments for readability.

    :param modifier: The modifier from parse_placeholder().
    :param arguments: The arguments from parse_placeholder().
    :param substitutions: Collection of TextSubstitution, for `sub`.
    :return: A human-readable form of the argument.
    :raises NotImplementedError: if modifier is unknown.
    """
    if modifier == "select":
        return format_alternative_list(arguments, substitutions)

    if modifier == "plural":
        forms = [arg.split(":")[1] for arg in arguments]
        return format_alternative_list(forms, substitutions)

    if modifier == "diff":
        return arguments[-1]

    if modifier == "sub":
        return substitutions[arguments[0]].summary

    raise NotImplementedError(f"Unhandled modifier %{modifier}")


def format_modifier(modifier: str | None, argument_idx: int) -> str:
    """
    Format modifier for readability.

    :param modifier: The modifier from parse_placeholder().
    :param argument_idx: The zero-based index of the argument.
    :return: A human-readable form of the format string.
    :raises NotImplementedError: if modifier is unknown.
    """
    if modifier is None or modifier in ("objcclass", "objcinstance", "q"):
        # Translate 0-9 into A-J
        return chr(ord("A") + argument_idx)

    if modifier == "s":
        return "(s)"

    if modifier == "ordinal":
        return "Nth"

    raise NotImplementedError(f"Unhandled modifier %{modifier}")


def resolve_format_string(message: str, substitutions: ClangTextSubstitutions) -> str:
    """
    Resolve a clang diagnostic message to a more readable form.

    Format string placeholders can be of the forms %0", "%modifier0", or
    "%modifier{arguments}0".

    Per `clang/lib/Basic/Diagnostic.cpp`. the digit is a number from 0-9
    indicating which argument this comes from. The modifier is a string of
    digits from the set `[-a-z]+`, arguments is a brace enclosed string.

    Simple strings are returned as-is:

    >>> subs = {"sel_foo": ClangTextSubstitution("a %select{unary|binary}2 operator")}
    >>> resolve_format_string("foo", subs)
    'foo'

    The %0 through %9 form resolve to A through J:

    >>> resolve_format_string("class %0 incompatible with struct %9", subs)
    'class A incompatible with struct J'

    Simple modifiers:
    - s: Simple plural. Resolves to `(s)`.
    - q: Fully qualified name. Resolves to same as `%0` form.
    - ordinal: Represents the value as ordinal. Resolves to `Nth`.

    >>> resolve_format_string("requires %1 parameter%s1", subs)
    'requires B parameter(s)'
    >>> resolve_format_string("requires %q2 parameter%s1", subs)
    'requires C parameter(s)'
    >>> resolve_format_string("ambiguity in %ordinal0 argument", subs)
    'ambiguity in Nth argument'

    Argument modifiers:
    - select: Enumerated alternatives, separated by `|`. Resolves to `<arguments>`.
    - plural: Select based on value. Arguments are number:form pairs separated
    by `|`. Resolves to the form portion of the arguments.
    - diff: Prints a type difference. Resolve as if tree printing were on, i.e.
    the text after the pipe
    - sub: Replace with a TextSubstitution

    >>> resolve_format_string("must be a %select{unary|binary}2 operator", subs)
    'must be a <unary|binary> operator'
    >>> resolve_format_string("must be a %select{|unary|binary}2 operator", subs)
    'must be a [unary|binary] operator'
    >>> resolve_format_string("you have %2 %plural{1:mouse|:mice}2 connected", subs)
    'you have C <mouse|mice> connected'
    >>> resolve_format_string("%diff{from $ to $|from arg type to param type}1,2", subs)
    'from arg type to param type'
    >>> resolve_format_string("must not be %sub{sel_foo}1", subs)
    'must not be a <unary|binary> operator'

    Duplicates are removed:

    >>> resolve_format_string("must be a %select{|unary|binary|unary}2 operator", subs)
    'must be a [unary|binary] operator'

    Argument modifiers may be recursive:

    >>> resolve_format_string("must be a %select{%0|unary|binary}2 operator", subs)
    'must be a <A|unary|binary> operator'
    >>> resolve_format_string("must be %select{%diff{foo|bar}0,1|unary|binary}2", subs)
    'must be <bar|unary|binary>'

    :param message: The message to resolve.
    :param substitutions: Optional dictionary of substitutions.
    :return: The message, better formatted for readability.
    :raises RuntimeError: if a failure is detected.
    """
    out_str = ""
    cur_idx = 0

    while cur_idx < len(message):
        if message[cur_idx] != "%":
            # Append non-%0 substring to out_str, if any.
            pct_pos = message.find("%", cur_idx)
            if pct_pos == -1:
                pct_pos = len(message)
            out_str += message[cur_idx:pct_pos]
            cur_idx = pct_pos
            continue
        elif message[cur_idx + 1] == "%":
            # Handle escaped %%
            out_str += "%"
            cur_idx += 2
            continue

        cur_idx, argument_idx, modifier, arguments = parse_placeholder(message, cur_idx)

        if arguments is None:
            out_str += format_modifier(modifier, argument_idx)
        else:
            if modifier is None:
                raise RuntimeError(f"arguments with no modifier: {message}")
            out_str += format_arguments(modifier, arguments, substitutions)

    return out_str


ClangDiagnosticJson = TypedDict(
    "ClangDiagnosticJson",
    {
        "!name": str,
        "Summary": NotRequired[str],
        "Text": str,
        "Group": Any,
        "DefaultSeverity": NotRequired[Any],
        "DefaultMapping": Any,
        "Class": Any,
    },
)


class ClangDiagnostic:
    """One clang warning message (Diagnostic)."""

    def __init__(
        self, obj: ClangDiagnosticJson, substitutions: ClangTextSubstitutions
    ) -> None:
        """
        Construct from a Diagnostic instance (JSON object).

        :param obj: The JSON object containing a Diagnostic instance.
        :param substitutions: Dictionary of available substitutions.
        """
        self.name = obj["!name"]
        try:
            self._summary = obj["Summary"]
        except KeyError:
            self._summary = obj["Text"]

        self._substitutions = substitutions
        if obj["Group"] is not None:
            self.group_name = obj["Group"]["def"]
        else:
            self.group_name = None
        if "DefaultSeverity" in obj:
            # clang 3.5+
            self.enabled_by_default = obj["DefaultSeverity"]["def"] != "SEV_Ignored"
        else:
            # clang 3.4 (and earlier)
            self.enabled_by_default = obj["DefaultMapping"]["def"] != "MAP_IGNORE"

        self.is_extension = obj["Class"]["def"] == "CLASS_EXTENSION"
        self.is_remark = obj["Class"]["def"] == "CLASS_REMARK"

    @property
    def summary(self) -> str:
        """:return: the summary text of the warning."""
        if self._summary == "%0":
            # Special case for W#pragma and similar. The text is taken from
            # clang/utils/TableGen/ClangDiagnosticsEmitter.cpp.
            return "The text of this diagnostic is not controlled by Clang"

        try:
            return resolve_format_string(self._summary, self._substitutions)
        except RuntimeError:
            logging.warning("Failed to resolve: %s", self._summary)
            return self._summary


class ClangDiagGroup:
    """One clang diagnostic group (DiagGroup record)."""

    def __init__(self, obj: dict[str, Any], parent: ClangDiagnostics) -> None:
        """
        Construct from a DiagGroup instance (JSON object).

        :param obj: The JSON object containing a DiagGroup instance.
        :param parent: The parent diagnostics collection. Used to retrieve the
            associated ClangDiagnosticSwitch.
        """
        self.name = obj["!name"]
        self.switch_name = obj["GroupName"]
        self.child_names = [s["def"] for s in obj["SubGroups"]]

        self.has_parent = False
        self.diagnostics: list[ClangDiagnostic] = []
        self.children: list[ClangDiagGroup] = []
        self.switch: ClangDiagnosticSwitch = parent.get_switch(self.switch_name)

    def get_messages(self, enabled_by_default: bool) -> list[str]:
        """
        Return a list of diagnostic messages in the group.

        :param enabled_by_default: If True, only the mesages enabled by default
            are returned. Otherwise, all messages are returned.
        :return: the messages in the group.
        """
        if enabled_by_default:
            return [
                diag.summary for diag in self.diagnostics if diag.enabled_by_default
            ]

        return [diag.summary for diag in self.diagnostics]

    def is_remark(self) -> bool:
        """
        Return whether a group is a remark.

        :return: True if the group has remark diagnostics, False otherwise.
        :raises RuntimeError: if disagreement about if it's a remark between the
            different subgroups and disagnostics
        """
        isRemarkArray = []

        for diagnostic in self.diagnostics:
            if diagnostic.is_remark:
                isRemarkArray.append(True)

        for subgroup in self.children:
            if subgroup.is_remark():
                isRemarkArray.append(True)

        # if not all the elements are the same (some subgroups/diagnostics think
        # it's a remark, others don't)
        if len(isRemarkArray) == 0:
            return False
        if not all(x == isRemarkArray[0] for x in isRemarkArray):
            raise RuntimeError(
                "disagrement about if this group is a remark in subgroups/diagnostics"
            )

        return isRemarkArray[0]

    def is_ignored(self) -> bool:
        """
        Return whether a group does nothing.

        An ignored group has no warnings, directly or indirectly.

        :return: True if the group is ignored, False otherwise.
        """
        if self.diagnostics:
            return False

        for child in self.children:
            if not child.is_ignored():
                return False

        return True

    def is_pedantic(self) -> bool:
        """
        Return whether a group is inferred pedantic.

        A group is inferred pedantic if it has at least one diagnostic (directly
        or indirectly), and all diagnostics are off-by-default extensions.

        :return: True if the group is inferred pedantic, False otherwise.
        """
        if self.is_ignored():
            return False

        for diagnostic in self.diagnostics:
            if diagnostic.enabled_by_default or not diagnostic.is_extension:
                return False

        for child in self.children:
            if not child.is_pedantic():
                return False

        return True

    def has_disabled_diagnostic(self) -> bool:
        """
        Return whether a group has a disabled diagnostic.

        :return: True if the group or any of its children has at least one
            diagnostic that is _not_ enabled by default, False otherwise.
        """
        for diagnostic in self.diagnostics:
            if not diagnostic.enabled_by_default:
                return True

        for child in self.children:
            if child.has_disabled_diagnostic():
                return True

        return False

    def has_enabled_diagnostic(self) -> bool:
        """
        Return whether a group has an enabled diagnostic.

        :return: True if the group or any of its children has at least one
            diagnostic that _is_ enabled by default, False otherwise.
        """
        for diagnostic in self.diagnostics:
            if diagnostic.enabled_by_default:
                return True

        for child in self.children:
            if child.has_enabled_diagnostic():
                return True

        return False

    def resolve_children(self, all_groups: dict[str, ClangDiagGroup]) -> None:
        """
        Resolve self.child_names to self.children.

        :param all_groups: List of all available diagnostic groups.
        """
        self.children = [all_groups[name] for name in self.child_names]
        for child_group in self.children:
            child_group.has_parent = True


@total_ordering
class ClangDiagnosticSwitch:
    """One clang warning switch (-Wxxxx option) or a remark (-Rxxxx)."""

    def __init__(self, name: str):
        """
        Construct from a name.

        :param name: The name of the switch.
        """
        self.name = name
        self.groups: list[ClangDiagGroup] = []

    def __eq__(self, other: object) -> bool:
        """
        Return True if self and other are equal.

        Two ClangDiagnosticSwitch are equal if they have the same name,
        case-insensitive.

        :param other: The object to compare for equality.
        :return: NotImplemented if `other` is _not_ a ClangDiagnosticSwitch,
            True if self and other have the same name, case-insensitive, or
            False otherwise.
        """
        if not isinstance(other, ClangDiagnosticSwitch):
            return NotImplemented

        return self.name.lower() == other.name.lower()

    def __lt__(self, other: object) -> bool:
        """
        Return True if self should be before other in a sorted list.

        Two ClangDiagnosticSwitch should be sorted by name, case-insensitive.

        :param other: The object to compare against.
        :return: NotImplemented if `other` is _not_ a ClangDiagnosticSwitch,
            True if the name of self is less than the name of other, case-insensitive,
            or False otherwise.
        """
        if not isinstance(other, ClangDiagnosticSwitch):
            return NotImplemented

        return self.name.lower() < other.name.lower()

    def __hash__(self) -> int:
        """:return: a hash of the switch name."""
        return hash(self.name.lower())

    def get_child_switches(
        self, enabled_by_default: bool
    ) -> list[ClangDiagnosticSwitch]:
        """
        Return a list of child ClangDiagnosticSwitch for the switch.

        :param enabled_by_default: If True, return only the switches that are
            partially or completely enabled by default. Otherwise, all child
            switches are returned.
        :return: a list of direct children.
        """
        child_groups: list[ClangDiagGroup] = []
        for group in self.groups:
            child_groups += group.children

        child_switches = [group.switch for group in child_groups]
        if enabled_by_default:
            child_switches = [
                switch
                for switch in child_switches
                if switch.is_enabled_by_default()
                or switch.partially_enabled_by_default()
            ]

        return child_switches

    def get_messages(self, enabled_by_default: bool) -> list[str]:
        """
        Return a list of diagnostic messages controlled by the switch.

        :param enabled_by_default: If True, only the mesages enabled by default
            are returned. Otherwise, all messages are returned.
        :return: the messages controlled by the switch.
        """
        messages = []
        for group in self.groups:
            messages += group.get_messages(enabled_by_default)

        return list(set(messages))  # Remove duplicates

    def is_remark(self) -> bool:
        """
        Return whether a switch is a remark.

        :return: True if the switch has remark diagnostics, False otherwise.
        """
        for group in self.groups:
            if not group.is_remark():
                return False

        return True

    def is_ignored(self) -> bool:
        """
        Return whether a switch does nothing.

        A switch is ignored (does nothing) if all groups are ignored.

        :return: True if the switch does nothing, False otherwise.
        """
        for group in self.groups:
            if not group.is_ignored():
                return False

        return True

    def is_enabled_by_default(self) -> bool:
        """
        Return whether a switch is enabled by default.

        A switch is enabled by default if no diagnostic (in any group)
        is disabled by default and the switch is not ignored.

        :return: True if all diagnostics controlled by the switch are enabled by
            default, False otherwise.
        """
        for group in self.groups:
            if group.has_disabled_diagnostic():
                return False

        return not self.is_ignored()

    def partially_enabled_by_default(self) -> bool:
        """
        Return whether a switch is partially enabled by default.

        A switch is partially enabled by default if it has both enabled and
        disabled diagnostics.

        :return: True if some (but not all) diagnostics controlled by the switch
            are enabled by default, False otherwise.
        """
        has_enabled = False
        has_disabled = False
        for group in self.groups:
            if group.has_disabled_diagnostic():
                has_disabled = True
            if group.has_enabled_diagnostic():
                has_enabled = True

        return has_enabled and has_disabled

    def is_top_level(self) -> bool:
        """
        Return whether a switch is top-level.

        A switch is top-level if none of its group(s) have a parent.

        :return: True if none of the groups have a parent, False otherwise.
        """
        for group in self.groups:
            if group.has_parent:
                return False

        return True


class ClangDiagnostics:
    """
    Data model for clang diagnostics.

    In the clang model, a switch controls one or more diagnostic groups. Each
    group is associated with one switch name, has zero or more warnings, and
    has zero or more subgroups.
    """

    def __init__(self, filename: str):
        """
        Construct from a JSON file.

        :param filename: The path to the JSON file to parse.
        """
        self.groups = {}  # Dict: group name -> ClangDiagGroup
        self.switches: dict[str, ClangDiagnosticSwitch] = {}
        self._substitutions: ClangTextSubstitutions = {}

        json_data = json.loads(open(filename).read())

        # Instantiate all text substitutions
        if "TextSubstitution" in json_data["!instanceof"]:
            for substitution_name in json_data["!instanceof"]["TextSubstitution"]:
                substitution = ClangTextSubstitution.from_json(
                    json_data[substitution_name]
                )
                self._substitutions[substitution_name] = substitution

        # Instantiate all group and switch objects
        for group_name in json_data["!instanceof"]["DiagGroup"]:
            group = ClangDiagGroup(json_data[group_name], self)

            self.groups[group_name] = group
            self.switches[group.switch_name].groups.append(group)

        # Instantiate all diagnostics and link to groups
        pedantic_group = self.groups["Pedantic"]
        for diag_name in json_data["!instanceof"]["Diagnostic"]:
            diag = ClangDiagnostic(json_data[diag_name], self._substitutions)

            if diag.group_name is not None and diag.group_name in self.groups:
                self.groups[diag.group_name].diagnostics.append(diag)
            elif diag.is_extension and not diag.enabled_by_default:
                pedantic_group.diagnostics.append(diag)

        # Resolve parent-child relationships in groups
        for group in self.groups.values():
            group.resolve_children(self.groups)

        # Find inferred-pedantic groups, filter to top-level groups, and add to
        # the pedantic group
        pedantic_group_names = []
        pedantic_subgroup_names = []
        for group in self.groups.values():
            if group.name != "Pedantic" and group.is_pedantic():
                pedantic_group_names.append(group.name)
                pedantic_subgroup_names += group.child_names

        pedantic_group_names = [
            group_name
            for group_name in pedantic_group_names
            if group_name not in pedantic_subgroup_names
        ]
        pedantic_group.child_names += pedantic_group_names
        pedantic_group.resolve_children(self.groups)

    def get_switch(self, switch_name: str) -> ClangDiagnosticSwitch:
        """
        Get the ClangDiagnosticSwitch with the given name.

        Creates a new ClangDiagnosticSwitch if the given name is new.

        :param switch_name: The name of the ClangDiagnosticSwitch to retrieve.
        :return: the ClangDiagnosticSwitch with the given name.
        """
        try:
            return self.switches[switch_name]
        except KeyError:
            self.switches[switch_name] = ClangDiagnosticSwitch(switch_name)
            return self.switches[switch_name]


def create_comment_text(
    switch: ClangDiagnosticSwitch, args: argparse.Namespace, enabled_by_default: bool
) -> str:
    """
    Return a comment appropriate for the switch and output type.

    :param switch: The switch to generate the comment for.
    :param args: The command line arguments to the script. Controls the form of
        the enabled-by-default comment.
    :param enabled_by_default: If True, the comment is for the enabled-by-default
        section of the output.
    :return: The comment text.
    """
    if switch.is_ignored():
        return " # IGNORED switch"
    if args.unique:
        if switch.is_enabled_by_default():
            return " # Enabled by default."
        if switch.partially_enabled_by_default():
            return " # Partially enabled by default."
    if enabled_by_default and switch.partially_enabled_by_default():
        return " (partial)"

    return ""


def print_references(
    switch: ClangDiagnosticSwitch,
    level: int,
    args: argparse.Namespace,
    enabled_by_default: bool,
) -> None:
    """
    Print all children of switch, indented.

    :param switch: The switch of interest.
    :param level: The indentation level to print the children at. The children
        of top-level switches are at level 1, and each level in the hierarchy
        increments this value by 1.
    :param args: The command line arguments to the script. Controls the form of
        the output.
    :param enabled_by_default: If True, the comment is for the enabled-by-default
        section of the output.
    """
    for child_switch in sorted(switch.get_child_switches(enabled_by_default)):
        print_switch(child_switch, level, args, enabled_by_default)


def print_switch(
    switch: ClangDiagnosticSwitch,
    level: int,
    args: argparse.Namespace,
    enabled_by_default: bool,
) -> None:
    """
    Print the given switch (and its children), indented.

    :param switch: The switch of interest.
    :param level: The indentation level of `switch` in the hierarchy. The top
        level is zero, and each subsequent level increments this value by 1.
    :param args: The command line arguments to the script. Controls the form of
        the output.
    :param enabled_by_default: If True, the comment is for the enabled-by-default
        section of the output.
    """
    comment_string = create_comment_text(switch, args, enabled_by_default)
    flag_type = "-R" if switch.is_remark() else "-W"
    print("# {}{}{}{}".format("  " * level, flag_type, switch.name, comment_string))
    if args.text:
        for item in sorted(switch.get_messages(enabled_by_default)):
            print("#       {}{}".format("  " * level, item))

    print_references(switch, level + 1, args, enabled_by_default)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Clang diagnostics group parser")
    common.add_common_parser_options(parser)
    parser.add_argument(
        "--text", action="store_true", help="Show text of each diagnostic message."
    )
    parser.add_argument(
        "json_path",
        metavar="json-path",
        help="The path to the JSON output from llvm-tblgen.",
    )
    args = parser.parse_args()

    diagnostics = ClangDiagnostics(args.json_path)

    # Print enabled-by-default switches in top-level output
    if args.top_level:
        # Find all switches that are enabled by default and are not children
        # of another switch that is enabled by default.
        all_defaults = {
            s
            for s in diagnostics.switches.values()
            if s.is_enabled_by_default() or s.partially_enabled_by_default()
        }
        children = set(
            chain.from_iterable([s.get_child_switches(True) for s in all_defaults])
        )
        toplevel_defaults = all_defaults - children

        print("# enabled by default:")
        for switch in sorted(toplevel_defaults):
            print_switch(switch, 1, args, enabled_by_default=True)

    for switch in sorted(diagnostics.switches.values()):
        if args.top_level and (
            not switch.is_top_level() or switch.is_enabled_by_default()
        ):
            continue
        comment_string = create_comment_text(switch, args, enabled_by_default=False)
        flag_type = "-R" if switch.is_remark() else "-W"
        print(f"{flag_type}{switch.name}{comment_string}")
        if args.text:
            for item in sorted(switch.get_messages(enabled_by_default=False)):
                print(f"#     {item}")
        if args.unique:
            continue
        print_references(switch, 1, args, enabled_by_default=False)


if __name__ == "__main__":
    main()
