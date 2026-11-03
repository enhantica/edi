"""Adapt only the app-oracle input identities for the manual estimate category."""

import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from tests.fixtures.background_estimate.manual_bytes import without_category

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = '74d6311c74cdba65431dbe8cfe4c9be4e46233b4'
PROJECT = 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project'
EXPERIMENT = 'experiments/hrpt.edi'


def parse(text):
    return json.loads(text.split('var frozen = ', 1)[1].removesuffix(';\n'))


def adapt_text(name, original, old_hash, new_hash):
    expected = copy.deepcopy(parse(original))
    if name == 'oracle.js':
        corpus = [row for row in expected['corpus'] if row['project'] == PROJECT]
        projects = [row for row in expected['projects'] if row['path'] == PROJECT]
        assert len(corpus) == len(projects) == 1, (
            'The retained oracle contains exactly one LBCO corpus and project witness'
        )
        assert corpus[0]['sha256'] == projects[0]['files'][EXPERIMENT] == old_hash, (
            'Both app-oracle identities retain the authenticated pre-category input digest'
        )
        corpus[0]['sha256'] = new_hash
        projects[0]['files'][EXPERIMENT] = new_hash
        updated = original.replace(old_hash, new_hash)
    else:
        target = PROJECT + '/' + EXPERIMENT
        assert expected['sources'][target] == old_hash, (
            'The display oracle retains the authenticated pre-category input digest'
        )
        expected['sources'][target] = new_hash
        old = json.dumps(target) + ': ' + json.dumps(old_hash)
        new = json.dumps(target) + ': ' + json.dumps(new_hash)
        assert original.count(old) == 1, (
            'The display adaptation changes only the published LBCO source identity'
        )
        updated = original.replace(old, new, 1)
    assert parse(updated) == expected, (
        'The source-hash adaptation preserves every frozen numerical and display expectation'
    )
    return updated


def main():
    before = (HERE / 'cli-before.edi').read_bytes()
    after = (ROOT / PROJECT / EXPERIMENT).read_bytes()
    assert without_category(after) == before, (
        'The app-oracle adaptation admits only the manual/arpls category and separator'
    )
    old_hash, new_hash = (hashlib.sha256(data).hexdigest() for data in (before, after))
    executable = shutil.which('git')
    if executable is None:
        raise SystemExit('Git is required to authenticate the retained app-oracle bytes')
    receipt = {
        'claim': 'INPUT BYTES: manual estimate category; all numerical expectations unchanged',
        'repository': 'https://github.com/enhantica/edi',
        'before_commit': BASE,
        'command': 'python -m tests.fixtures.background_estimate.adapt_oracles',
        'input_before_sha256': old_hash,
        'input_after_sha256': new_hash,
        'files': {},
    }
    for name in ('oracle.js', 'display_oracle.js'):
        relative = 'tests/fixtures/e04_t1/' + name
        original = subprocess.check_output(
            [executable, '-C', str(ROOT), 'show', BASE + ':' + relative], text=True
        )
        updated = adapt_text(name, original, old_hash, new_hash)
        destination = ROOT / relative
        assert destination.read_text() in {original, updated}, (
            'The app-oracle adaptation refuses any unrelated live fixture change'
        )
        destination.write_text(updated)
        receipt['files'][relative] = {
            'before_sha256': hashlib.sha256(original.encode()).hexdigest(),
            'after_sha256': hashlib.sha256(updated.encode()).hexdigest(),
        }
    output = HERE / 'app-oracle-bytes.json'
    contents = json.dumps(receipt, indent=2, sort_keys=True) + '\n'
    if output.exists():
        assert output.read_text() == contents, (
            'The app-oracle adaptation cannot replace its independently committed receipt'
        )
    else:
        output.write_text(contents)
    print(contents, end='')


if __name__ == '__main__':
    main()
