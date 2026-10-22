"""Equivalent reflection files must produce the same fit of the declared Pr case."""

import numpy as np
import pytest

from tests.integration.py.test_single_crystal import FIXTURE, calculated, engine, imported


def test_dat_and_int_produce_the_same_fit():
    case = 'sc-neut-cwl_pr2nio4_basic'
    values = []
    for extension in ('int', 'dat'):
        structure = engine().StructureFactory.from_cif_path(
            FIXTURE / 'projects' / case / 'structures/structure.edi'
        )
        observed = imported(FIXTURE / 'fullprof' / case / f'prnio.{extension}')
        wavelength = float(
            (FIXTURE / 'fullprof' / case / 'prnio.int').read_text().splitlines()[2].split()[0]
        )
        observed.instrument.setup_wavelength.value = wavelength
        model = engine().Project(name='reflection-formats')
        model.structures.clear()
        model.experiments.clear()
        link = engine().LinkedStructure()
        link.structure_id = structure.name
        observed.linked_structures.add(link)
        model.structures.add(structure)
        model.experiments.add(observed)
        experiment = model.experiments[0]
        experiment.linked_structure.structure_id = 'structure'
        experiment.linked_structure.scale.value = 1.7
        experiment.linked_structure.scale.free = True
        result = model.analysis.fit()
        values.append((
            float(experiment.linked_structure.scale.value),
            result.reduced_chi_square,
            calculated(model),
        ))
    assert values[0][:2] == pytest.approx(values[1][:2], rel=1e-12), (
        'Equivalent int and dat inputs must reach the same fitted scale and chi-square'
    )
    np.testing.assert_allclose(
        values[0][2],
        values[1][2],
        rtol=1e-12,
        atol=1e-12,
        err_msg='Equivalent reflection formats must give the same fitted F²',
    )
