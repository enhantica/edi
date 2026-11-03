"""ADR-0078 physical relation refusal retains the consumer diagnostic channel.

Inputs and invalid values come from the declared physical intervals and affine
relations, not engine output. The intermediate changes before the later failing
relation, so refusal must preserve both dependent values.
"""

import edi
import pytest

from tests.fixtures.xray_doublet import trial_domains

FAMILIES = ('ratio', 'second-line', 'polarization', 'monochromator', 'march-fraction')


def _parameters(project, family):
    bank = project.experiments['bank']
    field = trial_domains.CASES[family][0].split('.')[-1]
    target = (
        bank.preferred_orientation['phase'].march_random_fract
        if family == 'march-fraction'
        else getattr(bank.instrument, field)
    )
    return (
        project.structures['phase'].atom_sites['X'].fract_x,
        bank.instrument.calib_twotheta_offset,
        target,
    )


@pytest.mark.parametrize('family', FAMILIES)
@pytest.mark.parametrize('entrance', ['edit', 'calculate', 'load'])
def test_physical_relation_refusal_keeps_domain_diagnostics(tmp_path, family, entrance):
    root = trial_domains.write(tmp_path / 'input', family, source_kind='chain')
    project = edi.Project.load(root)
    project.analysis.calculate()
    parameters = _parameters(project, family)
    before = tuple(p.value for p in parameters)
    files = {p.relative_to(root): p.read_bytes() for p in root.rglob('*.edi')}
    if entrance == 'load':
        source = root / 'structures/phase.edi'
        source.write_text(source.read_text().replace('0.125()', '0.4()'))
        files = {p.relative_to(root): p.read_bytes() for p in root.rglob('*.edi')}
    else:
        parameters[0].value = 0.4

    def attempt():
        if entrance == 'edit':
            # Creating an alias invokes refresh_relations immediately. Merely
            # assigning expression text invalidates state and checks it on use.
            project.analysis.aliases.create(id='refresh_probe', param=parameters[0])
        elif entrance == 'calculate':
            project.analysis.calculate()
        else:
            edi.Project.load(root)

    with pytest.raises(edi.DomainValidationError) as caught:
        attempt()
    if entrance == 'edit':
        assert 'refresh_probe' not in project.analysis.aliases.names, (
            'ADR-0078 a refused relation edit must roll back the newly created alias'
        )
    diagnostics = caught.value.diagnostics
    assert len(diagnostics) == 1, (
        'ADR-0078 a later physical relation failure must retain one structured diagnostic'
    )
    diagnostic = diagnostics[0]
    assert diagnostic.code.startswith('crysta.domain.constraint_'), (
        'ADR-0078 the consumer must retain the engine constraint domain code'
    )
    assert str(diagnostic.severity).lower().endswith('error'), (
        'ADR-0078 physical relation refusal must be an error rather than an editing warning'
    )
    assert 'domain_relation' in diagnostic.message, (
        'ADR-0078 the diagnostic must identify the later failing relation'
    )
    assert trial_domains.CASES[family][0] in diagnostic.message, (
        'ADR-0078 the diagnostic must identify the physical target'
    )
    assert tuple(p.value for p in parameters[1:]) == before[1:], (
        'ADR-0078 a later physical failure must leave every earlier dependent unapplied'
    )
    assert files == {p.relative_to(root): p.read_bytes() for p in root.rglob('*.edi')}, (
        'ADR-0078 a refused physical relation must not rewrite its input files'
    )
    parameters[0].value = 0.1
    project.analysis.calculate()
    assert parameters[1].value == pytest.approx(0.06, abs=1e-15), (
        'ADR-0078 a valid retry must complete the first authored affine relation'
    )
    expected = 1.5 if family == 'second-line' else 50 if family == 'monochromator' else 0.4
    assert parameters[2].value == pytest.approx(expected, abs=1e-13), (
        'ADR-0078 a valid retry must retain the closed-form physical value without clamping'
    )
