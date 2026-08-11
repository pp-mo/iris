#!/usr/bin/env python3
# Copyright Iris contributors
#
# This file is part of Iris and is released under the BSD license.
# See LICENSE in the root of the repository for full licensing details.
"""CLI runner interface for Python doctests.

TODO this utility should be templated for easy code sharing across repos.
"""

import argparse
import doctest
import importlib
from pathlib import Path
import pkgutil
import sys
import traceback
from typing import Any, Callable
import warnings


def list_modules_recursive(
    module_importname: str,
    include_private: bool = True,
    exclude_fragments: list[str] = [],
) -> list[str]:
    """Find all the submodules of a given module.

    Also filter with private and exclude controls.
    """
    module_names = [module_importname]
    # Identify module from its import path : N.B. fail --> return [module-path]
    try:
        error = None
        module = importlib.import_module(module_importname)
    except Exception as exc:
        print(f"\n\nIMPORT FAILED: {module_importname}\n")
        error = exc

    if error is None:
        # Add all sub-modules to the list
        # Get the filepath of the module base directory
        module_filepath = Path(str(module.__file__))
        if module_filepath.name == "__init__.py":
            for _, name, ispkg in pkgutil.iter_modules([module_filepath.parent]):
                if name[:1] == "_" and not include_private:
                    continue
                submodule_name = module_importname + "." + name
                if any(match in submodule_name for match in exclude_fragments):
                    continue
                module_names.append(submodule_name)
                if ispkg:
                    module_names.extend(
                        list_modules_recursive(
                            submodule_name,
                            include_private=include_private,
                            exclude_fragments=exclude_fragments,
                        )
                    )

    # Remove duplicates, which may occur.
    return sorted(set(module_names))


def list_filepaths_recursive(
    file_spec: str, exclude_fragments: list[str] = []
) -> list[Path]:
    """Expand a filepath string, possibly containing globs, to a list of filepaths.

    Also filter with exclude controls.
    """
    segments = file_spec.split("/")
    i_wilds = [
        index
        for index, segment in enumerate(segments)
        if any(char in segment for char in "*?[")
    ]
    if len(i_wilds) == 0:
        found_paths = [Path(file_spec)]
    else:
        i_first_wild = i_wilds[0]
        # Split into a regular path prefix + the part including globs
        base_path = Path("/".join(segments[:i_first_wild]))
        glob_spec = "/".join(segments[i_first_wild:])
        # expand with globs
        found_paths = list(base_path.glob(glob_spec))

    # Also apply excludes to results
    # NB there is NO "private" filtering for sourcefiles
    found_paths = [
        path
        for path in found_paths
        if not path.is_dir()
        and not any(match in str(path) for match in exclude_fragments)
    ]
    return found_paths


def process_options(
    opt_str: str, paths_are_modules: bool = True
) -> dict[str, str | int | bool]:
    """Convert the "-o/--options" arg into a **kwargs for the doctest function call."""
    opt_str = opt_str.replace(" ", "")  # Remove spaces -- never meaningful
    # Split on commas, and split each one on "=" expecting a simple name=val form
    opts_dict: dict[str, str | int | bool] = {}
    if opt_str:  # N.B. to avoid unexpected behaviour: "".split() --> [""]
        for setting_str in opt_str.split(","):
            try:
                name, val = setting_str.split("=")
                # Detect + translate integers and booleans (only, else leave as 'str').
                value: str | int | bool = val
                bool_vals = {"true": True, "false": False}
                if val.isdigit():
                    value = int(val)
                elif val.lower() in bool_vals:
                    value = bool_vals[val.lower()]
            except ValueError:
                msg = f"Invalid option setting {setting_str!r}, expected 'name=value' only."
                raise ValueError(msg)
            opts_dict[name] = value

    # Implement some handy defaults
    if not paths_are_modules:
        if not "module_relative" in opts_dict:
            opts_dict["module_relative"] = False  # we want this OFF, by default anyway
    if not "optionflags" in opts_dict:
        default_flags = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
        opts_dict["optionflags"] = default_flags  # a generally useful default?

    return opts_dict


def run_doctest_paths(
    paths: list[str] | list[Path],
    paths_are_modules: bool = False,
    recurse_modules: bool = False,
    include_private_modules: bool = False,
    exclude_fragments: list[str] = [],
    doctest_kwargs: dict = {},
    verbose: bool = False,
    dry_run: bool = False,
    stop_on_failure: bool = False,
):
    n_total_fails, n_total_tests, n_paths_tested = 0, 0, 0

    if verbose:
        print(
            "RUNNING run_doctest("
            f"paths={paths!r}"
            f", paths_are_modules={paths_are_modules!r}"
            f", recurse_modules={recurse_modules!r}"
            f", include_private_modules={include_private_modules!r}"
            f", exclude_fragments={exclude_fragments!r}"
            f", doctest_kwargs={doctest_kwargs!r}"
            f", verbose={verbose!r}"
            f", dry_run={dry_run!r}"
            f", stop_on_failure={stop_on_failure!r}"
            ")"
        )

    if dry_run:
        verbose = True

    # For now at least, simply discard ALL warnings.
    warnings.simplefilter("ignore")

    doctest_function: Callable
    if paths_are_modules:
        doctest_function = doctest.testmod
        if recurse_modules:
            module_paths = []
            for path in paths:
                module_paths += list_modules_recursive(
                    str(path),  # for modules, 'paths' are always strings anyway
                    include_private=include_private_modules,
                    exclude_fragments=exclude_fragments,
                )
            paths = module_paths
    else:
        # paths are filepaths
        doctest_function = doctest.testfile
        filepaths = []
        for path in paths:
            filepaths += list_filepaths_recursive(
                str(path), exclude_fragments=exclude_fragments
            )
        paths = filepaths

    for path in paths:
        if verbose:
            print(f"\n-----\ndoctest.{doctest_function.__name__}: {path}")
        if dry_run:
            continue

        op_fail = None
        arg: Any  # can be a string or a 'Module' object
        if paths_are_modules:
            path_str = str(path)
            try:
                arg = importlib.import_module(path_str)
            except Exception as exc:
                op_fail = exc
        else:
            arg = path

        if op_fail is None:
            try:
                n_fails, n_tests = doctest_function(arg, **doctest_kwargs)
                n_total_fails += n_fails
                n_total_tests += n_tests
                n_paths_tested += 1
                if n_fails:
                    n_ok = n_tests - n_fails
                    msg = (
                        f"**ERRORS**\n"
                        f"{n_ok}/{n_tests} OK, {n_fails}/{n_tests} FAILED in path: {path}"
                    )
                    print(msg)
                elif verbose:
                    print(f"{n_tests}/{n_tests} OK in path: {path}")
            except Exception as exc:
                op_fail = exc

        if op_fail is not None:
            n_total_fails += 1
            print(f"\n\nERROR occurred at {path!r}: {op_fail}\n")
            if isinstance(op_fail, doctest.UnexpectedException):
                # E.G. this is what happens with "-o raise_on_error=True", which is
                #  the Python call equivalent of "-o FAIL_FAST" in the doctest CLI.
                print(f"Doctest caught exception: {op_fail}")
                traceback.print_exception(*op_fail.exc_info)

        if n_total_fails > 0 and stop_on_failure:
            break

    if verbose or n_total_fails > 0:
        # Print a final report
        msgs = ["", "=====", "run_doctest: FINAL REPORT"]
        if dry_run:
            msgs += ["(DRY RUN: no actual tests)"]
        elif stop_on_failure and n_total_fails > 0:
            msgs += ["(FAIL FAST: stopped at first path with errors)"]

        msgs += [
            f"    paths tested    = {n_paths_tested}",
            f"    tests completed = {n_total_tests}",
            f"    errors          = {n_total_fails}",
            "",
        ]
        if n_total_fails > 0:
            msgs += ["FAILED."]
        else:
            msgs += ["OK."]

        print("\n".join(msgs))

    return n_total_fails


_help_extra_lines = """\
Notes:
  * file paths support glob patterns '* ? [] **'  (** to include subdirectories)
      * N.B. use ** to include subdirectories
      * N.B. usually requires quotes, to avoid shell expansion
  * module paths do *not* support globs
      * but --recurse includes all submodules
  * \"--exclude\" patterns are a simple substring to match (not a glob/regexp)

Examples:
  $ run_doctests \"docs/**/*.rst\"                      # test all document sources
  $ run_doctests \"docs/user*/**/*.rst\" -e detail      # skip filepaths containing key string
  $ run_doctests -mr mymod                            # test module + all submodules
  $ run_doctests -mr mymod.util -e maths -e fun.err   # skip module paths with substrings
  $ run_doctests -mr mymod -o verbose=true            # make doctest print each test
"""


_parser = argparse.ArgumentParser(
    prog="run_doctests",
    description="Run doctests in docs files, or docstrings in packages.",
    epilog=_help_extra_lines,
    formatter_class=argparse.RawDescriptionHelpFormatter,
)
_parser.add_argument(
    "-m",
    "--module",
    action="store_true",
    help="paths are module paths (xx.yy.zz), instead of filepaths.",
)
_parser.add_argument(
    "-r",
    "--recurse",
    action="store_true",
    help="include submodules (only applies with -m).",
)
_parser.add_argument(
    "-p",
    "--publiconly",
    action="store_true",
    help="exclude module names beginning '_' (only applies with -m and -r)",
)
_parser.add_argument(
    "-e",
    "--exclude",
    action="append",
    help="exclude paths containing substring (may appear multiple times).",
)
_parser.add_argument(
    "-o",
    "--options",
    nargs="?",
    help=(
        'kwargs (Python) for doctest call, e.g. "raise_on_error=True,optionflags=8".'
    ),
    type=str,
    default="",
)
_parser.add_argument(
    "-v", "--verbose", action="store_true", help="show details of each operation."
)
_parser.add_argument(
    "-d",
    "--dryrun",
    action="store_true",
    help="only print names of modules/files which *would* be tested.",
)
_parser.add_argument(
    "-f",
    "--stop-on-fail",
    action="store_true",
    help="stop at the first path with an error (else continue to test all).",
)
_parser.add_argument(
    "paths",
    nargs="*",
    help="docs filepaths, or module paths (not both).",
    type=str,
    default=[],
)


def parserargs_as_kwargs(args):
    return dict(
        paths=args.paths,
        paths_are_modules=args.module,
        recurse_modules=args.recurse,
        include_private_modules=not args.publiconly,
        exclude_fragments=args.exclude or [],
        doctest_kwargs=process_options(args.options, args.module),
        verbose=args.verbose,
        dry_run=args.dryrun,
        stop_on_failure=args.stop_on_fail,
    )


if __name__ == "__main__":
    args = _parser.parse_args(sys.argv[1:])
    if not args.paths:
        _parser.print_help()
    else:
        kwargs = parserargs_as_kwargs(args)
        n_errs = run_doctest_paths(**kwargs)
        if n_errs > 0:
            exit(1)
