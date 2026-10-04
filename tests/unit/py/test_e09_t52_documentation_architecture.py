from __future__ import annotations

import json
import re
import shlex
import subprocess
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def _relocated_fullprof_path(path: str) -> str:
    """Apply 's packet mapping to the unchanged  retention inventory."""
    prefix = 'knowledge/verification/fullprof/'
    relative = path.removeprefix(prefix)
    if '/' not in relative:
        return path
    directory, filename = relative.split('/', 1)
    renamed = {
        'pd-neut-cwl_lbco_basic': 'pd-neut-cwl_lbco-hrpt_basic',
        'pd-neut-tof_ncaf_jorgensen-von-dreele': 'pd-neut-tof_ncaf-wish_jorgensen-von-dreele',
        'pd-neut-tof_si_jorgensen': 'pd-neut-tof_si-sepd_jorgensen',
        'pd-neut-tof_si_jorgensen-von-dreele': 'pd-neut-tof_si-sepd_jorgensen-von-dreele',
        'pd-neut-tof_si_jorgensen-von-dreele-size-strain': (
            'pd-neut-tof_si-sepd_jorgensen-von-dreele-size-strain'
        ),
    }
    # LaB6 held two projects at the historical anchor; preserve every file in its
    # declared split destination, without allowing arbitrary basename matches.
    if directory == 'pd-neut-cwl_lab6':
        if filename.startswith('ECH0030684_LaB6_1p622A_11B.'):
            directory = 'pd-neut-cwl_lab6-echidna_11b'
        elif filename.startswith('ECH0030684_LaB6_1p622A_baseline.'):
            directory = 'pd-neut-cwl_lab6-echidna_basic'
    if directory == 'pd-neut-cwl_y2o3_isotropic-adp' and filename == 'y2o3.dat':
        filename = 'y2o3_isotropic_adp.dat'
    return prefix + renamed.get(directory, directory) + '/' + filename


def _git(*args: str) -> set[str]:
    completed = subprocess.run(
        ['git', '-C', ROOT, *args],
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, (
        'the independent edi Git inventory must resolve:\n' + completed.stdout + completed.stderr
    )
    return set(completed.stdout.splitlines())


def _task_command(tasks: object, name: str) -> str:
    row = tasks.get(name) if isinstance(tasks, dict) else None
    if isinstance(row, str):
        return row
    if not isinstance(row, dict):
        return ''
    command = row.get('cmd', '')
    if isinstance(command, list):
        return shlex.join(str(item) for item in command)
    return command if isinstance(command, str) else ''


def _shell_commands(command: str) -> list[list[str]]:
    commands: list[list[str]] = []
    for segment in re.split(r'(?:\n|&&|\|\||;)', command):
        lexer = shlex.shlex(segment, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = '#'
        try:
            argv = list(lexer)
        except ValueError:
            continue
        if argv:
            commands.append(argv)
    return commands


def _task_executes(tasks: object, name: str, subcommand: str) -> bool:
    return any(
        argv[:2] == ['mkdocs', subcommand] or argv[:4] == ['python', '-m', 'mkdocs', subcommand]
        for argv in _shell_commands(_task_command(tasks, name))
    )


def _runs_docs_build(command: str) -> bool:
    for argv in _shell_commands(command):
        if argv[:2] != ['pixi', 'run']:
            continue
        tail = argv[2:]
        if len(tail) >= 2 and tail[0] in {'-e', '--environment'}:
            tail = tail[2:]
        if tail and tail[0] == 'docs-build':
            return True
    return False


def _without_comments(text: str) -> str:
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    return re.sub(r'(?m)//.*$', '', text)


def _ci_executes_docs_build() -> bool:
    for path in (ROOT / '.github/workflows').glob('*.y*ml'):
        workflow = yaml.safe_load(path.read_text(encoding='utf-8'))
        jobs = workflow.get('jobs', {}) if isinstance(workflow, dict) else {}
        for job in jobs.values() if isinstance(jobs, dict) else ():
            steps = job.get('steps', []) if isinstance(job, dict) else []
            for step in steps if isinstance(steps, list) else ():
                run = step.get('run') if isinstance(step, dict) else None
                if (
                    isinstance(run, str)
                    and step.get('continue-on-error') is not True
                    and _runs_docs_build(run)
                ):
                    return True
    return False


def _documentation_problems() -> list[str]:
    problems: list[str] = []
    pixi = tomllib.loads((ROOT / 'pixi.toml').read_text(encoding='utf-8'))
    tasks = pixi.get('tasks', {})
    for task, subcommand in (('docs-build', 'build'), ('docs-serve', 'serve')):
        if not _task_executes(tasks, task, subcommand):
            problems.append(f'edi `{task}` must execute `mkdocs {subcommand}`')
    if not _ci_executes_docs_build():
        problems.append('edi CI must execute docs-build in a parsed, gating workflow step')

    mkdocs = yaml.load((ROOT / 'mkdocs.yml').read_text(encoding='utf-8'), Loader=yaml.BaseLoader)
    config = mkdocs if isinstance(mkdocs, dict) else {}
    css_refs = config.get('extra_css', [])
    js_refs = config.get('extra_javascript', [])
    css_refs = css_refs if isinstance(css_refs, list) else []
    js_refs = js_refs if isinstance(js_refs, list) else []
    css = _without_comments(
        '\n'.join(
            (ROOT / 'docs' / str(ref)).read_text(encoding='utf-8', errors='ignore')
            for ref in css_refs
            if (ROOT / 'docs' / str(ref)).is_file()
        )
    ).casefold()
    javascript = _without_comments(
        '\n'.join(
            (ROOT / 'docs' / str(ref)).read_text(encoding='utf-8', errors='ignore')
            for ref in js_refs
            if (ROOT / 'docs' / str(ref)).is_file()
        )
    ).casefold()
    if not (
        'audience-switcher' in css
        and re.search(r'position\s*:\s*fixed', css)
        and re.search(r'\bbottom\s*:', css)
        and re.search(r'\bright\s*:', css)
        and 'audience-switcher' in javascript
        and re.search(r'(?:/|["\'])user(?:/|["\'])', javascript)
        and re.search(r'(?:/|["\'])dev(?:/|["\'])', javascript)
        and re.search(r'(?:queryselector|getelementbyid|createelement)', javascript)
    ):
        problems.append('edi mkdocs must wire the bottom-right user/developer audience control')

    private_link = re.compile(
        r'(?:https?://|git@|href\s*=\s*["\']|src\s*=\s*["\'])?'
        r'(?:github\.com[/:]enhantica/physics|enhantica/physics)',
        re.IGNORECASE,
    )
    linked = [
        path.relative_to(ROOT).as_posix()
        for root in (ROOT / 'docs/user', ROOT / 'docs/dev')
        for path in root.rglob('*.md')
        if private_link.search(path.read_text(encoding='utf-8'))
    ]
    if linked:
        problems.append(f'edi documentation links into the private physics repo: {linked}')
    return problems


def test_e09_t52_edi_documentation_and_fixture_contract() -> None:
    tracked = _git('ls-files')
    problems: list[str] = []
    for audience in ('user', 'dev'):
        root = ROOT / 'docs' / audience
        if not any(path.is_file() for path in root.rglob('*.md')):
            problems.append(f'edi docs/{audience} has no documentation pages')
    if 'COORDINATION.md' in tracked:
        problems.append('edi must not gain a passenger COORDINATION.md')

    # Independent oracle fixtures remain beside their references, including 's
    # cryspy oracle; unrelated documentation and prefix lookalikes remain forbidden.
    allowed_knowledge = (
        'knowledge/verification/fullprof/',
        'knowledge/verification/cryspy/',
        'knowledge/fitting/fullprof/',
    )
    stale_knowledge = sorted(
        path
        for path in tracked
        if path.startswith('knowledge/') and not path.startswith(allowed_knowledge)
    )
    if stale_knowledge:
        problems.append(
            f'edi documentation remains outside docs/user + docs/dev: {stale_knowledge[:20]}'
        )
    frozen_fullprof = json.loads(
        (ROOT / 'tests/fixtures/e04_t12_public_release/history/documentation.json').read_text()
    )
    assert frozen_fullprof, 'the retained FullProf document inventory must not be empty'
    missing_fullprof = sorted(
        {_relocated_fullprof_path(path) for path in frozen_fullprof} - tracked
    )
    if missing_fullprof:
        problems.append(
            'edi FullProf references must stay beside their tests, never move to physics: '
            f'{missing_fullprof[:20]}'
        )

    problems.extend(_documentation_problems())

    assert not problems, ' edi documentation architecture violations:\n- ' + '\n- '.join(problems)
