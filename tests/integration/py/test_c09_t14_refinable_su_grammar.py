"""independent gates for refinable decimal/empty s.u. brackets."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
REFERENCE_PATH = Path(__file__).parent / 'fixtures/c09_t14_refinable_su/reference.json'
REFERENCE_SHA256 = '3b2c35131b086a1bec91a414a4d6f81f01ec9f47f0bcaa5d28c77f12bca66d3f'
# Matched by WHOLE VALUE: the surviving corpus writes this tag as `0.5(1)`, `0.` or
# `0.0000`, so a prefix match would splice (`383.2(1.2).5(1)`).
PARAMETER_RE = re.compile(r'^_peak\.broad_gauss_sigma_0 +\S+$', re.MULTILINE)


def _reference() -> dict[str, Any]:
    assert hashlib.sha256(REFERENCE_PATH.read_bytes()).hexdigest() == REFERENCE_SHA256
    return json.loads(REFERENCE_PATH.read_text(encoding='utf-8'))


def _base_project() -> Path:
    # conftest is not importable at module scope from this tier.
    from conftest import corpus_case_dir  # noqa: PLC0415

    return corpus_case_dir('si-sepd-s2') / 'project'


def _experiment_path(project: Path) -> Path:
    experiments = sorted((project / 'experiments').glob('*.edi'))
    assert len(experiments) == 1
    return experiments[0]


def _project_variant(tmp_path: Path, name: str, structure_token: str) -> Path:
    destination = tmp_path / name
    shutil.copytree(_base_project(), destination)
    experiment = _experiment_path(destination)
    text = experiment.read_text(encoding='utf-8')
    assert PARAMETER_RE.search(text) is not None
    experiment.write_text(
        PARAMETER_RE.sub(lambda _m: f'_peak.broad_gauss_sigma_0 {structure_token}', text, count=1),
        encoding='utf-8',
    )
    return destination


def _load_cell(tmp_path: Path, name: str, token: str) -> Any:
    return edi.Project.load(
        _project_variant(tmp_path, name, token)
    ).experiment.peak.broad_gauss_sigma_0


def _assert_parameter(
    parameter: Any,
    *,
    value_hex: str,
    esd_hex: str | None,
    free: bool,
) -> None:
    assert float(parameter.value).hex() == value_hex
    assert (
        None if parameter.uncertainty is None else float(parameter.uncertainty).hex()
    ) == esd_hex, 'the public parameter uncertainty must match the expected bits'
    assert bool(parameter.free) is free


def test_c09_t14_external_reference_provenance_is_byte_locked() -> None:
    reference = _reference()
    assert reference['schema'] == 1
    assert reference['provenance'] == {
        'role': 'independent decimal-standard-uncertainty oracle',
        'engine': 'easydiffraction/diffraction-lib uncertainties.ufloat_fromstr',
        'commit': '39ada82c8aef8b4657c4ae8c68e888668db0f38e',
        'read_path': (
            'src/easydiffraction/io/cif/serialize.py::_set_param_from_cif -> '
            'src/easydiffraction/utils/utils.py::str_to_ufloat'
        ),
        'empty_bracket_contract': 'Empty brackets mark refinement intent, not a zero esd.',
    }
    assert reference['integer_reference_provenance'] == {
        'role': 'independent integer-bracket IEEE-754 oracle',
        'engine': 'easydiffraction/diffraction-lib uncertainties.ufloat_fromstr',
        'commit': '39ada82c8aef8b4657c4ae8c68e888668db0f38e',
        'arithmetic': 'N / 10^ndec',
    }


def test_c09_t14_decimal_brackets_are_absolute_on_edi(
    tmp_path: Path,
) -> None:
    for index, case in enumerate(_reference()['decimal_absolute']):
        _assert_parameter(
            _load_cell(tmp_path, f'decimal-{index}', case['token']),
            value_hex=case['value_hex'],
            esd_hex=case['esd_hex'],
            free=True,
        )


def test_c09_t14_reference_mantissas_are_accepted_on_edi(tmp_path: Path) -> None:
    for index, case in enumerate(_reference()['reference_mantissa_acceptance']):
        _assert_parameter(
            _load_cell(tmp_path, f'reference-mantissa-{index}', case['token']),
            value_hex=case['value_hex'],
            esd_hex=case['esd_hex'] if case['token'] != '.5' else '0x0.0p+0',  # noqa: S105
            free=case['free'],
        )


def test_c09_t14_four_parser_and_public_parameter_states_are_distinct(
    tmp_path: Path,
) -> None:
    observed = []
    for index, case in enumerate(_reference()['states']):
        parameter = _load_cell(tmp_path, f'state-{index}', case['token'])
        _assert_parameter(
            parameter,
            value_hex=case['value_hex'],
            esd_hex=case['esd_hex'] if case['token'] != '3.89' else '0x0.0p+0',  # noqa: S105
            free=case['free'],
        )
        observed.append((parameter.uncertainty is not None, bool(parameter.free)))

    assert observed == [(True, False), (True, True), (True, True), (False, True)]
    assert edi.Parameter(3.5).uncertainty == 0.0, (
        'default public parameter uncertainty must be zero'
    )
    assert edi.Parameter(3.5, None, True).uncertainty is None, (
        'explicit missing public uncertainty must remain absent'
    )
    assert edi.AtomSite().fract_x.uncertainty == 0.0, (
        'default site-coordinate uncertainty must be zero'
    )
    from_factory = edi.ExperimentFactory.from_dict({
        'linked_structure': {'scale': {'value': 3.5, 'uncertainty': None, 'free': True}}
    })
    assert from_factory.linked_structure.scale.uncertainty is None, (
        'factory scale uncertainty must preserve its missing state'
    )
    assert from_factory.linked_structure.scale.free is True


def test_c09_t14_legacy_integer_and_bare_semantics_are_bit_identical(
    tmp_path: Path,
) -> None:
    _assert_parameter(
        _load_cell(tmp_path, 'legacy-bare', '3.89'),
        value_hex='0x1.f1eb851eb851fp+1',
        esd_hex='0x0.0p+0',
        free=False,
    )
    for index, case in enumerate(_reference()['legacy_integer_reference']):
        _assert_parameter(
            _load_cell(tmp_path, f'legacy-integer-{index}', case['token']),
            value_hex=case['value_hex'],
            esd_hex=case['esd_hex'],
            free=True,
        )


def test_c09_t14_edi_matches_the_shared_engine_level_bit_corpus(
    tmp_path: Path,
) -> None:
    reference = _reference()
    cases = [
        *reference['decimal_absolute'],
        *reference['reference_mantissa_acceptance'],
        *reference['legacy_integer_reference'],
        *reference['states'],
    ]
    for index, case in enumerate(cases):
        parameter = _load_cell(tmp_path, f'parity-{index}', case['token'])
        assert float(parameter.value).hex() == case['value_hex']
        engine_esd = 0.0 if parameter.uncertainty is None else float(parameter.uncertainty)
        expected_engine_esd = (
            0.0 if case.get('esd_hex') is None else float.fromhex(case['esd_hex'])
        )
        assert engine_esd.hex() == expected_engine_esd.hex()
        assert bool(parameter.free) is case.get('free', True)


def test_c09_t14_empty_and_fixed_save_load_fixed_points_are_distinct(
    tmp_path: Path,
) -> None:
    empty = edi.Project.load(_project_variant(tmp_path, 'empty-source', '3.5()'))
    empty_destination = tmp_path / 'empty-saved'
    empty.save_as(empty_destination)
    empty_text = _experiment_path(empty_destination).read_text(encoding='utf-8')
    assert '_peak.broad_gauss_sigma_0 3.5()' in empty_text
    empty_reloaded = edi.Project.load(empty_destination).experiment.peak.broad_gauss_sigma_0
    assert empty_reloaded.uncertainty is None, 'empty uncertainty must round-trip as missing'
    assert empty_reloaded.free is True

    fixed = edi.Project.load(_project_variant(tmp_path, 'fixed-source', '3.5'))
    fixed_destination = tmp_path / 'fixed-saved'
    fixed.save_as(fixed_destination)
    fixed_text = _experiment_path(fixed_destination).read_text(encoding='utf-8')
    assert '_peak.broad_gauss_sigma_0 3.5\n' in fixed_text
    fixed_reloaded = edi.Project.load(fixed_destination).experiment.peak.broad_gauss_sigma_0
    assert fixed_reloaded.uncertainty == 0.0, 'fixed uncertainty must round-trip as zero'
    assert fixed_reloaded.free is False


@pytest.mark.parametrize('token', ['100(2.5)', '3.89(0.02)', '.5(1.5)'])
def test_c09_t14_decimal_su_save_load_preserves_reference_value_exactly(
    tmp_path: Path,
    token: str,
) -> None:
    cases = {case['token']: case for case in _reference()['decimal_absolute']}
    case = cases[token]

    source = edi.Project.load(_project_variant(tmp_path, 'decimal-save-source', token))
    _assert_parameter(
        source.experiment.peak.broad_gauss_sigma_0,
        value_hex=case['value_hex'],
        esd_hex=case['esd_hex'],
        free=True,
    )

    destination = tmp_path / 'decimal-save-destination'
    source.save_as(destination)
    restored = edi.Project.load(destination).experiment.peak.broad_gauss_sigma_0
    _assert_parameter(
        restored,
        value_hex=case['value_hex'],
        esd_hex=case['esd_hex'],
        free=True,
    )


@pytest.mark.parametrize(
    ('token', 'expected_esd'),
    [
        ('100(0.0000000001)', 1e-10),
        ('1(0.00000005)', 5e-8),
    ],
)
def test_c09_t14_small_nonzero_su_never_serializes_as_zero(
    tmp_path: Path,
    token: str,
    expected_esd: float,
) -> None:
    source = edi.Project.load(_project_variant(tmp_path, 'small-nonzero-source', token))
    assert source.experiment.peak.broad_gauss_sigma_0.uncertainty == expected_esd, (
        'small nonzero source uncertainty must match the reference'
    )

    destination = tmp_path / 'small-nonzero-destination'
    source.save_as(destination)
    saved_text = _experiment_path(destination).read_text(encoding='utf-8')
    saved_match = re.search(r'^_peak\.broad_gauss_sigma_0\s+(\S+)$', saved_text, re.MULTILINE)
    assert saved_match is not None
    bracket_match = re.fullmatch(
        r'[+-]?(?:\d+\.?\d*|\.\d+)\(([^()]*)\)',
        saved_match.group(1),
    )
    assert bracket_match is not None
    assert bracket_match.group(1)
    assert float(bracket_match.group(1)) != 0.0

    restored = edi.Project.load(destination).experiment.peak.broad_gauss_sigma_0
    assert restored.uncertainty == expected_esd, (
        'small nonzero uncertainty must survive serialization exactly'
    )


def test_c09_t14_extreme_su_round_trips_through_decimal_fallback(
    tmp_path: Path,
) -> None:
    decimal_su = '0.' + '0' * 39 + '1'
    source = edi.Project.load(
        _project_variant(tmp_path, 'extreme-su-source', f'100({decimal_su})')
    )
    expected_esd = source.experiment.peak.broad_gauss_sigma_0.uncertainty
    assert expected_esd == 1e-40

    destination = tmp_path / 'extreme-su-destination'
    source.save_as(destination)
    saved_text = _experiment_path(destination).read_text(encoding='utf-8')
    saved_match = re.search(r'^_peak\.broad_gauss_sigma_0\s+(\S+)$', saved_text, re.MULTILINE)
    assert saved_match is not None
    bracket_match = re.fullmatch(
        r'[+-]?(?:\d+\.?\d*|\.\d+)\((\d+\.\d+)\)',
        saved_match.group(1),
    )
    assert bracket_match is not None
    saved_su = bracket_match.group(1)
    assert float(saved_su) != 0.0
    assert float(saved_su) == expected_esd

    restored = edi.Project.load(destination).experiment.peak.broad_gauss_sigma_0
    assert restored.uncertainty == expected_esd, (
        'extreme uncertainty must survive decimal fallback exactly'
    )


@pytest.mark.parametrize(
    'value_token',
    [
        '0.9',
        '100',
        '383.2',
        '0.0000001',
        '0.000000000001',
        '100000000000000000000',
    ],
)
@pytest.mark.parametrize(
    'su_token',
    [
        '0.05',
        '2.5',
        '0.0000000001',
        '0.' + '0' * 39 + '1',
        None,
    ],
)
def test_c09_t14_writer_tokens_always_reparse_bit_exactly(
    tmp_path: Path,
    value_token: str,
    su_token: str | None,
) -> None:
    source_token = f'{value_token}({"" if su_token is None else su_token})'
    source = edi.Project.load(_project_variant(tmp_path, 'writer-matrix-source', source_token))
    source_parameter = source.experiment.peak.broad_gauss_sigma_0
    expected = (
        float(source_parameter.value).hex(),
        None
        if source_parameter.uncertainty is None
        else float(source_parameter.uncertainty).hex(),
        bool(source_parameter.free),
    )
    assert expected == (
        float(value_token).hex(),
        None if su_token is None else float(su_token).hex(),
        True,
    )

    destination = tmp_path / 'writer-matrix-destination'
    source.save_as(destination)
    saved_text = _experiment_path(destination).read_text(encoding='utf-8')
    saved_match = re.search(r'^_peak\.broad_gauss_sigma_0\s+(\S+)$', saved_text, re.MULTILINE)
    assert saved_match is not None
    saved_token = saved_match.group(1)
    assert 'e' not in saved_token.lower()
    assert re.fullmatch(
        r'[+-]?(?:\d+\.?\d*|\.\d+)\((?:\d+|\d*\.\d+|\d+\.)?\)',
        saved_token,
    )

    restored = edi.Project.load(destination).experiment.peak.broad_gauss_sigma_0
    assert (
        float(restored.value).hex(),
        None if restored.uncertainty is None else float(restored.uncertainty).hex(),
        bool(restored.free),
    ) == expected, 'every serialized token must reparse to its exact public state'


def test_c09_t14_exponent_non_finite_and_malformed_forms_stay_rejected(
    tmp_path: Path,
) -> None:
    reference = _reference()
    rejected = [
        *reference['strict_rejections'],
        *reference['non_finite_rejections'],
        *reference['malformed_rejections'],
    ]
    for index, token in enumerate(rejected):
        with pytest.raises(edi.IoError):
            edi.Project.load(_project_variant(tmp_path, f'rejected-{index}', token))
