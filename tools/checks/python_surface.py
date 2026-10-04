#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""edi's public Python surface — the declaration, its checks, and the necessity record.

edi's public Python interface is ``edi.__all__`` (``lib/edi/__init__.py``). This tool owns its
*declaration*: ``data/python-surface.json`` carries (a) ``public`` — every name in ``edi.__all__``
with its kind and, for a class, its sorted non-underscore attribute names (``dir()``), generated
by introspection of the built package; (b) ``classification`` — a verdict for EVERY current module
name and every member of EVERY class-like module attribute (``public`` / ``internal``: the
audience answer — a single-underscore name or a re-export is internal), each row also carrying a
``need`` object — the necessity answer: every member either has a diffraction-lib
COUNTERPART (``keep by=counterpart``, the inventory entity it implements), or is a DEVIATION
justified by a row of the deviation register (``keep by=deviation``, ``D<N>``), or is derived
from its owning class (``keep by=owner`` — an enum's values and members inherited from a base
outside the product), or is ``remove`` (deleted in the same change set, then recorded under (c)
``removed``), or is ``undecided`` (transient: a one-line question routed to the owner; red until
replaced). No verdict rests on a consumer search.

``--write`` regenerates the ``public`` and ``classification`` sections from the built package
(keeping every existing verdict and ``need``, auto-filling ``owner`` derivations); edi renders no
documentation region (``--docs none`` is the default here). ``--check`` regenerates in memory and
diffs: drift, an unclassified or stale entry, a public key with a non-public verdict, a row without
a ``need``, a ``remove`` or ``undecided`` verdict, a ``removed`` name that is still reachable, an
``owner`` derivation that no longer re-resolves or whose owner is not kept, a stale documentation
region — all red. ``--sweep`` prints, per row, what the entity map proposes (the
counterpart entity, or none): a candidate filter, never a verdict.

WHAT THE CHECKS PROVE, AND DO NOT (``NECESSITY_LIMIT``): totality and resolution of the shape —
every published name and member carries a verdict that names a counterpart entity or a register
row; whether that entity exists in the committed inventory and is tied to THIS member by the
entity map, and whether that register row exists, is well-formed and names the member, is proven
by the register's own check. Neither half proves that a member is NEEDED — that judgement is
the register row's, written by a human — nor that a counterpart means the same thing (kept by
review).

This is the edi copy of crysta's ``tools/checks/python_surface.py`` (same schema, same ``need``
vocabulary, same checks): the two files differ in ``MODULE_NAME``, the audience vocabulary and the
docs default, and edi's superset gate (``python_surface_superset.py``) is what ties the two
declarations together. See ``EXISTENCE_LIMIT``; direction: see ``DIRECTIONALITY``.

ARCHIVE_NOTE: a removal record protects its own cycle from the
LIVE manifest; at ship it is ROTATED into ``data/python-surface-removed-archive.json`` by
``--archive-removed``, and the check asserts unreachability over the UNION of live + archive, so
an archived name stays asserted-absent forever while the live map stays bounded to the cycles
since the last rotation. The first rotation is a ship-time act coordinated with the hidden gates
that freeze against the removed inventory.
"""

from __future__ import annotations

import argparse
import importlib
import json
import pkgutil
import re
import sys
import types
from pathlib import Path
from typing import Any

SCHEMA = 4
MODULE_NAME = 'edi'
DIRECTIONALITY = (
    'crysta-py ⊆ edi-py is a standing constraint on edi: a name enters crysta.__all__ only in a '
    "commit where edi carries it; a public crysta name edi lacks is red at crysta's PR consumer "
    "job today, and at edi's verify against the pinned crysta once edi's tools/ci/crysta.pin "
    'carries the declaration — crysta cannot add a public name without edi '
    'following'
)
EXISTENCE_LIMIT = (
    'This check proves EXISTENCE only: every declared name, and every declared member of a '
    'declared class, resolves in edi by attribute lookup - the rule that crysta may not get ahead '
    'of edi, and nothing more. It records and compares no signature, default, type, base chain or '
    'behaviour - surface existence, never semantics; whether refine computes the same thing on '
    'both is demonstrated by the substitution scripts (crysta tools/substitution/) for the paths '
    'they cover and proven by tests, never by this gate.'
)
NECESSITY_LIMIT = (
    'The necessity checks prove RESOLUTION, not need: every published name and member carries '
    'exactly one verdict naming a diffraction-lib counterpart entity (anchor 0ffba46f), a '
    'deviation-register row, or its owning class; none is undecided; no removed name is '
    'reachable. Whether the entity is tied to this member by the committed entity map and '
    'whether the register row exists, is well-formed and names the member is proven by the '
    "necessity register's own check. The checks do not prove that a member is needed "
    '- that judgement is the register row, written by a human and reviewed - nor that a '
    'counterpart means the same thing (kept by review), nor anything about an enum '
    "value or an inherited member beyond its owner's justification."
)
SCHEMA_BOUND = (
    f'Schema v{SCHEMA} is generated internal data, not hostile input: this check does not '
    'exhaustively reject malformed public-record shape.'
)


# Module machinery every extension module carries, plus PEP 396 version metadata: outside the
# classification universe. Every OTHER attribute of the module — dunder or not — is a live name
# that must carry a verdict (I2), so an injected attribute is unclassified rather than invisible.
MODULE_MACHINERY = frozenset(dir(types.ModuleType('m'))) | frozenset({
    '__all__',
    '__builtins__',
    '__cached__',
    '__file__',
    '__path__',
    '__version__',
})

CLASS_KINDS = frozenset({'class', 'exception', 'enum'})
# edi's audience vocabulary: a name is public (in ``edi.__all__``) or internal — N1 a
# single-underscore helper or table, N2 a re-export (``np``) — nothing else exists on edi's side.
VERDICT_REASONS: dict[str, frozenset[str]] = {
    'public': frozenset({'C'}),
    'internal': frozenset({'N1', 'N2'}),
}
TASK_VERDICTS: frozenset[str] = frozenset()
TASK_ID = re.compile(r'^[A-Z]\d{2}-T\d+$')
# The necessity vocabulary: three verdicts plus one transient.
NEED_VERDICTS = frozenset({'keep', 'remove', 'undecided'})
KEEP_BY = frozenset({'counterpart', 'deviation', 'owner'})
DEVIATION_REF = re.compile(r'^D\d+$')
COUNTERPART_REF = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$')
REGION_BEGIN = '<!-- python-surface:begin -->'
REGION_END = '<!-- python-surface:end -->'


# ---------------------------------------------------------------------------------------------
# Introspection of the built module — names and members only, read with `isinstance` and `dir()`.
# No nanobind rendering is parsed anywhere in this tool.
# ---------------------------------------------------------------------------------------------
def kind_of(obj: Any) -> str:  # noqa: ANN401 - any module attribute
    """Classify a module attribute: module / exception / enum / class / function / constant."""
    if isinstance(obj, types.ModuleType):
        return 'module'
    if isinstance(obj, type):
        if issubclass(obj, BaseException):
            return 'exception'
        if hasattr(obj, '__members__'):
            return 'enum'
        return 'class'
    if callable(obj):
        return 'function'
    return 'constant'


def member_names(cls: type) -> list[str]:
    """Return the non-underscore attribute names of a class, sorted (I1; ctor is class-level).

    A single-underscore member (``_cache``, ``_impl``) is internal by the same rule as a module
    name. Inherited members and enum values are members like any other.
    """
    return sorted(name for name in dir(cls) if not name.startswith('_'))


def class_record(cls: type) -> dict[str, Any]:
    """Return the manifest record of a class-like name: its kind and its member names."""
    return {'kind': kind_of(cls), 'members': member_names(cls)}


def name_record(obj: Any) -> dict[str, Any]:  # noqa: ANN401 - any module attribute
    """Return the manifest record of one module-level name."""
    kind = kind_of(obj)
    if kind in CLASS_KINDS:
        return class_record(obj)
    return {'kind': kind}


def introspect(module: types.ModuleType) -> dict[str, Any]:
    """Return the live surface: every non-underscore name with its record, plus ``__all__``."""
    # A package's on-disk submodules are reachable as attributes the moment anything imports them
    # (``edi.verification`` after a verification page runs), so they belong to the total universe
    # whether or not this process happened to import them first.
    for info in pkgutil.iter_modules(getattr(module, '__path__', [])):
        if not info.name.startswith('_'):
            importlib.import_module(f'{module.__name__}.{info.name}')
    names = {
        name: name_record(getattr(module, name))
        for name in sorted(dir(module))
        # A leading underscore keeps a module attribute out of the surface universe, as it keeps a
        # member out of ``member_names()``.
        if name not in MODULE_MACHINERY and not name.startswith('_')
    }
    return {'all': sorted(getattr(module, '__all__', [])), 'names': names}


def _is_product_type(cls: type) -> bool:
    return (getattr(cls, '__module__', '') or '').split('.')[0] == MODULE_NAME


def live_class(class_name: str) -> type:
    """Return the built module's class object for a classified class name."""
    return getattr(importlib.import_module(MODULE_NAME), class_name)


def derivation(cls: type, member: str) -> str | None:
    """Return why ``member`` is derived from ``cls`` (``enum-value`` / ``inherited``), or None.

    An enum's values are its own domain; a member the class does not define itself but a base
    outside the product does (``BaseException.args``, nanobind's enum machinery) is inherited.
    Either derives its necessity from the owning class's verdict, never from its own existence.
    Read from the class namespaces along the MRO — no signature, no rendering.
    """
    if member in (getattr(cls, '__members__', None) or {}):
        return 'enum-value'
    if member in vars(cls):
        return None
    for base in cls.__mro__[1:]:
        if member in vars(base):
            return None if _is_product_type(base) else 'inherited'
    return None


# ---------------------------------------------------------------------------------------------
# The two sections and the documentation region.
# ---------------------------------------------------------------------------------------------
def public_section(surface: dict[str, Any]) -> dict[str, Any]:
    """Return the ``public`` manifest: the record of every name in ``__all__``."""
    return {
        name: dict(surface['names'][name]) for name in surface['all'] if name in surface['names']
    }


def candidate_classes(surface: dict[str, Any]) -> list[str]:
    """Return the member-classification universe: every live class-like module attribute (I1)."""
    return sorted(
        name for name, record in surface['names'].items() if record.get('kind') in CLASS_KINDS
    )


def _public_row() -> dict[str, str]:
    return {'verdict': 'public', 'reason': 'C'}


def _owner_need() -> dict[str, str]:
    return {'verdict': 'keep', 'by': 'owner'}


def classification_for_write(
    surface: dict[str, Any], existing: dict[str, Any] | None
) -> dict[str, Any]:
    """Regenerate the classification: ``__all__`` names become public; other verdicts persist.

    Every row keeps the ``need`` it already carries; a derived member (enum value, inherited)
    without one is auto-filled ``keep by=owner``; any other row without one stays without, which
    ``--check`` reports (I7).
    """
    existing = existing or {}
    old_module = existing.get('module', {})
    old_members = existing.get('members', {})
    declared = set(surface['all'])
    module_rows: dict[str, Any] = {}
    for name in surface['names']:
        row = dict(old_module.get(name, {}))
        if name in declared:
            row.update(_public_row())
        elif not row:
            continue
        module_rows[name] = row
    member_rows: dict[str, Any] = {}
    for class_name in candidate_classes(surface):
        rows: dict[str, Any] = {}
        old_rows = old_members.get(class_name, {})
        cls = live_class(class_name)
        for member in surface['names'][class_name]['members']:
            row = dict(old_rows.get(member, {}))
            if class_name in declared:
                row.update(_public_row())
            elif not row:
                continue
            if 'need' not in row and derivation(cls, member) is not None:
                row['need'] = _owner_need()
            rows[member] = row
        member_rows[class_name] = rows
    return {'module': module_rows, 'members': member_rows}


def _closes_text(row: dict[str, Any]) -> str:
    return ', '.join(piece.strip() for piece in str(row.get('closes', '')).split('+'))


def need_text(row: dict[str, Any]) -> str:
    """Render a row's necessity verdict for the documentation table."""
    need = row.get('need')
    if not isinstance(need, dict):
        return '—'
    verdict = need.get('verdict')
    if verdict == 'keep':
        by = need.get('by')
        if by == 'owner':
            return 'keep (with its class)'
        return f'keep — {by} `{need.get("ref", "")}`'
    if verdict == 'undecided':
        return 'undecided (with the owner)'
    return str(verdict)


def docs_region(public: dict[str, Any], classification: dict[str, Any]) -> str:
    """Return the generated contract table: every declared and every contract module name."""
    lines = [
        REGION_BEGIN,
        '| name | state | spelling | closes with | necessity |',
        '| --- | --- | --- | --- | --- |',
    ]
    module_rows = classification.get('module', {})
    contract = {name for name, row in module_rows.items() if row.get('verdict') == 'contract'}
    keys = sorted(set(public) | contract)
    for name in keys:
        row = module_rows.get(name, {})
        if name in public:
            lines.append(
                f'| `{name}` | declared (in `{MODULE_NAME}.__all__`) | `{name}` | — | '
                f'{need_text(row)} |'
            )
        else:
            edi_name = row.get('edi_name', name)
            lines.append(
                f'| `{name}` | contract (not yet declared) | `{edi_name}` | {_closes_text(row)} '
                f'| {need_text(row)} |'
            )
    lines.append(REGION_END)
    return '\n'.join(lines)


def _extract_region(text: str) -> str | None:
    begin = text.find(REGION_BEGIN)
    end = text.find(REGION_END)
    if begin < 0 or end < 0 or end < begin:
        return None
    return text[begin : end + len(REGION_END)]


def render_docs(existing: str | None, region: str) -> str:
    """Return the documentation page with the generated region replaced, appended or created."""
    if existing is None:
        return f'# Python API\n\n{region}\n'
    current = _extract_region(existing)
    if current is None:
        return existing.rstrip('\n') + '\n\n' + region + '\n'
    return existing.replace(current, region)


# ---------------------------------------------------------------------------------------------
# The check.
# ---------------------------------------------------------------------------------------------
def _check_header(doc: dict[str, Any]) -> list[str]:
    findings = []
    if doc.get('schema') != SCHEMA:
        findings.append(f'header: schema {doc.get("schema")!r} is not {SCHEMA}')
    if doc.get('directionality') != DIRECTIONALITY:
        findings.append('header: directionality text does not state the I6 direction')
    return findings


def _check_public(doc: dict[str, Any], surface: dict[str, Any]) -> list[str]:
    expected = public_section(surface)
    actual = doc.get('public', {})
    findings = [
        f'public: {name} is declared in {MODULE_NAME}.__all__ but is not a live attribute of the '
        f'built module (a typo in the declaration; fail closed)'
        for name in sorted(set(surface['all']) - set(surface['names']))
    ]
    findings.extend(
        f'public: {name} is not in {MODULE_NAME}.__all__'
        for name in sorted(set(actual) - set(expected))
    )
    findings.extend(
        f'public: {name} is declared in {MODULE_NAME}.__all__ but absent from the manifest'
        for name in sorted(set(expected) - set(actual))
    )
    findings.extend(
        f'public: {name} differs from the built module (regenerate with --write)'
        for name in sorted(set(expected) & set(actual))
        if expected[name] != actual[name]
    )
    return findings


def _check_need(path: str, row: dict[str, Any]) -> list[str]:
    """Check the necessity verdict's shape (I2): one verdict, its witness well-formed."""
    need = row.get('need')
    if not isinstance(need, dict):
        return [f'necessity: {path} carries no need verdict (keep / remove / undecided)']
    verdict = need.get('verdict')
    if verdict not in NEED_VERDICTS:
        return [f'necessity: {path} has invalid need verdict {verdict!r}']
    findings = []
    if verdict == 'keep':
        by = need.get('by')
        if by not in KEEP_BY:
            return [f'necessity: {path} keep has invalid by {by!r}']
        ref = need.get('ref')
        if by == 'counterpart' and not (isinstance(ref, str) and COUNTERPART_REF.match(ref)):
            findings.append(
                f'necessity: {path} keep by=counterpart needs a diffraction-lib entity ref '
                f'(Owner or Owner.member), got {ref!r}'
            )
        if by == 'deviation' and not (isinstance(ref, str) and DEVIATION_REF.match(ref)):
            findings.append(
                f'necessity: {path} keep by=deviation needs a register row ref (D<N>), got {ref!r}'
            )
        if by == 'owner' and '.' not in path:
            findings.append(
                f'necessity: {path} keep by=owner is a member derivation, not a class verdict'
            )
    elif verdict == 'remove':
        findings.append(
            f'necessity: {path} is verdicted remove but is still live - delete it in the same '
            f'change set and record it under removed (I6)'
        )
    elif verdict == 'undecided':
        question = need.get('question')
        findings.append(
            f'necessity: {path} is undecided - routed to the owner: {question!r} (red until '
            f'replaced)'
        )
    return findings


def _check_row(path: str, row: Any) -> list[str]:  # noqa: ANN401 - unvalidated JSON
    if not isinstance(row, dict):
        return [f'classification: {path} is not a row']
    verdict = row.get('verdict')
    if verdict not in VERDICT_REASONS:
        return [f'classification: {path} has invalid verdict {verdict!r}']
    findings = []
    reason = row.get('reason')
    if not isinstance(reason, str) or reason not in VERDICT_REASONS[verdict]:
        findings.append(f'classification: {path} has invalid reason {reason!r} for {verdict}')
    if verdict in TASK_VERDICTS:
        findings.extend(_check_task_metadata(path, row))
    edi_name = row.get('edi_name')
    if edi_name is not None and not (isinstance(edi_name, str) and edi_name.isidentifier()):
        findings.append(f'classification: {path} has invalid edi_name {edi_name!r}')
    if not path.rsplit('.', 1)[-1].startswith('_'):
        # I1: the necessity universe is the non-underscore surface; a single-underscore name is
        # internal by the audience rule and carries no need verdict.
        findings.extend(_check_need(path, row))
    return findings


def _check_task_metadata(path: str, row: dict[str, Any]) -> list[str]:
    closes = row.get('closes')
    if not isinstance(closes, str) or not closes.strip():
        message = (
            f'classification: {path} ({row["verdict"]}) has a missing or invalid closes text '
            f'(the closing task ids, "+"-separated)'
        )
        return [message]
    return [
        f'classification: {path} closes names an invalid task id {task!r}'
        for task in (piece.strip() for piece in closes.split('+'))
        if not TASK_ID.match(task)
    ]


def _check_universe(
    label: str, expected: set[str], actual: set[str], missing_word: str
) -> list[str]:
    missing = [f'{label}: {name} {missing_word}' for name in sorted(expected - actual)]
    stale = [
        f'{label}: {name} stale (absent from the built module)'
        for name in sorted(actual - expected)
    ]
    return missing + stale


def _check_module_rows(classification: dict[str, Any], surface: dict[str, Any]) -> list[str]:
    rows = classification.get('module', {})
    findings = _check_universe(
        'classification.module', set(surface['names']), set(rows), 'unclassified'
    )
    for name in sorted(set(rows) & set(surface['names'])):
        findings.extend(_check_row(name, rows[name]))
        if name in surface['all'] and rows[name].get('verdict') != 'public':
            findings.append(
                f'classification.module: {name} is declared public but classified '
                f'{rows[name].get("verdict")!r}'
            )
    return findings


def _owner_is_kept(class_name: str, classification: dict[str, Any]) -> bool:
    need = classification.get('module', {}).get(class_name, {}).get('need')
    return isinstance(need, dict) and need.get('verdict') == 'keep' and need.get('by') != 'owner'


def _check_member_rows(classification: dict[str, Any], surface: dict[str, Any]) -> list[str]:
    classes = classification.get('members', {})
    expected_classes = set(candidate_classes(surface))
    findings = _check_universe(
        'classification.members', expected_classes, set(classes), 'omitted (unclassified class)'
    )
    declared = set(surface['all'])
    for class_name in sorted(expected_classes & set(classes)):
        rows = classes[class_name] if isinstance(classes[class_name], dict) else {}
        live = set(surface['names'][class_name]['members'])
        findings.extend(
            _check_universe(
                'classification.members',
                {f'{class_name}.{m}' for m in live},
                {f'{class_name}.{m}' for m in rows},
                'unclassified',
            )
        )
        cls = live_class(class_name)
        for member in sorted(live & set(rows)):
            path = f'{class_name}.{member}'
            findings.extend(_check_row(path, rows[member]))
            if class_name in declared and rows[member].get('verdict') != 'public':
                findings.append(
                    f'classification.members: {path} belongs to a declared public class but is '
                    f'classified {rows[member].get("verdict")!r}'
                )
            need = rows[member].get('need')
            if isinstance(need, dict) and need.get('by') == 'owner':
                if derivation(cls, member) is None:
                    findings.append(
                        f'necessity: {path} keep by=owner no longer re-resolves (not an enum '
                        f'value and not inherited from a base outside the product)'
                    )
                if not _owner_is_kept(class_name, classification):
                    findings.append(
                        f'necessity: {path} keep by=owner derives from {class_name}, whose own '
                        f'verdict is not a keep by counterpart or deviation'
                    )
    return findings


def _check_removed(doc: dict[str, Any], surface: dict[str, Any]) -> list[str]:
    """Every name recorded as removed is unreachable from the built module (I6, I7)."""
    removed = doc.get('removed', {})
    if not isinstance(removed, dict):
        return ['removed: section is not a mapping']
    findings = []
    for path, record in sorted(removed.items()):
        well_formed = (
            isinstance(record, dict) and record.get('removed_in') and record.get('reason')
        )
        if not well_formed:
            findings.append(f'removed: {path} needs removed_in and reason')
        class_name, _, member = path.partition('.')
        live = surface['names'].get(class_name)
        if live is None:
            continue
        if not member or member in live.get('members', []):
            findings.append(f'removed: {path} is recorded as removed but is still reachable')
    return findings


def _check_docs(doc: dict[str, Any], docs_text: str | None, docs_path: Path | None) -> list[str]:
    if docs_path is None:
        return []
    expected = docs_region(doc.get('public', {}), doc.get('classification', {}))
    if docs_text is None:
        return [f'docs: {docs_path} is missing']
    actual = _extract_region(docs_text)
    if actual is None:
        return [f'docs: {docs_path} carries no generated region ({REGION_BEGIN} ... {REGION_END})']
    if actual != expected:
        return [f'docs: the generated contract table in {docs_path} is stale (run --write)']
    return []


def check(
    doc: dict[str, Any],
    surface: dict[str, Any],
    docs_text: str | None,
    docs_path: Path | None,
    archive: dict[str, Any] | None = None,
) -> list[str]:
    """Every finding against the committed declaration; empty means the declaration holds."""
    classification = doc.get('classification', {})
    findings = _check_header(doc)
    findings.extend(_check_public(doc, surface))
    findings.extend(_check_module_rows(classification, surface))
    findings.extend(_check_member_rows(classification, surface))
    findings.extend(_check_removed(doc, surface))
    if archive:
        # Archived records stay asserted-absent forever - the union is the check's
        # universe.
        overlap = sorted(set(archive) & set(doc.get('removed', {})))
        findings.extend(
            f'removed-archive: {p} is recorded both live and archived' for p in overlap
        )
        findings.extend(
            f.replace('removed:', 'removed-archive:', 1)
            for f in _check_removed({'removed': archive}, surface)
        )
    findings.extend(_check_docs(doc, docs_text, docs_path))
    return findings


# ---------------------------------------------------------------------------------------------
# The sweep: what the entity map proposes per row. A candidate filter, never a verdict.
# ---------------------------------------------------------------------------------------------
def sweep(surface: dict[str, Any], entity_map: dict[str, Any]) -> dict[str, Any]:
    """Return, per module name and member, the diffraction-lib entity the map ties to it."""
    by_product: dict[str, list[str]] = {}
    for row in entity_map.get('rows', []):
        side = row.get(MODULE_NAME, {})
        name = side.get('name', '')
        if row.get('dl') and name:
            by_product.setdefault(name, []).append(f'{row["dl"]} [{side.get("state")}]')
        if side.get('state') == 'parameter' and side.get('onclass') and side.get('uid'):
            leaf = side['uid'].rsplit('.', 1)[-1]
            by_product.setdefault(f'{side["onclass"]}.{leaf}', []).append(
                f'{row["dl"]} [parameter {side["uid"]}]'
            )
    proposals: dict[str, Any] = {}
    for name, record in surface['names'].items():
        proposals[name] = by_product.get(name, [])
        for member in record.get('members', []):
            proposals[f'{name}.{member}'] = by_product.get(f'{name}.{member}', [])
    return proposals


# ---------------------------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------------------------
def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding='utf-8'))


def _write(manifest_path: Path, docs_path: Path | None, surface: dict[str, Any]) -> list[str]:
    existing = _load_json(manifest_path) or {}
    doc = {
        'schema': SCHEMA,
        'directionality': DIRECTIONALITY,
        'public': public_section(surface),
        'classification': classification_for_write(surface, existing.get('classification')),
        'removed': existing.get('removed', {}),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    docs_text = None
    if docs_path is not None:
        docs_text = docs_path.read_text(encoding='utf-8') if docs_path.is_file() else None
        docs_path.parent.mkdir(parents=True, exist_ok=True)
        docs_path.write_text(
            render_docs(docs_text, docs_region(doc['public'], doc['classification'])),
            encoding='utf-8',
        )
        docs_text = docs_path.read_text(encoding='utf-8')
    archive = _load_json(manifest_path.parent / 'python-surface-removed-archive.json')
    return check(doc, surface, docs_text, docs_path, archive=archive or {})


def _emit(line: str) -> None:
    sys.stdout.write(line + '\n')


def _report(findings: list[str], *, wrote: bool, surface: dict[str, Any]) -> int:
    for finding in findings:
        _emit(finding)
    verb = 'written' if wrote else 'checked'
    if findings:
        _emit(f'python-surface: RED - {len(findings)} finding(s) {verb}')
        _emit(DIRECTIONALITY)
    else:
        public = public_section(surface)
        members = sum(len(record.get('members', [])) for record in public.values())
        classes = candidate_classes(surface)
        member_total = sum(len(surface['names'][c]['members']) for c in classes)
        _emit(
            f'python-surface OK ({verb}) - {len(public)} declared public name(s), {members} '
            f'member(s), {len(surface["names"])} module name(s) and {member_total} member(s) of '
            f'{len(classes)} class-like name(s) classified'
        )
    _emit(EXISTENCE_LIMIT)
    _emit(f'NECESSITY_LIMIT: {NECESSITY_LIMIT}')
    _emit(SCHEMA_BOUND)
    return 1 if findings else 0


def _archive_removed(manifest_path: Path, archive_path: Path) -> int:
    """Rotate every live removal record into the archive."""
    doc = _load_json(manifest_path)
    if doc is None:
        _emit(f'python-surface: RED - {manifest_path} is missing')
        return 1
    live = doc.get('removed', {})
    archive = _load_json(archive_path) or {}
    collisions = sorted(set(live) & set(archive))
    if collisions:
        _emit(
            f'python-surface: RED - {len(collisions)} record(s) already archived: {collisions[:3]}'
        )
        return 1
    archive.update(live)
    doc['removed'] = {}
    archive_path.write_text(json.dumps(archive, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    manifest_path.write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    _emit(
        f'python-surface: rotated {len(live)} removal record(s) into {archive_path.name} '
        f'({len(archive)} archived total); the live removed map is empty for the next cycle'
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point: ``--write`` regenerates, ``--check`` diffs, ``--sweep`` proposes."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--manifest', type=Path, help='default: <root>/data/python-surface.json')
    parser.add_argument('--docs', default='none', help='a docs page to render; default: none')
    parser.add_argument('--entity-map', type=Path, help='--sweep: the entity-map.json')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', action='store_true')
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--sweep', action='store_true')
    mode.add_argument(
        '--archive-removed',
        action='store_true',
        help='rotate every live removal record into data/python-surface-removed-archive.json '
        '(ship-time retention)',
    )
    args = parser.parse_args(argv)
    manifest_path = args.manifest or args.root / 'data' / 'python-surface.json'
    docs_path: Path | None
    if args.docs == 'none':
        docs_path = None
    else:
        default_docs = args.root / 'docs' / 'user' / 'api' / 'python.md'
        docs_path = Path(args.docs) if args.docs else default_docs
    archive_path = args.root / 'data' / 'python-surface-removed-archive.json'
    if args.archive_removed:
        return _archive_removed(manifest_path, archive_path)
    surface = introspect(importlib.import_module(MODULE_NAME))
    if args.sweep:
        if args.entity_map is None or not args.entity_map.is_file():
            _emit('python-surface: --sweep needs --entity-map <entity-map.json>')
            return 2
        _emit(json.dumps(sweep(surface, json.loads(args.entity_map.read_text())), indent=1))
        return 0
    if args.write:
        return _report(_write(manifest_path, docs_path, surface), wrote=True, surface=surface)
    doc = _load_json(manifest_path)
    if doc is None:
        _emit(f'python-surface: RED - {manifest_path} is missing (run --write)')
        _emit(DIRECTIONALITY)
        _emit(EXISTENCE_LIMIT)
        _emit(f'NECESSITY_LIMIT: {NECESSITY_LIMIT}')
        _emit(SCHEMA_BOUND)
        return 1
    docs_text = None
    if docs_path is not None and docs_path.is_file():
        docs_text = docs_path.read_text(encoding='utf-8')
    archive = _load_json(archive_path) or {}
    return _report(
        check(doc, surface, docs_text, docs_path, archive=archive), wrote=False, surface=surface
    )


if __name__ == '__main__':
    sys.exit(main())
