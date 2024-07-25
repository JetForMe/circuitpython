"""
Generate header file with macros defining MicroPython version info.

# CIRCUITPY-CHANGE: This script is thoroughly reword for use with CircuitPython.
This script works with Python 3.7 and newer
"""

from __future__ import print_function

import argparse
import sys
import os
import pathlib
import datetime
import subprocess

# CIRCUITPY-CHANGE: use external script that can override git describe output with an
# environment variable.
tools_describe = str(pathlib.Path(__file__).resolve().parent.parent / "tools/describe")


def get_version_info_from_git(repo_path):
    # Python 2.6 doesn't have check_output, so check for that
    try:
        subprocess.check_output
        subprocess.check_call
    except AttributeError:
        return None

    # Note: git describe doesn't work if no tag is available
    try:
        git_tag = subprocess.check_output(
            [tools_describe],
            cwd=repo_path,
            shell=True,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        ).strip()
    except subprocess.CalledProcessError as er:
        if er.returncode == 128:
            # git exit code of 128 means no repository found
            return None
        git_tag = ""
    except OSError:
        return None
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_path,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        ).strip()
    except subprocess.CalledProcessError:
        git_hash = "unknown"
    except OSError:
        return None

    try:
        # Check if there are any modified files.
        subprocess.check_call(
            ["git", "diff", "--no-ext-diff", "--quiet", "--exit-code"],
            cwd=repo_path,
            stderr=subprocess.STDOUT,
        )
        # Check if there are any staged files.
        subprocess.check_call(
            ["git", "diff-index", "--cached", "--quiet", "HEAD", "--"],
            cwd=repo_path,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError:
        git_hash += "-dirty"
    except OSError:
        return None

    # CIRCUITPY-CHANGE
    # Try to extract MicroPython version from git tag
    ver = git_tag.split("-")[0].split(".")

    return git_tag, git_hash, ver


def cannot_determine_version():
    raise SystemExit(
        """Cannot determine version.

CircuitPython must be built from a git clone with tags.
If you cloned from a fork, fetch the tags from adafruit/circuitpython as follows:

    make fetch-tags"""
    )


def make_version_header(repo_path, filename):
    # Get version info using git (required)
    info = get_version_info_from_git(repo_path)
    if info is None:
        cannot_determine_version()
    git_tag, git_hash, ver = info
    if len(ver) < 3:
        cannot_determine_version()
    else:
        version_string = ".".join(ver)

    build_date = datetime.date.today()
    if "SOURCE_DATE_EPOCH" in os.environ:
        build_date = datetime.datetime.utcfromtimestamp(
            int(os.environ["SOURCE_DATE_EPOCH"])
        ).date()

    # Generate the file with the git and version info
    file_data = """\
// This file was generated by py/makeversionhdr.py
#define MICROPY_GIT_TAG "%s"
#define MICROPY_GIT_HASH "%s"
#define MICROPY_BUILD_DATE "%s"
#define MICROPY_VERSION_MAJOR (%s)
#define MICROPY_VERSION_MINOR (%s)
#define MICROPY_VERSION_MICRO (%s)
#define MICROPY_VERSION_STRING "%s"
// Combined version as a 32-bit number for convenience
#define MICROPY_VERSION (MICROPY_VERSION_MAJOR << 16 | MICROPY_VERSION_MINOR << 8 | MICROPY_VERSION_MICRO)
#define MICROPY_FULL_VERSION_INFO "Adafruit CircuitPython " MICROPY_GIT_TAG " on " MICROPY_BUILD_DATE "; " MICROPY_BANNER_MACHINE
""" % (
        git_tag,
        git_hash,
        datetime.date.today().strftime("%Y-%m-%d"),
        ver[0].replace("v", ""),
        ver[1],
        ver[2],
        version_string,
    )

    # Check if the file contents changed from last time
    write_file = True
    if os.path.isfile(filename):
        with open(filename, "r") as f:
            existing_data = f.read()
        if existing_data == file_data:
            write_file = False

    # Only write the file if we need to
    if write_file:
        print("GEN %s" % filename)
        with open(filename, "w") as f:
            f.write(file_data)


def main():
    parser = argparse.ArgumentParser()
    # makeversionheader.py lives in repo/py, so default repo_path to the
    # parent of sys.argv[0]'s directory.
    parser.add_argument(
        "-r",
        "--repo-path",
        default=os.path.join(os.path.dirname(sys.argv[0]), ".."),
        help="path to MicroPython Git repo to query for version",
    )
    parser.add_argument("dest", nargs=1, help="output file path")
    args = parser.parse_args()

    make_version_header(args.repo_path, args.dest[0])


if __name__ == "__main__":
    main()
