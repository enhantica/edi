"""The public adopting Save writes its completed declarations, then reopens that file."""

import re

import edi as engine
import pytest

from tests.fixtures.constraint_expressions.project import materialize
from tests.fixtures.project_save.reference import require_saved_parameters, saved_parameters


@pytest.mark.parametrize('calculated', [False, True], ids=['uncalculated', 'calculated'])
def test_final_save_write_contains_the_adopted_complement_and_optional_dependent(
    tmp_path, calculated
):
    aliases = [
        ('leader', 'phase.atom_site.A.fract_x'),
        ('dependent', 'phase.atom_site.B.occupancy'),
        ('instrument', 'bank.instrument.setup_monochromator_twotheta'),
    ]
    source = materialize(
        tmp_path / 'input',
        aliases,
        ['dependent = 1-leader', 'instrument = dependent'],
    )
    structure = source / 'structures/phase.edi'
    text = structure.read_text()
    assert text.count('A La a Biso 0.17 0.23 0.31') == 1, (
        'Required: final save write contains the adopted complement and optional dependent.'
    )
    structure.write_text(
        text.replace('A La a Biso 0.17 0.23 0.31', 'A La a Biso 0.91234567 0.23 0.31')
    )
    experiment = source / 'experiments/bank.edi'
    text = experiment.read_text()
    assert text.count('_experiment_type.radiation_probe neutron\n') == 1, (
        'Required: final save write contains the adopted complement and optional dependent.'
    )
    experiment.write_text(
        text.replace(
            '_experiment_type.radiation_probe neutron\n', '_experiment_type.radiation_probe xray\n'
        )
    )
    project = engine.Project.load(source)
    if calculated:
        project.analysis.calculate()
    assert project.structure.atom_sites[0].fract_x.value == 0.91234567, (
        'Required: final save write contains the adopted complement and optional dependent.'
    )
    reference = saved_parameters(project, 'iucr_99')
    # These are input-derived decimal and binary-arithmetic literals, not a
    # copy of the reference's vector or of a current saved-file observation.
    adopted = 1 - 0.912346
    destination = tmp_path / 'saved'
    project.save_as(destination)
    assert project.structure.atom_sites[0].fract_x.value == 0.912346, (
        'Required: final save write contains the adopted complement and optional dependent.'
    )
    assert project.structure.atom_sites[1].occupancy.value == adopted, (
        'Required: final save write contains the adopted complement and optional dependent.'
    )
    optional = project.experiment.instrument.setup_monochromator_twotheta
    assert (optional.value, optional.uncertainty, optional.free) == (
        adopted,
        0.0,
        False,
    ), 'Required: final save write contains the adopted complement and optional dependent.'
    require_saved_parameters(project.parameters, reference, model=project, phase='completed')
    final_experiment = (destination / 'experiments/bank.edi').read_text()
    assert re.findall(
        r'(?m)^_instrument\.setup_monochromator_twotheta[ \t]+(\S+)[ \t]*$',
        final_experiment,
    ) == ['0.087654'], (
        'Required: final save write contains the adopted complement and optional dependent.'
    )
    reopened = engine.Project.load(destination)
    assert reopened.structure.atom_sites[1].occupancy.value == 0.087654, (
        'Required: final save write contains the adopted complement and optional dependent.'
    )
    optional = reopened.experiment.instrument.setup_monochromator_twotheta
    assert (optional.value, optional.uncertainty, optional.free) == (
        0.087654,
        0.0,
        False,
    ), 'Required: final save write contains the adopted complement and optional dependent.'
    require_saved_parameters(reopened.parameters, reference, model=reopened, phase='loaded')
    reopened.analysis.calculate()
    assert reopened.structure.atom_sites[1].occupancy.value == adopted, (
        'Required: final save write contains the adopted complement and optional dependent.'
    )
    optional = reopened.experiment.instrument.setup_monochromator_twotheta
    assert (optional.value, optional.uncertainty, optional.free) == (
        adopted,
        0.0,
        False,
    ), 'Required: final save write contains the adopted complement and optional dependent.'
    require_saved_parameters(reopened.parameters, reference, model=reopened, phase='completed')
    reopened.save()
    require_saved_parameters(reopened.parameters, reference, model=reopened, phase='completed')
