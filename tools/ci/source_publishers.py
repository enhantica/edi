# SPDX-License-Identifier: BSD-3-Clause
"""Check that edi's CI neither stores nor prints crysta's source (edi ADR-0083).

Reads the workflows and local actions. A job that fetches the source (the crysta-source action)
runs its steps in two phases: before the fetch each script names `shell: bash`, after it every
script runs under the output filter and everything stored goes through .github/actions/store. Every
place that publishes anything is in the table below; a new one is a change of the table.
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
# Every publisher outside a job with the source, by workflow and job (inside: the store action).
PUBLISHERS = {
    'ci.yml/system-time': {'artifact'},
    'ci.yml/system-durations': {'cache'},
    'installer-accessibility.yml/macos': {'artifact'},
    'installers.yml/installer-pages': {'artifact'},
    'installers.yml/qualify-release': {'artifact'},
    'installers.yml/draft-preview-release': {'release'},
    'installers.yml/publish-installers': {'site'},
    'pages.yml/publish-docs': {'site'},
    'pages.yml/publish-wasm': {'site'},
    'release-plan.yml/plan': {'artifact'},
    'release-publish.yml/publish': {'artifact', 'release', 'site'},
    'coverage.yml/coverage': {'summary'},
}
USES = {
    'actions/upload-artifact': 'artifact',
    'actions/upload-pages-artifact': 'artifact',
    'actions/cache': 'cache',
    'actions/cache/save': 'cache',
    'softprops/action-gh-release': 'release',
    'actions/deploy-pages': 'site',
}
RUNS = {
    'release': re.compile(
        r'\bgh release (?:create|upload)\b|uploads\.github\.com|/releases/assets\b'
    ),
    'site': re.compile(r'push_deploy_branch\.sh|\bgit push\b'),
    'summary': re.compile(r'GITHUB_STEP_SUMMARY'),
}
# What may run beside the source: none of these runs crysta's code or prints its files.
BESIDE = {
    'actions/cache/restore',
    'actions/download-artifact',
    'apple-actions/import-codesign-certs',
    'digicert/code-signing-software-trust-action',
    './.github/actions/crysta-sdk',
    './.github/actions/edi-native',
    './.github/actions/setup-pixi',
    './.github/actions/wasm-cache',
    STORE,
}
# Prefixes of the compiler caches from before their entries were checked.
RETIRED = re.compile(
    r'(?<![\w-])(?:ccache-(?:core|app|app-windows|installer|wasm)-|crysta-objects-|crysta-sdk-v[123]-)'
)


def action(step: dict) -> str:
    """The action a step uses, without its version."""
    return str(step.get('uses', '')).split('@')[0]


def published(step: dict) -> set[str]:
    """How a step publishes."""
    kinds = {USES[action(step)]} if action(step) in USES else set()
    return kinds | {kind for kind, text in RUNS.items() if text.search(str(step.get('run', '')))}


def off(value: object) -> bool:
    """Whether an action input is false."""
    return str(value).lower() == 'false'


def source_job(where: str, job: dict) -> Iterator[str]:
    """What breaks the two phases of a job with the source."""
    if job.get('defaults', {}).get('run', {}).get('shell') != FILTER:
        yield f'{where}: its scripts do not run under the output filter'
    fetched = False
    for step in job['steps']:
        name = step.get('name') or step.get('id') or action(step) or 'a step'
        if action(step) == SOURCE:
            fetched = True
        elif not fetched:
            if 'run' in step and step.get('shell') != 'bash':
                yield f'{where}: {name!r} comes before the source and does not name `shell: bash`'
            if published(step):
                yield f'{where}: {name!r} publishes outside the store action'
        else:
            if 'shell' in step:
                yield f'{where}: {name!r} overrides the output filter'
            if 'uses' in step and action(step) not in BESIDE:
                yield f'{where}: {name!r} uses {action(step)} beside the source'
            if action(step) == './.github/actions/setup-pixi' and not off(
                (step.get('with') or {}).get('cache', 'true')
            ):
                yield f'{where}: {name!r} caches an environment beside the source'
            if published(step) - {'summary'}:
                yield f'{where}: {name!r} publishes outside the store action'


def jobs() -> Iterator[tuple[str, dict]]:
    """Every workflow job with its steps."""
    for path in sorted((ROOT / '.github/workflows').glob('*.yml')):
        for name, job in (
            yaml.safe_load(path.read_text(encoding='utf-8')).get('jobs') or {}
        ).items():
            if job.get('steps'):
                yield f'{path.name}/{name}', job


def local_actions() -> Iterator[tuple[str, list[dict]]]:
    """Every local action's steps."""
    for path in sorted((ROOT / '.github/actions').glob('*/action.yml')):
        runs = yaml.safe_load(path.read_text(encoding='utf-8')).get('runs') or {}
        yield path.parent.name, runs.get('steps') or []


def problems() -> Iterator[str]:
    """Everything the workflows may not do."""
    for where, job in jobs():
        if any(action(step) == SOURCE for step in job['steps']):
            yield from source_job(where, job)
        kinds = set().union(*map(published, job['steps']))
        has_source = any(action(step) == SOURCE for step in job['steps'])
        for kind in sorted(kinds - PUBLISHERS.get(where, set())):
            if not has_source or kind == 'summary':
                yield f'{where}: publishes ({kind}) and is not in the table of publishers'
    for name, steps in local_actions():
        for step in steps:
            if name != 'store' and published(step):
                yield f'actions/{name}: publishes outside the store action'
    for path in sorted((ROOT / '.github').rglob('*.yml')):
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
