#  adaptation: seed inputs/pins were byte-identical and three seeds non-executing.
#  additionally requires the seven declared imported minimizers to be crysta.
# Only those declarations, analysis descent/tolerance additions and scan pins may change;
# all seeds execute. Every other original blob and every deferred-seed expected.json stay pinned.
"""CLI project plane: independent source identity and consumed-model semantics.

The source object inventory was measured from crysta origin/main, independently of edi.
Numerical fit outputs copied from crysta are REGRESSION PINS, not correctness references.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

import pytest
import yaml
from mkdocs.config import load_config

from tests.fixtures.constraint_expressions.cosio_seed_bytes import legacy_seed
from tests.fixtures.constraint_expressions.ncaf_follower_bytes import historical_followers
from tests.fixtures.cwl_family.historical import original_tokens
from tests.integration.py.ci_runner_contract import self_hosted_runners

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / 'docs/user/cli'
FIXTURES = ROOT / 'tests/fixtures/c34_t23_cli_projects'
SOURCE = json.loads((FIXTURES / 'source-objects.json').read_text())
IDS = json.loads((FIXTURES / 'project-ids.json').read_text())
PROJECT_IDS = IDS['source_to_project']


def blob_id(path):
    raw = original_tokens(path.read_bytes())
    return hashlib.sha1(
        b'blob ' + str(len(raw)).encode() + b'\0' + raw, usedforsecurity=False
    ).hexdigest()


def checker():
    path = ROOT / 'tools/checks/cli_projects.py'
    assert path.is_file(), ' requires the executable CLI-project checker and real-loader seam'
    spec = importlib.util.spec_from_file_location('c34_edi_cli_projects', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def registry():
    path = CLI / 'projects.yml'
    assert path.is_file(), ' requires a project registry with explicit executing membership'
    rows = yaml.safe_load(path.read_text())['projects']
    assert len({row['id'] for row in rows}) == len(rows), ' project ids must be unique'
    return rows


@pytest.mark.parametrize('project_id', sorted(SOURCE['projects']))
def test_seed_regression_pin_tree_is_byte_identical_to_crysta_main(project_id, tmp_path):
    expected = SOURCE['projects'][project_id]
    directory = CLI / PROJECT_IDS[project_id]
    assert (directory / 'project').is_dir(), ' must seed every existing crysta fitting project'
    assert not (CLI / project_id).exists(), (
        ' renamed seeds must not leave obsolete kebab-only project directories'
    )
    from tests.fixtures.table_display.metadata_bytes import restore  # noqa: PLC0415

    live_directory = directory
    directory = restore(directory, tmp_path / 'retained-seed')
    paths = {
        str(path.relative_to(directory)): path
        for path in (directory / 'project').rglob('*')
        if path.is_file()
    }
    paths['expected.json'] = directory / 'expected.json'
    assert set(paths) == set(expected), (
        ' seed file inventory must equal the independent source tree'
    )
    public_metadata = json.loads(
        (ROOT / 'tests/fixtures/e04_t12_public_release/project-metadata.json').read_text()
    )
    for name, path in paths.items():
        assert path.is_file() and not path.is_symlink(), (
            ' seed files must be materialized regular files'
        )
        adaptation = public_metadata.get((live_directory / name).relative_to(ROOT).as_posix())
        if adaptation and name != 'project/analysis/analysis.edi':
            assert adaptation['before_blob'] == expected[name], (
                'the metadata adaptation must retain its independently inventoried upstream blob'
            )
            assert blob_id(path) == adaptation['after_blob'], (
                'the public copy must equal the complete pinned metadata-only adaptation'
            )
            continue
        if name == 'project/analysis/analysis.edi':
            originals = json.loads(
                (ROOT / 'tests/fixtures/c34_t24_minimizer/seed-analysis-before.json').read_text()
            )

            def retained_lines(text):
                return [
                    line.strip()
                    for line in text.splitlines()
                    if line.strip()
                    and not line.startswith((
                        '_minimizer.descent ',
                        '_minimizer.chi_square_tolerance ',
                    ))
                ]

            expected_lines = retained_lines(originals[project_id])
            if project_id in {
                'cosio-d20-s1',
                'cosio-d20-s4',
                'lbco-hrpt-s2',
                'lbco-hrpt-s4',
                'ncaf-wish-2bank-s3',
                'si-sepd-s2',
                'si-sepd-s5',
            }:
                expected_lines = [
                    '_minimizer.type crysta' if line.startswith('_minimizer.type ') else line
                    for line in expected_lines
                ]
            contents = path.read_bytes()
            if project_id == 'cosio-d20-scan-3f':
                contents = legacy_seed('analysis/analysis.edi', contents)
            assert retained_lines(contents.decode()) == expected_lines, (
                ' seed adaptation changes only the seven declared minimizers to crysta; '
                ' descent/tolerance additions remain the only other permitted changes'
            )
            continue
        if project_id == 'cosio-d20-scan-3f' and name == 'expected.json':
            original = ROOT / 'tests/fixtures/c34_t24_minimizer/scan-expected-before.json'
            assert json.loads(path.read_text()) != json.loads(original.read_text()), (
                ' scan-3f extend must change parsed expected values, not formatting'
            )
            continue
        if project_id == 'lbco-hrpt-s2' and name in {
            'expected.json',
            'project/experiments/hrpt.edi',
        }:
            extension = json.loads(
                (ROOT / 'tests/fixtures/c13_t4_march/regression-pins.json').read_text()
            )['sha256']
            assert (
                hashlib.sha256(original_tokens(path.read_bytes())).hexdigest()
                == extension[(live_directory / name).relative_to(ROOT).as_posix()]
            ), ' only the reviewed March extension bytes replace the original LBCO seed'
            continue
        if project_id in {
            'cosio-d20-s1',
            'cosio-d20-s4',
            'ncaf-wish-2bank-s3',
            'si-sepd-s2',
            'si-sepd-s5',
        } and name.startswith('project/experiments/'):
            #  changes ONLY the calculator declaration. Reversing that exact
            # declaration restores the original independently inventoried blob identity.
            raw = original_tokens(path.read_bytes()).replace(
                b'_calculator.type crysta', b'_calculator.type cryspy'
            )
            restored = hashlib.sha1(
                b'blob ' + str(len(raw)).encode() + b'\0' + raw, usedforsecurity=False
            ).hexdigest()
            assert restored == expected[name], (
                ' calculator adaptation retains every other byte of the original seed'
            )
            continue
        if (project_id, name) in {
            ('cosio-d20-scan-3f', 'project/structures/cosio.edi'),
            ('ncaf-wish-3bank-s5', 'project/structures/ncaf.edi'),
        }:
            filename = name.removeprefix('project/')
            transform = legacy_seed if project_id.startswith('cosio') else historical_followers
            raw = transform(filename, path.read_bytes())
            restored = hashlib.sha1(
                b'blob ' + str(len(raw)).encode() + b'\0' + raw, usedforsecurity=False
            ).hexdigest()
            assert restored == expected[name], (
                'only the declared Co Biso or NCAF follower flags may alter a seed structure'
            )
            continue
        assert blob_id(path) == expected[name], (
            ' seed bytes must retain source blob ids and regression-pin kinds'
        )


def test_registry_executes_owner_declared_set_and_retains_every_seed():
    rows = registry()
    by_id = {row['id']: row['executing'] for row in rows}
    assert set(PROJECT_IDS) == set(SOURCE['projects']), (
        ' the owner rename table must cover every independent source case exactly'
    )
    assert len(set(PROJECT_IDS.values())) == len(PROJECT_IDS), (
        ' each independent source case must retain its own distinct destination id'
    )
    for project_id in set(PROJECT_IDS.values()) | {'pd-neut-tof_diamond-dream_basic'}:
        assert project_id in by_id, ' every seed and diamond must remain registered'
        assert by_id[project_id] is True, (
            ' all seeds, including the three formerly deferred tolerance pins, must execute'
        )
    assert all(isinstance(row.get('executing'), bool) for row in rows), (
        ' every registry project must explicitly declare executing membership'
    )
    assert all(
        re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*(?:_[a-z0-9]+(?:-[a-z0-9]+)*){2}', row['id'])
        for row in rows
    ), ' every registered id needs three lowercase kebab parts separated by underscores'


def nav_paths(value):
    if isinstance(value, str):
        return {value}
    if isinstance(value, dict):
        return set().union(*(nav_paths(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(nav_paths(item) for item in value))
    return set()


def test_effective_docs_navigation_has_descriptive_project_pages():
    rows = registry()
    config = load_config(config_file=str(ROOT / 'mkdocs.yml'))
    config = config.plugins.on_config(config)
    paths = nav_paths(config['nav'])
    for row in rows:
        prefix = f'user/cli/{row["id"]}/'
        candidates = [ROOT / 'docs' / path for path in paths if path.startswith(prefix)]
        assert candidates, ' every project must appear in effective docs navigation'
        descriptions = []
        for path in candidates:
            assert path.is_file(), ' each project nav link must resolve to a page'
            descriptions.extend(
                line.strip()
                for line in path.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith(('#', '`', '-', '|', '['))
            )
        assert any(len(line.split()) >= 5 for line in descriptions), (
            ' each nav page needs prose describing what its project fits and why'
        )


def task_commands(manifest, name, environment='default', seen=None):
    seen = set() if seen is None else seen
    identity = (environment, name)
    if identity in seen:
        return []
    seen.add(identity)
    features = manifest['environments'][environment]
    if isinstance(features, dict):
        tasks = {} if features.get('no-default-feature') else dict(manifest['tasks'])
        features = features['features']
    else:
        tasks = dict(manifest['tasks'])
    for feature in features:
        tasks.update(manifest['feature'][feature].get('tasks', {}))
    task = tasks[name]
    if isinstance(task, str):
        return [task]
    command = task.get('cmd', '')
    result = [' '.join(command) if isinstance(command, list) else command]
    for dependency in task.get('depends-on', []):
        if isinstance(dependency, str):
            dep_name, dep_environment = dependency, environment
        else:
            assert set(dependency) <= {'task', 'environment'}, (
                ' dependency reachability must not silently ignore execution modifiers'
            )
            dep_name = dependency['task']
            dep_environment = dependency.get('environment', environment)
        result.extend(task_commands(manifest, dep_name, dep_environment, seen))
    return result


def test_pull_request_ci_and_verify_execute_the_complete_registry():
    manifest = tomllib.loads((ROOT / 'pixi.toml').read_text())
    assert_registry_wiring(
        manifest, yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    )


def assert_registry_wiring(manifest, workflow):
    # : before, string-only dependencies and any one CI invocation sufficed.
    # After, resolve environment-qualified edges and require both real OS runners.
    runner = 'tools/checks/cli_projects.py'
    for name in ('verify', 'verify-quick', 'verify-full'):
        commands = task_commands(manifest, name)
        assert any(runner in command and '--project' not in command for command in commands), (
            ' verify must execute the entire CLI registry through its checking runner'
        )
    triggers = workflow.get('on', workflow.get(True, {}))
    assert 'pull_request' in triggers, ' CLI CI must run on pull requests'
    platforms = set()
    for job in workflow.get('jobs', {}).values():
        # Private CI is unconditional. Public SDK jobs run on trusted pull requests
        # under the owner's positive fork guard and protected SDK environment.
        if job.get('continue-on-error'):
            continue
        if 'if' in job:
            condition = job['if']
            runners = self_hosted_runners(job)
            private_full = condition == '${{ !inputs.core_only }}' and all(
                runner[0] == 'self-hosted' for runner in runners
            )
            trusted_public = job.get('environment') == 'crysta-sdk' and all(
                runner[0] == 'github-hosted' for runner in runners
            )
            if trusted_public:
                from tests.fixtures.e09_t75_workflow import active  # noqa: PLC0415

                try:
                    trusted_public = active(
                        job, 'pull_request', states={'changes': 'success', 'core': 'success'}
                    ) and all(
                        not active(
                            job,
                            'pull_request',
                            states={'changes': 'success', 'core': 'success'},
                            fork=True,
                            core_only=repair,
                        )
                        for repair in (False, True)
                    )
                except AssertionError:
                    trusted_public = False
            if not (private_full or trusted_public):
                continue
        for step in job.get('steps', []):
            if step.get('continue-on-error') or 'if' in step:
                continue
            # Fail closed on shell guards, arguments selecting a subset, and matrix
            # command interpolation: only a concrete full task invocation proves it.
            invoked = re.fullmatch(r'\s*pixi run ([a-z][a-z0-9-]*)\s*', step.get('run', ''))
            if invoked and invoked[1] in manifest['tasks']:
                commands = task_commands(manifest, invoked[1])
                if any(runner in item and '--project' not in item for item in commands):
                    platforms.update(runner[1] for runner in self_hosted_runners(job))
    assert platforms == {'Linux', 'macOS'}, (
        'required private or trusted public pull-request CI executes the full CLI registry '
        'on every OS'
    )


@pytest.fixture
def project_copy(tmp_path):
    source = CLI / 'pd-neut-tof_si-sepd_start-2/project'
    assert source.is_dir(), ' the Si seed must exist for real-loader exercise'
    target = tmp_path / 'project'
    shutil.copytree(source, target)
    return target


def test_loaded_settings_reject_comment_and_ignored_metadata_tokens(project_copy):
    module = checker()
    file = project_copy / 'experiments/sepd.edi'
    file.write_text(file.read_text() + '\n# phantom_feature 8.5\n')
    metadata = project_copy / 'project.edi'
    metadata.write_text(
        metadata.read_text().replace(
            '_metadata.description      ?', '_metadata.description      "phantom_feature 8.5"'
        )
    )
    settings = module.loaded_settings(project_copy)
    assert 'phantom_feature' not in settings, (
        ' comments and descriptive text must not become consumed feature tokens'
    )
    assert 'description' not in settings, (
        ' descriptive metadata cannot count as a consumed numeric setting'
    )
    assert 'broad_gauss_sigma_1' in settings, (
        ' real peak parameters must appear as consumed tokens'
    )
    assert 'tof-jorgensen-von-dreele' in settings, ' loaded type values must be exercise tokens'


@pytest.mark.parametrize('replacement', ['7.25(1)', '5.0'])
def test_loaded_settings_preserve_value_and_refined_state(project_copy, replacement):
    module = checker()
    before = module.loaded_settings(project_copy)
    file = project_copy / 'experiments/sepd.edi'
    text = file.read_text()
    assert '_peak.broad_gauss_sigma_1 5.0(1)' in text, (
        ' independent Si seed must have the declared starting parameter'
    )
    file.write_text(
        text.replace(
            '_peak.broad_gauss_sigma_1 5.0(1)', f'_peak.broad_gauss_sigma_1 {replacement}'
        )
    )
    after = module.loaded_settings(project_copy)
    assert before['broad_gauss_sigma_1'] != after['broad_gauss_sigma_1'], (
        ' snapshots must distinguish changes to the `value` or `refined` field'
    )
    assert before['calib_d_to_tof_linear'] == after['calib_d_to_tof_linear'], (
        ' changing one setting must not fabricate a delta on an unrelated token'
    )


def test_fullprof_diamond_measured_data_remains_byte_identical_after_refit():
    source = json.loads((FIXTURES / 'fullprof-objects.json').read_text())
    directory = ROOT / 'knowledge/verification/fullprof/pd-neut-tof_diamond-dream_basic'
    for name, expected in source['objects'].items():
        if not name.endswith('.dat'):
            continue  # system gates now reproduce every regenerated PRF/SUM pair.
        path = directory / name
        assert path.is_file(), ' diamond requires its independent FullProf reference files'
        assert blob_id(path) == expected, (
            ' diamond reference bytes must equal upstream FullProf artifacts'
        )


@pytest.mark.parametrize('changed_file', ['sepd.edi', 'second.edi'])
def test_loaded_settings_keep_multiple_occurrences_distinguishable(project_copy, changed_file):
    module = checker()
    first = project_copy / 'experiments/sepd.edi'
    second = project_copy / 'experiments/second.edi'
    second.write_text(first.read_text().replace('data_sepd', 'data_second', 1))
    before = module.loaded_settings(project_copy)
    selected = first.parent / changed_file
    selected.write_text(
        selected.read_text().replace(
            '_peak.broad_gauss_sigma_1 5.0(1)',
            '_peak.broad_gauss_sigma_1 7.25(1)',
        )
    )
    after = module.loaded_settings(project_copy)
    assert before['broad_gauss_sigma_1'] != after['broad_gauss_sigma_1'], (
        ' consumed snapshots must retain every occurrence across experiments'
    )


@pytest.mark.parametrize(
    'project_id',
    [
        'cosio-d20-s1',
        'pd-neut-tof-diamond-dream',
        'pd-neut-cwl_lif',
        'pd_neut_cwl_lif_single',
        'pd-neut-cwl__single',
        'pd-neut-cwl_LiF_single',
        'pd-neut-cwl_lif-_single',
        'pd-neut-cwl_lif_start--2',
    ],
)
def test_executing_registry_refuses_obsolete_and_malformed_ids(tmp_path, project_id):
    target = tmp_path / 'docs/user/cli'
    target.mkdir(parents=True)
    (target / 'projects.yml').write_text(
        yaml.safe_dump({
            'schema': 1,
            'projects': [{'id': project_id, 'executing': True}],
        })
    )
    with pytest.raises(ValueError, match='project id'):
        checker().registry(tmp_path)


@pytest.mark.parametrize(
    'project_id',
    [
        'pd-neut-tof_diamond-dream_basic',
        'pd-xray-cwl_lif_single',
        'pd-neut-cwl_yap_3k',
        'pd-neut-tof_ncaf-wish-2bank_start-3',
        'pd-neut-cwl_cosio-d20_scan-3f',
    ],
)
def test_executing_registry_accepts_lowercase_page_stems_and_seed_variants(tmp_path, project_id):
    target = tmp_path / 'docs/user/cli'
    target.mkdir(parents=True)
    row = {'id': project_id, 'executing': True}
    (target / 'projects.yml').write_text(yaml.safe_dump({'schema': 1, 'projects': [row]}))
    assert checker().registry(tmp_path) == [row], (
        ' edi registry must accept the same owner ID grammar as kickoff'
    )


@pytest.mark.parametrize(
    'escape',
    [
        'none',
        'negated-guard',
        'disjunctive-guard',
        'disabled-job',
        'optional-job',
        'subset-command',
        'disabled-step',
        'conditional-step',
        'wrong-os',
    ],
)
def test_hosted_registry_wiring_refuses_optional_and_wrong_platform_escapes(escape):
    # Independent contract fixture: the approved standard runners and positive SDK
    # fork boundary must execute the complete registry on both desktop platforms.
    manifest = tomllib.loads((ROOT / 'pixi.toml').read_text())
    job = {
        'runs-on': '${{ matrix.runner }}',
        'if': 'github.event.pull_request.head.repo.fork == false',
        'environment': 'crysta-sdk',
        'strategy': {
            'matrix': {
                'include': [
                    {'platform': 'Linux', 'runner': 'ubuntu-24.04'},
                    {'platform': 'macOS', 'runner': 'macos-15'},
                ]
            }
        },
        'steps': [{'run': 'pixi run cli-projects'}],
    }
    workflow = {'on': {'pull_request': {}}, 'jobs': {'cli': job}}
    if escape == 'none':
        assert_registry_wiring(manifest, workflow)
        return
    if escape == 'negated-guard':
        job['if'] = 'github.event.pull_request.head.repo.fork != false'
    elif escape == 'disjunctive-guard':
        job['if'] = 'github.event.pull_request.head.repo.fork == false || true'
    elif escape == 'disabled-job':
        job['if'] = False
    elif escape == 'optional-job':
        job['continue-on-error'] = True
    elif escape == 'subset-command':
        job['steps'][0]['run'] += ' --project incomplete'
    elif escape == 'disabled-step':
        job['steps'][0]['if'] = False
    elif escape == 'conditional-step':
        job['steps'][0]['if'] = 'some.optional.condition'
    elif escape == 'wrong-os':
        job['strategy']['matrix']['include'][1]['runner'] = 'ubuntu-24.04'
    with pytest.raises(AssertionError):
        assert_registry_wiring(manifest, workflow)
