#!/usr/bin/env python3

import argparse
import antlr4
import common
import enum
import io
import sys
from typing import Iterable, List, Set

import GccOptionsLexer
import GccOptionsListener
import GccOptionsParser


class ParseState(enum.Enum):
    NEWLINE = enum.auto()
    OPTION_NAME = enum.auto()
    OPTION_ATTRIBUTES = enum.auto()
    OPTION_HELP = enum.auto()
    FINALIZE = enum.auto()


BORING_OPTIONS = {"Variable", "Enum", "EnumValue"}

NON_WARNING_WS = {"Werror", "Werror=", "Wfatal-errors"}

WARNINGS_NON_W = {"pedantic"}

# Many of these go into common.opt in GCC 4.6 but before that they are aliases:
HIDDEN_WARNINGS = [
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


def parse_warning_blocks(fp: io.TextIOBase):
    """
    Parse option definition records from fp.

    Parses option definition records and returns a list of 4-tuples containing
    the option name, display name, option_properties, and help text.

    See https://gcc.gnu.org/onlinedocs/gccint/Option-file-format.html for the
    file format.
    """
    blocks = []
    state = ParseState.OPTION_NAME  # Expected content of line
    help_lines = []
    option_name = None
    for line in fp.readlines():
        line = line.rstrip("\n")  # Remove newline
        line = line.split(";", 1)[0]  # Remove trailing comment
        line = line.strip()  # Remove whitespace

        if state == ParseState.OPTION_NAME:
            if line:
                option_name = line
                state = ParseState.OPTION_ATTRIBUTES
        elif state == ParseState.OPTION_ATTRIBUTES:
            if line:
                option_attributes = line
                help_lines = []
                if "Undocumented" in option_attributes:
                    state = ParseState.FINALIZE
                else:
                    state = ParseState.OPTION_HELP
        elif state == ParseState.OPTION_HELP:
            if line:
                help_lines.append(line)
            else:
                state = ParseState.FINALIZE

        if state == ParseState.FINALIZE:
            state = ParseState.OPTION_NAME
            if option_name in BORING_OPTIONS:
                continue
            help_text = " ".join(help_lines)
            if "\t" in help_text:
                display_name, help_text = help_text.split("\t", maxsplit=1)
            else:
                display_name = None
            blocks.append((option_name, display_name, option_attributes, help_text))

    if state == ParseState.OPTION_HELP and option_name not in BORING_OPTIONS:
        help_text = " ".join(help_lines)
        if "\t" in help_text:
            display_name, help_text = help_text.split("\t", maxsplit=1)
        else:
            display_name = None
        blocks.append((option_name, display_name, option_attributes, help_text))

    return blocks


def get_parse_tree(string_value: str):
    string_input = antlr4.InputStream(string_value)
    lexer = GccOptionsLexer.GccOptionsLexer(string_input)
    stream = antlr4.CommonTokenStream(lexer)
    parser = GccOptionsParser.GccOptionsParser(stream)
    return parser.optionAttributes()


def apply_listener(input, listener: GccOptionsListener.GccOptionsListener):
    if isinstance(input, str):
        tree = get_parse_tree(input)
    else:
        tree = input
    walker = antlr4.ParseTreeWalker()
    walker.walk(listener, tree)


class VariableAssignmentListener(GccOptionsListener.GccOptionsListener):
    """
    >>> listener = VariableAssignmentListener()
    >>> apply_listener("Var(varname)", listener)
    >>> listener.variable_name
    'varname'
    """

    def __init__(self):
        self.variable_name = None
        self._last_name = None

    def enterVariableName(self, ctx):
        self._last_name = ctx.getText()

    def enterAtom(self, ctx):
        if self._last_name == "Var":
            self.variable_name = ctx.getText()

    def exitTrailer(self, ctx):
        self._last_name = None


class AliasAssignmentListener(GccOptionsListener.GccOptionsListener):
    """
    >>> listener = AliasAssignmentListener()
    >>> apply_listener("Alias(Wall)", listener)
    >>> listener.alias_name
    'Wall'
    >>> listener = AliasAssignmentListener()
    >>> apply_listener("Alias(Wformat=,1,0)", listener)
    >>> listener.alias_name
    'Wformat=1'
    """

    def __init__(self):
        self.alias_name = None
        self._last_name = None
        self._argument_id = 0

    def enterVariableName(self, ctx):
        self._last_name = ctx.getText()
        self._argument_id = 0

    def enterArgument(self, ctx):
        self._argument_id += 1

    def enterAtom(self, ctx):
        if self._last_name == "Alias" and self._argument_id == 1:
            self.alias_name = ctx.getText()
        if self._last_name == "Alias" and self._argument_id == 2:
            self.alias_name += ctx.getText()

    def exitTrailer(self, ctx):
        self._last_name = None


class LanguagesEnabledListener(GccOptionsListener.GccOptionsListener):
    """
    Listens to LangEnabledBy(languagelist,warningflags) function calls

    There are two forms:
        - LangEnabledBy(languagelist,warningflags)
        - LangEnabledBy(languagelist,warningflags,posarg,negarg)

    "warningflags" are the most interesting ones, as it means that this warning
    is enabled by another flag.

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall,0,1)", listener)
    >>> listener.flags
    ['Wall']

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall99,0,1)", listener)
    >>> listener.flags
    ['Wall99']

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall || Wc++-compat)", listener)
    >>> listener.flags
    ['Wall', 'Wc++-compat']

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wformat=,v >= 2,0)", listener)
    >>> listener.flags
    ['Wformat=2']
    >>> listener.arg
    '1'

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall,1,0)", listener)
    >>> listener.flags
    ['Wall']
    >>> listener.arg
    '1'

    >>> listener = LanguagesEnabledListener()
    >>> apply_listener("LangEnabledBy(C C++,Wall,2,0)", listener)
    >>> listener.flags
    ['Wall']
    >>> listener.arg
    '2'
    """

    def __init__(self):
        self._last_name = None
        self._argument_id = 0
        self._flag_name = None
        self._enabled_by_comparison = False
        self.flags = []
        self.arg = None

    def enterVariableName(self, ctx):
        if ctx.getText() == "LangEnabledBy":
            self._last_name = "LangEnabledBy"
            self._argument_id = 0

    def enterArgument(self, ctx):
        self._argument_id += 1

    def enterCompOp(self, ctx):
        if self._last_name == "LangEnabledBy" and self._argument_id == 3:
            self._enabled_by_comparison = True

    def enterAtom(self, ctx):
        if self._last_name == "LangEnabledBy":
            if self._argument_id == 2:
                self._flag_name = ctx.getText()
                self.flags.append(self._flag_name)
            elif self._argument_id == 3 and ctx.getText().isdigit():
                if self._enabled_by_comparison:
                    # Argument form is var >= N, so is enabled by-Wflag=N
                    self.flags.remove(self._flag_name)
                    self.flags.append(self._flag_name + ctx.getText())
                    # When -Wflag=N, var >= N evaluates to 1
                    self.arg = "1"
                else:
                    # Argument form is N, so flags enables -Wthis=N
                    self.arg = ctx.getText()

    def exitTrailer(self, ctx):
        self._last_name = None


class LanguagesListener(GccOptionsListener.GccOptionsListener):
    """
    Listens for applicable languages (C C++ ObjC)

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

    def __init__(self):
        self.languages = set()

    def enterVariableName(self, ctx):
        if ctx.getText() in INTERESTING_LANGUAGES:
            self.languages.add(ctx.getText())


class EnabledByListener(GccOptionsListener.GccOptionsListener):
    """
    Listens to EnabledBy(warningflag) function calls

    >>> listener = EnabledByListener()
    >>> apply_listener("EnabledBy(Wextra)", listener)
    >>> listener.enabled_by
    'Wextra'
    """

    def __init__(self):
        self._last_name = None
        self.enabled_by = None

    def enterVariableName(self, ctx):
        if ctx.getText() == "EnabledBy":
            self._last_name = "EnabledBy"

    def enterAtom(self, ctx):
        if self._last_name == "EnabledBy":
            self.enabled_by = ctx.getText()

    def exitTrailer(self, ctx):
        self._last_name = None


class DefaultsListener(GccOptionsListener.GccOptionsListener):
    """
    Listens to attributes to infer 'enabled by default' status

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

    def __init__(self):
        self._last_name = None
        self._init_value = None
        self._is_boolean = True

    def enterVariableName(self, ctx):
        if ctx.getText() == "Init":
            self._last_name = "Init"
        elif ctx.getText() in ("Enum", "Host_Wide_Int", "Joined", "UInteger"):
            self._is_boolean = False

    def enterAtom(self, ctx):
        if self._last_name == "Init":
            self._init_value = ctx.getText()

    def exitTrailer(self, ctx):
        self._last_name = None

    def isEnabledByDefault(self):
        return self._is_boolean and self._init_value in ("1", "-1")


class DeprecationsListener(GccOptionsListener.GccOptionsListener):
    """
    Listens to attributes to infer deprecation status

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

    def __init__(self):
        self._deprecated = False

    def enterVariableName(self, ctx):
        if ctx.getText() in ("Deprecated", "WarnRemoved"):
            self._deprecated = True

    def isDeprecated(self):
        return self._deprecated


class IntegerRangeListener(GccOptionsListener.GccOptionsListener):
    """
    Searches for IntegerRange attribute.

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

    def __init__(self):
        self._atoms: List[int] = []
        self._variable_name = None

    def enterVariableName(self, ctx):
        self._variable_name = ctx.getText()
        if self._variable_name == "IntegerRange":
            self._atoms.clear()

    def enterAtom(self, ctx):
        if self._variable_name == "IntegerRange":
            self._atoms.append(int(ctx.getText()))

    def exitTrailer(self, ctx):
        self._variable_name = None

    def has_range(self) -> bool:
        return len(self._atoms) == 2

    def get_range(self) -> tuple:
        return tuple(self._atoms)


class WarningOptionListener(GccOptionsListener.GccOptionsListener):
    """
    Searches for Warning attributes.

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

    def __init__(self):
        self._last_name = None
        self.is_warning = False

    def enterVariableName(self, ctx):
        if ctx.getText() == "Warning":
            self.is_warning = True
        elif ctx.getText() == "Var":
            self._last_name = "Var"

    def enterAtom(self, ctx):
        if self._last_name != "Var":
            return
        if ctx.getText().startswith("warn_"):
            self.is_warning = True

    def exitTrailer(self, ctx):
        self._last_name = None


class DummyWarningListener(GccOptionsListener.GccOptionsListener):
    """
    Checks if switch does nothing.

    >>> listener = DummyWarningListener()
    >>> apply_listener("C C++ Warning Ignore", listener)
    >>> listener.is_dummy
    True
    """

    def __init__(self):
        self.is_dummy = False

    def enterVariableName(self, ctx):
        if ctx.getText() == "Ignore":
            self.is_dummy = True


class GccOption:
    """Represents one option parsed from the input file(s)."""

    _WARN_REMOVED_HELP = "This option is deprecated and has no effect."

    def __init__(self, name: str, aliases: Set[str] = None, warning=False):
        self._aliases = aliases if aliases else set()
        self._children: Set[str] = set()
        self._default = False
        self._deprecated = False
        self._display_name = None
        self._dummy = False
        self._help_text = str()
        self._languages: Set[str] = set()
        self._name = name
        self._warning = warning

    def __eq__(self, other):
        return self._name == other._name

    def __lt__(self, other):
        return self._name.lower() < other._name.lower()

    def add_alias(self, name: str):
        self._aliases.add(name)

    def add_child(self, name: str):
        self._children.add(name)

    def get_aliases(self) -> List[str]:
        return sorted(self._aliases, key=lambda x: x.lower())

    def get_children(self) -> Set[str]:
        return self._children

    def get_comment_text(self) -> str:
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
        return self._display_name if self._display_name else "-" + self._name

    def get_dummy_text(self) -> str:
        return " # DUMMY switch" if self._dummy else str()

    def get_help_text(self) -> str:
        if self._help_text:
            return self._help_text
        if self._deprecated:
            return GccOption._WARN_REMOVED_HELP
        return self._help_text

    def get_name(self) -> str:
        return self._name

    def is_default(self) -> bool:
        return self._default

    def is_warning(self) -> bool:
        return self._warning

    def set_default(self):
        self._default = True

    def set_deprecated(self):
        self._deprecated = True

    def set_display_name(self, display_name: str):
        if display_name.startswith("-"):
            self._display_name = display_name
        else:
            self._display_name = "-" + display_name

    def set_dummy(self):
        self._dummy = True

    def set_help_text(self, help_text: str):
        self._help_text = help_text

    def set_warning(self):
        self._warning = True

    def update_languages(self, languages: Iterable[str]):
        self._languages.update(languages)


class GccDiagnostics:
    """A collection of GccOption."""

    def __init__(self):
        self._options = dict()  # Map from option name to GccOption

    def get(self, option_name: str) -> GccOption:
        try:
            return self._options[option_name]
        except KeyError:
            self._options[option_name] = GccOption(option_name)
            return self._options[option_name]

    def parse_options_file(self, filename: str):
        """Parse filename and add options from the file."""
        blocks = parse_warning_blocks(open(filename))

        for option_name, display_name, option_arguments, help_text in blocks:
            option = self.get(option_name)

            if display_name:
                option.set_display_name(display_name)

            if help_text:
                option.set_help_text(help_text)
            else:
                # Attempt to retrieve from previous instance
                help_text = option.get_help_text()

            parse_tree = get_parse_tree(option_arguments)
            warning_option = WarningOptionListener()
            apply_listener(parse_tree, warning_option)

            if warning_option.is_warning or could_be_warning(option_name):
                option.set_warning()

            dummy_option = DummyWarningListener()
            apply_listener(parse_tree, dummy_option)
            if dummy_option.is_dummy:
                option.set_dummy()

            if option_name[-1:] == "=" and not display_name:
                integer_range_listener = IntegerRangeListener()
                apply_listener(parse_tree, integer_range_listener)
                if integer_range_listener.has_range():
                    min_value, max_value = integer_range_listener.get_range()
                    option.set_display_name(
                        "-{}<{}..{}>".format(option_name, min_value, max_value)
                    )

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

            flag_enablers = EnabledByListener()
            apply_listener(parse_tree, flag_enablers)
            if flag_enablers.enabled_by:
                flag = flag_enablers.enabled_by
                self.get(flag).add_child(option_name)

            bydefault_option = DefaultsListener()
            apply_listener(parse_tree, bydefault_option)
            if bydefault_option.isEnabledByDefault():
                option.set_default()

            deprecation_option = DeprecationsListener()
            apply_listener(parse_tree, deprecation_option)
            if deprecation_option.isDeprecated():
                option.set_deprecated()

            alias_enablers = AliasAssignmentListener()
            apply_listener(parse_tree, alias_enablers)
            if alias_enablers.alias_name is not None:
                option.add_alias(alias_enablers.alias_name)

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
        Returns True if option_name is top-level, False otherwise.

        An option is top-level if it is not an alias, is not enabled by default,
        and is not the child of any other option.
        """
        return (
            not option.get_aliases()
            and not option.is_default()
            and not self._has_parent(option)
        )

    @classmethod
    def hidden_options(cls):
        options = GccDiagnostics()
        for switch, aliases in HIDDEN_WARNINGS:
            options._options[switch] = GccOption(switch, aliases=aliases, warning=True)
        return options

    def get_children(self, option: GccOption) -> List[GccOption]:
        return sorted(
            [self.get(option_name) for option_name in option.get_children()],
            key=lambda x: x.get_name().lower(),
        )

    def get_all_warnings(self) -> List[GccOption]:
        """Returns a list of GccOption, sorted by name."""
        return sorted(
            [switch for switch in self._options.values() if switch.is_warning()]
        )

    def get_default_warnings(self) -> List[GccOption]:
        """Returns a list of GccOption, sorted by name."""
        return sorted(
            [
                option
                for option in self._options.values()
                if option.is_warning() and option.is_default()
            ]
        )

    def _is_warning(self, option: GccOption) -> bool:
        """
        Returns True if option is a warning, False otherwise.

        option is a warning if it is set as a warning, or if any of its
        aliases are warnings.
        """
        if option.is_warning():
            return True

        for alias in option.get_aliases():
            if self.get(alias).is_warning():
                return True

        return False


def print_option(
    all_options: GccDiagnostics, option: GccOption, level: int, args: argparse.Namespace
):
    if level:
        print("#  " + "  " * level + option.get_display_name())
    else:
        print(option.get_display_name())
    if args.text and option.get_help_text():
        print("#  " + "  " * (level + 2), option.get_help_text())
    for child in all_options.get_children(option):
        print_option(all_options, child, level + 1, args)


def print_default_options(all_options: GccDiagnostics, args: argparse.Namespace):
    defaults = all_options.get_default_warnings()
    if not defaults:
        return

    print("# enabled by default:")
    for option in defaults:
        print_option(all_options, option, 1, args)


def could_be_warning(option_name):
    if "," in option_name:
        return False
    if option_name in NON_WARNING_WS:
        return False

    return option_name.startswith("W")


def print_warning_flags(args: argparse.Namespace, all_options: GccDiagnostics):
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


def main(argv):
    parser = argparse.ArgumentParser(
        description="Parses GCC option files for warning options."
    )
    common.add_common_parser_options(parser)
    parser.add_argument(
        "--text", action="store_true", help="Show help text of each diagnostic.",
    )
    parser.add_argument("option_file", metavar="option-file", nargs="+")
    args = parser.parse_args(argv[1:])

    all_options = GccDiagnostics.hidden_options()

    for filename in args.option_file:
        all_options.parse_options_file(filename)

    print_warning_flags(args, all_options)


if __name__ == "__main__":
    main(sys.argv)
