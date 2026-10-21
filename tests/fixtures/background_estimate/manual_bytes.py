"""Labelled manual-settings byte extension; retain the original serialization pins."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from tests.fixtures.c34_t28_baseline import generate_bytes as legacy
from tests.fixtures.cwl_family.historical import original_tokens
from tests.fixtures.weight_fractions.single_phase_bytes import historical_single_fraction

HERE = Path(__file__).resolve().parent
EXPERIMENT = 'experiments/hrpt.edi'
CASES = {'corpus:lbco-hrpt-s2/project', 'repo:docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project'}
BLOCK = b'_background_estimate.mode manual\n_background_estimate.method arpls\n\n'


def without_category(contents):
    assert contents.count(BLOCK) == 1, (
        'The manual estimate byte extension requires exactly its canonical block'
    )
    assert len(re.findall(rb'(?m)^_background_estimate\.', contents)) == 2, (
        'The manual estimate byte extension requires exactly its two declared canonical lines'
    )
    return contents.replace(BLOCK, b'', 1)


def require_bytes(contents, before, after):
    assert hashlib.sha256(contents).hexdigest() == after, (
        'The labelled manual estimate regression pin retains every new experiment byte'
    )
    assert hashlib.sha256(without_category(contents)).hexdigest() == before, (
        'The manual estimate adaptation changes only its two category lines and separator'
    )


def adapted_pin(expected, source):
    receipt = json.loads((HERE / 'manual-bytes.json').read_text())
    assert receipt['claim'].startswith('REGRESSION PIN:'), (
        'Engine-generated serialization identities must be labelled regression pins'
    )
    result = {key: dict(value) for key, value in expected.items()}
    for channel in ('input_sha256', 'saved_sha256'):
        assert receipt['before'][channel] == expected[channel][EXPERIMENT], (
            'The manual estimate extension retains the immutable historical experiment pin'
        )
        result[channel][EXPERIMENT] = receipt['after'][channel]
    require_input(source, expected['input_sha256'][EXPERIMENT], result['input_sha256'][EXPERIMENT])
    return result


def require_input(source, before, after):
    require_bytes(original_tokens((source / EXPERIMENT).read_bytes()), before, after)


def require_saved(directory, before, after):
    contents = historical_single_fraction(EXPERIMENT, (directory / EXPERIMENT).read_bytes())
    require_bytes(legacy.without_saved_calculator(EXPERIMENT, contents), before, after)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', action='store_true', required=True)
    parser.parse_args()
    destination = HERE / 'manual-bytes.json'
    if destination.exists():
        parser.error('the labelled regression receipt cannot overwrite an existing pin')
    case = 'corpus:lbco-hrpt-s2/project'
    baseline = json.loads(
        (legacy.ROOT / 'tests/fixtures/c34_t28_baseline/saved-bytes.json').read_text()
    )
    before = {
        key: baseline['cases'][case][key][EXPERIMENT] for key in ('input_sha256', 'saved_sha256')
    }
    source = legacy.inputs()[case]
    data = original_tokens((source / EXPERIMENT).read_bytes())
    after = {'input_sha256': hashlib.sha256(data).hexdigest()}
    require_bytes(data, before['input_sha256'], after['input_sha256'])
    with tempfile.TemporaryDirectory() as temporary:
        saved = Path(temporary) / 'saved'
        legacy.observe(source, saved)
        data = legacy.without_saved_calculator(
            EXPERIMENT, historical_single_fraction(EXPERIMENT, (saved / EXPERIMENT).read_bytes())
        )
        after['saved_sha256'] = hashlib.sha256(data).hexdigest()
        require_bytes(data, before['saved_sha256'], after['saved_sha256'])
    executable = shutil.which('git')
    if executable is None:
        parser.error('Git is required to record the serialization source identity')
    commit = subprocess.check_output(
        [executable, '-C', str(legacy.ROOT), 'rev-parse', 'HEAD'], text=True
    ).strip()
    receipt = {
        'claim': 'REGRESSION PIN: manual estimate settings serialization; no physics oracle',
        'repository': 'https://github.com/enhantica/' + legacy.PACKAGE,
        'source_commit': commit,
        'command': 'python -m tests.fixtures.background_estimate.manual_bytes --record',
        'before': before,
        'after': after,
    }
    if legacy.PACKAGE == 'edi':
        receipt['crysta_commit'] = (
            (legacy.ROOT / 'build/ci/.crysta-linked-sha').read_text().strip()
        )
    destination.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
