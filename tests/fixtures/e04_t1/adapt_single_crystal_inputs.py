"""Bounded source-only adaptation of the existing single-crystal GUI witnesses.

The original frozen files are independently matched to committed f0fc35eb bytes.
Current expectations are parsed from committed input text, never app/engine output.
Powder witnesses, scientific fit references and registry order are retained.
"""

import copy
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import generate as category_inputs
import generate_display as display_inputs

from tests.fixtures.example_catalogue.migrate_single_crystal_ids import (
    historical_path,
    renamed,
    same_science,
)

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = '379901ca'
ARCHIVE = 'f0fc35eb'
PROJECT_IDS = (
    'sc-neut-cwl_pr2nio4-5c2_basic',
    'sc-neut-cwl_tb2ti2o7-heidi_basic',
    'sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction',
    'sc-neut-cwl_tb2ti2o7-heidi_anisotropic-adp',
    'sc-neut-cwl_tb2ti2o7-heidi',
    'sc-neut-cwl_pr2nio4-5c2',
    'sc-neut-tof_taurine-unknown_basic',
    'sc-neut-tof_taurine-senju',
)
PATHS = {'docs/user/cli/' + name + '/project' for name in PROJECT_IDS}


def archived(rev, relative):
    return subprocess.check_output([
        'git',
        '-C',
        str(ROOT),
        'show',
        rev + ':' + historical_path(relative),
    ])


def read(text):
    return json.loads(text.split('var frozen = ', 1)[1].removesuffix(';\n'))


def replace_rows(previous, fresh, key):
    replacement = {path: [row for row in fresh if row[key] == path] for path in PATHS}
    result, inserted = [], set()
    for row in previous:
        path = row[key]
        if path not in PATHS:
            result.append(row)
        elif path not in inserted:
            assert replacement[path], (
                'Source adaptation must retain every selected project witness'
            )
            result.extend(replacement[path])
            inserted.add(path)
    assert inserted == PATHS, (
        'Source adaptation must cover exactly the declared single-crystal projects'
    )
    return result


def generate():
    baseline = archived(BASE, 'tests/fixtures/e04_t1/oracle.js').decode()
    display_baseline = archived(BASE, 'tests/fixtures/e04_t1/display_oracle.js').decode()
    oracle, display = renamed(read(baseline)), renamed(read(display_baseline))
    selected = [p for p in oracle['projects'] if p['id'] in PROJECT_IDS]
    assert len(selected) == len(PROJECT_IDS), (
        'Source adaptation must name all and only the existing eight single-crystal projects'
    )
    for project in selected:
        for relative, expected in project['files'].items():
            assert (
                hashlib.sha256(archived(ARCHIVE, project['path'] + '/' + relative)).hexdigest()
                == expected
            ), (
                'Source adaptation must prove every old project-file pin '
                'against committed historical bytes'
            )
    for path in PATHS:
        for current in (ROOT / path).rglob('*.edi'):
            before = archived(BASE, current.relative_to(ROOT).as_posix())
            after = current.read_bytes()
            assert (
                same_science(before, after) if current.name == 'project.edi' else before == after
            ), 'Source adaptation must use only the reviewed committed current input bytes'
    # Independently reviewed zero-effect case named by the conductor: the
    # entire reflection body and every other byte are identical.
    relative = 'docs/user/cli/sc-neut-cwl_pr2nio4-5c2_basic/project/experiments/pr2nio4.edi'
    before, after = archived('250b87b6', relative), (ROOT / relative).read_bytes()
    old = (
        b'_extinction.type becker-coppens\n_extinction.model gauss\n'
        b'_extinction.radius 0\n_extinction.mosaicity 0\n'
    )
    assert (
        hashlib.sha256(before).hexdigest()
        == 'deb6c159d59a8bb7c6518844f593681bb22f5fa5af480f56bb95a0ff10eca891'
    ), 'Zero-effect source adaptation must begin at the exact independently frozen experiment'
    assert (
        before.count(old) == 1 and before.replace(old, b'_extinction.type none\n', 1) == after
    ), (
        'Zero-effect source adaptation must retain every byte '
        'outside the zero extinction declaration'
    )
    assert (
        hashlib.sha256(after).hexdigest()
        == 'f46766cc6784c097c10fa90a1763ee630032c49e3630a34eef2beab7d8554ca7'
    ), 'Zero-effect source adaptation must end at the reviewed explicit-none experiment'
    with tempfile.TemporaryDirectory(prefix='e04-source-capture-') as scratch:
        category_inputs.generate(output_dir=scratch)
        display_inputs.generate(output_dir=scratch)
        fresh = read((Path(scratch) / 'oracle.js').read_text())
        fresh_display = read((Path(scratch) / 'display_oracle.js').read_text())
    assert [p['id'] for p in oracle['projects']] == [p['id'] for p in fresh['projects']], (
        'Source adaptation must preserve the full registry and its order without filtering'
    )
    retained = copy.deepcopy(oracle)
    oracle['projects'] = replace_rows(oracle['projects'], fresh['projects'], 'path')
    oracle['corpus'] = replace_rows(oracle['corpus'], fresh['corpus'], 'project')
    assert [row for row in oracle['corpus'] if row['project'] not in PATHS] == [
        row for row in retained['corpus'] if row['project'] not in PATHS
    ], 'Source adaptation must preserve every powder corpus value and witness'
    display['cases'] = replace_rows(display['cases'], fresh_display['cases'], 'path')
    display['sources'] = {
        name: digest
        for name, digest in display['sources'].items()
        if not any(name.startswith(path + '/') for path in PATHS)
    }
    display['sources'].update({
        name: digest
        for name, digest in fresh_display['sources'].items()
        if any(name.startswith(path + '/') for path in PATHS)
    })
    for name, original, data in [
        ('oracle.js', baseline, oracle),
        ('display_oracle.js', display_baseline, display),
    ]:
        header = original.split('var frozen = ', 1)[0]
        (HERE / name).write_text(
            header
            + 'var frozen = '
            + json.dumps(data, indent=2, ensure_ascii=name == 'display_oracle.js')
            + ';\n'
        )


if __name__ == '__main__':
    generate()
