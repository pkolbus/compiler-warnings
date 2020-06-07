#!/usr/bin/env python3
"""
Parser for gcc option files.

Parses the .opt files in the gcc repository for warnings, and outputs relevant
information about the compiler warning options.

For details of the option file format, see the gcc internals documentation at
<https://gcc.gnu.org/onlinedocs/gccint/Option-file-format.html>
"""

import argparse
import enum
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

import antlr4

import common
from GccOptionsLexer import GccOptionsLexer
from GccOptionsListener import GccOptionsListener
from GccOptionsParser import GccOptionsParser


class ParseState(enum.Enum):
    """Possible states for parse_warning_blocks()."""

    NEWLINE = enum.auto()
    OPTION_NAME = enum.auto()
    OPTION_ATTRIBUTES = enum.auto()
    OPTION_HELP = enum.auto()
    FINALIZE = enum.auto()


BORING_OPTIONS = {"Variable", "Enum", "EnumValue"}

NON_WARNING_WS = {"Werror", "Werror=", "Wfatal-errors"}

WARNINGS_NON_W = {"pedantic"}

# Many of these go into common.opt in GCC 4.6 but before that they are aliases:
HIDDEN_WARNINGS: List[Tuple[str, Set[str]]] = [
    # Pedantic is always in but in the options file it is only in 4.8 and later
    # GCC versions.
    ("pedantic", set()),
    ("-all-warnings", {"Wall"}),
    ("-extra-warnings", {"Wextra"}),
    ("-pedantic", {"pedantic"}),
    ("W", {"Wextra"}),
]

# Languages of interest
INTERESTING_LANGUAGES = ["C", "C++", "ObjC", "ObjC++"]

# Tuple containing the option name, display name, option_properties, and help text
# from an option definition record.
OptionDefinition = Tuple[str, Optional[str], str, str]


class OptionFile:
    """
    Represents one gcc options file.

    See https://gcc.gnu.org/onlinedocs/gccint/Option-file-format.html for the
    file format.
    """

    def __init__(self, filename: str) -> None:
        """
        Create a new OptionFile from filename.

        :param filename: Filename to parse.
        """
        self._filename = filename
        self._options: List[OptionDefinition] = []

        # Initialize the parse state
        self._state = ParseState.OPTION_NAME  # Expected content of line
        self._help_lines: List[str] = []
        self._option_name = str()
        self._display_name: Optional[str] = None

        self._parse_file()

    def get_options(self) -> List[OptionDefinition]:
        """:return: The list of OptionDefinition parsed from the file."""
        return self._options

    def _parse_file(self) -> None:
        # Parse option definition records in the file.
        for line in open(self._filename).readlines():
            line = line.rstrip("\n")  # Remove newline
            line = line.split(";", 1)[0]  # Remove trailing comment
            line = line.strip()  # Remove whitespace

            if self._state == ParseState.OPTION_NAME:
                self._parse_option_name(line)
            elif self._state == ParseState.OPTION_ATTRIBUTES:
                self._parse_option_attributes(line)
            elif self._state == ParseState.OPTION_HELP:
                self._parse_option_help(line)

            if self._state == ParseState.FINALIZE:
                self._finalize_option()

        if self._state == ParseState.OPTION_HELP:
            self._finalize_option()

    def _parse_option_attributes(self, line: str) -> None:
        # Parse line as option attributes.
        if line:
            self._option_attributes = line
            self._help_lines = []
            if "Undocumented" in self._option_attributes:
                self._state = ParseState.FINALIZE
            else:
                self._state = ParseState.OPTION_HELP

    def _parse_option_help(self, line: str) -> None:
        # Parse line as option help.
        if line:
            self._help_lines.append(line)
        else:
            self._state = ParseState.FINALIZE

    def _parse_option_name(self, line: str) -> None:
        # Parse line as the option name.
        if line:
            self._option_name = line
            self._state = ParseState.OPTION_ATTRIBUTES

    def _finalize_option(self) -> None:
        # Add the option from the parse state to self._options.
        self._state = ParseState.OPTION_NAME
        if self._option_name in BORING_OPTIONS:
            return

        help_text = " ".join(self._help_lines)
        display_name: Optional[str] = None

        if "\t" in help_text:
            display_name, help_text = help_text.split("\t", maxsplit=1)

        self._options.append(
            (self._option_name, display_name, self._option_attributes, help_text)
        )


def get_parse_tree(string_value: str) -> antlr4.tree.Tree.ParseTree:
    """
    Construct a ParseTree from the given string_value.

    Computing the ParseTree once (instead of once per listener) improves
    performance.

    :param string_value: The input to parse.
    :return: The antlr4 ParseTree for, use in apply_listener().
    """
    string_input = antlr4.InputStream(string_value)
    lexer = GccOptionsLexer(string_input)
    stream = antlr4.CommonTokenStream(lexer)
    parser = GccOptionsParser(stream)
    return parser.optionAttributes()  # type: ignore[no-untyped-call]


def apply_listener(
    listener_input: Union[str, antlr4.tree.Tree.ParseTree],
    listener: GccOptionsListener,
) -> None:
    """
    Walk the ParseTree using the given listener.

    :param listener_input: The data to parse, may be either a string or a
        ParseTree. If it is a string, it is converted into a ParseTree before
        processing.
    :param listener: The GccOptionsListener to be called when walking the
        ParseTree.
    """
    if isinstance(listener_input, str):
        tree = get_parse_tree(listener_input)
    else:
        tree = listener_input
    walker = antlr4.ParseTreeWalker()
    walker.walk(listener, tree)


class AliasAssignmentListener(GccOptionsListener):
    """
    Listener for Alias(opt) expressions.

    There are three forms of interest:
        - Alias(opt)
        - Alias(opt, posarg)
        - Alias(opt, posarg, negarg)

    In the first form, the alias is simply the value of <opt>. In the second and
    third forms, the alias is <opt><posarg> (opt ends with an =).

    The value of negarg is not used as the negative form of the alias is not
    needed.

    >>> listener = AliasAssignmentListener()
    >>> apply_listener("Alias(Wall)", listener)
    >>> listener.alias_name
    'Wall'
    >>> listener = AliasAssignmentListener()
    >>> apply_listener("Alias(Wformat=,1,0)", listener)
    >>> listener.alias_name
    'Wformat=1'
    """

    def __init__(self) -> None:
        """Create an AliasAssignmentListener."""
        self.alias_name: Optional[str] = None
        self._last_name: Optional[str] = None
        self._argument_id = 0

    def enterVariableName(self, ctx: GccOptionsParser.VariableNameContext) -> None:
        """
        Handle entry to the VariableName token.

        Track the variable name, and reset the argument index, for use by
        enterAtom.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        self._last_name = ctx.getText()
        self._argument_id = 0

    def enterArgument(self, ctx: GccOptionsParser.ArgumentContext) -> None:
        """
        Handle entry to the Argument token.

        Track the argument index for use in enterAtom.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        self._argument_id += 1

    def enterAtom(self, ctx: GccOptionsParser.AtomContext) -> None:
        """
        Handle entry to the Atom token.

        If the VariableName is Alias, decide if the Atom is the opt or the
        posarg Argument, and capture into self.alias_name as appropriate.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if self._last_name == "Alias" and self._argument_id == 1:
            self.alias_name = ctx.getText()
        if self._last_name == "Alias" and self._argument_id == 2:
            self.alias_name += ctx.getText()

    def exitTrailer(self, ctx: GccOptionsParser.TrailerContext) -> None:
        """
        Handle exit from the Trailer token.

        Forget the variable name.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        self._last_name = None


class LanguagesEnabledListener(GccOptionsListener):
    """
    Listener for LangEnabledBy(languagelist,warningflags) expressions.

    There are two forms:

    - LangEnabledBy(language-list,other-opt)
    - LangEnabledBy(language-list,other-opt,posarg,negarg)

    "other-opt" indicate the other options that cause this warning to be
    enabled. This can be a single item or a list of || separated options.

    If posarg is present, then it is considered the warning value when other-opt
    is used. This can have two forms:

    - a condition, which means that the warning gets a value of 1
    - a number, which means the warning gets the given number.

    A simple warning flag, enabled when -Wall is specified:

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall,0,1)", listener)
    >>> listener.flags
    ['Wall']

    A simple warning flag, enabled by -Wall99:

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall99,0,1)", listener)
    >>> listener.flags
    ['Wall99']

    A simple warning flag, enabled by -Wall or -Wc++-compat:

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall || Wc++-compat)", listener)
    >>> listener.flags
    ['Wall', 'Wc++-compat']

    Use of comparison in posarg implies that the var is associated with the
    enabled-by option. If true, posarg evaluates to 1. So the following example
    would indicate the warning is enabled by -Wformat=2:

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wformat=,v >= 2,0)", listener)
    >>> listener.flags
    ['Wformat=2']
    >>> listener.arg
    '1'

    Use of a number in posarg means the warning flag gets that value when the
    enabled-by option is present. If this were a record for Wfoo, this would
    be interpreted as "-Wall enables -Wfoo=1". (Or simply -Wfoo, since a zero
    or one is interpreted as a boolean:

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall,1,0)", listener)
    >>> listener.flags
    ['Wall']
    >>> listener.arg
    '1'

    Use of a number in posarg means the warning flag gets that value when the
    enabled-by option is present. If this were a record for Wfoo, this would
    be interpreted as "-Wall enables -Wfoo=2":

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall,2,0)", listener)
    >>> listener.flags
    ['Wall']
    >>> listener.arg
    '2'
    """

    def __init__(self) -> None:
        """Create a LanguagesEnabledListener."""
        self._last_name: Optional[str] = None
        self._argument_id = 0
        self._flag_name = str()
        self._enabled_by_comparison = False
        self.flags: List[str] = []
        self.arg: Optional[str] = None

    def enterVariableName(self, ctx: GccOptionsParser.VariableNameContext) -> None:
        """
        Handle entry to the VariableName token.

        Track the variable name, and reset the argument index, for use by
        enterAtom.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if ctx.getText() == "LangEnabledBy":
            self._last_name = "LangEnabledBy"
            self._argument_id = 0

    def enterArgument(self, ctx: GccOptionsParser.ArgumentContext) -> None:
        """
        Handle entry to the Argument token.

        Track the argument index for use in enterAtom.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        self._argument_id += 1

    def enterCompOp(self, ctx: GccOptionsParser.CompOpContext) -> None:
        """
        Handle entry to the CompOp token.

        If this is the 3rd argument of the LangEnabledBy expression, track that
        the option is conditionally enabled (if a comparison is true).

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if self._last_name == "LangEnabledBy" and self._argument_id == 3:
            self._enabled_by_comparison = True

    def enterAtom(self, ctx: GccOptionsParser.AtomContext) -> None:
        """
        Handle entry to an Atom token.

        When parsing the second argument of LangEnabledBy (other-opt),
        capture the atom as the "other" flag name.

        When parsing the third argument of LangEnabledBy (posarg):
            - if the Atom is the numeric value for a CompOp, edit the "other"
              flag name to include the value.
            - if the Atom is a simple number, track the number as the value
              used with the warning.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if self._last_name == "LangEnabledBy":
            if self._argument_id == 2:
                self._flag_name = ctx.getText()
                self.flags.append(self._flag_name)
            elif self._argument_id == 3 and ctx.getText().isdigit():
                if self._enabled_by_comparison:
                    # Argument form is var >= N, so is enabled by -Wflag=N
                    self.flags.remove(self._flag_name)
                    self.flags.append(self._flag_name + ctx.getText())
                    # When -Wflag=N, var >= N evaluates to 1
                    self.arg = "1"
                else:
                    # Argument form is N, so flags enables -Wthis=N
                    self.arg = ctx.getText()

    def exitTrailer(self, ctx: GccOptionsParser.TrailerContext) -> None:
        """
        Handle exit from the Trailer token.

        Forget the variable name.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        self._last_name = None


class LanguagesListener(GccOptionsListener):
    """
    Listens for applicable languages (C C++ ObjC ObjC++).

    >>> listener = LanguagesListener()
    >>> apply_listener("C C++ Enum", listener)
    >>> sorted(listener.languages)
    ['C', 'C++']
    >>> listener = LanguagesListener()
    >>> apply_listener("C++", listener)
    >>> sorted(listener.languages)
    ['C++']
    >>> listener = LanguagesListener()
    >>> apply_listener("LTO C ObjC C++ Enum", listener)
    >>> sorted(listener.languages)
    ['C', 'C++', 'ObjC']
    """

    def __init__(self) -> None:
        """Create a LanguagesListener."""
        self.languages: Set[str] = set()

    def enterVariableName(self, ctx: GccOptionsParser.VariableNameContext) -> None:
        """
        Handle entry to the VariableName token.

        If the variable name is a language of interest, add it to the list.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if ctx.getText() in INTERESTING_LANGUAGES:
            self.languages.add(ctx.getText())


class EnabledByListener(GccOptionsListener):
    """
    Listens for EnabledBy(warningflag) expressions.

    >>> listener = EnabledByListener()
    >>> apply_listener("EnabledBy(Wextra)", listener)
    >>> listener.enabled_by
    'Wextra'
    """

    def __init__(self) -> None:
        """Create an EnabledByListener."""
        self._last_name: Optional[str] = None
        self.enabled_by: Optional[str] = None

    def enterVariableName(self, ctx: GccOptionsParser.VariableNameContext) -> None:
        """
        Handle entry to the VariableName token.

        Track the variable name for use by enterAtom.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if ctx.getText() == "EnabledBy":
            self._last_name = "EnabledBy"

    def enterAtom(self, ctx: GccOptionsParser.AtomContext) -> None:
        """
        Handle entry to an Atom token.

        If the variable name is EnabledBy, capture the atom as the "other" flag
        name.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if self._last_name == "EnabledBy":
            self.enabled_by = ctx.getText()

    def exitTrailer(self, ctx: GccOptionsParser.TrailerContext) -> None:
        """
        Handle exit from the Trailer token.

        Forget the variable name.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        self._last_name = None


class DefaultsListener(GccOptionsListener):
    """
    Listens to attributes to infer 'enabled by default' status.

    This attempts to infer whether an option is enabled by default by use of
    idioms. The implementation favors type II errors (missing an enabled-by-
    default case) over type I errors (marking a flag as enabled-by-default
    when it is not).

    - Presence of Enum, Host_Wide_Int, Joined, or UInteger indicates this is not
      an on-off switch
    - A value of '1' or '-1' typically means on by default
    - A value of '0' typically means off by default
    - Another numeric value typically signifies more complex logic is used,
      such as for trigraphs.
    - A non-numeric value is a configure symbol, so this script cannot be sure.

    >>> listener = DefaultsListener()
    >>> apply_listener("Init(1)", listener)
    >>> listener.isEnabledByDefault()
    True
    >>> listener = DefaultsListener()
    >>> apply_listener("Init(-1)", listener)
    >>> listener.isEnabledByDefault()
    True
    >>> listener = DefaultsListener()
    >>> apply_listener("Init(0)", listener)
    >>> listener.isEnabledByDefault()
    False
    >>> listener = DefaultsListener()
    >>> apply_listener("Init(2)", listener)
    >>> listener.isEnabledByDefault()
    False
    >>> listener = DefaultsListener()
    >>> apply_listener("Init(COND)", listener)
    >>> listener.isEnabledByDefault()
    False
    >>> listener = DefaultsListener()
    >>> apply_listener("UInteger Init(1)", listener)
    >>> listener.isEnabledByDefault()
    False
    >>> listener = DefaultsListener()
    >>> apply_listener("Init(1) Enum", listener)
    >>> listener.isEnabledByDefault()
    False
    >>> listener = DefaultsListener()
    >>> apply_listener("Init(-1) Joined", listener)
    >>> listener.isEnabledByDefault()
    False
    >>> listener = DefaultsListener()
    >>> apply_listener("Host_Wide_Int Init(1)", listener)
    >>> listener.isEnabledByDefault()
    False
    """

    def __init__(self) -> None:
        """Create a DefaultsListener."""
        self._last_name: Optional[str] = None
        self._init_value: Optional[str] = None
        self._is_boolean = True

    def enterVariableName(self, ctx: GccOptionsParser.VariableNameContext) -> None:
        """
        Handle entry to the VariableName token.

        Track the variable name for use by enterAtom. If the variable name
        indicates the warning is not on-off, mark the warning as such.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if ctx.getText() == "Init":
            self._last_name = "Init"
        elif ctx.getText() in ("Enum", "Host_Wide_Int", "Joined", "UInteger"):
            self._is_boolean = False

    def enterAtom(self, ctx: GccOptionsParser.AtomContext) -> None:
        """
        Handle entry to an Atom token.

        If the variable name is Init, capture the atom as the initial value of
        the flag.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if self._last_name == "Init":
            self._init_value = ctx.getText()

    def exitTrailer(self, ctx: GccOptionsParser.TrailerContext) -> None:
        """
        Handle exit from the Trailer token.

        Forget the variable name.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        self._last_name = None

    def isEnabledByDefault(self) -> bool:
        """:return: True if the warning is enabled-by-default, False otherwise."""
        return self._is_boolean and self._init_value in ("1", "-1")


class DeprecationsListener(GccOptionsListener):
    """
    Listens to attributes to infer deprecation status.

    In gcc 9 and earlier, the attribute of interest is "Deprecated". This was
    changed to "WarnRemoved" for gcc 10.

    >>> listener = DeprecationsListener()
    >>> apply_listener("Deprecated", listener)
    >>> listener.isDeprecated()
    True
    >>> listener = DeprecationsListener()
    >>> apply_listener("Init(-1)", listener)
    >>> listener.isDeprecated()
    False
    >>> listener = DeprecationsListener()
    >>> apply_listener("Deprecated Enum", listener)
    >>> listener.isDeprecated()
    True
    >>> listener = DeprecationsListener()
    >>> apply_listener("WarnRemoved", listener)
    >>> listener.isDeprecated()
    True
    """

    def __init__(self) -> None:
        """Create a DeprecationsListener."""
        self._deprecated = False

    def enterVariableName(self, ctx: GccOptionsParser.VariableNameContext) -> None:
        """
        Handle entry to the VariableName token.

        If the variable name indicates deprecation, track the warning as such.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if ctx.getText() in ("Deprecated", "WarnRemoved"):
            self._deprecated = True

    def isDeprecated(self) -> bool:
        """:return: True if the warning is deprecated, False otherwise."""
        return self._deprecated


class IntegerRangeListener(GccOptionsListener):
    """
    Searches for IntegerRange attribute.

    The IntegerRange indicates the allowed values for a warning option. The
    range is closed (both the min and max values are allowed).

    >>> listener = IntegerRangeListener()
    >>> apply_listener("C C++ Warning IntegerRange(1, 3)", listener)
    >>> listener.has_range()
    True
    >>> listener.get_range()
    (1, 3)
    >>> listener = IntegerRangeListener()
    >>> apply_listener("C C++ Warning", listener)
    >>> listener.has_range()
    False
    """

    def __init__(self) -> None:
        """Create an IntegerRangeListener."""
        self._atoms: List[int] = []
        self._variable_name = None

    def enterVariableName(self, ctx: GccOptionsParser.VariableNameContext) -> None:
        """
        Handle entry to the VariableName token.

        Track the variable name for use by enterAtom. On entry to IntegerRange,
        ensure the list of collected atoms is empty.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        self._variable_name = ctx.getText()
        if self._variable_name == "IntegerRange":
            self._atoms.clear()

    def enterAtom(self, ctx: GccOptionsParser.AtomContext) -> None:
        """
        Handle entry to an Atom token.

        If the variable name is IntegerRange, capture the atom as a bound on the
        range.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if self._variable_name == "IntegerRange":
            self._atoms.append(int(ctx.getText()))

    def exitTrailer(self, ctx: GccOptionsParser.TrailerContext) -> None:
        """
        Handle exit from the Trailer token.

        Forget the variable name.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        self._variable_name = None

    def has_range(self) -> bool:
        """:return: True if the warning has a range, False otherwise."""
        return len(self._atoms) == 2

    def get_range(self) -> Tuple[int, ...]:
        """:return: the allowed range, as a tuple."""
        return tuple(self._atoms)


class WarningOptionListener(GccOptionsListener):
    """
    Listener for expressions indicating a warning option.

    There are two forms of interest:

    - A VariableName of Warning
    - A Var(var), where var starts with `warn_`

    >>> listener = WarningOptionListener()
    >>> apply_listener("C C++ Warning", listener)
    >>> listener.is_warning
    True

    Search for warn_* variables:

    >>> listener = WarningOptionListener()
    >>> apply_listener("C C++ Var(warn_sign_conversion) Init(-1)", listener)
    >>> listener.is_warning
    True
    """

    def __init__(self) -> None:
        """Create a WarningOptionListener."""
        self._last_name: Optional[str] = None
        self.is_warning = False

    def enterVariableName(self, ctx: GccOptionsParser.VariableNameContext) -> None:
        """
        Handle entry to the VariableName token.

        If the variable name is Warning, mark the warning as such. Otherwise,
        track the variable name for use by enterAtom.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if ctx.getText() == "Warning":
            self.is_warning = True
        elif ctx.getText() == "Var":
            self._last_name = "Var"

    def enterAtom(self, ctx: GccOptionsParser.AtomContext) -> None:
        """
        Handle entry to the Atom token.

        Detect Var(warn_*) and set the is_warning flag if detected.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if self._last_name != "Var":
            return
        if ctx.getText().startswith("warn_"):
            self.is_warning = True

    def exitTrailer(self, ctx: GccOptionsParser.TrailerContext) -> None:
        """
        Handle exit from the Trailer token.

        Forget the variable name.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        self._last_name = None


class DummyWarningListener(GccOptionsListener):
    """
    Checks if switch does nothing.

    This is defined by the "Ignore" attribute.

    >>> listener = DummyWarningListener()
    >>> apply_listener("C C++ Warning Ignore", listener)
    >>> listener.is_dummy
    True
    """

    def __init__(self) -> None:
        """Create a DummyWarningListener."""
        self.is_dummy = False

    def enterVariableName(self, ctx: GccOptionsParser.VariableNameContext) -> None:
        """
        Handle entry to the VariableName token.

        If the variable name is Ignore, mark the warning as a dummy.

        :param ctx: The rule invocation context. Contains relevant information
            about the rule from parsing.
        """
        if ctx.getText() == "Ignore":
            self.is_dummy = True


class GccOption:
    """Represents one option parsed from the input file(s)."""

    _WARN_REMOVED_HELP = "This option is deprecated and has no effect."

    def __init__(
        self, name: str, aliases: Optional[Set[str]] = None, warning: bool = False
    ) -> None:
        """
        Create a GccOption from the given data.

        :param name: The name of the option.
        :param aliases: Names of any aliases.
        :param warning: If True, this option is known to be a warning.
        """
        self._aliases = aliases if aliases else set()
        self._children: Set[str] = set()
        self._default = False
        self._deprecated = False
        self._display_name: Optional[str] = None
        self._dummy = False
        self._help_text = str()
        self._languages: Set[str] = set()
        self._name = name
        self._warning = warning

    def __eq__(self, other: object) -> bool:
        """
        Return True if self and other are equal.

        Two GccOption are equal if they have the same name.

        :param other: The object to compare for equality.
        :return: NotImplemented if `other` is _not_ a GccOption, True if self
            and other have the same name, or False otherwise.
        """
        if not isinstance(other, GccOption):
            return NotImplemented

        return self._name == other._name

    def __lt__(self, other: object) -> bool:
        """
        Return True if self should be before other in a sorted list.

        Two GccOption should be sorted by name, case-insensitive.

        :param other: The object to compare against.
        :return: NotImplemented if `other` is _not_ a GccOption, True if the
            name of self is less than the name of other, case-insensitive,
            or False otherwise.
        """
        if not isinstance(other, GccOption):
            return NotImplemented

        return self._name.lower() < other._name.lower()

    def add_alias(self, name: str) -> None:
        """
        Add the given name as an alias.

        :param name: The alias to add.
        """
        self._aliases.add(name)

    def add_child(self, name: str) -> None:
        """
        Add the given name as a a child option.

        :param name: The name of the chid option to add.
        """
        self._children.add(name)

    def get_aliases(self) -> List[str]:
        """:return: the list of aliases, sorted case-insensitively."""
        return sorted(self._aliases, key=lambda x: x.lower())

    def get_children(self) -> Set[str]:
        """:return: the list of child options."""
        return self._children

    def get_comment_text(self) -> str:
        """
        Get the comment to print for this option.

        The comment indicates the following, as applicable:
            - deprecated
            - enabled by default
            - applies to a subset of all interesting languages

        If none of these conditions are applicable, an empty string is returned.

        :return: The comment text.
        """
        has_comment = False
        comment = " #"

        if self._deprecated:
            comment += " Deprecated."
            has_comment = True

        if self._default:
            comment += " Enabled by default."
            has_comment = True

        if self._languages and len(self._languages) != len(INTERESTING_LANGUAGES):
            comment += " Applies to " + ",".join(sorted(self._languages))
            has_comment = True

        if has_comment:
            return comment
        else:
            return ""

    def get_display_name(self) -> str:
        """:return: the display name for the option."""
        return self._display_name if self._display_name else "-" + self._name

    def get_dummy_text(self) -> str:
        """
        Get the dummy comment to print for this option.

        :return: a comment if the option is a dummy switch, an empty string
            otherwise.
        """
        return " # DUMMY switch" if self._dummy else str()

    def get_help_text(self) -> str:
        """:return: the help text."""
        if self._help_text:
            return self._help_text
        if self._deprecated:
            return GccOption._WARN_REMOVED_HELP
        return self._help_text

    def get_name(self) -> str:
        """:return: the option name."""
        return self._name

    def is_default(self) -> bool:
        """:return: True if the option is enabled by default, False otherwise."""
        return self._default

    def is_warning(self) -> bool:
        """:return: True if the option is a warning flag, False otherwise."""
        return self._warning

    def set_default(self) -> None:
        """Set the option as enabled by default."""
        self._default = True

    def set_deprecated(self) -> None:
        """Set the option as deprecated."""
        self._deprecated = True

    def set_display_name(self, display_name: str) -> None:
        """
        Set the display name of the option.

        :param display_name: The alternate display name to use. If this does not
            start with a hyphen, one is added.
        """
        if display_name.startswith("-"):
            self._display_name = display_name
        else:
            self._display_name = "-" + display_name

    def set_dummy(self) -> None:
        """Set the option as a dummy."""
        self._dummy = True

    def set_help_text(self, help_text: str) -> None:
        """
        Set the help text for the option.

        :param help_text: The help text to use.
        """
        self._help_text = help_text

    def set_warning(self) -> None:
        """Set the option as a warning."""
        self._warning = True

    def update_languages(self, languages: Iterable[str]) -> None:
        """
        Add the given languages as applicable.

        :param languages: The languages to add.
        """
        self._languages.update(languages)


class GccDiagnostics:
    """A collection of GccOption."""

    def __init__(self) -> None:
        """Create a new collection."""
        self._options: Dict[str, GccOption] = {}

    def get(self, option_name: str) -> GccOption:
        """
        Return the GccOption with the given name.

        If the given name is new, create a new GccOption.

        :param option_name: The name of the GccOption to retrieve.
        :return: The GccOption with the given name.
        """
        try:
            return self._options[option_name]
        except KeyError:
            self._options[option_name] = GccOption(option_name)
            return self._options[option_name]

    def parse_options_file(self, filename: str) -> None:
        """
        Parse an options file and add/update options from the file.

        :param filename: Filename to parse.
        """
        for block in OptionFile(filename).get_options():
            self._parse_option(block)

    def _parse_option(self, option_definition: OptionDefinition) -> None:
        # Parse one option_definition.

        # Unpack the tuple
        option_name, display_name, option_arguments, help_text = option_definition

        # Get the underlying option
        option = self.get(option_name)

        if display_name:
            option.set_display_name(display_name)

        if help_text:
            option.set_help_text(help_text)
        else:
            # Attempt to retrieve from previous instance
            help_text = option.get_help_text()

        parse_tree = get_parse_tree(option_arguments)

        # Parse and apply warning indications
        warning_option = WarningOptionListener()
        apply_listener(parse_tree, warning_option)
        if warning_option.is_warning or could_be_warning(option_name):
            option.set_warning()

        # Parse and apply dummy indications
        dummy_option = DummyWarningListener()
        apply_listener(parse_tree, dummy_option)
        if dummy_option.is_dummy:
            option.set_dummy()

        # Parse and apply IntegerRange, if the option takes a value and doesn't
        # have a more human-readable display form.
        if option_name[-1:] == "=" and not display_name:
            integer_range_listener = IntegerRangeListener()
            apply_listener(parse_tree, integer_range_listener)
            if integer_range_listener.has_range():
                min_value, max_value = integer_range_listener.get_range()
                option.set_display_name(
                    "-{}<{}..{}>".format(option_name, min_value, max_value)
                )

        # Parse and apply LangEnabledBy
        # - If option is enabled by another, option is a child of that one.
        # - LangEnabledBy can identify possible values for qualified options.
        language_enablers = LanguagesEnabledListener()
        apply_listener(parse_tree, language_enablers)
        qualified_option = option_name
        if qualified_option[-1:] == "=" and language_enablers.arg is not None:
            qualified_option += language_enablers.arg
            if help_text:
                self.get(qualified_option).set_help_text(help_text)
        for flag in language_enablers.flags:
            other_option = self.get(flag)
            other_option.add_child(qualified_option)
            other_option.set_warning()

        # Parse and apply EnabledBy
        # - If this option is enabled by another, this option is a child of the
        #   other.
        flag_enablers = EnabledByListener()
        apply_listener(parse_tree, flag_enablers)
        if flag_enablers.enabled_by:
            flag = flag_enablers.enabled_by
            self.get(flag).add_child(option_name)

        # Parse and apply enabled-by-default
        bydefault_option = DefaultsListener()
        apply_listener(parse_tree, bydefault_option)
        if bydefault_option.isEnabledByDefault():
            option.set_default()

        # Parse and apply deprecation
        deprecation_option = DeprecationsListener()
        apply_listener(parse_tree, deprecation_option)
        if deprecation_option.isDeprecated():
            option.set_deprecated()

        # Parse and apply aliases
        alias_enablers = AliasAssignmentListener()
        apply_listener(parse_tree, alias_enablers)
        if alias_enablers.alias_name is not None:
            option.add_alias(alias_enablers.alias_name)

        # Parse and apply applicable languages
        languages_listener = LanguagesListener()
        apply_listener(parse_tree, languages_listener)
        option.update_languages(languages_listener.languages)

    def _has_parent(self, option: GccOption) -> bool:
        for parent in self._options.values():
            if option.get_name() in parent.get_children():
                return True

        return False

    def is_top_level(self, option: GccOption) -> bool:
        """
        Return whether or not the option is top-level.

        An option is top-level if it is not an alias, is not enabled by default,
        and is not the child of any other option.

        :param option: The option of interest.
        :return: True if the given option is top-level, False otherwise.
        """
        return (
            not option.get_aliases()
            and not option.is_default()
            and not self._has_parent(option)
        )

    @classmethod
    def hidden_options(cls) -> "GccDiagnostics":
        """:return: a GccDiagnostics collection containing hidden warnings."""
        options = GccDiagnostics()
        for switch, aliases in HIDDEN_WARNINGS:
            options._options[switch] = GccOption(switch, aliases=aliases, warning=True)
        return options

    def get_children(self, option: GccOption) -> List[GccOption]:
        """
        Return the children of the given option.

        :param option: The GccOption of interest.
        :return: the direct children of the given option, sorted by name,
            case-insensitive.
        """
        option_names = [self.get(option_name) for option_name in option.get_children()]
        return sorted(option_names, key=lambda x: x.get_name().lower())

    def get_all_warnings(self) -> List[GccOption]:
        """:return: the list of warnings, sorted by name."""
        return sorted(
            switch for switch in self._options.values() if switch.is_warning()
        )

    def get_default_warnings(self) -> List[GccOption]:
        """:return: the list of enabled-by-default warnings, sorted by name."""
        return sorted(
            option
            for option in self._options.values()
            if option.is_warning() and option.is_default()
        )

    def _is_warning(self, option: GccOption) -> bool:
        """
        Return whether or not the given option is a warning.

        :param option: The GccOption of interest.
        :return: True if option is a warning or if any of its aliases are
            warnings; False otherwise.
        """
        if option.is_warning():
            return True

        for alias in option.get_aliases():
            if self.get(alias).is_warning():
                return True

        return False


def print_option(
    all_options: GccDiagnostics, option: GccOption, level: int, args: argparse.Namespace
) -> None:
    """
    Print detail of the given option (and all of its children).

    :param option: The GccOption to print.
    :param level: The indentation level of `option` in the hierarchy. The top
        level is zero, and each subsequent level increments this value by 1.
    :param args: The command-line arguments. These control the format of the
        report.
    :param all_options: The GccDiagnostics collection to report on.
    """
    if level:
        print("#  " + "  " * level + option.get_display_name())
    else:
        print(option.get_display_name())
    if args.text and option.get_help_text():
        print("#  " + "  " * (level + 2), option.get_help_text())
    for child in all_options.get_children(option):
        print_option(all_options, child, level + 1, args)


def print_default_options(
    all_options: GccDiagnostics, args: argparse.Namespace
) -> None:
    """
    Print detail of the warnings that are enabled by default.

    :param args: The command-line arguments. These control the format of the
        report.
    :param all_options: The GccDiagnostics collection to report on.
    """
    defaults = all_options.get_default_warnings()
    if not defaults:
        return

    print("# enabled by default:")
    for option in defaults:
        print_option(all_options, option, 1, args)


def could_be_warning(option_name: str) -> bool:
    """
    Return whether or not option_name could be a warning.

    Warning options start with W, unless the name contains a comma or is one of
    a few exceptions (such as Werror).

    :param option_name: The option name of interest.
    :return: True if option_name could be a warning, False otherwise.
    """
    if "," in option_name:
        return False
    if option_name in NON_WARNING_WS:
        return False

    return option_name.startswith("W")


def print_warning_flags(args: argparse.Namespace, all_options: GccDiagnostics) -> None:
    """
    Print a report detailing the warning flags.

    :param args: The command-line arguments. These control the format of the
        report.
    :param all_options: The GccDiagnostics collection to report on.
    """
    if args.top_level:
        # Print a group that has all enabled-by-default warnings together
        print_default_options(all_options, args)

    for option in all_options.get_all_warnings():

        dummy_text = option.get_dummy_text()
        if args.unique:
            comment_text = option.get_comment_text()
            print(option.get_display_name() + dummy_text + comment_text)
            continue

        if args.top_level and not all_options.is_top_level(option):
            continue

        sorted_aliases = option.get_aliases()
        if sorted_aliases:
            print(
                "{} = -{}{}".format(
                    option.get_display_name(), ", -".join(sorted_aliases), dummy_text
                )
            )
        else:
            print(option.get_display_name() + dummy_text)

        if args.text and option.get_help_text():
            print("#     {}".format(option.get_help_text()))

        for child in all_options.get_children(option):
            print_option(all_options, child, 1, args)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Parses GCC option files for warning options."
    )
    common.add_common_parser_options(parser)
    parser.add_argument(
        "--text", action="store_true", help="Show help text of each diagnostic.",
    )
    parser.add_argument("option_file", metavar="option-file", nargs="+")
    args = parser.parse_args()

    all_options = GccDiagnostics.hidden_options()

    for filename in args.option_file:
        all_options.parse_options_file(filename)

    print_warning_flags(args, all_options)


if __name__ == "__main__":
    main()
