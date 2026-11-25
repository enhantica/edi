# SPDX-License-Identifier: BSD-3-Clause
"""Check that edi's CI neither stores nor prints crysta's source (edi ADR-0083).

Reads the workflows and local actions, following a local action into its steps. A job that fetches
the source (the crysta-source action) runs in two phases: before the fetch each script names
`shell: bash`, after it every script runs under the output filter, everything stored goes through
the store action, and a script that publishes a folder comes after the check of that folder. What a
job without the source publishes is in the table below, by its own name; a new one is a change of
the table.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
FILTER = 'python3 tools/ci/public_log.py {0}'
SOURCE = './.github/actions/crysta-source'
STORE = './.github/actions/store'
# What jobs without the source publish: how, and the artifact, cache or command itself.
PUBLISHERS = {
    'ci.yml/system-time': {('artifact', 'system-time')},
    'ci.yml/system-durations': {('cache', 'test-durations-')},
    'installer-accessibility.yml/macos': {('artifact', 'installer-accessibility-macos')},
    'installers.yml/installer-pages': {('artifact', 'installer-pages-')},
    'installers.yml/qualify-release': {('artifact', 'qualified-release-plan-')},
    'release-plan.yml/plan': {('artifact', 'release-plan-')},
}
# What a job may keep before the source is on its runner: the browser toolchain it just installed.
BEFORE = {('cache', '${{ steps.wasm-cache.outputs.toolchain }}')}
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
# Prefixes of the compiler caches from before their entries were checked, and the families since.
RETIRED = re.compile(
    r'(?<![\w-])(?:ccache-(?:core|app|app-windows|installer|wasm)-|crysta-objects-|crysta-sdk-v[123]-)'
)
FAMILY = re.compile(r'ccache2-(core|app-windows|app|installer|wasm|crysta-sdk)-')
CHECKED = re.compile(r'tools/ci/stored_source\.py((?: +[^\n;&|]+)?)')


def action(step: dict) -> str:
    """The action a step uses, without its version."""
    return str(step.get('uses', '')).split('@')[0]


def named(step: dict) -> str:
    """What to call a step."""
    return step.get('name') or step.get('id') or action(step) or 'a step'


def published(step: dict) -> set[tuple[str, str]]:
    """How a step publishes, and what."""
    given = step.get('with') or {}
    found = set()
    if kind := USES.get(action(step)):
        found.add((kind, str(given.get('name') or given.get('key') or '')))
    for kind, text in RUNS.items():
        for match in text.finditer(str(step.get('run', ''))):
            folder = next((value for value in match.groupdict().values() if value), '')
            found.add((kind, folder))
    return found


def local_action(name: str) -> list[dict] | None:
    """A local action's steps."""
    for suffix in ('yml', 'yaml'):
        path = ROOT / name / f'action.{suffix}'
        if path.is_file():
            loaded = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
            return (loaded.get('runs') or {}).get('steps') or []
    return None


def inner(step: dict, seen: frozenset[str] = frozenset()) -> Iterator[tuple[str, dict]]:
    """The steps a local action runs, its own actions' too, and the action each is in."""
    name = action(step)
    if not name.startswith('./') or name in seen:
        return
    for nested in local_action(name) or []:
        yield name, nested
        yield from inner(nested, seen | {name})


def off(value: object) -> bool:
    """Whether an action input is false."""
    return str(value).lower() == 'false'


def before(where: str, step: dict) -> Iterator[str]:
    """What a step before the source may not do."""
    if 'run' in step and step.get('shell') != 'bash':
        yield f'{where}: {named(step)!r} comes before the source and does not name `shell: bash`'
    stored = published(step).union(*(published(nested) for _, nested in inner(step)))
    for kind, _ in sorted(stored - BEFORE):
        yield f'{where}: {named(step)!r} publishes ({kind}) outside the store action'


def after(where: str, step: dict, checked: set[str]) -> Iterator[str]:
    """What a step after the source may not do."""
    if 'shell' in step:
        yield f'{where}: {named(step)!r} overrides the output filter'
    if 'uses' in step and action(step) not in BESIDE:
        yield f'{where}: {named(step)!r} uses {action(step)} beside the source'
    if action(step) == './.github/actions/setup-pixi' and not off(
        (step.get('with') or {}).get('cache', 'true')
    ):
        yield f'{where}: {named(step)!r} caches an environment beside the source'
    if action(step) != STORE:
        for name, nested in inner(step):
            if 'run' in nested and nested.get('shell') != FILTER:
                yield f'{where}: {named(step)!r} runs {name} without the output filter'
            for kind, _ in published(nested):
                yield f'{where}: {named(step)!r} publishes ({kind}) outside the store action'
    for kind, what in sorted(published(step)):
        if kind != 'summary' and not (
            kind in {'site', 'release'} and what.split('/')[0] in checked
        ):
            yield f'{where}: {named(step)!r} publishes ({kind}) what no step has checked'


def source_job(where: str, job: dict) -> Iterator[str]:
    """What breaks the two phases of a job with the source."""
    if job.get('defaults', {}).get('run', {}).get('shell') != FILTER:
        yield f'{where}: its scripts do not run under the output filter'
    fetched, checked = False, set()
    for step in job['steps']:
        if action(step) == SOURCE:
            fetched = True
        elif not fetched:
            yield from before(where, step)
        else:
            yield from after(where, step, checked)
            for match in CHECKED.finditer(str(step.get('run', ''))):
                checked |= {
                    word.split('/')[0] for word in match[1].split() if word[0] not in '-"$'
                }


def other_job(where: str, job: dict) -> Iterator[str]:
    """What a job without the source publishes beside the table."""
    allowed = PUBLISHERS.get(where, set())
    for step in job['steps']:
        if action(step) == STORE:
            yield f'{where}: {named(step)!r} stores, and the job has no source to check against'
        nested = [pair for _, other in inner(step) for pair in published(other)]
        for kind, what in sorted([*published(step), *([] if action(step) == STORE else nested)]):
            if not any(kind == k and what.startswith(prefix) for k, prefix in allowed):
                yield f'{where}: {named(step)!r} publishes ({kind}) beside the table of publishers'


def store_action() -> Iterator[str]:
    """The store action stores exactly what it checked."""
    steps = local_action(STORE) or []
    paths = {str((step.get('with') or {}).get('path')) for step in steps if published(step)} | {
        str(value)
        for step in steps
        for name, value in (step.get('env') or {}).items()
        if name in {'PATHS', 'DIRECTORY'}
    }
    if paths != {'${{ inputs.path }}'}:
        yield 'actions/store: what it checks is not what it stores'
    if any('run' in step and step.get('shell') != FILTER for step in steps):
        yield 'actions/store: a check runs without the output filter'


def families(where: str, steps: list[dict]) -> Iterator[str]:
    """A compiler cache is restored and saved under its own family's prefix only."""
    by_path: dict[str, set[str]] = {}
    # Keys a step of this list, or of an action it uses, writes as its outputs.
    written = [str(step.get('run', '')) for step in steps]
    written += [str(nested.get('run', '')) for step in steps for _, nested in inner(step)]
    given_keys = {
        f'${{{{ steps.{source}.outputs.{name} }}}}': value
        for text in written
        for name, value in re.findall(r'echo "(\w+)=([^"]+)" >> "\$GITHUB_OUTPUT"', text)
        for source in ('keys', 'wasm-cache')
    }
    for step in steps:
        given = step.get('with') or {}
        keys = [str(given.get('key', ''))] + str(given.get('restore-keys', '')).split('\n')
        keys = [key.strip() for key in keys if key.strip()]
        path = str(given.get('path', ''))
        if 'ccache' not in path:
            continue
        for key in keys:
            if found := FAMILY.match(key) or FAMILY.search(given_keys.get(key, '')):
                by_path.setdefault(path, set()).add(found[1])
            else:
                yield f'{where}: {named(step)!r} uses a compiler cache key of no family'
    for path, found in by_path.items():
        if len(found) > 1 and found != {'core', 'app'}:
            yield f'{where}: the compiler cache {path} mixes the families {sorted(found)}'


def jobs() -> Iterator[tuple[str, dict]]:
    """Every workflow job with its steps."""
    folder = ROOT / '.github/workflows'
    for path in sorted([*folder.glob('*.yml'), *folder.glob('*.yaml')]):
        loaded = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        for name, job in (loaded.get('jobs') or {}).items():
            if job.get('steps'):
                yield f'{path.name}/{name}', job


def problems() -> Iterator[str]:
    """Everything the workflows may not do."""
    for where, job in jobs():
        has_source = any(
            action(step) == SOURCE or any(action(s) == SOURCE for _, s in inner(step))
            for step in job['steps']
        )
        yield from (source_job if has_source else other_job)(where, job)
        yield from families(where, job['steps'])
    for path in sorted((ROOT / '.github/actions').iterdir()):
        name = f'./.github/actions/{path.name}'
        steps = local_action(name) or []
        yield from families(f'actions/{path.name}', steps)
        if name != STORE:
            for step in steps:
                for kind, _ in published(step):
                    yield f'actions/{path.name}: publishes ({kind}) outside the store action'
    yield from store_action()
    for path in sorted([*(ROOT / '.github').rglob('*.yml'), *(ROOT / '.github').rglob('*.yaml')]):
        text = path.read_text(encoding='utf-8')
        where = path.relative_to(ROOT)
        if RETIRED.search(text):
            yield f'{where}: names a cache from before its entries were checked'
        if 'CCACHE_DEBUG' in text:
            yield f'{where}: CCACHE_DEBUG stores preprocessed source'
        if 'crysta-src-' in text:
            yield f'{where}: names an archive of the source'


def main() -> int:
    """Exit 1 with every problem."""
    found = list(problems())
    for line in found:
        print(f'source-publishers: {line}', file=sys.stderr)
    return 1 if found else 0


if __name__ == '__main__':
    raise SystemExit(main())
