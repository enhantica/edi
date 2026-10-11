"""Every parameter-bearing loop uses its declared row id (owner seq 17/18).

Names come from the frozen diffraction-lib capture for these exact projects.
The field projection keeps numeric parameters owned by the native model, not
the reference's text and integer descriptors. No engine-produced name is an oracle.
"""

import hashlib
import json
import shlex
import shutil
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/loop_parameter_ids'
REFERENCE = json.loads((FIXTURE / 'reference.json').read_text())
FIELDS = {
    'background': {'intensity', 'coef'},
    'linked_structure': {'scale'},
    'preferred_orientation': {'march_r', 'march_random_fract'},
    'atom_site': {'fract_x', 'fract_y', 'fract_z', 'occupancy', 'adp_iso'},
    'atom_site_aniso': {'adp_11', 'adp_22', 'adp_33', 'adp_12', 'adp_13', 'adp_23'},
}


def relevant(name):
    parts = name.split('.')
    return len(parts) == 4 and parts[1] in FIELDS and parts[3] in FIELDS[parts[1]]


def expected(kind):
    return sorted(name for name in REFERENCE['projects'][kind]['names'] if relevant(name))


def names(project):
    # The native descriptor intentionally has no public unique_name property.
    # Alias creation observes the production name resolver for the held parameter.
    aliases = project.analysis.aliases
    result = []
    bank = project.experiments['bank']
    descriptors = [row.intensity for row in bank.background]
    descriptors += [row.coef for row in bank.background_terms]
    descriptors += [row.scale for row in bank.linked_structures]
    descriptors += [
        getattr(row, field)
        for row in bank.preferred_orientation
        for field in sorted(FIELDS['preferred_orientation'])
    ]
    descriptors += [
        getattr(row, field)
        for row in project.structures['phase'].atom_sites
        for field in sorted(FIELDS['atom_site'])
    ]
    for index, parameter in enumerate(descriptors):
        key = 'identity_probe_' + str(index)
        aliases.create(id=key, param=parameter)
        result.append(aliases[key].parameter_unique_name)
        aliases.remove(key)
    return result


@pytest.mark.parametrize('kind', ['line-segment', 'polynomial', 'chebyshev'])
def test_loop_parameter_names_match_independent_declared_ids(kind, tmp_path):
    record = REFERENCE['projects'][kind]
    assert {
        p.relative_to(FIXTURE / kind).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (FIXTURE / kind).rglob('*.edi')
    } == record['sha256'], (
        'The external names must belong to the exact committed physical input files'
    )
    project = engine.Project.load(FIXTURE / kind)
    # Prefix census includes old positional and single-structure shortcut names;
    # filtering by four-part relevant() here would silently omit those escapes.
    actual = sorted(
        name
        for name in names(project)
        if any(
            name.startswith(prefix)
            for prefix in (
                'bank.background',
                'bank.linked_structure',
                'bank.preferred_orientation',
                'phase.atom_site',
                'bank.scale',
                'bank.march_r',
                'bank.march_random_fract',
            )
        )
    )
    assert actual == expected(kind), (
        'All numeric loop parameters must match diffraction-lib row ids, '
        'including a single linked structure'
    )
    destination = tmp_path / 'saved'
    project.save_as(destination)
    reopened = engine.Project.load(destination)
    assert sorted(name for name in names(reopened) if relevant(name)) == expected(kind), (
        'Save and reload must preserve every declared loop parameter identity'
    )


@pytest.mark.parametrize('kind', ['line-segment', 'polynomial', 'chebyshev'])
def test_legacy_positional_aliases_and_constraints_migrate_on_load(kind, tmp_path):
    private = tmp_path / 'input'
    shutil.copytree(FIXTURE / kind, private)
    line = kind == 'line-segment'
    targets = [
        (
            'left',
            'bank.background[0]' if line else 'bank.background.1.coef',
            {'bank.background.pA.intensity', 'bank.background[pA]'}
            if line
            else {'bank.background.base.coef'},
        ),
        (
            'right',
            'bank.background[1]' if line else 'bank.background.2.coef',
            {'bank.background.pB.intensity', 'bank.background[pB]'}
            if line
            else {'bank.background.ramp.coef'},
        ),
        ('scale', 'bank.scale', {'bank.linked_structure.phase.scale', 'bank.phase.scale'}),
        (
            'texture',
            'bank.march_r',
            {'bank.preferred_orientation.phase.march_r', 'bank.phase.march_r'},
        ),
    ]
    analysis = private / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text()
        + '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
        + '\n'.join(alias + ' ' + old for alias, old, _ in targets)
        + '\n\nloop_\n_constraint.id\n_constraint.expression\n'
        + 'bind "right = 2*left"\n'
    )
    project = engine.Project.load(private)
    destination = tmp_path / 'saved'
    project.save_as(destination)
    tokens = shlex.split((destination / 'analysis/analysis.edi').read_text())
    alias_start = tokens.index('_alias.parameter_unique_name') + 1
    alias_end = tokens.index('loop_', alias_start)
    aliases = dict(
        zip(tokens[alias_start:alias_end:2], tokens[alias_start + 1 : alias_end : 2], strict=True)
    )
    assert all(
        aliases[alias] in names and old not in aliases.values() for alias, old, names in targets
    ), 'Load must migrate every legacy positional alias to its declared row id before save'
    assert 'right = 2*left' in tokens, (
        'Alias migration must preserve the constraint expression and its alias identities'
    )
    reopened = engine.Project.load(destination)
    second = tmp_path / 'reopened'
    reopened.save_as(second)
    assert (second / 'analysis/analysis.edi').read_bytes() == (
        destination / 'analysis/analysis.edi'
    ).read_bytes(), 'Migrated aliases and constraints must reach a stable saved representation'
