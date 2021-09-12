# C/C++/Objective-C compiler warning flags collection and parsers

This project includes tools and lists to figure out all warning flags
that [clang compiler](http://clang.llvm.org/) and
[GNU Compiler Collection](https://gcc.gnu.org/) have for C family
languages (C, C++, and Objective-C). This also shows all aliases and
warning flags that a certain flag enables (prefixed with "#"
character) so that you can easily see which flag is enabled by
what. There are also warning flags that do nothing for compatibility
or deprecation reasons. They are suffixed with "# DUMMY switch" text.

The purpose of these collections is to make it more easy to use the
static code analysis tools that compilers provide.

## Clang warning flags

Clang includes `-Weverything` flag, that is not shown in these lists,
that enables all warnings. Clang documentation provides
[reference for some of the diagnostic flags in Clang](https://clang.llvm.org/docs/DiagnosticsReference.html).

* clang 12 [all](clang/warnings-12.txt)
  • [top level](clang/warnings-top-level-12.txt)
  • [messages](clang/warnings-messages-12.txt)
  • [unique](clang/warnings-unique-12.txt)
  • [diff](clang/warnings-diff-11-12.txt)
* clang 11 [all](clang/warnings-11.txt)
  • [top level](clang/warnings-top-level-11.txt)
  • [messages](clang/warnings-messages-11.txt)
  • [unique](clang/warnings-unique-11.txt)
  • [diff](clang/warnings-diff-10-11.txt)
* clang 10 [all](clang/warnings-10.txt)
  • [top level](clang/warnings-top-level-10.txt)
  • [messages](clang/warnings-messages-10.txt)
  • [unique](clang/warnings-unique-10.txt)
  • [diff](clang/warnings-diff-9-10.txt)
* clang 9 [all](clang/warnings-9.txt)
  • [top level](clang/warnings-top-level-9.txt)
  • [messages](clang/warnings-messages-9.txt)
  • [unique](clang/warnings-unique-9.txt)
  • [diff](clang/warnings-diff-8-9.txt)
* clang 8 [all](clang/warnings-8.txt)
  • [top level](clang/warnings-top-level-8.txt)
  • [messages](clang/warnings-messages-8.txt)
  • [unique](clang/warnings-unique-8.txt)
  • [diff](clang/warnings-diff-7-8.txt)
* clang 7 [all](clang/warnings-7.txt)
  • [top level](clang/warnings-top-level-7.txt)
  • [messages](clang/warnings-messages-7.txt)
  • [unique](clang/warnings-unique-7.txt)
  • [diff](clang/warnings-diff-6-7.txt)
* clang 6 [all](clang/warnings-6.txt)
  • [top level](clang/warnings-top-level-6.txt)
  • [messages](clang/warnings-messages-6.txt)
  • [unique](clang/warnings-unique-6.txt)
  • [diff](clang/warnings-diff-5-6.txt)
* clang 5 [all](clang/warnings-5.txt)
  • [top level](clang/warnings-top-level-5.txt)
  • [messages](clang/warnings-messages-5.txt)
  • [unique](clang/warnings-unique-5.txt)
  • [diff](clang/warnings-diff-4-5.txt)
* clang 4 [all](clang/warnings-4.txt)
  • [top level](clang/warnings-top-level-4.txt)
  • [messages](clang/warnings-messages-4.txt)
  • [unique](clang/warnings-unique-4.txt)
  • [diff](clang/warnings-diff-3.9-4.txt)
* clang 3.9 [all](clang/warnings-3.9.txt)
  • [top level](clang/warnings-top-level-3.9.txt)
  • [messages](clang/warnings-messages-3.9.txt)
  • [unique](clang/warnings-unique-3.9.txt)
  • [diff](clang/warnings-diff-3.8-3.9.txt)
* clang 3.8 [all](clang/warnings-3.8.txt)
  • [top level](clang/warnings-top-level-3.8.txt)
  • [messages](clang/warnings-messages-3.8.txt)
  • [unique](clang/warnings-unique-3.8.txt)
  • [diff](clang/warnings-diff-3.7-3.8.txt)
* clang 3.7 [all](clang/warnings-3.7.txt)
  • [top level](clang/warnings-top-level-3.7.txt)
  • [messages](clang/warnings-messages-3.7.txt)
  • [unique](clang/warnings-unique-3.7.txt)
  • [diff](clang/warnings-diff-3.6-3.7.txt)
* clang 3.6 [all](clang/warnings-3.6.txt)
  • [top level](clang/warnings-top-level-3.6.txt)
  • [messages](clang/warnings-messages-3.6.txt)
  • [unique](clang/warnings-unique-3.6.txt)
  • [diff](clang/warnings-diff-3.5-3.6.txt)
* clang 3.5 [all](clang/warnings-3.5.txt)
  • [top level](clang/warnings-top-level-3.5.txt)
  • [messages](clang/warnings-messages-3.5.txt)
  • [unique](clang/warnings-unique-3.5.txt)
  • [diff](clang/warnings-diff-3.4-3.5.txt)
* clang 3.4 [all](clang/warnings-3.4.txt)
  • [top level](clang/warnings-top-level-3.4.txt)
  • [messages](clang/warnings-messages-3.4.txt)
  • [unique](clang/warnings-unique-3.4.txt)
  • [diff](clang/warnings-diff-3.3-3.4.txt)
* clang 3.3 [all](clang/warnings-3.3.txt)
  • [top level](clang/warnings-top-level-3.3.txt)
  • [messages](clang/warnings-messages-3.3.txt)
  • [unique](clang/warnings-unique-3.3.txt)
  • [diff](clang/warnings-diff-3.2-3.3.txt)
* clang 3.2 [all](clang/warnings-3.2.txt)
  • [top level](clang/warnings-top-level-3.2.txt)
  • [messages](clang/warnings-messages-3.2.txt)
  • [unique](clang/warnings-unique-3.2.txt)

## GCC warning flags

If you need a full list of
[GCC warning options](https://gcc.gnu.org/onlinedocs/gcc/Warning-Options.html),
for a specific version of GCC that you have, you can run GCC with `gcc
--help=warnings` to get that list. Otherwise some plain GCC warning
options lists are available below:

* GCC 11 [all](gcc/warnings-gcc-11.txt)
  • [top level](gcc/warnings-gcc-top-level-11.txt)
  • [detail](gcc/warnings-gcc-detail-11.txt)
  • [unique](gcc/warnings-gcc-unique-11.txt)
  • [diff](gcc/warnings-gcc-diff-10-11.txt)
* GCC 10 [all](gcc/warnings-gcc-10.txt)
  • [top level](gcc/warnings-gcc-top-level-10.txt)
  • [detail](gcc/warnings-gcc-detail-10.txt)
  • [unique](gcc/warnings-gcc-unique-10.txt)
  • [diff](gcc/warnings-gcc-diff-9-10.txt)
* GCC 9 [all](gcc/warnings-gcc-9.txt)
  • [top level](gcc/warnings-gcc-top-level-9.txt)
  • [detail](gcc/warnings-gcc-detail-9.txt)
  • [unique](gcc/warnings-gcc-unique-9.txt)
  • [diff](gcc/warnings-gcc-diff-8-9.txt)
* GCC 8 [all](gcc/warnings-gcc-8.txt)
  • [top level](gcc/warnings-gcc-top-level-8.txt)
  • [detail](gcc/warnings-gcc-detail-8.txt)
  • [unique](gcc/warnings-gcc-unique-8.txt)
  • [diff](gcc/warnings-gcc-diff-7-8.txt)
* GCC 7 [all](gcc/warnings-gcc-7.txt)
  • [top level](gcc/warnings-gcc-top-level-7.txt)
  • [detail](gcc/warnings-gcc-detail-7.txt)
  • [unique](gcc/warnings-gcc-unique-7.txt)
  • [diff](gcc/warnings-gcc-diff-6-7.txt)
* GCC 6 [all](gcc/warnings-gcc-6.txt)
  • [top level](gcc/warnings-gcc-top-level-6.txt)
  • [detail](gcc/warnings-gcc-detail-6.txt)
  • [unique](gcc/warnings-gcc-unique-6.txt)
  • [diff](gcc/warnings-gcc-diff-5-6.txt)
* GCC 5 [all](gcc/warnings-gcc-5.txt)
  • [top level](gcc/warnings-gcc-top-level-5.txt)
  • [detail](gcc/warnings-gcc-detail-5.txt)
  • [unique](gcc/warnings-gcc-unique-5.txt)
  • [diff](gcc/warnings-gcc-diff-4.9-5.txt)
* GCC 4.9 [all](gcc/warnings-gcc-4.9.txt)
  • [top level](gcc/warnings-gcc-top-level-4.9.txt)
  • [detail](gcc/warnings-gcc-detail-4.9.txt)
  • [unique](gcc/warnings-gcc-unique-4.9.txt)
  • [diff](gcc/warnings-gcc-diff-4.8-4.9.txt)
* GCC 4.8 [all](gcc/warnings-gcc-4.8.txt)
  • [top level](gcc/warnings-gcc-top-level-4.8.txt)
  • [detail](gcc/warnings-gcc-detail-4.8.txt)
  • [unique](gcc/warnings-gcc-unique-4.8.txt)
  • [diff](gcc/warnings-gcc-diff-4.7-4.8.txt)
* GCC 4.7 [all](gcc/warnings-gcc-4.7.txt)
  • [top level](gcc/warnings-gcc-top-level-4.7.txt)
  • [detail](gcc/warnings-gcc-detail-4.7.txt)
  • [unique](gcc/warnings-gcc-unique-4.7.txt)
  • [diff](gcc/warnings-gcc-diff-4.6-4.7.txt)
* GCC 4.6 [all](gcc/warnings-gcc-4.6.txt)
  • [top level](gcc/warnings-gcc-top-level-4.6.txt)
  • [detail](gcc/warnings-gcc-detail-4.6.txt)
  • [unique](gcc/warnings-gcc-unique-4.6.txt)
  • [diff](gcc/warnings-gcc-diff-4.5-4.6.txt)
* GCC 4.5 [all](gcc/warnings-gcc-4.5.txt)
  • [top level](gcc/warnings-gcc-top-level-4.5.txt)
  • [detail](gcc/warnings-gcc-detail-4.5.txt)
  • [unique](gcc/warnings-gcc-unique-4.5.txt)
  • [diff](gcc/warnings-gcc-diff-4.4-4.5.txt)
* GCC 4.4 [all](gcc/warnings-gcc-4.4.txt)
  • [top level](gcc/warnings-gcc-top-level-4.4.txt)
  • [detail](gcc/warnings-gcc-detail-4.4.txt)
  • [unique](gcc/warnings-gcc-unique-4.4.txt)
  • [diff](gcc/warnings-gcc-diff-4.3-4.4.txt)
* GCC 4.3 [all](gcc/warnings-gcc-4.3.txt)
  • [top level](gcc/warnings-gcc-top-level-4.3.txt)
  • [detail](gcc/warnings-gcc-detail-4.3.txt)
  • [unique](gcc/warnings-gcc-unique-4.3.txt)
  • [diff](gcc/warnings-gcc-diff-4.2-4.3.txt)
* GCC 4.2 [all](gcc/warnings-gcc-4.2.txt)
  • [top level](gcc/warnings-gcc-top-level-4.2.txt)
  • [detail](gcc/warnings-gcc-detail-4.2.txt)
  • [unique](gcc/warnings-gcc-unique-4.2.txt)
  • [diff](gcc/warnings-gcc-diff-4.1-4.2.txt)
* GCC 4.1 [all](gcc/warnings-gcc-4.1.txt)
  • [top level](gcc/warnings-gcc-top-level-4.1.txt)
  • [detail](gcc/warnings-gcc-detail-4.1.txt)
  • [unique](gcc/warnings-gcc-unique-4.1.txt)
  • [diff](gcc/warnings-gcc-diff-4.0-4.1.txt)
* GCC 4.0 [all](gcc/warnings-gcc-4.0.txt)
  • [top level](gcc/warnings-gcc-top-level-4.0.txt)
  • [detail](gcc/warnings-gcc-detail-4.0.txt)
  • [unique](gcc/warnings-gcc-unique-4.0.txt)
  • [diff](gcc/warnings-gcc-diff-3.4-4.0.txt)
* GCC 3.4 [all](gcc/warnings-gcc-3.4.txt)
  • [top level](gcc/warnings-gcc-top-level-3.4.txt)
  • [detail](gcc/warnings-gcc-detail-3.4.txt)
  • [unique](gcc/warnings-gcc-unique-3.4.txt)
  (first GCC with domain specific language options file)

## Apple clang (Xcode) warning flags

Apple's fork of clang (as shipped with Xcode) is _based on_ the LLVM project but
is not a 100% match; some warnings are added, others are removed, and the
versioning scheme is different. The official Xcode releases are built from an
Apple-internal repository, so the exact list of compiler warning flags is not
truly knowable without experimentation.

That said, [Apple's public fork of LLVM](https://github.com/apple/llvm-project)
has `apple/stable/*` branches which are a close approximation of the Xcode
sources especially with regard to available compiler warnings. For example, the
delta between `apple/stable/20200108` and Xcode 12.2 is about ten flags.

Warnings available in each `apple/stable` branch are as follows:

* 20210628 [all](xcode/warnings-xcode-20210628.txt)
  • [top level](xcode/warnings-xcode-top-level-20210628.txt)
  • [messages](xcode/warnings-xcode-messages-20210628.txt)
  • [unique](xcode/warnings-xcode-unique-20210628.txt)
  • [diff](xcode/warnings-xcode-diff-20210107-20210628.txt)
* 20210107 [all](xcode/warnings-xcode-20210107.txt)
  • [top level](xcode/warnings-xcode-top-level-20210107.txt)
  • [messages](xcode/warnings-xcode-messages-20210107.txt)
  • [unique](xcode/warnings-xcode-unique-20210107.txt)
  • [diff](xcode/warnings-xcode-diff-20200714-20210107.txt)
* 20200714 [all](xcode/warnings-xcode-20200714.txt)
  • [top level](xcode/warnings-xcode-top-level-20200714.txt)
  • [messages](xcode/warnings-xcode-messages-20200714.txt)
  • [unique](xcode/warnings-xcode-unique-20200714.txt)
  • [diff](xcode/warnings-xcode-diff-20200108-20200714.txt)
* 20200108 [all](xcode/warnings-xcode-20200108.txt)
  • [top level](xcode/warnings-xcode-top-level-20200108.txt)
  • [messages](xcode/warnings-xcode-messages-20200108.txt)
  • [unique](xcode/warnings-xcode-unique-20200108.txt)
  • [diff](xcode/warnings-xcode-diff-20191106-20200108.txt)
* 20191106 [all](xcode/warnings-xcode-20191106.txt)
  • [top level](xcode/warnings-xcode-top-level-20191106.txt)
  • [messages](xcode/warnings-xcode-messages-20191106.txt)
  • [unique](xcode/warnings-xcode-unique-20191106.txt)
  • [diff](xcode/warnings-xcode-diff-20190619-20191106.txt)
* 20190619 [all](xcode/warnings-xcode-20190619.txt)
  • [top level](xcode/warnings-xcode-top-level-20190619.txt)
  • [messages](xcode/warnings-xcode-messages-20190619.txt)
  • [unique](xcode/warnings-xcode-unique-20190619.txt)
  • [diff](xcode/warnings-xcode-diff-20190104-20190619.txt)
* 20190104 [all](xcode/warnings-xcode-20190104.txt)
  • [top level](xcode/warnings-xcode-top-level-20190104.txt)
  • [messages](xcode/warnings-xcode-messages-20190104.txt)
  • [unique](xcode/warnings-xcode-unique-20190104.txt)
  • [diff](xcode/warnings-xcode-diff-20180801-20190104.txt)
* 20180801 [all](xcode/warnings-xcode-20180801.txt)
  • [top level](xcode/warnings-xcode-top-level-20180801.txt)
  • [messages](xcode/warnings-xcode-messages-20180801.txt)
  • [unique](xcode/warnings-xcode-unique-20180801.txt)
  • [diff](xcode/warnings-xcode-diff-20180719-20180801.txt)
* 20180719 [all](xcode/warnings-xcode-20180719.txt)
  • [top level](xcode/warnings-xcode-top-level-20180719.txt)
  • [messages](xcode/warnings-xcode-messages-20180719.txt)
  • [unique](xcode/warnings-xcode-unique-20180719.txt)
  • [diff](xcode/warnings-xcode-diff-20180103-20180719.txt)
* 20180103 [all](xcode/warnings-xcode-20180103.txt)
  • [top level](xcode/warnings-xcode-top-level-20180103.txt)
  • [messages](xcode/warnings-xcode-messages-20180103.txt)
  • [unique](xcode/warnings-xcode-unique-20180103.txt)
  • [diff](xcode/warnings-xcode-diff-20170719-20180103.txt)
* 20170719 [all](xcode/warnings-xcode-20170719.txt)
  • [top level](xcode/warnings-xcode-top-level-20170719.txt)
  • [messages](xcode/warnings-xcode-messages-20170719.txt)
  • [unique](xcode/warnings-xcode-unique-20170719.txt)
  • [diff](xcode/warnings-xcode-diff-20170116-20170719.txt)
* 20170116 [all](xcode/warnings-xcode-20170116.txt)
  • [top level](xcode/warnings-xcode-top-level-20170116.txt)
  • [messages](xcode/warnings-xcode-messages-20170116.txt)
  • [unique](xcode/warnings-xcode-unique-20170116.txt)
  • [diff](xcode/warnings-xcode-diff-20160817-20170116.txt)
* 20160817 [all](xcode/warnings-xcode-20160817.txt)
  • [top level](xcode/warnings-xcode-top-level-20160817.txt)
  • [messages](xcode/warnings-xcode-messages-20160817.txt)
  • [unique](xcode/warnings-xcode-unique-20160817.txt)
  • [diff](xcode/warnings-xcode-diff-20160127-20160817.txt)
* 20160127 [all](xcode/warnings-xcode-20160127.txt)
  • [top level](xcode/warnings-xcode-top-level-20160127.txt)
  • [messages](xcode/warnings-xcode-messages-20160127.txt)
  • [unique](xcode/warnings-xcode-unique-20160127.txt)

## Examining differences

One use case for these kinds of lists is to see what differences there
are between different compilers and compiler versions. I have made
available rudimentary compiler flag differences between two consequent
compiler versions as diff-files, but for more specific differences you
need to use some (visual) diff program, as shown below:

![Some GCC 5 and 6 -Wall differences shown with meld](gcc/meld-gcc-5-6-wall.png)

# Development

## Overview

This uses [ANTLR](http://www.antlr.org/) as a parser generator with
some supporting Python code to parse warning flags from actual
compiler option data files. Other requirements are following (plus
their dependencies):

* [Ninja](https://ninja-build.org/)
* [ANTLR4](http://www.antlr.org/)
* [Python 3.9+](https://www.python.org/)
* [antlr4-python3-runtime](https://pypi.python.org/pypi/antlr4-python3-runtime/)
* llvm-tblgen from [LLVM 7 or newer](https://llvm.org/)

## Building (the easy way)

A top-level script, `make.sh`, is provided. The `make.sh` script takes
care of setting up a Docker image with all of the above dependencies,
creates/updates local clones of the gcc and clang source repositories,
builds the parsers, and generates the lists.

The only prerequisite for `make.sh` is a recent version of [Docker](https://www.docker.com).

## Building gcc warning lists (by hand)

After you have installed all the requirements and are able to run
ANTLR with `antlr4` command, just use following commands in `parsers/`
directory to generate the gcc lists yourself:

    ninja
    ./parse-gcc-warning-options.py <path-to-gcc-source>/gcc/{common.opt,c-family/c.opt}

## Building clang warning lists (by hand)

After you have installed all the requirements and are able to run
`llvm-tblgen`, just use following commands in `parsers/` directory to
generate the clang lists yourself:

    llvm-tblgen -dump-json -I<path-to-clang-source>/include/clang/Basic \
      include/clang/Basic/Diagnostic.td > ../clang/warnings-$VERSION.json
    ./parse-clang-diagnostic-groups.py ../clang/warnings-$VERSION.json

And you'll get the list of all individual warning flags and their
dependencies that are in the requested compiler version.

To generate filtered lists, you may use `--top-level` and `--unique`
switches.

* `--top-level` switch does not include warnings that are enabled by
  some other switch in the list.
* `--unique` lists all warnings without any information what other
  warnings they enable. Diffs on this page are created from these
  files.

## Tests

There are some unit tests testing the low level functionality. You may
run time with `ninja test` command in `parsers/` directory to verify
that unit tests pass.

## Processing git repositories

When parser gets a change that affects formatting or other output for
multiple files these warning lists need to be recreated. There are
`process_clang_git.py` and `process_gcc_git.py` scripts that take the
git repository root as their first parameter and apply all different
variants of these commands to create final text files.
