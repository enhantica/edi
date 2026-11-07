"""Capture decided pin and metadata changes without rewriting the original retention oracle."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
PINS = (
    'pd-neut-tof_ncaf-wish-2bank_start-3',
    'pd-neut-tof_ncaf-wish-3bank_start-5',
    'pd-neut-tof_ncaf-wish-5bank_start-5',
    'pd-neut-tof_ncaf-wish-5bank_start-fullprof',
    'pd-neut-tof_si-sepd_start-2',
    'pd-neut-tof_si-sepd_start-5',
    'pd-neut-tof_cecoal-polaris_chebyshev',
    'pd-neut-tof_ceo2-pearl_polynomial',
    'pd-neut-tof_ferrite-austenite-beer_joint',
)


def committed(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)


def reference_rows(value, prefix=''):
    output = {}
    if isinstance(value, dict):
        if value.get('kind') == 'reference':
            output[prefix] = value
        for key, child in value.items():
            output.update(reference_rows(child, prefix + '/' + key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            output.update(reference_rows(child, prefix + '/' + str(index)))
    return output


def extend_stop_rule(before_commit, after_commit):
    target = HERE / 'retention-adaptations.json'
    document = json.loads(target.read_text())
    paths = subprocess.check_output(
        [
            'git',
            'diff',
            '--name-only',
            before_commit,
            after_commit,
            '--',
            'docs/user/cli/*/expected.json',
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    for path in paths:
        before, after = committed(before_commit, path), committed(after_commit, path)
        old, new = json.loads(before), json.loads(after)
        assert reference_rows(old) == reference_rows(new), (
            'Stop-rule re-pins preserve every independent reference and its tolerance'
        )

        def compare(left, right, trail=(), old=old, path=path):
            if isinstance(left, dict) and isinstance(right, dict):
                assert left.keys() == right.keys(), (
                    'A stop-rule re-pin retains its complete schema'
                )
                for key in left:
                    compare(left[key], right[key], (*trail, key), old=old, path=path)
            elif left != right:
                if trail[-1] == 'value':
                    parent = old
                    for key in trail[:-1]:
                        parent = parent[key]
                    assert parent['kind'] == 'regression-pin', (
                        'Only an explicitly labelled regression value can be re-pinned'
                    )
                else:
                    assert (
                        path.endswith('pd-xray-cwl_latp-bm01_scan/expected.json')
                        and trail == ('variants', 'asymmetry-off', 'status')
                        and left == 'max_iter'
                        and right == 'done'
                    ), 'Only the documented LATP completion outcome changes outside pin values'

        compare(old, new)
        assert (ROOT / path).read_bytes() == after, (
            'The archived stop-rule replacement equals the complete committed project pin'
        )
        row = document['files'].get(path)
        original = row['before'].encode() if row else before
        document['files'][path] = {
            'source_commit': after_commit,
            'reason': (
                'Shift/s.u. root fix; exact regression re-pins '
                'with unchanged references and tolerances'
            ),
            'before_sha256': hashlib.sha256(original).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
            'before': original.decode(),
            'after': after.decode(),
        }
    source = json.loads(
        (ROOT / 'tests/fixtures/c34_t23_cli_projects/source-objects.json').read_text()
    )['projects']
    projects = json.loads(
        (ROOT / 'tests/fixtures/c34_t23_cli_projects/project-ids.json').read_text()
    )['source_to_project']
    for seed in ('cosio-d20-s1', 'cosio-d20-s4', 'lbco-hrpt-s2', 'lbco-hrpt-s4'):
        path = 'docs/user/cli/' + projects[seed] + '/expected.json'
        original = subprocess.check_output(
            ['git', 'cat-file', 'blob', source[seed]['expected.json']], cwd=ROOT
        )
        if seed == 'lbco-hrpt-s2':
            original = (
                ROOT / 'tests/fixtures/background_estimate/cli-expected-before.json'
            ).read_bytes()
        after = committed(after_commit, path)
        old, new = json.loads(original), json.loads(after)
        assert reference_rows(old) == reference_rows(new), (
            'Historical seed adaptation preserves every independent reference and tolerance'
        )
        compare(old, new, old=old, path=path)
        document['files'][path] = {
            'source_commit': after_commit,
            'reason': 'Exact historical seed pins through the stop-rule and FCJ changes',
            'before_sha256': hashlib.sha256(original).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
            'before': original.decode(),
            'after': after.decode(),
        }
    target.write_text(json.dumps(document, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stop-rule-before')
    parser.add_argument('--stop-rule-after')
    args = parser.parse_args()
    if args.stop_rule_before or args.stop_rule_after:
        if not (args.stop_rule_before and args.stop_rule_after):
            parser.error('Both committed endpoints are required')
        extend_stop_rule(args.stop_rule_before, args.stop_rule_after)
        return
    files = {}
    paths = [(case + '/expected.json', 'b339d832') for case in PINS]
    paths.append(('pd-neut-cwl_y2o3_beta-adp/project/project.edi', '34168971'))
    for suffix, commit in paths:
        path = 'docs/user/cli/' + suffix
        before, after = committed('3a6b4dc8', path), committed(commit, path)
        if suffix.endswith('expected.json'):
            assert reference_rows(json.loads(before)) == reference_rows(json.loads(after)), (
                'Decided pin changes retain every correctness reference and tolerance'
            )
            reason = (
                'Decided descent recovery and out-of-range TOF tails; '
                'documented before/after regression pins'
            )
        else:
            fields = (b'_metadata.title ', b'_metadata.instrument ', b'_metadata.facility ')
            strip = lambda data, fields=fields: b''.join(  # noqa: E731 - exact byte projection
                line for line in data.splitlines(keepends=True) if not line.startswith(fields)
            )
            assert strip(before) == strip(after), 'The Y2O3 change is descriptive metadata only'
            reason = 'Main supplies SPODI at FRM II; all scientific bytes remain unchanged'
        assert (ROOT / path).read_bytes() == after, (
            'Capture only the declared committed replacement'
        )
        files[path] = {
            'source_commit': commit,
            'reason': reason,
            'before_sha256': hashlib.sha256(before).hexdigest(),
            'after_sha256': hashlib.sha256(after).hexdigest(),
            'before': before.decode(),
            'after': after.decode(),
        }
    (HERE / 'retention-adaptations.json').write_text(json.dumps({'files': files}, indent=2) + '\n')


if __name__ == '__main__':
    main()
