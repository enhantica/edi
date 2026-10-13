"""Freeze pre-change saved correlation bytes with a declared, existing Release build.

This generator runs only while authoring. Delivered gates read its committed bytes.
The bytes are serialization regression pins, not independent fitted physics.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REFERENCE = 'bd72193898d2dc6fefb1d692703d1f7a4137c731'
HERE = Path(__file__).resolve().parent
SUBJECTS = {
    'single': 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project',
    'scan': 'docs/user/cli/pd-neut-cwl_cosio-d20_scan-3f/project',
}


def hashes(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def loop_bytes(contents):
    match = re.search(rb'(?m)^loop_\n(?:_fit_parameter_correlation\.[^\n]+\n)+', contents)
    if match is None:
        raise ValueError('The pre-change fit must save its complete correlation loop')
    end = re.search(rb'(?m)^(?:loop_|_|data_)', contents[match.end() :])
    return contents[match.start() : match.end() + end.start() if end else len(contents)]


def freeze_numeric_tables(output):
    """Project the retained producer's fitted coefficients into row-free numeric inputs."""
    provenance = json.loads((output / 'saved-provenance.json').read_text())
    tables = {'claim': 'REGRESSION INPUT: frozen pre-change fitted numeric tables', 'cases': {}}
    for case, receipt in provenance['cases'].items():
        frozen = (output / (case + '-correlations.edi')).read_bytes()
        if hashlib.sha256(frozen).hexdigest() != receipt['loop_sha256']:
            raise ValueError(
                'The numeric input must come from the unchanged frozen producer bytes'
            )
        rows = [line.split() for line in frozen.decode().splitlines() if ' deterministic ' in line]
        names = list(dict.fromkeys(name for row in rows for name in row[2:4]))
        pairs = [(names[i], names[j]) for i in range(len(names)) for j in range(i + 1, len(names))]
        if [(row[2], row[3]) for row in rows] != pairs:
            raise ValueError('The retained fit must declare the complete packed column order')
        data = '\n'.join([
            str(len(names)),
            *names,
            str(len(rows)),
            *[float(row[4]).hex() for row in rows],
            '',
        ])
        destination = output / (case + '-numeric.table')
        destination.write_text(data)
        tables['cases'][case] = {
            'producer_loop_sha256': receipt['loop_sha256'],
            'numeric_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
        }
    (output / 'numeric-provenance.json').write_text(json.dumps(tables, indent=2) + '\n')


def capture(reference, output):
    import edi  # noqa: PLC0415 - selected source and compiled module belong to the old build

    revision = subprocess.check_output(
        ['git', '-C', str(reference), 'rev-parse', 'HEAD'], text=True
    ).strip()
    if revision != REFERENCE or not edi.__build_commit__.startswith(REFERENCE):
        raise ValueError(
            'The saved-byte reference must be the declared pre-change compiled source'
        )
    manifest = {
        'claim': 'REGRESSION PIN: pre-change saved bytes',
        'reference': REFERENCE,
        'cases': {},
    }
    for name, relative in SUBJECTS.items():
        with tempfile.TemporaryDirectory(prefix='retained-correlation-') as temporary:
            source = Path(temporary) / 'input'
            shutil.copytree(reference / relative, source)
            project_file = source / 'project.edi'
            text = project_file.read_text()
            for field in ['created', 'last_modified']:
                text = re.sub(r'(?m)^_metadata\.' + field + r'[^\n]*\n?', '', text)
                text += '\n_metadata.' + field + ' "01 Jan 2099 00:00:00"\n'
            project_file.write_text(text)
            for filename in ['results.csv', 'results-provenance.csv', 'scan-notes.csv']:
                (source / 'analysis' / filename).unlink(missing_ok=True)
            if name == 'scan':
                template = sorted((source / 'experiments/d20_scan').glob('*.dat'))[1].name
                analysis = source / 'analysis/analysis.edi'
                analysis.write_text(
                    analysis.read_text() + '\n_sequential_fit.template_file ' + template + '\n'
                )
            input_hashes = hashes(source)
            shutil.copytree(source, output / (name + '-input'), dirs_exist_ok=True)
            project = edi.Project.load(source)
            result = project.fit_sequential() if name == 'scan' else project.fit()
            if result.status != edi.FitStatus.DONE:
                raise ValueError('The reference subject must complete its real fit: ' + name)
            saved = Path(temporary) / 'saved'
            project.save_as(saved)
            data = (saved / 'analysis/analysis.edi').read_bytes()
            loop = loop_bytes(data)
            (output / (name + '-analysis.edi')).write_bytes(data)
            (output / (name + '-correlations.edi')).write_bytes(loop)
            manifest['cases'][name] = {
                'source': relative,
                'input_sha256': input_hashes,
                'analysis_sha256': hashlib.sha256(data).hexdigest(),
                'loop_sha256': hashlib.sha256(loop).hexdigest(),
            }
    (output / 'saved-provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
    freeze_numeric_tables(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    capture(args.reference.resolve(), args.output)


if __name__ == '__main__':
    main()
