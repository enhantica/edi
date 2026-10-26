"""Freeze main's saved bytes as labelled regression pins, under both s.u. rules."""

import argparse
import hashlib
import importlib
import json
import re
import shutil
import subprocess
import tempfile
import warnings
from pathlib import Path


def staged(source, target, rule):
    target.mkdir(parents=True)
    for child in source.iterdir():
        if child.name != 'project.edi':
            shutil.copytree(
                child, target / child.name, symlinks=True
            ) if child.is_dir() else shutil.copy2(child, target / child.name)
    record = (
        (source / 'project.edi').read_text()
        if (source / 'project.edi').is_file()
        else '_edi.schema_version 3\n'
    )
    record = re.sub(r'(?m)^_su_format.rule\s+[^\n]*\n?', '', record)
    (target / 'project.edi').write_text(record + '\n_su_format.rule ' + rule + '\n')
    return target


def fingerprints(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        content = path.read_bytes()
        if relative == 'project.edi':
            content = re.sub(
                rb'(?m)^(_metadata\.(?:created|last_modified)[ \t]+)[^\r\n]+',
                rb'\1<CLOCK>',
                content,
            )
        if relative == 'analysis/analysis.edi':
            content = re.sub(
                rb'(?m)^(_fit_result.fitting_time[ \t]+)[^\r\n]+', rb'\1<CLOCK>', content
            )
        result[relative] = hashlib.sha256(content).hexdigest()
    return result


def sources(root):
    tracked = (
        subprocess
        .check_output([shutil.which('git'), 'ls-files', '-z'], cwd=root)
        .decode()
        .split('\0')
    )
    folders = {name.rsplit('/structures/', 1)[0] for name in tracked if '/structures/' in name}
    folders.update(str(Path(name).parent) for name in tracked if name.endswith('/project.edi'))
    return sorted(
        name
        for name in folders
        if (root / name / 'experiments').is_dir() and (root / name / 'structures').is_dir()
    )


def snapshot(api, source, scratch, rule):
    with warnings.catch_warnings(record=True) as notes:
        warnings.simplefilter('always')
        project = api.Project.load(staged(source, scratch / 'input', rule))
    if any('dependent_free_ignored' in str(note.message) for note in notes):
        message = 'The input marks a dependent free'
        raise ValueError(message)
    for parameter in project.parameters:
        if parameter.free and parameter.name in {
            'crystal_radius',
            'asym_beba_limit',
            'abscor2',
            'calib_d_to_tof_reciprocal',
        }:
            message = 'The input marks a descriptor or unsupported derivative free'
            raise ValueError(message)
    project.save_as(scratch / 'saved')
    return fingerprints(scratch / 'saved')


def fit_snapshot(api, source, scratch, rule):
    project = api.Project.load(staged(source, scratch / 'input', rule))
    project.analysis.fit()
    radius = project.experiments[0].extinction.crystal_radius
    if not radius.user_constrained or radius.uncertainty <= 0:
        message = 'The fitted dependent crystal radius must carry a propagated uncertainty'
        raise ValueError(message)
    project.save_as(scratch / 'saved')
    return fingerprints(scratch / 'saved')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api', required=True, choices=['crysta', 'edi'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    api = importlib.import_module(args.api)
    revision = subprocess.check_output(
        [shutil.which('git'), 'rev-parse', 'HEAD'], cwd=root, text=True
    ).strip()
    subprocess.run(
        [shutil.which('git'), 'merge-base', '--is-ancestor', revision, 'origin/main'],
        cwd=root,
        check=True,
    )
    record = {
        'kind': 'regression pin from main',
        'source_commit': revision,
        'normalization': ['metadata.created', 'metadata.last_modified', 'fit_result.fitting_time'],
        'projects': {},
        'excluded': {},
    }
    for name in sources(root):
        values = {}
        try:
            for rule in ('iucr_19', 'iucr_99'):
                with tempfile.TemporaryDirectory() as folder:
                    values[rule] = snapshot(api, root / name, Path(folder), rule)
        except (ValueError, RuntimeError, OSError) as error:
            record['excluded'][name] = (
                type(error).__name__
                + ': '
                + re.sub(r'/[^ \n:]+', '<path>', str(error).splitlines()[0])
            )
        else:
            record['projects'][name] = values
        print(name, 'saved' if name in record['projects'] else 'excluded', flush=True)
    record['fit_projects'] = {}
    case = 'docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction/project'
    record['fit_projects'][case] = {}
    for rule in ('iucr_19', 'iucr_99'):
        with tempfile.TemporaryDirectory() as folder:
            record['fit_projects'][case][rule] = fit_snapshot(api, root / case, Path(folder), rule)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
