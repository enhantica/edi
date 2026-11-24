"""Observe effective file arguments at the analyzer process boundary."""

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path


def invocation():
    args = sys.argv[1:]
    if any(arg == '--project' or arg.startswith('--project=') for arg in args):
        parser = argparse.ArgumentParser()
        parser.add_argument('--project', type=Path, required=True)
        parser.add_argument('--file-filter', action='append', default=[])
        parser.add_argument('--error-exitcode', type=int, default=0)
        options, _ = parser.parse_known_args(args)
        return (
            'cpp-cppcheck',
            options.project,
            options.error_exitcode != 0,
            lambda file: (
                not options.file_filter
                or any(fnmatch.fnmatchcase(file, pattern) for pattern in options.file_filter)
            ),
        )
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', type=Path, required=True)
    parser.add_argument('-j')
    parser.add_argument('-quiet', action='store_true')
    parser.add_argument('-header-filter')
    parser.add_argument('-exclude-header-filter')
    parser.add_argument('-extra-arg', action='append')
    parser.add_argument('-warnings-as-errors')
    parser.add_argument('files', nargs='*')
    options = parser.parse_args(args)
    return (
        'cpp-tidy',
        options.p / 'compile_commands.json',
        options.warnings_as_errors == '*',
        lambda file: (
            not options.files or any(re.search(pattern, file) for pattern in options.files)
        ),
    )


def main():
    tool, database, fatal, selected = invocation()
    root = Path(os.environ['EDI_TEST_ANALYSIS_ROOT'])
    entries = json.loads(database.read_text())
    observed = []
    for entry in entries:
        file = (Path(entry['directory']) / entry['file']).resolve()
        if selected(str(file)):
            observed.append(file.relative_to(root).as_posix())
    with Path(os.environ['EDI_TEST_ANALYSIS_RECORD']).open('a', encoding='utf-8') as output:
        output.write(
            json.dumps({'tool': tool, 'fatal': fatal, 'files': sorted(set(observed))}) + '\n'
        )


if __name__ == '__main__':
    main()
