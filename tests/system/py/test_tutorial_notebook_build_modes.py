"""Owner 17dfac195: local conversion, skipped placeholders and strict publication."""

import os
import re
import shlex
import subprocess
import sys
import tomllib
from urllib.parse import urlparse

import pytest
import yaml
from bs4 import BeautifulSoup

from tests.fixtures.tutorial_cases.assistant_hub import local_page
from tests.fixtures.tutorial_cases.assistant_versions import USER_BASE
from tests.fixtures.tutorial_cases.contract import ROOT, cases_for
from tests.fixtures.tutorial_cases.pipeline import executed_inputs, stage

UNRUN = 'pd-neut-cwl_lbco-hrpt'
RUN = 'pd-neut-cwl_cosio-d20'


@pytest.fixture(scope='module')
def mode_builds(tmp_path_factory):
    commit = subprocess.check_output(
        ['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True
    ).strip()
    builds = {}
    for mode, flags in [
        ('local', []),
        ('strict', ['--require-outputs']),
        ('skip', ['--no-notebooks']),
    ]:
        root = stage(tmp_path_factory.mktemp('notebook-' + mode) / 'source')
        # Actual menu inputs and data are prerequisites of the public builder, not answers.
        import shutil  # noqa: PLC0415

        for relative in ['data', 'app/qml', 'app/src']:
            shutil.copytree(ROOT / relative, root / relative)
        for source in (ROOT / 'docs/user/tutorials').glob('*.py'):
            shutil.copy2(source, root / 'docs/user/tutorials' / source.name)
        executed_inputs(root, unrun=UNRUN)
        if mode == 'skip':
            for path in (root / 'docs/user/tutorials').glob('*.ipynb'):
                path.unlink()
        result = subprocess.run(
            [
                sys.executable,
                str(root / 'website/build.py'),
                'surfaces',
                '--base-url',
                USER_BASE,
                *flags,
            ],
            cwd=root,
            env={
                **os.environ,
                'GITHUB_ACTIONS': 'true',
                'GITHUB_WORKSPACE': str(root),
                'GITHUB_SHA': commit,
                'GITHUB_REF_NAME': 'main',
                'EDI_DOCS_REF': commit,
                'EDI_PREVIEW_PAGES_REF': '',
                'NO_COLOR': '1',
            },
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        (root / 'mode-build.log').write_text(result.stdout + result.stderr)
        builds[mode] = root, result
    return builds


def built_page(builds, mode, case):
    root, result = builds[mode]
    assert result.returncode == 0, (
        'Gate 3: the public '
        + mode
        + ' build must succeed without executing notebooks: '
        + result.stdout[-1500:]
        + result.stderr[-2500:]
    )
    page = root / 'website/_build/python/tutorials/cases' / case / 'index.html'
    assert page.is_file(), 'Gate 3: local modes retain each declared tutorial URL'
    return BeautifulSoup(page.read_text(), 'html.parser')


def test_local_build_publishes_unrun_code_with_a_visible_not_run_note(mode_builds):
    soup = built_page(mode_builds, 'local', UNRUN)
    main = soup.select_one('main')
    assert main is not None and 'CONVERSION_MUST_NOT_EXECUTE' in main.get_text(), (
        'Gate 3: a local unrun page shows its actual input code without executing it'
    )
    notes = main.select('.admonition, [role=note]')
    assert any(
        re.search(r'not\s+run', note.get_text(' ', strip=True), re.IGNORECASE) for note in notes
    ), 'Gate 3: the local unrun page has a visible Not run notice'


def test_local_build_preserves_existing_outputs_and_hides_install_cells(mode_builds):
    soup = built_page(mode_builds, 'local', RUN)
    main = soup.select_one('main')
    assert main is not None and 'CONVERTED_OUTPUT_SENTINEL' in main.get_text(), (
        'Gate 3: permissive local conversion preserves the outputs that are present'
    )
    assert not any(
        token in main.get_text() for token in ['HIDDEN_INPUT_SENTINEL', 'HIDDEN_OUTPUT_SENTINEL']
    ), 'Gate 3: local conversion still omits every hide-in-docs input and output'


def test_strict_public_build_refuses_the_unrun_case_with_an_execution_instruction(mode_builds):
    _root, result = mode_builds['strict']
    output = result.stdout + result.stderr
    assert result.returncode != 0 and UNRUN in output and 'notebooks-run' in output, (
        'Gate 3: --require-outputs refuses the actual unrun case and directs the user to run it'
    )
    assert 'CONVERSION_MUST_NOT_EXECUTE' not in output, (
        'Gate 3: a strict build refuses missing outputs without running the raising control cell'
    )


def test_no_notebooks_build_has_placeholders_and_resolving_tutorial_navigation(mode_builds):
    root, _result = mode_builds['skip']
    assert not list((root / 'docs/user/tutorials').glob('*.ipynb')), (
        'Gate 3: the skip-mode witness really has no notebook files'
    )
    for case in cases_for('python'):
        soup = built_page(mode_builds, 'skip', case)
        main = soup.select_one('main')
        assert main is not None and re.search(
            r'skip|not\s+included|not\s+built', main.get_text(), re.IGNORECASE
        ), 'Gate 3: --no-notebooks writes a visible placeholder at every declared Python URL'
    site = root / 'website/_build'
    home = site / 'index.html'
    nav = BeautifulSoup(home.read_text(), 'html.parser').select_one('.md-nav--primary')
    assert nav is not None, 'Gate 3: a skipped-notebook build retains real site navigation'
    links = [link['href'] for link in nav.select('a[href]') if 'tutorial' in link['href']]
    assert links, 'Gate 3: skip mode retains tutorial navigation rather than deleting its links'
    for address in links:
        if not urlparse(address).netloc or address.startswith(USER_BASE):
            local_page(address, home, site)


@pytest.mark.parametrize('task', ['site-build', 'site-serve'])
def test_both_local_task_entry_points_expose_the_notebook_mode_switches(task):
    tasks = tomllib.loads((ROOT / 'pixi.toml').read_text())['tasks']
    definition = tasks[task]
    command = definition.get('cmd') if isinstance(definition, dict) else definition
    arguments = shlex.split(command) if isinstance(command, str) else list(command)
    if arguments[0] in {'python', 'python3'}:
        arguments[0] = sys.executable
    result = subprocess.run(
        [*arguments, '--help'], cwd=ROOT, capture_output=True, text=True, timeout=15, check=False
    )
    assert result.returncode == 0 and all(
        flag in result.stdout for flag in ['--require-outputs', '--no-notebooks']
    ), 'Gate 3: site-build and site-serve expose strict and skip modes through their real commands'


@pytest.mark.parametrize('filename', ['pages.yml', 'ci.yml'])
def test_publishing_and_ci_docs_checks_explicitly_require_notebook_outputs(filename):
    workflow = yaml.safe_load((ROOT / '.github/workflows' / filename).read_text())
    jobs = workflow['jobs']
    if filename == 'ci.yml':
        assert 'docs' in jobs, 'Gate 3: CI retains its documentation-check job'
        jobs = {'docs': jobs['docs']}
    commands = [step.get('run', '') for job in jobs.values() for step in job.get('steps', [])]
    site_commands = []
    for command in commands:
        for line in command.replace('\\\n', ' ').splitlines():
            arguments = shlex.split(line, comments=True)
            if not arguments:
                continue
            if (arguments[0] == 'pixi' and 'run' in arguments and 'site-build' in arguments) or (
                arguments[0] in {'python', 'python3'} and 'website/build.py' in arguments
            ):
                site_commands.append(arguments)
    assert site_commands and all(
        '--require-outputs' in command and '--no-notebooks' not in command
        for command in site_commands
    ), 'Gate 3: Pages and the CI docs check explicitly require outputs and never skip notebooks'
