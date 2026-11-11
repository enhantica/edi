# SPDX-License-Identifier: BSD-3-Clause
"""Write a case's Command line tutorial from its Python tutorial's stages, with real output.

The command line fits whatever a project marks free with `()`, so it teaches the same staged fit
as the Python tutorial: per stage, edit the project's files to mark the stage's parameters, then
run `edi fit`. This script makes that page at authoring time. It starts from the case's project
with nothing free, and for each stage of `docs/user/tutorials/<case>.py` applies the stage's lines
(what it frees, its aliases and constraints) through edi, which writes the `()` marks; shows the
lines that changed; and runs the standalone executable's fit on the project, recording its output.
The page is committed, as its output is a measurement:

    python website/render_cli_tutorials.py <case> [--binary build/ci-consumer/cli/easydiffraction]
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / 'website/surfaces/docs/cli/tutorials/cases'
SHOWN_LINES = 12
# A case whose Python tutorial builds its structure and experiment by hand starts here from its
# starting project, as building a project by hand on the command line is still to come.
BY_HAND = (
    ' The Python tutorial builds this project by hand; here the command line starts from its '
    'starting project instead, since building a project by hand on the command line is planned '
    'for a later release.'
)
# The lines of a stage that change the project: what it frees or fixes, a value it resets, and
# its aliases and constraints.
EDITS = re.compile(
    r'(\.free = (True|False)$|^\s+point\.intensity\.free|^for point in |\.adp_iso = |'
    r'\.aliases\.create\(|\.constraints\.create\(|\.auto_estimate\()'
)


def cells(source: str) -> list[tuple[str, str]]:
    """The tutorial's cells as (kind, text): `markdown` without its `# ` prefixes, or `code`."""
    out = []
    for block in re.split(r'^# %%', source, flags=re.MULTILINE)[1:]:
        header, _, body = block.partition('\n')
        if header.strip() == '[markdown]':
            text = '\n'.join(
                line[2:] if line.startswith('# ') else line.lstrip('#')
                for line in body.splitlines()
            )
            out.append(('markdown', text.strip()))
        else:
            out.append(('code', body.strip()))
    return out


def stages(source: str) -> list[dict]:
    """Each fit stage of the analysis: its heading and text, and the lines it applies."""
    parts = cells(source)
    start = next(
        i
        for i, (kind, text) in enumerate(parts)
        if kind == 'markdown' and '## Perform the analysis' in text
    )
    out, current = [], {'title': '', 'text': '', 'edits': []}
    for kind, text in parts[start:]:
        if kind == 'markdown':
            heading = re.search(r'^### (.+)$', text, flags=re.MULTILINE)
            if heading:
                current['title'] = heading.group(1)
                current['text'] = text[heading.end() :].strip()
            continue
        if 'project.analysis.fit()' in text:
            out.append(current)
            current = {'title': '', 'text': '', 'edits': []}
            continue
        lines, keep = text.splitlines(), []
        in_loop = False  # inside a top-level loop's block, nested loops included
        for index, line in enumerate(lines):
            in_loop = in_loop and line.startswith(' ')
            if (
                EDITS.search(line)
                or in_loop
                or (line.startswith('for ') and index + 1 < len(lines))
            ):
                keep.append(line)
            if line.startswith('for '):
                in_loop = True
        current['edits'].extend(keep)
    return out


def names(source: str) -> str:
    """The tutorial's names for its structures and experiments, as code for a loaded project."""
    found = re.findall(
        r'^(\w+) = project\.(?:structures|experiments)\[[^\]]+\]$', source, flags=re.MULTILINE
    )
    return (
        '\n'.join(
            line
            for line in source.splitlines()
            if re.match(r'^\w+ = project\.(structures|experiments)\[', line)
        )
        if found
        else ''
    )


def snapshot(folder: Path) -> dict[str, list[str]]:
    return {
        str(path.relative_to(folder)): path.read_text(encoding='utf-8').splitlines()
        for path in sorted(folder.rglob('*.edi'))
    }


# The case that also shows measured data from a file on disk (owner record 2026-11-08).
FROM_FILE = {'pd-neut-tof_si-sepd'}
FROM_FILE_TEXT = (
    'The command line fits the files of a project. To start from a measured-data file on your '
    'own disk, create the experiment in the Python package with `add_from_data_path`, or in the '
    'app with **Load ▾ Measured data From file…**, and save the project; creating one from a '
    'data file on the command line comes in a later version.\n'
)
MARK = re.compile(r'\((\d*)\)')
# The project settings a stage may change: the fitting mode and the background estimate's.
SETTINGS = ('_fitting_mode.type', '_background_estimate.')
FREED = re.compile(r'\(0?\)')


def changes(
    before: dict, after: dict, relations: set[str], rows: frozenset[str] = frozenset()
) -> list[tuple[str, str, list[str]]]:
    """Per file, the lines a stage edited, as a reader writes them, by kind.

    `free` is a value given its `()`, `fixed` a value's `()` removed and `relations` the aliases
    and constraints it added (by id). Values a fit moved are not edits.
    """
    out = []
    for name, lines in after.items():
        if name == 'project.edi':
            continue
        old = set(before.get(name, []))
        unmarked = {MARK.sub('', line) for line in old}
        kinds: dict[str, list[str]] = {
            'setting': [],
            'value': [],
            'free': [],
            'added': [],
            'fixed': [],
            'relations': [],
        }
        for line in lines:
            if line in old:
                continue
            if line.startswith('_background_estimate.points_digest'):
                continue  # written by edi, never by hand
            if line.startswith(SETTINGS):
                kinds['setting'].append(line)
            elif line.split(' ', 1)[0] in relations and name.startswith('analysis'):
                kinds['relations'].append(line)
            elif not name.startswith('analysis') and MARK.sub('', line) in unmarked:
                # A value the stage frees is written with an empty or zero bracket; a value that
                # keeps an earlier fit's s.u. (a constraint's dependent) was not edited.
                if FREED.search(line):
                    kinds['free'].append(MARK.sub('()', line))
                elif not MARK.search(line):
                    kinds['fixed'].append(line)
            elif (
                line.startswith('_')
                and FREED.search(line)
                and line.split(' ', 1)[0] not in {held.split(' ', 1)[0] for held in old}
            ):
                # A value the file leaves out while it is zero and fixed (a sample displacement).
                kinds['added'].append(MARK.sub('()', line))
            elif not name.startswith('analysis') and line.split(' ', 1)[0] in rows:
                # A value the stage sets, on a row its lines name (`atom_sites['Co1']`).
                kinds['value'].append(MARK.sub('()', line))
        out.extend((name, kind, found) for kind, found in kinds.items() if found)
    return out


def tabs(command: str) -> str:
    return (
        f'=== "Standalone executable"\n\n    ```console\n    edi {command}\n    ```\n\n'
        f'=== "Python package"\n\n    ```console\n    python -m edi {command}\n    ```\n'
    )


WORDS = {
    'setting': 'set',
    'value': 'set the values the stage starts again from',
    'free': 'add `()` after the values the stage frees',
    'added': 'add these lines, free with `()`; a value left out reads as zero',
    'fixed': 'remove the `()` from',
    'relations': 'add these rows to its alias and constraint loops',
}


# Rows of one loop a stage edits together are shown as one excerpt, the rest said in words (owner
# records 2026-11-09: a group is fixed or freed in one action).
EXCERPT_ROWS = 2


def edited(edits: list[tuple[str, str, list[str]]], words: dict[str, str] = WORDS) -> str:
    out = []
    for name, kind, lines in edits:
        keyed = [line for line in lines if line.startswith('_')]
        rows = [line for line in lines if not line.startswith('_')]
        shown = keyed[:SHOWN_LINES] + rows[:EXCERPT_ROWS]
        more = ''
        if len(keyed) > SHOWN_LINES:
            more += f'\n… and {len(keyed) - SHOWN_LINES} more lines'
        rest = len(rows) - EXCERPT_ROWS
        after = f'The same for every other row ({rest} more).\n' if rest > 0 else ''
        out.append(
            f'In `{name}`, {words[kind]}:\n\n```edi\n'
            + '\n'.join(shown)
            + more
            + '\n```\n'
            + (f'\n{after}' if after else '')
        )
    return '\n'.join(out)


def render_calculation(case: str, title: str) -> Path:
    """A case with nothing to fit: get the project, calculate it and write its report.

    The standalone executable fits measured data only, so the calculation runs in the Python
    package. Its output is shown as it prints, without the time the calculation took.
    """
    with tempfile.TemporaryDirectory(prefix=f'cli-tutorial-{case}-') as scratch:
        shutil.copytree(ROOT / f'docs/user/cli/{case}/project', Path(scratch) / case)
        run = subprocess.run(
            [sys.executable, '-m', 'edi', 'calc', case, '--dry'],
            cwd=scratch,
            capture_output=True,
            text=True,
            check=True,
        )
    output = [line for line in run.stdout.rstrip().splitlines() if not line.startswith('elapsed_')]
    python_only = (
        '=== "Standalone executable"\n\n    {why}; use the Python package.\n\n'
        '=== "Python package"\n\n    ```console\n    python -m edi {command}\n    ```\n'
    )
    parts = [
        f'# {title}\n',
        (
            'Nothing to fit: edi calculates from the model as the project holds it, as the Python '
            'tutorial does.\n'
        ),
        '## Get the project\n',
        tabs(f'download-data {case}'),
        '## Calculate\n',
        (
            'Calculate the project without writing the result back (drop `--dry` to save it into '
            'the project). The output names what was calculated and a checksum of it; the time it '
            'took is left out here.\n'
        ),
        python_only.format(
            why='The standalone executable fits measured data only', command=f'calc {case} --dry'
        ),
        '```text\n' + '\n'.join(output) + '\n```\n',
        '## Report\n',
        'Write the HTML report of the project and open it in a browser.\n',
        python_only.format(
            why='The standalone executable has no `report`',
            command=f'report {case} --output {case}.html',
        ),
    ]
    PAGES.mkdir(parents=True, exist_ok=True)
    page = PAGES / f'{case}.md'
    page.write_text('\n'.join(parts), encoding='utf-8')
    return page


def render(case: str, binary: Path) -> Path:  # noqa: PLR0914, PLR0915 - one page, step by step
    import edi  # noqa: PLC0415 - only rendering needs the package; the stage parsing does not

    source = (ROOT / f'docs/user/tutorials/{case}.py').read_text(encoding='utf-8')
    title = re.search(r'^# # (.+)$', source, flags=re.MULTILINE).group(1)
    if 'project.calculate()' in source and '.free = True' not in source:
        return render_calculation(case, title)
    with tempfile.TemporaryDirectory(prefix=f'cli-tutorial-{case}-') as scratch:
        work = Path(scratch) / case
        shutil.copytree(ROOT / f'docs/user/cli/{case}/project', work)
        project = edi.Project.load(str(work))
        # One save first, so every snapshot below is in edi's own layout and only the edits differ.
        project.save_as(str(work))
        created = set(re.findall(r"\.(?:aliases|constraints)\.create\(id='([^']+)'", source))
        for collection in (project.analysis.constraints, project.analysis.aliases):
            for item_id in [item.id for item in collection if item.id in created]:
                collection.remove(item_id)
        before = snapshot(work)
        for parameter in project.free_parameters:
            parameter.free = False
        project.save_as(str(work))
        parts = [
            f'# {title}\n',
            (
                'The same staged fit as the Python tutorial, on the command line. The command '
                'line fits whatever the project marks free with `()` after a value, so each stage '
                "marks its parameters in the project's files with a text editor and runs "
                '`edi fit`, which writes the fitted values back into the project for the next '
                'stage.' + (BY_HAND if 'project.structures.create(' in source else '') + '\n'
            ),
            '## Get the project\n',
            tabs(f'download-data {case}'),
            '## Start with nothing free\n',
            (
                'The project marks what its finished fit frees. Remove every `()`, so the stages '
                'below free one group at a time.\n'
            ),
            edited(
                changes(before, snapshot(work), set()),
                {'fixed': 'remove the `()` from every value; they now read'},
            ),
        ]
        namespace = {'project': project}
        exec(names(source), namespace)  # noqa: S102 - the tutorial's own name lines
        auto: set[str] = set()

        def step(
            title: str, text: str, code: list[str], shown: int = 0, verbosity: str = 'full'
        ) -> None:
            """Apply `code`, show its edits, run edi fit and show its output.

            With `shown`, only the output's first and last `shown` lines.
            """
            nonlocal project
            lines = []
            for line in code:
                estimate = re.match(r'(\s*)(\w+)\.background\.auto_estimate\((.*)\)$', line)
                if estimate:
                    indent, var, args = estimate.groups()
                    auto.add(var)
                    lines.append(f"{indent}{var}.background_estimate.mode = 'auto'")
                    for key, value in re.findall(r'(\w+)=([^,]+)', args):
                        lines.append(f'{indent}{var}.background_estimate.{key} = {value}')
                    continue
                freed = re.match(r'for point in (\w+)\.background:', line)
                if freed and freed.group(1) in auto:
                    lines.append(f"{freed.group(1)}.background_estimate.mode = 'manual'")
                    auto.discard(freed.group(1))
                # A sample displacement fixed at zero is not saved, so it is absent after a reload.
                optional = re.match(r'(\s*)(.+\.calib_sample_\w+)\.free = True$', line)
                if optional and eval(optional.group(2), namespace) is None:  # noqa: S307
                    lines.append(f'{optional.group(1)}{optional.group(2)} = 0')
                lines.append(line)
            before = snapshot(work)
            exec('\n'.join(lines), namespace)  # noqa: S102 - the tutorial's own lines
            project.save_as(str(work))
            # The rows whose values the stage sets: `atom_sites['Co1'].adp_iso = 0.5` names Co1.
            rows = frozenset(re.findall(r"\['([^']+)'\]\.\w+ = (?!True|False)", '\n'.join(lines)))
            edits = changes(before, snapshot(work), created, rows)
            run = subprocess.run(
                [str(binary), 'fit', case, '--verbosity', verbosity],
                cwd=scratch,
                capture_output=True,
                text=True,
                check=True,
            )
            output = run.stdout.rstrip().splitlines()
            if shown and len(output) > 2 * shown:
                output = [*output[:shown], '…', *output[-shown:]]
            project = edi.Project.load(str(work))
            namespace['project'] = project
            exec(names(source), namespace)  # noqa: S102
            parts.extend([
                f'## {title}\n',
                text + '\n' if text else '',
                edited(edits),
                tabs(f'fit {case}' + (' --verbosity full' if verbosity == 'full' else '')),
                '```text\n' + '\n'.join(output) + '\n```\n',
            ])

        # What the tutorial does before its stages, a scan's single template fit and an estimated
        # background, joins the first stage: edi fit needs something free to fit.
        start = source.index('## Perform the analysis')
        before_lines, notes = [], []
        if "fitting_mode = 'single'" in source[:start]:
            before_lines.append("project.analysis.fitting_mode = 'single'")
            notes.append(
                'Switch the fitting mode to a single fit, so the stages fit the template alone.'
            )
        estimates = re.findall(
            r'^\w+\.background\.auto_estimate\(.*\)$', source[:start], flags=re.MULTILINE
        )
        if estimates:
            before_lines += estimates
            notes.append(
                'Set the background to its automatic estimate in the experiment file: each fit '
                'places its points first, by the arPLS method, a smooth curve under the pattern '
                'that ignores the peaks.'
            )
        first_stage = stages(source)[0]
        step(
            first_stage['title'],
            ' '.join([*notes, first_stage['text']]).strip(),
            [*before_lines, *first_stage['edits']],
        )
        first = 1
        for number, stage in enumerate(stages(source)[first:], start=first + 1):
            step(stage['title'] or f'Stage {number}', stage['text'], stage['edits'])
        if "fitting_mode = 'sequential'" in source:
            step(
                'Fit the scan',
                'Back to the sequential mode: every pattern is fitted in turn, each from the fit '
                'before it.',
                ["project.analysis.fitting_mode = 'sequential'"],
                shown=6,
                verbosity='compact',
            )
        if case in FROM_FILE:
            parts += ['## Your own measured data\n', FROM_FILE_TEXT]
        parts += [
            '## Report\n',
            'Write the HTML report of the fitted project and open it in a browser.\n',
            (
                '=== "Standalone executable"\n\n'
                '    The standalone executable has no `report`; use the Python package.\n\n'
                '=== "Python package"\n\n    ```console\n'
                f'    python -m edi report {case} --output {case}.html\n    ```\n'
            ),
        ]
    PAGES.mkdir(parents=True, exist_ok=True)
    page = PAGES / f'{case}.md'
    page.write_text('\n'.join(part for part in parts if part), encoding='utf-8')
    return page


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cases', nargs='+')
    parser.add_argument('--binary', type=Path, default=ROOT / 'build/ci/cli/easydiffraction')
    args = parser.parse_args()
    for case in args.cases:
        print(render(case, args.binary.resolve()))


if __name__ == '__main__':
    main()
