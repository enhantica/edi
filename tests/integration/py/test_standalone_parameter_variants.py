"""Individual parameters retain the display context of their actual owner."""

import importlib

import pytest

from tests.fixtures import cif_accounting as case


@pytest.mark.parametrize('walk', ['getter', 'site'])
def test_f3_standalone_site_parameter_keeps_its_variant_after_selector_changes(walk):
    api = importlib.import_module(case.API)
    site = api.AtomSite()
    site.adp_type = 'Biso'
    site.adp_iso.value = 0.123456
    if walk == 'getter':
        parameter = site.adp_iso
    else:
        parameters = site.parameters
        parameter = next(p for p in parameters if p.name == site.adp_iso.name)
    for kind, expected in [
        ('Biso', 'B iso = 0.123'),
        ('Uiso', 'U iso = 0.12346'),
        ('Biso', 'B iso = 0.123'),
    ]:
        site.adp_type = kind
        assert expected in repr(parameter), (
            'F3 a retained standalone ADP uses its owner variant and Python decimal reference'
        )
        assert parameter.value == pytest.approx(0.123456), (
            'F3 owner-dependent display never rounds the stored atomic displacement'
        )


@pytest.mark.parametrize('walk', ['getter', 'instrument', 'experiment'])
def test_f3_standalone_experiment_parameter_tracks_doublet_owner(walk):
    api = importlib.import_module(case.API)
    source = case.ROOT / 'tests/fixtures/loop_parameter_ids/line-segment/experiments/bank.edi'
    text = source.read_text().replace('radiation_probe neutron', 'radiation_probe xray')
    text = text.replace('_instrument.setup_wavelength 1.54', '_instrument.setup_wavelength 1.5406')
    text += (
        '\n_instrument.setup_wavelength_2 1.5444\n_instrument.setup_wavelength_2_to_1_ratio 0.4\n'
    )
    experiment = api.ExperimentFactory.from_cif_str(text)
    parameter = experiment.instrument.setup_wavelength
    if walk != 'getter':
        owner = experiment.instrument if walk == 'instrument' else experiment
        parameter = next(p for p in owner.parameters if p.name == parameter.name)
    for ratio, label in [(0.4, 'Wavelength 1'), (0, 'Wavelength'), (0.4, 'Wavelength 1')]:
        experiment.instrument.setup_wavelength_2_to_1_ratio.value = ratio
        assert repr(parameter).startswith('<' + label + ' = '), (
            'F3 an individual unattached wavelength follows its actual experiment doublet selector'
        )
        assert parameter.value == pytest.approx(1.5406), (
            'F3 doublet labels do not change the stored primary wavelength'
        )
