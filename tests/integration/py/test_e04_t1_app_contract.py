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

from tests.fixtures.table_display import gui_base
from tests.integration.py.ci_runner_contract import self_hosted_runners

ROOT = Path(__file__).resolve().parents[3]
SCREENSHOTS = ROOT / 'docs/dev/design/app-screenshots'
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


def report_model_exception_spans(source, relative_path):  # noqa: PLR0911 - each failed identity check refuses independently
    # OWNER DECISION 2026-10-14, hub 3f2ce1cf6, decision-records.md:
    # "the report model crosses into the Report page untyped for now".
    # The planned schema successor removes this sole temporary exception.
    # Its exact task identity and the owner citation live in the hub acceptance receipt.
    if relative_path != 'app/src/report_view_model.hpp':
        return set()
    classes = []
    for match in re.finditer(r'\b(?:class|struct)\s+(\w+)[^;{}]*\{', source):
        depth, end = 1, match.end()
        while end < len(source) and depth:
            depth += (source[end] == '{') - (source[end] == '}')
            end += 1
        if depth:
            return set()
        classes.append((match[1], match.end(), end))
    if sum(name == 'ReportViewModel' for name, _, _ in classes) != 1:
        return set()
    namespaces = []
    for match in re.finditer(r'\bnamespace\s*(\w+(?:::\w+)*)?\s*\{', source):
        depth, end = 1, match.end()
        while end < len(source) and depth:
            depth += (source[end] == '{') - (source[end] == '}')
            end += 1
        if depth:
            return set()
        namespaces.append((match[1], match.end(), end))
    properties = list(re.finditer(r'Q_PROPERTY\s*\((.*?)\)', source, re.DOTALL))
    named = [
        m
        for m in properties
        if re.fullmatch(r'\s*QVariantMap\s+model\s+READ\s+model\s+NOTIFY\s+modelChanged\s*', m[1])
    ]
    if len(named) != 1:
        return set()
    prop = named[0]
    enclosing = [name for name, start, end in namespaces if start <= prop.start() < end]
    if enclosing != ['edi_app']:
        return set()
    owners = [entry for entry in classes if entry[1] <= prop.start() < entry[2]]
    if not owners or min(owners, key=lambda entry: entry[2] - entry[1])[0] != 'ReportViewModel':
        return set()
    return {prop.span()}


def api_violations(source, relative_path=None):
    source = without_comments(source)
    forbidden = set(FORBIDDEN)
    aliases = re.findall(r'using\s+(\w+)\s*=\s*([^;]+);|typedef\s+([^;]+)\s+(\w+)\s*;', source)
    for _ in range(len(aliases) + 1):
        for name, value, old_value, old_name in aliases:
            if set(re.findall(r'\w+', value or old_value)) & forbidden:
                forbidden.add(name or old_name)
    allowed = report_model_exception_spans(source, relative_path)
    surfaces = re.finditer(r'Q_PROPERTY\s*\((.*?)\)|Q_INVOKABLE\s+([^;{]+)', source, re.DOTALL)
    fragments = [
        ' '.join(part or '' for part in match.groups())
        for match in surfaces
        if match.span() not in allowed
    ]
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
        assert not api_violations(file.read_text(), file.relative_to(ROOT).as_posix()), (
            f'I2: no JSON/dictionary state crosses the API in {file.relative_to(ROOT)}'
        )
    for file in (ROOT / 'app/qml').rglob('*.qml'):
        assert not re.search(
            r'JSON\s*\.\s*(?:parse|stringify)\s*\(|\bJsonListModel\b',
            without_comments(file.read_text()),
        ), f'I2: no dictionary round trips or JsonListModel in {file.relative_to(ROOT)}'


REPORT_EXCEPTION = (
    'namespace edi_app { class ReportViewModel : public QObject { '
    'Q_PROPERTY(QVariantMap model READ model NOTIFY modelChanged) }; }'
)
REPORT_HEADER = 'app/src/report_view_model.hpp'


def test_report_model_owner_exception_is_exactly_one_named_property():
    assert not api_violations(REPORT_EXCEPTION, REPORT_HEADER), (
        'I2 owner decision 3f2ce1cf6 admits only ReportViewModel.model QVariantMap; '
        'the planned schema successor removes the exception'
    )


@pytest.mark.parametrize(
    'escape',
    [
        'anonymous-namespace',
        'foreign-namespace',
        'nested-namespace',
        'second',
        'renamed',
        'other-class',
        'other-file',
        'duplicate',
        'list',
        'hash',
        'json',
        'alias',
        'nested',
        'method',
        'signal',
        'savedReports',
        'figures',
        'suText',
        'setPoints',
    ],
)
def test_report_model_owner_exception_cannot_widen(escape):
    source, path = REPORT_EXCEPTION, REPORT_HEADER
    if escape == 'anonymous-namespace':
        source = source.replace('namespace edi_app {', 'namespace edi_app { namespace {') + '}'
    elif escape == 'foreign-namespace':
        source = source.replace('namespace edi_app', 'namespace other')
    elif escape == 'nested-namespace':
        source = (
            source.replace('namespace edi_app {', 'namespace edi_app { namespace other {') + '}'
        )
    elif escape == 'second':
        source = source.replace('};', 'Q_PROPERTY(QVariantMap second READ second) };')
    elif escape == 'renamed':
        source = source.replace('QVariantMap model', 'QVariantMap payload')
    elif escape == 'other-class':
        source = source.replace('ReportViewModel', 'OtherViewModel')
    elif escape == 'other-file':
        path = 'app/src/other.hpp'
    elif escape == 'duplicate':
        source += REPORT_EXCEPTION
    elif escape in {'list', 'hash', 'json'}:
        source = source.replace(
            'QVariantMap',
            {'list': 'QVariantList', 'hash': 'QVariantHash', 'json': 'QJsonObject'}[escape],
        )
    elif escape == 'alias':
        source = 'using Payload = QVariantMap;' + source.replace(
            'QVariantMap model', 'Payload model'
        )
    elif escape == 'nested':
        source = source.replace('Q_PROPERTY', 'class OtherViewModel { Q_PROPERTY').replace(
            ' };', ' }; };'
        )
    else:
        added = {
            'method': 'Q_INVOKABLE QVariantMap payload();',
            'signal': 'signals:\n void changed(QVariantList values);',
            'savedReports': 'Q_PROPERTY(QVariantList savedReports READ savedReports)',
            'figures': 'Q_INVOKABLE void saveReport(QVariantMap figures);',
            'suText': 'Q_PROPERTY(QVariantMap suText READ suText)',
            'setPoints': 'Q_INVOKABLE void setPoints(QVariantList points);',
        }[escape]
        source = source.replace('};', added + ' };')
    assert api_violations(source, path), (
        'I2: the single temporary model exception refuses second/renamed/foreign '
        f'properties and every other dictionary, list or JSON crossing; escape={escape}'
    )


def assert_gui_pin(source):
    source = re.sub(r'#[^\n]*', '', source)
    for name, value in (
        ('SHA', gui_base.PIN),
        ('ARCHIVE_SHA256', gui_base.ARCHIVE_SHA256),
        ('SRC_SHA256', gui_base.SOURCE_SHA256),
    ):
        values = re.findall(
            r'set\s*\(\s*EDI_GUI_COMPONENTS_' + name + r'\s+([^\s)]+)\s*\)', source
        )
        assert values == [value], (
            'The selected upstream GUI commit and both independently frozen digests must be exact'
        )


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
    assert_gui_pin(cmake.read_text())
    host = (ROOT / 'app/main.cpp').read_text()
    assert 'QTest::' not in host, 'I16: the shipped demo uses real events without linking QtTest'


@pytest.mark.parametrize('damage', ['commit', 'archive', 'source', 'comment', 'duplicate'])
def test_gui_pin_rejects_identity_digest_and_declaration_escapes(damage):
    source = (ROOT / 'cmake/EdiGuiBase.cmake').read_text()
    assert_gui_pin(source)
    selected = {
        'commit': gui_base.PIN,
        'archive': gui_base.ARCHIVE_SHA256,
        'source': gui_base.SOURCE_SHA256,
    }
    if damage in selected:
        source = source.replace(selected[damage], '0' * len(selected[damage]))
    elif damage == 'comment':
        source = re.sub(
            r'(?m)^set\(EDI_GUI_COMPONENTS_SHA ', '# set(EDI_GUI_COMPONENTS_SHA ', source
        )
    else:
        source += f'\nset(EDI_GUI_COMPONENTS_SHA {gui_base.PIN})\n'
    with pytest.raises(AssertionError, match='upstream GUI commit'):
        assert_gui_pin(source)


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


NIGHTLY_APP_CONDITION = (
    "${{ !cancelled() && (github.event_name == 'schedule' || "
    "github.event_name == 'workflow_dispatch') }}"
)
APP_GROUP_TITLE = "The app group's Python tests (tests/integration/app)"
APP_TIER_STEPS = (
    ("The app's Qt Quick Test tier", 'app-test'),
    ('The UI test against the one committed image set', 'app-ui-test'),
)
APP_IMAGE_UPLOAD_TITLE = "Upload the UI test's images and similarity maps"


def assert_nightly_app_steps(job):
    for title, task in APP_TIER_STEPS:
        steps = [step for step in job['steps'] if step.get('name') == title]
        assert len(steps) == 1, (
            f'owner decision: each nightly app tier is present once; title={title!r}, '
            f'actual count={len(steps)}'
        )
        assert steps[0].get('if') == NIGHTLY_APP_CONDITION, (
            'owner decision: app tiers run only on schedule or manual dispatch, including '
            f'after earlier failures; title={title!r}, actual if={steps[0].get("if")!r}'
        )
        assert steps[0].get('run') == f'pixi run -e app --skip-deps {task}', (
            f'owner decision: retain the app tier command; title={title!r}, '
            f'actual run={steps[0].get("run")!r}'
        )
    uploads = [step for step in job['steps'] if step.get('name') == APP_IMAGE_UPLOAD_TITLE]
    assert len(uploads) == 1, (
        f'owner decision: the nightly UI image upload is present once; actual count={len(uploads)}'
    )
    assert uploads[0].get('if') == NIGHTLY_APP_CONDITION, (
        'owner decision: image upload has the same schedule/manual and cancellation condition; '
        f'actual if={uploads[0].get("if")!r}'
    )
    assert uploads[0].get('uses') == 'actions/upload-artifact@v4' and set(
        uploads[0].get('with', {}).get('path', '').split()
    ) == {'build/app/ui-actual', 'build/app/ui-diff'}, (
        'owner decision: the nightly upload keeps the actual-image and similarity-map inputs; '
        f'actual upload={uploads[0]}'
    )
    groups = [step for step in job['steps'] if step.get('name') == APP_GROUP_TITLE]
    assert len(groups) == 1 and groups[0].get('run') == 'pixi run --skip-deps group-app', (
        'owner decision: keep the group-app command present once before Qt Quick Test; '
        f'actual group steps={groups}'
    )
    from tests.fixtures.e09_t75_workflow import active  # noqa: PLC0415

    for event in ('pull_request', 'push', 'schedule', 'workflow_dispatch'):
        assert active(groups[0], event) == (event != 'pull_request'), (
            'owner decision: app group skips PRs and runs on push, nightly and full dispatch'
        )
    titles = [step.get('name') for step in job['steps']]
    assert titles.index(APP_GROUP_TITLE) < titles.index(APP_TIER_STEPS[0][0]), (
        'owner decision: group-app runs before Qt Quick Test so a Qt Quick failure cannot skip '
        f'the Python app group; actual step order={titles}'
    )


def assert_nightly_app_step_escape_controls():
    # Independent positive policy fixture: these values come from the workflow contract.
    job = {
        'steps': [
            {
                'name': APP_GROUP_TITLE,
                'if': "github.event_name != 'pull_request'",
                'run': 'pixi run --skip-deps group-app',
            },
            *[
                {
                    'name': title,
                    'if': NIGHTLY_APP_CONDITION,
                    'run': f'pixi run -e app --skip-deps {task}',
                }
                for title, task in APP_TIER_STEPS
            ],
            {
                'name': APP_IMAGE_UPLOAD_TITLE,
                'if': NIGHTLY_APP_CONDITION,
                'uses': 'actions/upload-artifact@v4',
                'with': {'path': 'build/app/ui-actual\nbuild/app/ui-diff'},
            },
        ]
    }
    assert_nightly_app_steps(job)
    for title in [*(title for title, _ in APP_TIER_STEPS), APP_IMAGE_UPLOAD_TITLE]:
        for condition in (
            None,
            False,
            True,
            'false',
            '${{ false }}',
            '${{ always() }}',
            '${{ !cancelled() }}',
            "${{ github.event_name == 'push' }}",
            "${{ github.event_name == 'pull_request' }}",
        ):
            broken = copy.deepcopy(job)
            step = next(step for step in broken['steps'] if step['name'] == title)
            if condition is None:
                step.pop('if')
            else:
                step['if'] = condition
            with pytest.raises(AssertionError, match='owner decision'):
                assert_nightly_app_steps(broken)
        for duplicate in (False, True):
            broken = copy.deepcopy(job)
            step = next(step for step in broken['steps'] if step['name'] == title)
            if duplicate:
                broken['steps'].append(copy.deepcopy(step))
            else:
                broken['steps'].remove(step)
            with pytest.raises(AssertionError, match='owner decision'):
                assert_nightly_app_steps(broken)
    for condition in (
        None,
        False,
        True,
        "github.event_name != 'push'",
        "github.event_name != 'schedule'",
        "github.event_name != 'workflow_dispatch'",
    ):
        broken = copy.deepcopy(job)
        if condition is None:
            broken['steps'][0].pop('if')
        else:
            broken['steps'][0]['if'] = condition
        with pytest.raises(AssertionError, match='owner decision'):
            assert_nightly_app_steps(broken)
    broken = copy.deepcopy(job)
    broken['steps'][0], broken['steps'][1] = broken['steps'][1], broken['steps'][0]
    with pytest.raises(AssertionError, match='before Qt Quick Test'):
        assert_nightly_app_steps(broken)
    for index in (0, 1, 2):
        broken = copy.deepcopy(job)
        broken['steps'][index]['run'] = 'true'
        with pytest.raises(AssertionError, match='owner decision'):
            assert_nightly_app_steps(broken)


@pytest.mark.parametrize('damage', ['missing-edge', 'empty-checker'])
def test_app_reachability_observer_rejects_missing_group_or_checker(damage):
    assert_nightly_app_step_escape_controls()
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
        assert_nightly_app_steps(job)
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
    # Before: pre-category LBCO input. After: exact manual/arpls addition, with
    # the original numerical/display expectations retained by adapt_oracles.py.
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
    # The manual estimate extension changes only the LBCO experiment source hash;
    # all project-block values, other files and the complete registry stay pinned.
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
        for dataset in project.get('datasets', []):
            directory = project['analysis']['_sequential_fit.data_dir']
            source = ROOT / project['path'] / directory / dataset['file']
            assert hashlib.sha256(source.read_bytes()).hexdigest() == dataset['sha256'], (
                'Dataset catalogue and ranges retain independent measured ASCII provenance'
            )
        assert project['structures'] and project['experiments'], (
            'I19: each page-population witness contains real structures and experiments'
        )
        for relative, digest in project['files'].items():
            assert (
                hashlib.sha256((ROOT / project['path'] / relative).read_bytes()).hexdigest()
                == digest
            ), 'I19: all project-block expectations retain input provenance'
