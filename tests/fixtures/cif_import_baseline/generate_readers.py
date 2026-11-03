"""Capture labelled reader regression pins from the pre-import main model."""

import gzip
import importlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from tests.fixtures import cif_import_cases as case


def saved_columns(text):
    """Observe CIF1 columns with Gemmi, preserving CIF2 list cells (ADR-0097)."""
    if not text.startswith('#\\#CIF_2.0\n'):
        return case.columns(text)
    # Quoted values, comments and text fields must not expose their brackets.
    tokens = list(
        re.finditer(
            r'(?m:^;[\s\S]*?^;(?=\s|$))|#[^\n]*|'
            r"'[^\n]*?'(?=\s|$|\])|\"[^\n]*?\"(?=\s|$|\])|[\[\]]|[^\s\[\]]+",
            text,
        )
    )
    spans = list_spans(tokens)
    replacements = {}
    for start, end in reversed(spans):
        marker = f'CIF2_LIST_CELL_{start}_END'
        if marker in text:
            message = 'CIF2 observer marker collision'
            raise ValueError(message)
        replacements[marker] = text[start:end]
        text = text[:start] + marker + text[end:]
    return {
        tag: [replacements.get(value, value) for value in values]
        for tag, values in case.columns(text).items()
    }


def list_spans(tokens):
    spans = []
    opening = None
    depth = 0
    for token in tokens:
        if token[0] == '[':
            if depth == 0:
                opening = token.start()
            depth += 1
        elif token[0] == ']':
            depth -= 1
            if depth < 0:
                message = 'Unmatched CIF2 list closing bracket'
                raise ValueError(message)
            if depth == 0:
                spans.append((opening, token.end()))
    if depth:
        message = 'Unterminated CIF2 list'
        raise ValueError(message)
    return spans


PATH_MOVES = {
    'sc-neut-cwl_pr2nio4-5c2_fit/': 'sc-neut-cwl_pr2nio4-5c2/',
    'sc-neut-cwl_tb2ti2o7-heidi_fit/': 'sc-neut-cwl_tb2ti2o7-heidi/',
    'sc-neut-tof_taurine_fit/': 'sc-neut-tof_taurine-senju/',
}


def source_path(relative):
    for before, after in PATH_MOVES.items():
        relative = relative.replace(before, after)
    return case.ROOT / relative


def normalized(text):
    cells = saved_columns(text)
    return {
        tag: values
        for tag, values in cells.items()
        if not re.match(
            r'_(?:experiment_type_(?:dimensionality|polarisation)|instrument_(?:name|facility))$',
            tag,
        )
    }


def generate():
    rows = []
    api = importlib.import_module(case.API)
    paths = subprocess.check_output(
        [shutil.which('git'), 'ls-files', '--', '*.edi', '*.cif', '*.CIF'],
        cwd=case.ROOT,
        text=True,
    ).splitlines()
    for relative in paths:
        if relative.startswith(('tests/unit/', 'tests/integration/', 'tests/system/')):
            continue
        path = case.ROOT / relative
        if 'structures' in path.parts:
            kinds = ['structure']
        elif 'experiments' in path.parts:
            kinds = ['experiment']
        elif path.suffix.lower() == '.cif':
            kinds = ['structure', 'experiment']
        else:
            continue
        for kind in kinds:
            try:  # noqa: PLW0717 - capture only successful baseline reads
                factory = api.StructureFactory if kind == 'structure' else api.ExperimentFactory
                obj = factory.from_cif_path(path)
                project = case.attach(api, kind, obj)
                with tempfile.TemporaryDirectory() as scratch:
                    saved = Path(scratch) / 'saved'
                    project.save_as(saved)
                    folder = saved / ('structures' if kind == 'structure' else 'experiments')
                    files = list(folder.glob('*.edi'))
                    if len(files) != 1:
                        raise RuntimeError  # noqa: TRY301 - refuse ambiguous observer output
                    text = files[0].read_text()
                rows.append({'path': relative, 'kind': kind, 'values': normalized(text)})
            except (ValueError, RuntimeError):
                pass
    payload = {
        'label': 'Regression pins of main readers, not independent physical references',
        'baseline': subprocess.check_output(
            [shutil.which('git'), 'rev-parse', 'HEAD'], cwd=case.ROOT, text=True
        ).strip(),
        'rows': rows,
    }
    Path(__file__).with_name('readers-before.json.gz').write_bytes(
        gzip.compress(json.dumps(payload, separators=(',', ':')).encode(), mtime=0)
    )


def generate_save_transitions():
    """Capture labelled regression pins for ADR-0092's rounded save."""
    baseline = json.loads(
        gzip.decompress(Path(__file__).with_name('readers-before.json.gz').read_bytes())
    )
    api = importlib.import_module(case.API)
    rows = []
    refused = []
    for row in baseline['rows']:
        factory = api.StructureFactory if row['kind'] == 'structure' else api.ExperimentFactory
        print(row['kind'], row['path'], flush=True)
        obj = factory.from_cif_path(source_path(row['path']))
        project = case.attach(api, row['kind'], obj)
        with tempfile.TemporaryDirectory() as scratch:
            project.save_as(Path(scratch) / 'saved')
            folder = (
                Path(scratch)
                / 'saved'
                / ('structures' if row['kind'] == 'structure' else 'experiments')
            )
            files = list(folder.glob('*.edi'))
            if len(files) != 1:
                raise RuntimeError
            try:
                actual = normalized(files[0].read_text())
            except ValueError as error:
                refused.append({'kind': row['kind'], 'path': row['path'], 'error': str(error)})
                continue
        before = row['values']
        changes = {
            tag: {'before': before.get(tag), 'after': actual.get(tag)}
            for tag in sorted(before.keys() | actual.keys())
            if before.get(tag) != actual.get(tag)
        }
        if changes:
            rows.append({'kind': row['kind'], 'path': row['path'], 'changes': changes})
    payload = {
        'label': 'Rounded-save regression pins, not independent physical references',
        'adr': 'ADR-0092 sections 7 and 8; ADR-0106 published state',
        'refused': refused,
        'rows': rows,
    }
    Path(__file__).with_name('rounded-save-transitions.json.gz').write_bytes(
        gzip.compress(json.dumps(payload, separators=(',', ':')).encode(), mtime=0)
    )


if __name__ == '__main__':
    import sys

    if sys.argv[1:] == ['--rounded-save-transitions']:
        generate_save_transitions()
    else:
        generate()
