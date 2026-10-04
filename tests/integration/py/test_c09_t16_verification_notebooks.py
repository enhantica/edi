"""Hidden plane gates for 's executable verification notebooks."""

from __future__ import annotations

import ast
import json
import re
import shlex
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import jupytext
import nbstripout

ROOT = Path(__file__).resolve().parents[3]
VERIFICATION = ROOT / 'docs/dev/verification'
FULLPROF = ROOT / 'knowledge/verification/fullprof'
CORPUS_MANIFEST = FULLPROF / 'cw-corpus-manifest.json'
PAGES = {
    'pd-neut-cwl_LBCO_preferred-orientation': 'pd-neut-cwl_lbco-hrpt_preferred-orientation',
    'pd-xray-cwl_LiF_single': 'pd-xray-cwl_lif_single',
    'pd-xray-cwl_LiF_single_polarization': 'pd-xray-cwl_lif_single-polarization',
    'pd-neut-cwl_LaB6_fcj-asymmetry': 'pd-neut-cwl_lab6-echidna_fcj-asymmetry',
    'pd-neut-cwl_PbSO4_beba-asymmetry': 'pd-neut-cwl_pbso4_beba-asymmetry',
    'pd-neut-tof_Fe_pseudo-voigt': 'pd-neut-tof_fe_pseudo-voigt',
    'pd-neut-tof_diamond_dream': 'pd-neut-tof_diamond-dream_basic',
    'pd-neut-cwl_LaB6_basic': 'pd-neut-cwl_lab6-echidna_basic',
    'pd-neut-cwl_LaB6_absorption': 'pd-neut-cwl_lab6-echidna_absorption',
    'pd-neut-cwl_LBCO_basic': 'pd-neut-cwl_lbco-hrpt_basic',
    'pd-neut-cwl_PbSO4_basic': 'pd-neut-cwl_pbso4_basic',
    'pd-neut-cwl_Y2O3_isotropic-adp': 'pd-neut-cwl_y2o3_isotropic-adp',
    'pd-neut-cwl_LaB6_11B': 'pd-neut-cwl_lab6-echidna_11b',
    'pd-neut-tof_Si_jorgensen': 'pd-neut-tof_si-sepd_jorgensen',
    'pd-neut-tof_Si_jorgensen-von-dreele': 'pd-neut-tof_si-sepd_jorgensen-von-dreele',
    'pd-neut-tof_Si_jorgensen-von-dreele-size-strain': (
        'pd-neut-tof_si-sepd_jorgensen-von-dreele-size-strain'
    ),
    'pd-neut-tof_NCAF_jorgensen-von-dreele': ('pd-neut-tof_ncaf-wish_jorgensen-von-dreele'),
}


def _run(
    *args: str, cwd: Path = ROOT, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        capture_output=True,
    )


def _assert_ok(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


def _task_config(name: str) -> tuple[list[str], set[str]]:
    tasks = tomllib.loads((ROOT / 'pixi.toml').read_text())['tasks']
    assert name in tasks, f'missing pixi task: {name}'
    task = tasks[name]
    if isinstance(task, str):
        return shlex.split(task), set()

    command = task.get('cmd', [])
    tokens = (
        [str(token) for token in command] if isinstance(command, list) else shlex.split(command)
    )
    dependencies = task.get('depends-on', [])
    if isinstance(dependencies, str):
        dependencies = [dependencies]
    return tokens, set(dependencies)


def _call_name(node: ast.Call) -> str | None:
    function = node.func
    if isinstance(function, ast.Attribute) and isinstance(function.value, ast.Name):
        return f'{function.value.id}.{function.attr}'
    if isinstance(function, ast.Name):
        return function.id
    return None


def _assigned_literals(tree: ast.Module) -> dict[str, object]:
    values: dict[str, object] = {}
    for statement in tree.body:
        if not isinstance(statement, (ast.Assign, ast.AnnAssign)):
            continue
        targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
        value = statement.value
        if not isinstance(value, ast.Constant):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                values[target.id] = value.value
    return values


def _names(node: ast.AST) -> set[str]:
    return {child.id for child in ast.walk(node) if isinstance(child, ast.Name)}


def _job_body(workflow: str, name: str) -> str:
    match = re.search(
        rf'^  {re.escape(name)}:\n(?P<body>.*?)(?=^  \S|\Z)',
        workflow,
        re.MULTILINE | re.DOTALL,
    )
    assert match, f'missing CI job: {name}'
    return match.group('body')


def _condition_outputs(job: str) -> set[str]:
    match = re.search(r'^\s*if:\s*(.+)$', job, re.MULTILINE)
    assert match, 'missing conditional CI routing'
    return set(re.findall(r'needs\.changes\.outputs\.(\w+)', match.group(1)))


def _plugin_config(config: dict[str, Any], name: str) -> dict[str, Any]:
    for plugin in config.get('plugins', []):
        if plugin == name:
            return {}
        if isinstance(plugin, dict) and name in plugin:
            value = plugin[name]
            return value if isinstance(value, dict) else {}
    raise AssertionError(f'missing MkDocs plugin: {name}')


def _assert_reference_files(
    page: str,
    expected_project: str,
    tree: ast.Module,
    tracked: set[str],
) -> None:
    literals = _assigned_literals(tree)
    assert literals.get('FULLPROF_PROJECT_DIR') == expected_project
    reference_files = {
        name: value
        for name, value in literals.items()
        if name.startswith('FULLPROF_') and name.endswith('_FILE')
    }
    assert {
        'FULLPROF_PRF_FILE',
        'FULLPROF_SUM_FILE',
        'FULLPROF_BAC_FILE',
    } <= reference_files.keys()
    for constant, filename in reference_files.items():
        assert isinstance(filename, str), f'{page}: {constant} must name a file'
        path = FULLPROF / expected_project / filename
        assert path.is_file() and not path.is_symlink(), (
            f'{page}: unresolved {constant}={filename!r}'
        )
        relative = str(path.relative_to(ROOT))
        assert relative in tracked, f'{page}: reference is not committed: {relative}'


def _assert_calculated_candidate_flow(page: str, tree: ast.Module) -> None:
    # ACCIDENT: an identifier called calc_ed_crysta is actually assigned the external oracle.
    bindings = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == 'calc_ed_crysta'
            for target in node.targets
        )
    ]
    assert len(bindings) == 1, f'{page}: calculated candidate must have one source binding'
    binding = bindings[0]
    expected = ast.parse(
        'verify.restrict_to_included(project.experiment, project.experiment.data.intensity_calc)',
        mode='eval',
    ).body
    assert ast.dump(binding.value) == ast.dump(expected), (
        f'{page}: calculated candidate must consume the project experiment calculated pattern'
    )
    calculations = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and ast.unparse(node.func) == 'project.analysis.calculate'
        and node.lineno < binding.lineno
    ]
    assert calculations, f'{page}: calculated candidate must follow the project calculation'


def _assert_fullprof_reference_flow(  # noqa: PLR0914
    page: str, tree: ast.Module
) -> None:
    _assert_calculated_candidate_flow(page, tree)
    expected_reference_candidates = {'calc_ed_crysta'}
    expected_cross_pairs: set[tuple[frozenset[str], frozenset[str]]] = set()
    if page == 'pd-neut-cwl_LaB6_absorption':
        expected_reference_candidates.add('calc_pointwise')
        expected_cross_pairs.add((frozenset({'calc_pointwise'}), frozenset({'calc_ed_crysta'})))

    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    loaders = [call for call in calls if _call_name(call) == 'verify.load_fullprof_calc_profile']
    assert len(loaders) == 1, f'{page}: expected one FullProf profile load'
    assert [_names(argument) for argument in loaders[0].args[:4]] == [
        {'FULLPROF_PROJECT_DIR'},
        {'FULLPROF_PRF_FILE'},
        {'FULLPROF_BAC_FILE'},
        {'FULLPROF_ZERO'},
    ]

    assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and node.value is loaders[0]
    ]
    assert len(assignments) == 1
    assert any(
        isinstance(target, (ast.Tuple, ast.List))
        and [item.id for item in target.elts if isinstance(item, ast.Name)]
        == ['x', 'calc_fullprof']
        for target in assignments[0].targets
    ), f'{page}: FullProf loader output must supply calc_fullprof at run time'

    expected_plot_candidates = set(expected_reference_candidates)
    if page == 'pd-neut-cwl_LBCO_preferred-orientation':
        # The random-powder negative control is plotted but must not claim agreement.
        expected_plot_candidates.add('calc_random')
    plots = [call for call in calls if _call_name(call) == 'verify.plot_pattern_comparison']
    assert len(plots) == len(expected_plot_candidates), (
        f'{page}: every expected FullProf candidate must have exactly one comparison plot'
    )
    plotted_candidates = set()
    for plot in plots:
        plot_keywords = {keyword.arg: keyword.value for keyword in plot.keywords}
        assert _names(plot_keywords['reference']) == {'calc_fullprof'}, (
            f'{page}: every comparison plot must use the loaded FullProf profile as reference'
        )
        candidate_names = _names(plot_keywords['candidate'])
        assert len(candidate_names) == 1, (
            f'{page}: every comparison plot must name exactly one seeded candidate'
        )
        plotted_candidates.update(candidate_names)
    assert plotted_candidates == expected_plot_candidates, (
        f'{page}: comparison plots must cover exactly the page-specific candidate set'
    )

    assertions = [call for call in calls if _call_name(call) == 'verify.assert_patterns_agree']
    assert len(assertions) == len(expected_reference_candidates) + len(expected_cross_pairs), (
        f'{page}: expected one executable assertion per reference and cross-comparison'
    )
    asserted_reference_candidates = set()
    asserted_cross_pairs = set()
    for assertion in assertions:
        triples = [
            node
            for node in ast.walk(assertion)
            if isinstance(node, (ast.Tuple, ast.List)) and len(node.elts) == 3
        ]
        assert len(triples) == 1, (
            f'{page}: every agreement assertion must carry exactly one labelled comparison'
        )
        triple = triples[0]
        reference = triple.elts[1]
        candidate = triple.elts[2]
        if (
            isinstance(reference, ast.Call)
            and _call_name(reference) == 'verify.restrict_to_included'
            and 'calc_fullprof' in _names(reference)
        ):
            candidate_names = _names(candidate)
            assert len(candidate_names) == 1, (
                f'{page}: every FullProf assertion must name exactly one seeded candidate'
            )
            asserted_reference_candidates.update(candidate_names)
        else:
            asserted_cross_pairs.add((frozenset(_names(reference)), frozenset(_names(candidate))))
    assert asserted_reference_candidates == expected_reference_candidates, (
        f'{page}: FullProf assertions must cover exactly the page-specific candidate set'
    )
    assert asserted_cross_pairs == expected_cross_pairs, (
        f'{page}: non-reference assertions must match the exact page-specific comparison set'
    )


def test_verification_sources_generate_stripped_notebooks_on_demand() -> None:
    expected_sources = {f'{page}.py' for page in PAGES}
    expected_notebooks = {f'{page}.ipynb' for page in PAGES}
    actual_sources = {path.name for path in VERIFICATION.glob('*.py')}

    assert (VERIFICATION / 'index.md').is_file(), 'the verification page index must be present'
    assert actual_sources == expected_sources, (
        'the tracked percent sources must be the canonical declared verification set'
    )

    manifest = json.loads(CORPUS_MANIFEST.read_text(encoding='utf-8'))
    committed = manifest.get('committed')
    assert isinstance(committed, dict), 'manifest committed inventory must be a mapping'
    shipped_cw_pages = {
        page: project
        for page, project in PAGES.items()
        if page.startswith(('pd-neut-cwl_', 'pd-xray-cwl_'))
    }
    assert set(shipped_cw_pages) <= set(manifest.get('pages', ())), (
        'a shipped CW page is absent from the independently declared planned corpus'
    )
    assert set(shipped_cw_pages.values()) == set(committed), (
        'shipped CW page projects differ from the manifest committed inventory'
    )

    required = {VERIFICATION / 'index.md'}
    required.update(VERIFICATION / name for name in expected_sources)
    tracked = set(_run('git', 'ls-files').stdout.splitlines())
    untracked = sorted(
        str(path.relative_to(ROOT))
        for path in required
        if str(path.relative_to(ROOT)) not in tracked
    )
    assert not untracked, f'verification sources must be committed: {untracked}'

    notebook_paths = {str((VERIFICATION / name).relative_to(ROOT)) for name in expected_notebooks}
    assert not notebook_paths & tracked, (
        'generated verification notebooks must remain untracked derived artifacts'
    )
    ignored = set(
        _run('git', 'check-ignore', '--no-index', *sorted(notebook_paths)).stdout.splitlines()
    )
    assert ignored == notebook_paths, (
        'every derived verification notebook must be ignored until generated on demand'
    )

    for page in sorted(PAGES):
        notebook = jupytext.read(VERIFICATION / f'{page}.py', fmt='py:percent')
        code_cells = [cell for cell in notebook.cells if cell.cell_type == 'code']
        assert code_cells, f'{page}.ipynb must generate executable cells'
        for cell in code_cells:
            cell['execution_count'] = 1
            cell['outputs'] = [
                {'output_type': 'stream', 'name': 'stdout', 'text': 'derived output\n'}
            ]
        nbstripout.strip_output(
            notebook,
            keep_output=False,
            keep_count=False,
            keep_id=False,
        )
        for cell in code_cells:
            assert cell.get('execution_count') is None, (
                f'{page}.ipynb must be stripped after on-demand generation'
            )
            assert cell.get('outputs', []) == [], (
                f'{page}.ipynb must carry no generated outputs before execution'
            )


def test_fullprof_files_resolve_and_feed_every_page_comparison() -> None:
    tracked = set(_run('git', 'ls-files').stdout.splitlines())

    for page, expected_project in PAGES.items():
        source_path = VERIFICATION / f'{page}.py'
        tree = ast.parse(source_path.read_text(), filename=str(source_path))
        _assert_reference_files(page, expected_project, tree, tracked)
        if page != 'pd-neut-cwl_PbSO4_beba-asymmetry':
            _assert_fullprof_reference_flow(page, tree)
        #  PbSO4 uses the separate nonzero cryspy comparison gate.


def test_pixi_notebook_tasks_form_the_local_execution_gate() -> None:
    convert, _ = _task_config('notebook-convert')
    strip, _ = _task_config('notebook-strip')
    prepare, prepare_dependencies = _task_config('notebook-prepare')
    notebook_tests, notebook_test_dependencies = _task_config('notebook-tests')
    notebook_exec, notebook_exec_dependencies = _task_config('notebook-exec-ci')
    verification_exec, verification_exec_dependencies = _task_config('verification-exec')
    notebook_lint, _ = _task_config('notebook-lint-check')
    _, verify_chain = _task_config('verify')
    _, verify_dependencies = _task_config('verify-full')

    assert 'jupytext' in convert
    assert 'docs/dev/verification/*.py' in convert, (
        'notebook conversion must consume the relocated developer verification sources'
    )
    assert 'py:percent' in convert
    assert 'ipynb' in convert
    assert 'nbstripout' in strip
    assert 'docs/dev/verification/*.ipynb' in strip, (
        'notebook stripping must consume the relocated developer verification notebooks'
    )
    assert {'notebook-convert', 'notebook-strip'} <= prepare_dependencies or (
        'notebook-convert' in ' '.join(prepare) and 'notebook-strip' in ' '.join(prepare)
    )

    notebook_test_command = ' '.join(notebook_tests)
    assert 'pytest' in notebook_tests[0] or 'pytest' in notebook_test_command
    assert '--nbmake' in notebook_tests
    assert 'docs/dev/verification/' in notebook_tests, (
        'the local notebook gate must execute the relocated developer verification tree'
    )
    assert re.search(r'--nbmake-timeout(?:=|\s+)600(?:\s|$)', notebook_test_command)
    assert '--overwrite' not in notebook_tests
    assert 'core-build' in notebook_test_dependencies
    # : `verify` IS the merge-time full chain (`verify-full`); no wall-clock wrapper.
    assert 'verify-full' in verify_chain, (
        'the merge-time verification chain must include the declared full entry point'
    )
    assert 'notebook-tests' in verify_dependencies

    assert '--nbmake' in notebook_exec
    assert 'docs/dev/verification/' in notebook_exec, (
        'the CI notebook gate must execute the relocated developer verification tree'
    )
    assert '--overwrite' in notebook_exec
    assert 'core-build' in notebook_exec_dependencies
    assert 'notebook-exec-ci' in verification_exec_dependencies or (
        '--nbmake' in verification_exec
        and 'docs/dev/verification/' in verification_exec
        and '--overwrite' in verification_exec
    ), 'verification execution must transitively run the relocated notebooks with nbmake'
    assert 'ruff' in notebook_lint
    assert any('docs/dev/verification' in token for token in notebook_lint), (
        'notebook lint must inspect the relocated developer verification sources'
    )


def test_ci_runs_notebooks_for_every_result_changing_surface() -> None:
    workflow = (ROOT / '.github/workflows/ci.yml').read_text()
    notebook_job = _job_body(
        workflow, 'notebooks' if '\n  notebooks:' in workflow else 'notebook-tests'
    )
    # Before: per-surface filters. After  I1/I34: unconditional native reuse.
    assert re.search(r'^\s*needs:\s*\[changes, native\]\s*$', notebook_job, re.MULTILINE), (
        '/ notebooks wait for the shared pin and native producer'
    )
    from tests.fixtures.e09_t75_workflow import (  # noqa: PLC0415 - avoid test-module import cycles
        active,
    )
    from tests.integration.py.test_e09_t75_native_workflow import (  # noqa: PLC0415 - defer cross-module test wiring
        jobs,
        public_profile,
    )

    data = jobs()
    public = public_profile(data)
    assert all(
        active(data['notebooks'], event) for event in ('push', 'pull_request', 'workflow_dispatch')
    ), '/ notebooks run for every result-changing surface'
    assert 'uses: ./.github/actions/setup-pixi' in notebook_job
    assert 'pixi run notebook-tests' in notebook_job

    docs_job = _job_body(workflow, 'docs')
    assert all(
        active(data['docs'], event) for event in ('push', 'pull_request', 'workflow_dispatch')
    ), '/ required docs execution cannot be path-filtered'
    if not public:
        assert not re.search(r'^\s*if:', notebook_job + docs_job, re.MULTILINE), (
            'private notebooks and docs must retain unconditional jobs and steps'
        )
    else:
        from tests.system.py.test_e04_t12_public_release import (  # noqa: PLC0415 - avoid test-module import cycles
            test_public_ci_uses_hosted_runners_and_guards_private_tokens,
        )

        test_public_ci_uses_hosted_runners_and_guards_private_tokens()
    commands = [
        'pixi run notebook-prepare',
        'pixi run notebook-exec-ci',
        'pixi run docs-build',
    ]
    positions = [docs_job.find(command) for command in commands]
    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions), 'docs must prepare, execute, then render notebooks'
