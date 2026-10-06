"""build, surface and regression-image boundaries.

The screenshot checks are labelled regression pins; they do not certify the look.
The source checker closes the explicitly forbidden dictionary/JSON API seam and
carries adversarial inputs. Behavioral correctness is in tests/unit/app.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shlex
import struct
import tomllib
from pathlib import Path

import pytest
import yaml

from tests.integration.py.ci_runner_contract import self_hosted_runners

ROOT = Path(__file__).resolve().parents[3]
SCREENSHOTS = ROOT / 'docs/dev/design/app-screenshots'
PIN = 'a573a9695e53a0807de197785e12f9facd06da05'
FORBIDDEN = {
    'QVariant',
    'QVariantMap',
    'QVariantHash',
    'QVariantList',
    'QJsonObject',
    'QJsonArray',
    'QJsonDocument',
    'QJsonValue',
}


def without_comments(source):
    return re.sub(r'//[^\n]*|/\*.*?\*/', '', source, flags=re.DOTALL)


def api_violations(source):
    source = without_comments(source)
    forbidden = set(FORBIDDEN)
    aliases = re.findall(r'using\s+(\w+)\s*=\s*([^;]+);|typedef\s+([^;]+)\s+(\w+)\s*;', source)
    for _ in range(len(aliases) + 1):
        for name, value, old_value, old_name in aliases:
            if set(re.findall(r'\w+', value or old_value)) & forbidden:
                forbidden.add(name or old_name)
    surfaces = re.findall(r'Q_PROPERTY\s*\((.*?)\)|Q_INVOKABLE\s+([^;{]+)', source, re.DOTALL)
    fragments = [' '.join(parts) for parts in surfaces]
    fragments += re.findall(
        r'(?:Q_SIGNALS|signals|(?:public|protected|private)\s+(?:Q_SLOTS|slots))\s*:(.*?)(?=\n\s*(?:public|private|protected|signals|Q_SIGNALS)\s*:|\Z)',
        source,
        re.DOTALL,
    )
    return [part for part in fragments if set(re.findall(r'\w+', part)) & forbidden]


@pytest.mark.parametrize(
    'declaration',
    [
        'Q_PROPERTY(QVariantMap state READ state NOTIFY changed)',
        'Q_INVOKABLE QJsonObject snapshot() const;',
        'signals:\n void changed(QVariant state);\nprivate:\n int x;',
        'public slots:\n void replace(QJsonDocument state);',
        'using Payload = QVariantHash; using State = Payload; Q_PROPERTY(State state READ state)',
        'typedef QVariantList Payload; Q_INVOKABLE void replace(Payload p);',
    ],
)
def test_typed_api_escape_rehearsals(declaration):
    assert api_violations(declaration), (
        'I2: dictionary/JSON properties, methods, signals, slots and aliases must be rejected'
    )


def test_typed_api_allows_model_internal_variants():
    assert not api_violations(
        'QVariant data(const QModelIndex&, int); Q_PROPERTY(double value READ value)'
    ), 'I2: Qt model data() may return QVariant internally while its QML API stays typed'


def test_shipped_view_model_api_is_typed():
    files = list((ROOT / 'app/src').rglob('*.hpp')) + list((ROOT / 'app/src').rglob('*.h'))
    assert files, 'gate 4: the app must declare the typed QObject view-model contract'
    for file in files:
        assert not api_violations(file.read_text()), (
            f'I2: no JSON/dictionary state crosses the API in {file.relative_to(ROOT)}'
        )
    for file in (ROOT / 'app/qml').rglob('*.qml'):
        assert not re.search(
            r'JSON\s*\.\s*(?:parse|stringify)\s*\(|\bJsonListModel\b',
            without_comments(file.read_text()),
        ), f'I2: no dictionary round trips or JsonListModel in {file.relative_to(ROOT)}'


def test_shipped_qml_imports_and_base_pin():
    # Before: LGPL modules only. 's GPL app decision and 's
    # accepted plan admit QtGraphs and QtQuick3D; the other exclusions stay.
    forbidden = r'QtWebEngine|QtWebView|QtCharts|Qt5Compat|QtTest|QtMultimedia'
    files = list((ROOT / 'app/qml').rglob('*.qml'))
    assert files, 'gate 2: the product QML tree is nonempty'
    for file in files:
        assert not re.search(
            r'^\s*import\s+(?:' + forbidden + r')\b', file.read_text(), re.MULTILINE
        ), f'I13 /: only base modules and GPL QtGraphs/QtQuick3D ship: {file}'
    cmake = ROOT / 'cmake/EdiGuiBase.cmake'
    assert cmake.is_file(), (
        'I11: gui-components must be acquired through the checked pinned base adapter'
    )
    assert PIN in cmake.read_text(), (
        'I11: the configured gui-components input is the accepted v0.9.1 commit'
    )
    host = (ROOT / 'app/main.cpp').read_text()
    assert 'QTest::' not in host, 'I16: the shipped demo uses real events without linking QtTest'


def dependency_commands(manifest, name, seen=None):
    seen = set() if seen is None else seen
    if name in seen:
        return {}
    seen.add(name)
    tasks = dict(manifest.get('tasks', {}))
    for feature in manifest.get('feature', {}).values():
        tasks.update(feature.get('tasks', {}))
    task = tasks.get(name, {})
    if isinstance(task, str):
        return {name: task}
    cmd = task.get('cmd', '')
    commands = {name: shlex.join(cmd) if isinstance(cmd, list) else cmd}
    for dep in task.get('depends-on', []):
        commands.update(
            dependency_commands(manifest, dep if isinstance(dep, str) else dep['task'], seen)
        )
    return commands


def assert_local_app_checks(manifest):
    for task in ('verify-quick', 'verify-full'):
        commands = dependency_commands(manifest, task)
        for disabled in ('app-test', 'app-ui-test'):
            assert disabled not in commands, (
                f' owner decisions 2026-10-02: {task} must not reach disabled {disabled}'
            )
        for script in ('app-lint', 'app-format-check', 'group-app'):
            assert script in commands, f'gate 6/7: {task} must actually reach {script}'
            if script == 'group-app':
                assert shlex.split(commands[script])[:4] == [
                    'python',
                    '-m',
                    'pytest',
                    'tests/integration/app',
                ], 'gate 6/7: reachable group-app must execute its Python app suite'
            else:
                assert f'tools/ci/{script}.sh' in commands[script], (
                    f'gate 6/7: reachable {script} must execute its native app checker'
                )

    for task in ('app-verify', 'app-gates'):
        commands = dependency_commands(manifest, task)
        assert not {'app-test', 'app-ui-test'} & commands.keys(), (
            ' owner decisions: both local app gate aggregators omit both disabled tiers'
        )
    for task in ('app-test', 'app-ui-test', 'app-ui-bless'):
        assert f'tools/ci/{task}.sh' in dependency_commands(manifest, task)[task], (
            ' owner decisions: disabled app tiers and image bless remain runnable by hand'
        )


def assert_disabled_app_steps(job):
    for title, task in (
        ("The app's Qt Quick Test tier", 'app-test'),
        ('The UI test against the one committed image set', 'app-ui-test'),
    ):
        steps = [step for step in job['steps'] if step.get('name') == title]
        assert len(steps) == 1 and steps[0].get('if') is False, (
            ' owner decisions: each disabled app tier is retained once with literal if: false'
        )
        assert steps[0].get('run') == f'pixi run -e app --skip-deps {task}', (
            ' owner decisions: retain the manual tier command for owner re-enable'
        )
    uploads = [
        step
        for step in job['steps']
        if step.get('name') == "Upload the UI test's images and similarity maps"
    ]
    assert len(uploads) == 1 and uploads[0].get('if') is False, (
        ' owner decision: retain the image upload once with literal if: false'
    )


@pytest.mark.parametrize('damage', ['missing-edge', 'empty-checker'])
def test_app_reachability_observer_rejects_missing_group_or_checker(damage):
    manifest = tomllib.loads((ROOT / 'pixi.toml').read_text())
    assert_local_app_checks(manifest)
    for aggregator in ('app-verify', 'app-gates'):
        for task in ('app-test', 'app-ui-test'):
            enabled = copy.deepcopy(manifest)
            spec = (
                enabled['tasks']
                if aggregator == 'app-verify'
                else enabled['feature']['app']['tasks']
            )[aggregator]
            spec['depends-on'].append({'task': task, 'environment': 'app'})
            with pytest.raises(AssertionError, match='owner decision'):
                assert_local_app_checks(enabled)
    broken = copy.deepcopy(manifest)
    if damage == 'missing-edge':
        broken['tasks']['app-verify']['depends-on'].remove('group-app')
    else:
        broken['tasks']['group-app']['cmd'] = 'true'
    with pytest.raises(AssertionError, match='gate 6/7:'):
        assert_local_app_checks(broken)


def test_local_and_ci_gates_reach_app_tests():
    manifest = tomllib.loads((ROOT / 'pixi.toml').read_text())
    assert_local_app_checks(manifest)
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    # : both desktop platforms share one matrix; keep the original gate payload.
    app_jobs = []
    for name, job in workflow['jobs'].items():
        if name not in {'app', 'app-macos'} and not job.get('name', '').startswith('app · '):
            continue
        if 'WebAssembly' in job.get('name', ''):
            continue
        app_jobs.extend(runner[1] for runner in self_hosted_runners(job))
        assert job.get('if') is not False, (
            ' owner decisions: both app jobs remain active and required'
        )
        assert_disabled_app_steps(job)
        for title in (
            "The app's Qt Quick Test tier",
            'The UI test against the one committed image set',
        ):
            for condition in (None, True, 'false', '${{ false }}'):
                mutant = copy.deepcopy(job)
                step = next(step for step in mutant['steps'] if step.get('name') == title)
                if condition is None:
                    step.pop('if')
                else:
                    step['if'] = condition
                with pytest.raises(AssertionError, match='owner decision'):
                    assert_disabled_app_steps(mutant)
        commands = '\n'.join(
            step.get('run', '') for step in job['steps'] if step.get('if') is not False
        )
        for script in (
            'app-build',
            'app-lint',
            'app-format-check',
            'group-app',
        ):
            assert script in commands, f'gate 6/7: {name} invokes the shared {script} task'
        uploads = [step for step in job['steps'] if 'upload-artifact' in step.get('uses', '')]
        assert any(
            step.get('if') is False
            and 'build/app/ui-actual' in step.get('with', {}).get('path', '')
            and 'build/app/ui-diff' in step.get('with', {}).get('path', '')
            for step in uploads
        ), f' owner decision: {name} retains disabled image upload inputs for re-enable'

    assert sorted(app_jobs) == ['Linux', 'macOS'], (
        'gate 7: both desktop platforms execute app checks'
    )


def test_originals_remain_byte_identical():
    manifest = yaml.safe_load((SCREENSHOTS / 'originals/provenance.yml').read_text())
    assert manifest['app'] == 'easydiffractionbeta v0.9.9', (
        'gate 5: the owner originals are v0.9.9'
    )
    assert len(manifest['images']) == 16, (
        'gate 5: all selected owner reference states must remain available'
    )
    for row in manifest['images']:
        file = SCREENSHOTS / 'originals' / row['file']
        assert hashlib.sha256(file.read_bytes()).hexdigest() == row['sha256'], (
            f'gate 5: preserve original screenshot bytes: {file.name}'
        )


def assert_numbered_states(names):
    assert sorted(int(name[:2]) for name in names) == list(range(1, 29)), (
        'gate 7: exactly one expected image covers each numbered state 01 through 28'
    )


def assert_image_families(names, example_names, captures, final_captures=()):
    numbered = [name for name in names if re.fullmatch(r'\d{2}-.+\.png', name)]
    assert_numbered_states(numbered)
    task_names = {row['image'] for row in captures if row['image'].startswith('t2-')}
    assert task_names and all(re.fullmatch(r't2-\d{2}-.+\.png', name) for name in task_names), (
        'gate 7/: new captures use the explicitly declared t2 numbered filename family'
    )
    final_names = {row['image'] for row in final_captures if row['image'].startswith('t4-')}
    assert all(re.fullmatch(r't4-\d{2}-.+\.png', name) for name in final_names), (
        'gate 7/: final captures use the explicitly declared t4 numbered filename family'
    )
    expected = example_names | task_names | final_names
    actual = set(names) - set(numbered)
    assert actual == expected, (
        'Example image inventory includes every registered example and every mapped capture; '
        f'missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)}'
    )


def test_one_shared_labelled_regression_baseline_and_pairs():
    # Owner direction 2026-09-27 supersedes the accepted plan's per-OS sets.
    baselines = [
        p
        for p in SCREENSHOTS.iterdir()
        if p.is_dir() and p.name != 'originals' and list(p.glob('*.png'))
    ]
    assert len(baselines) == 1, (
        'gate 7: exactly one committed expected-image set serves every platform'
    )
    baseline = baselines[0]
    assert not any(
        platform in baseline.name.lower() for platform in ('linux', 'macos', 'windows')
    ), 'gate 7: one shared baseline without OS selection'
    provenance = (baseline / 'provenance.yml').read_text()
    assert 'regression pin' in provenance.lower(), (
        'I16: expected images are regression pins, never look-correctness oracles'
    )
    images = sorted(baseline.glob('*.png'))
    # Plan §5b/§15.4 plus owner direction 2026-09-28: include the About capture.
    numbered = [p for p in images if re.fullmatch(r'\d{2}-.+\.png', p.name)]
    assert_numbered_states([p.name for p in numbered])
    assert {
        '09-model-text-mode.png',
        '23-experiment-text.png',
        '24-analysis-text.png',
        '25-report-tof.png',
        '28-home-about.png',
    } <= {p.name for p in numbered}, (
        'gate 7: capture About and the stable TOF report while retaining the monospace Text tabs'
    )
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())
    example_names = {f'ex-{project["id"]}.png' for project in registry['projects']}
    example_names.add('ex-pd-xray-cwl_lif.png')
    captures = json.loads((ROOT / 'docs/dev/design/app-review-captures.json').read_text())[
        'captures'
    ]
    final_captures = json.loads((ROOT / 'docs/dev/design/app-example-captures.json').read_text())
    assert_image_families([p.name for p in images], example_names, captures, final_captures)
    for file in images:
        assert file.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n', (
            'gate 7: each baseline is a valid PNG'
        )
        assert struct.unpack('>II', file.read_bytes()[16:24]) == (1280, 768), (
            'seam 17: baseline dimensions are the declared 1280 by 768 app viewport'
        )
    inventory = (ROOT / 'docs/dev/design/app-design-inventory.md').read_text()
    for original in sorted((SCREENSHOTS / 'originals').glob('*.png')):
        assert original.name in inventory, (
            f'gate 5: the design review includes original {original.name}'
        )
        counterpart = next(p for p in images if p.name[:2] == original.name[:2])
        assert counterpart.name in inventory, (
            f'gate 5: the design review pairs the actual baseline {counterpart.name}'
        )
    differences = re.search(r'(?ms)^## Differences\s*\n(.*?)(?=^## |\Z)', inventory)
    assert differences is not None, 'gate 5: the inventory records visible differences'
    rows = [
        [cell.strip() for cell in line.strip('|').split('|')]
        for line in differences[1].splitlines()
        if line.startswith('|')
    ]
    assert len(rows) > 2 and rows[0] == ['where', 'original', 'edi', 'class'], (
        'gate 5: each difference pairs the original and edi state with its reason class'
    )
    assert all(
        len(row) == 4 and all(row) and re.fullmatch(r'[OCDSPT](?: \(.+\))?', row[3])
        for row in rows[2:]
    ), 'gate 5: every visible difference names one of the plan-defined justification classes'


def test_adr_records_the_decision_and_comparison_plan():
    file = ROOT / 'docs/dev/adrs/0015-edi-app-stack.md'
    assert file.is_file(), 'gate 1: commit the app-stack ADR before implementing the port'
    text = file.read_text().lower()
    for term in (
        'easydiffractionbeta',
        'gui-components',
        'tauri',
        'typescript',
        'bundle',
        'startup',
        'plot',
        'wasm',
        'licens',
        'reuse',
        'measurement',
        'rietx',
    ):
        assert term in text, (
            f'gate 1: the ADR must cover the agreed decision/comparison criterion {term}'
        )


def test_frozen_oracle_inputs_are_the_committed_fixture_bytes():
    text = (ROOT / 'tests/fixtures/e04_t1/oracle.js').read_text()
    oracle = json.loads(text.split('var frozen = ', 1)[1].removesuffix(';\n'))
    assert oracle['corpus'], 'I7: the independent frozen category corpus cannot be empty'
    for case in oracle['corpus']:
        file = ROOT / case['project'] / 'experiments' / (case['experiment'] + '.edi')
        assert hashlib.sha256(file.read_bytes()).hexdigest() == case['sha256'], (
            'I7: a changed fixture requires an independently reviewed expectation update'
        )
    profiles = {case['peakType'] for case in oracle['corpus']}
    assert profiles == set(oracle['profiles']), (
        'I7: committed examples cover every declared peak profile'
    )
    display = json.loads(
        (ROOT / 'tests/fixtures/e04_t1/display_oracle.js')
        .read_text()
        .split('var frozen = ', 1)[1]
        .removesuffix(';\n')
    )
    assert display['sources'], 'gate 3: displayed-value expectations must name their .edi sources'
    for relative, digest in display['sources'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest, (
            'gate 3: rendered-value oracle retains independently frozen source bytes'
        )
    assert len({case['tag'] for case in display['cases']}) == len(display['cases']), (
        'gate 3: every display witness is independently collected by QtTest'
    )


def test_existing_projects_oracle_covers_the_registry_without_filters():
    text = (ROOT / 'tests/fixtures/e04_t1/oracle.js').read_text()
    oracle = json.loads(text.split('var frozen = ', 1)[1].removesuffix(';\n'))
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())
    ids = [p['id'] for p in registry['projects']]
    assert [p['id'] for p in oracle['projects']] == ids, (
        'I19: fixture follows registry order without executing/offline filters'
    )
    assert set(ids) == {p.parent.name for p in (ROOT / 'docs/user/cli').glob('*/project')}, (
        'I19: every committed project directory is registered and exercised'
    )
    display = json.loads(
        (ROOT / 'tests/fixtures/e04_t1/display_oracle.js')
        .read_text()
        .split('var frozen = ', 1)[1]
        .removesuffix(';\n')
    )
    for project in oracle['projects']:
        cases = [case for case in display['cases'] if case['path'] == project['path']]
        assert {case['group'] for case in cases} >= {
            'space_group',
            'experiment_type',
            'data',
            'engines',
        }, 'gate 3: each frozen project covers every common read-only display family'
        for group in ('experiment_type', 'data'):
            assert {case['selection'] for case in cases if case['group'] == group} == set(
                project['experiments']
            ), 'gate 3: read-only displayed values cover every experiment, not only the first'
        if project['analysis'].get('_fitting_mode.type') == 'sequential':
            assert any(case['group'] == 'sequential_fit' for case in cases), (
                'gate 3: scan projects exercise every read-only scan field'
            )
    for project in oracle['projects']:
        assert project['structures'] and project['experiments'], (
            'I19: each page-population witness contains real structures and experiments'
        )
        for relative, digest in project['files'].items():
            assert (
                hashlib.sha256((ROOT / project['path'] / relative).read_bytes()).hexdigest()
                == digest
            ), 'I19: all project-block expectations retain input provenance'
