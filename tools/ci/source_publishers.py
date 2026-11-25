# SPDX-License-Identifier: BSD-3-Clause
"""Check that edi's CI neither stores nor prints crysta's source (edi ADR-0083).

Reads the workflows and local actions, following a local action into its steps with its inputs. A
job that fetches the source (the crysta-source action) runs in two phases: before the fetch each
script names `shell: bash`, after it every script runs under the output filter, everything stored
goes through the store action, and a script that publishes a folder comes right after a check of
that folder that always runs. The two actions all of this rests on are held to their committed
form. What a job without the source publishes, and the keys of each cache, are in the tables
below; a new one is a change of its table.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
FILTER = 'python3 tools/ci/public_log.py {0}'
SOURCE = './.github/actions/crysta-source'
STORE = './.github/actions/store'
# The steps of the actions everything here relies on, as reviewed: `--digests` prints them.
REVIEWED = {
    SOURCE: '816fb94ec132e30ded9f0c8fc76c59e2f840ba00dde3a195a691d890395ed656',
    STORE: '05b4c58e0eac79e613bc94a9fbab5a7863d29549d196ff9c6b7206d340eaa11f',
}
# What jobs without the source publish: how, and the artifact, cache key or command itself.
PUBLISHERS = {
    'ci.yml/system-time': {('artifact', 'system-time')},
    'ci.yml/system-durations': {('cache', 'test-durations-${{ runner.os }}-${{ github.run_id }}')},
    'installer-accessibility.yml/macos': {('artifact', 'installer-accessibility-macos')},
    'installers.yml/installer-pages': {('artifact', 'installer-pages-${{ runner.os }}')},
    'installers.yml/qualify-release': {
        ('artifact', 'qualified-release-plan-${{ github.run_attempt }}')
    },
    'release-plan.yml/plan': {('artifact', 'release-plan-${{ github.run_attempt }}')},
}
# What a job may keep before the source is on its runner: the browser toolchain it just installed.
BEFORE = {('cache', '${{ steps.wasm-cache.outputs.toolchain }}')}
# Every cache a job may restore or save: its path, and how each of its keys begins.
CORE = {'~/.cache/edi-ccache': 'ccache2-core-'}
APP = {
    '~/.cache/edi-ccache': 'ccache2-app-',
    '${{ runner.temp }}/edi-ccache': 'ccache2-app-windows-',
    'build/app/app/edi_app\nbuild/app/app/edi_app_tests\nbuild/app/app/edi_assistant_guard': (
        'edi-app-'
    ),
    'build/tutorial-transactions': 'edi-observer-',
}
WASM = {'~/.cache/edi-ccache': 'ccache2-wasm-', '~/.cache/edi-wasm': 'edi-wasm2-'}
DURATIONS = {'build/test-durations.json': 'test-durations-'}
CACHES = {
    **dict.fromkeys(
        [
            f'ci.yml/{job}'
            for job in ('native', 'audit', 'core', 'notebooks', 'cli-python', 'docs')
        ],
        CORE,
    ),
    'ci.yml/system': {
        **CORE,
        **DURATIONS,
        **{path: key for path, key in APP.items() if not key.startswith('ccache2-')},
    },
    'ci.yml/system-durations': DURATIONS,
    **dict.fromkeys([f'ci.yml/{job}' for job in ('app', 'app-macos', 'app-windows')], APP),
    'ci.yml/app-wasm': WASM,
    'pages.yml/wasm': WASM,
    'crysta-sdk.yml/build': {
        'crysta-sdk-archives': 'crysta-sdk-v4-',
        '${{ runner.temp }}/crysta-ccache': 'ccache2-crysta-sdk-',
    },
    'installers.yml/installers': {'${{ runner.temp }}/edi-ccache': 'ccache2-installer-'},
}
USES = {
    'actions/upload-artifact': 'artifact',
    'actions/upload-pages-artifact': 'artifact',
    'actions/cache': 'cache',
    'actions/cache/save': 'cache',
    'softprops/action-gh-release': 'release',
    'actions/deploy-pages': 'site',
    'peaceiris/actions-gh-pages': 'site',
}
# A script that publishes, and the folder it takes.
RUNS = {
    'site': re.compile(r'push_deploy_branch\.sh +(?P<folder>[^\s"]+)|\bgit push\b'),
    'release': re.compile(
        r'publish_assets\.py\b[^\n]*--folder +(?P<folder>[^\s"]+)'
        r'|preview_draft\.py\b[\s\S]*?(?P<drafts>preview-delivery)/'
        r'|\bgh release (?:create|upload)\b|uploads\.github\.com'
    ),
    'summary': re.compile(r'GITHUB_STEP_SUMMARY'),
}
# What may run beside the source: none of these runs crysta's code or prints its files.
BESIDE = {
    'actions/cache/restore',
    'actions/create-github-app-token',
    'actions/download-artifact',
    'apple-actions/import-codesign-certs',
    'digicert/code-signing-software-trust-action',
    './.github/actions/setup-pixi',
    STORE,
}
# What may come between a check and what it lets publish: neither writes into the folder.
HARMLESS = {'actions/create-github-app-token', STORE}
# Prefixes of caches from before their content was checked.
RETIRED = re.compile(
    r'(?<![\w-])(?:ccache-(?:core|app|app-windows|installer|wasm)-|crysta-objects-'
    r'|crysta-sdk-v[123]-|edi-wasm-(?=\$))'
)
CHECK = re.compile(
    r'python3 tools/ci/stored_source\.py((?: +--receipt [\w./-]+)?)((?: +[\w./-]+)+)'
)


def action(step: dict) -> str:
    """The action a step uses, without its version."""
    return str(step.get('uses', '')).split('@')[0]


def given(step: dict, name: str) -> str:
    """An input of the action a step uses."""
    return str((step.get('with') or {}).get(name, '')).strip()


def named(step: dict) -> str:
    """What to call a step."""
    return step.get('name') or step.get('id') or action(step) or 'a step'


def published(step: dict) -> set[tuple[str, str]]:
    """How a step publishes, and what."""
    found = set()
    if kind := USES.get(action(step)):
        found.add((kind, given(step, 'name') or given(step, 'key')))
    for kind, text in RUNS.items():
        for match in text.finditer(str(step.get('run', ''))):
            folder = next((value for value in match.groupdict().values() if value), '')
            found.add((kind, folder))
    return found


def local_action(name: str) -> dict:
    """A local action."""
    for suffix in ('yml', 'yaml'):
        path = ROOT / name / f'action.{suffix}'
        if path.is_file():
            return yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    return {}


def steps_of(name: str) -> list[dict]:
    """A local action's steps."""
    return (local_action(name).get('runs') or {}).get('steps') or []


def digest(name: str) -> str:
    """What identifies a local action's behaviour: its inputs' defaults and its steps."""
    loaded = local_action(name)
    inputs = {key: (value or {}).get('default') for key, value in loaded.get('inputs', {}).items()}
    held = json.dumps([inputs, loaded.get('runs')], sort_keys=True)
    return hashlib.sha256(held.encode()).hexdigest()


def inner(step: dict, seen: frozenset[str] = frozenset()) -> Iterator[tuple[str, dict]]:
    """The steps a local action runs with its inputs filled in, its own actions' too."""
    name = action(step)
    if not name.startswith('./') or name in seen:
        return
    defaults = local_action(name).get('inputs') or {}
    for nested in steps_of(name):
        filled = json.dumps(nested)
        for key, value in defaults.items():
            text = given(step, key) or str((value or {}).get('default', ''))
            filled = filled.replace(f'${{{{ inputs.{key} }}}}', json.dumps(text)[1:-1])
        made = json.loads(filled)
        yield name, made
        yield from inner(made, seen | {name})


def before(where: str, step: dict) -> Iterator[str]:
    """What a step before the source may not do."""
    if 'run' in step and step.get('shell') != 'bash':
        yield f'{where}: {named(step)!r} comes before the source and does not name `shell: bash`'
    if action(step) == STORE:
        yield f'{where}: {named(step)!r} stores before there is a source to check against'
        return
    stored = published(step).union(*(published(nested) for _, nested in inner(step)))
    for kind, _ in sorted(stored - BEFORE):
        yield f'{where}: {named(step)!r} publishes ({kind}) outside the store action'


def after(where: str, step: dict, checked: set[str]) -> Iterator[str]:
    """What a step after the source may not do."""
    if 'shell' in step:
        yield f'{where}: {named(step)!r} overrides the output filter'
    if 'uses' in step and action(step) not in BESIDE:
        yield f'{where}: {named(step)!r} uses {action(step)} beside the source'
    if action(step) == './.github/actions/setup-pixi' and given(step, 'cache').lower() != 'false':
        yield f'{where}: {named(step)!r} caches an environment beside the source'
    if action(step) != STORE:
        for name, nested in inner(step):
            if 'run' in nested and nested.get('shell') != FILTER:
                yield f'{where}: {named(step)!r} runs {name} without the output filter'
            for kind, _ in published(nested):
                yield f'{where}: {named(step)!r} publishes ({kind}) outside the store action'
    for kind, what in sorted(published(step)):
        if kind != 'summary' and not (kind in {'site', 'release'} and within(what, checked)):
            yield f'{where}: {named(step)!r} publishes ({kind}) what no step has checked'


def within(folder: str, checked: set[str]) -> bool:
    """Whether a published folder is a checked one or inside it."""
    plain = re.fullmatch(r'[\w.-]+(?:/[\w.-]+)*', folder) and '..' not in folder.split('/')
    return bool(plain) and any(folder == path or folder.startswith(f'{path}/') for path in checked)


def checks(step: dict) -> set[str]:
    """The folders a step checks, always and with nothing else."""
    match = CHECK.fullmatch(str(step.get('run', '')).strip())
    if match is None or {'if', 'continue-on-error', 'working-directory', 'env'} & set(step):
        return set()
    return set(match[2].split())


def source_job(where: str, job: dict) -> Iterator[str]:
    """What breaks the two phases of a job with the source."""
    run = (job.get('defaults') or {}).get('run') or {}
    if run.get('shell') != FILTER or 'working-directory' in run:
        yield f'{where}: its scripts do not run under the output filter'
    if 'continue-on-error' in job:
        yield f'{where}: it goes on after a refusal'
    fetched: dict | None = None
    checked: set[str] = set()
    for step in job['steps']:
        if action(step) == SOURCE:
            if 'continue-on-error' in step:
                yield f'{where}: it goes on without the source'
            fetched = step
        elif fetched is None:
            yield from before(where, step)
        else:
            yield from after(where, step, checked)
            publishes = {kind for kind, _ in published(step)} & {'site', 'release'}
            if publishes and given(fetched, 'history') != 'true':
                yield f'{where}: {named(step)!r} publishes what other commits made'
            if found := checks(step):
                checked |= found
            elif action(step) not in HARMLESS and not publishes:
                checked = set()


def other_job(where: str, job: dict) -> Iterator[str]:
    """What a job without the source publishes beside the table."""
    allowed = PUBLISHERS.get(where, set())
    for step in job['steps']:
        if action(step) == STORE:
            yield f'{where}: {named(step)!r} stores, and the job has no source to check against'
            continue
        made = published(step).union(*(published(nested) for _, nested in inner(step)))
        for kind, _ in sorted(made - allowed):
            yield f'{where}: {named(step)!r} publishes ({kind}) beside the table of publishers'


def resolved(key: str, steps: list[dict]) -> str:
    """A cache key, with an output of the job's own steps as that step writes it."""
    match = re.fullmatch(r'\$\{\{ steps\.([\w-]+)\.outputs\.([\w-]+) \}\}', key)
    step = next((step for step in steps if match and step.get('id') == match[1]), None)
    if match is None or step is None:
        return key
    if match[2] == 'cache-primary-key':
        return given(step, 'key')
    value = ((local_action(action(step)).get('outputs') or {}).get(match[2]) or {}).get(
        'value', ''
    )
    nested = [made for _, made in inner(step)]
    if value:
        return resolved(value, nested)
    written = re.search(
        rf'echo "{match[2]}=([^"]+)" >> "\$GITHUB_OUTPUT"', str(step.get('run', ''))
    )
    return written[1] if written else key


def cache_steps(step: dict, steps: list[dict]) -> Iterator[tuple[str, list[str]]]:
    """Each cache a step restores or saves: its path and keys."""
    scope = [(step, steps)]
    nested = [made for _, made in inner(step)]
    scope += [(made, nested + steps) for made in nested]
    for made, around in scope:
        if action(made) not in {'actions/cache', 'actions/cache/restore', 'actions/cache/save'}:
            continue
        keys = [given(made, 'key'), *given(made, 'restore-keys').splitlines()]
        keys = [resolved(key.strip(), around) for key in keys if key.strip()]
        if keys:
            yield given(made, 'path'), keys


def caches(where: str, job: dict) -> Iterator[str]:
    """A cache is restored and saved at its own path under its own keys."""
    allowed = CACHES.get(where, {})
    for step in job['steps']:
        for path, keys in cache_steps(step, job['steps']):
            prefix = allowed.get(path)
            for key in keys:
                if prefix is None or not re.fullmatch(rf'{re.escape(prefix)}(?:\$\{{\{{.*)?', key):
                    yield f'{where}: {named(step)!r} uses the cache {path} with the key {key}'


def jobs() -> Iterator[tuple[str, dict]]:
    """Every workflow job with its steps."""
    folder = ROOT / '.github/workflows'
    for path in sorted([*folder.glob('*.yml'), *folder.glob('*.yaml')]):
        loaded = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        for name, job in (loaded.get('jobs') or {}).items():
            yield f'{path.name}/{name}', job


def problems() -> Iterator[str]:
    """Everything the workflows may not do."""
    for name, known in REVIEWED.items():
        if digest(name) != known:
            yield f'{name}: it is not the action that was reviewed'
    for where, job in jobs():
        if 'steps' not in job:
            if not str(job.get('uses', '')).startswith('./.github/workflows/'):
                yield f'{where}: runs a workflow that is not here'
            continue
        uses = [action(step) for step in job['steps']]
        uses += [action(made) for step in job['steps'] for _, made in inner(step)]
        yield from (source_job if SOURCE in uses else other_job)(where, job)
        yield from caches(where, job)
    for path in sorted((ROOT / '.github/actions').iterdir()):
        name = f'./.github/actions/{path.name}'
        for step in steps_of(name) if name != STORE else []:
            for kind, _ in published(step):
                yield f'actions/{path.name}: publishes ({kind}) outside the store action'
    for path in sorted([*(ROOT / '.github').rglob('*.yml'), *(ROOT / '.github').rglob('*.yaml')]):
        text = path.read_text(encoding='utf-8')
        where = path.relative_to(ROOT)
        if RETIRED.search(text):
            yield f'{where}: names a cache from before its content was checked'
        if 'CCACHE_DEBUG' in text:
            yield f'{where}: CCACHE_DEBUG stores preprocessed source'
        if 'crysta-src-' in text:
            yield f'{where}: names an archive of the source'


def main() -> int:
    """Exit 1 with every problem."""
    if sys.argv[1:] == ['--digests']:
        for name in REVIEWED:
            print(name, digest(name))
        return 0
    found = list(problems())
    for line in found:
        print(f'source-publishers: {line}', file=sys.stderr)
    return 1 if found else 0


if __name__ == '__main__':
    raise SystemExit(main())
