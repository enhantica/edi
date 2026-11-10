"""Hidden gates for 's seeded-scale, zero-fit verification pages."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
VERIFICATION = ROOT / 'knowledge/verification'
FULLPROF = VERIFICATION / 'fullprof'
UPSTREAM_PIN = '39ada82c8aef8b4657c4ae8c68e888668db0f38e'


@dataclass(frozen=True)
class ConversionCase:
    """One conversion frozen from diffraction-lib at ``UPSTREAM_PIN``."""

    page: str
    project: str
    pcr_file: str
    prf_file: str
    pcr_blob: str
    prf_blob: str
    old_scale: Decimal
    new_scale: Decimal
    general_multiplicity: Decimal
    old_occupancies: dict[str, Decimal]
    new_occupancies: dict[str, str]


CASES = (
    ConversionCase(
        page='pd-neut-tof_Si_jorgensen',
        project='pd-neut-tof_si-sepd_jorgensen',
        pcr_file='arg_si.pcr',
        prf_file='arg_si.prf',
        pcr_blob='4961c13589f39605da7d5fadfa7b3043b492a0df',
        prf_blob='d75b75de6613b173061b31a1fcff5c0c7b5d9f78',
        old_scale=Decimal('0.6620058'),
        new_scale=Decimal('381.3153'),
        general_multiplicity=Decimal(192),
        old_occupancies={'Si': Decimal('1.00000')},
        new_occupancies={'Si': '0.04167'},
    ),
    ConversionCase(
        page='pd-neut-tof_Si_jorgensen-von-dreele',
        project='pd-neut-tof_si-sepd_jorgensen-von-dreele',
        pcr_file='arg_si.pcr',
        prf_file='arg_si.prf',
        pcr_blob='aa3e9f505486d7c34ef1485c4976522ea125383e',
        prf_blob='aea3025cf9be838c632d3b966219240e79dd0502',
        old_scale=Decimal('0.6750847'),
        new_scale=Decimal('388.8488'),
        general_multiplicity=Decimal(192),
        old_occupancies={'Si': Decimal('1.00000')},
        new_occupancies={'Si': '0.04167'},
    ),
    ConversionCase(
        page='pd-neut-tof_Si_jorgensen-von-dreele-size-strain',
        project='pd-neut-tof_si-sepd_jorgensen-von-dreele-size-strain',
        pcr_file='arg_si.pcr',
        prf_file='arg_si.prf',
        pcr_blob='dd217709a3ddca58183439f4daf9defad8c35864',
        prf_blob='94bf5aa5da973bd41197e9027d589b5c891303c1',
        old_scale=Decimal('0.6750847'),
        new_scale=Decimal('388.8488'),
        general_multiplicity=Decimal(192),
        old_occupancies={'Si': Decimal('1.00000')},
        new_occupancies={'Si': '0.04167'},
    ),
    ConversionCase(
        page='pd-neut-tof_NCAF_jorgensen-von-dreele',
        project='pd-neut-tof_ncaf-wish_jorgensen-von-dreele',
        pcr_file='tmpl_one_bank.pcr',
        prf_file='tmpl_one_bank.prf',
        pcr_blob='aa9e065264856f745633c4fc4e86e1c46e91328f',
        prf_blob='5281375666a367ade535cb09a88a54811079edfc',
        old_scale=Decimal('4.019304'),
        new_scale=Decimal('36.17374'),
        general_multiplicity=Decimal(24),
        old_occupancies={
            'Ca1': Decimal('1.50000'),
            'Al1': Decimal('1.00000'),
            'Na1': Decimal('1.00000'),
            'F1': Decimal('3.00000'),
            'F2': Decimal('3.00000'),
            'F3': Decimal('1.00000'),
        },
        new_occupancies={
            'Ca1': '0.50000',
            'Al1': '0.33333',
            'Na1': '0.33333',
            'F1': '1.00000',
            'F2': '1.00000',
            'F3': '0.33333',
        },
    ),
)


def _pcr_scale(lines: list[str]) -> str:
    header = next(
        index for index, line in enumerate(lines) if line.lstrip().startswith('!  Scale')
    )
    return lines[header + 1].split()[0]


def _pcr_occupancy(lines: list[str], label: str) -> str:
    fields = next(line.split() for line in lines if line.split()[:1] == [label])
    return fields[6]


def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    payload = f'blob {len(data)}\0'.encode() + data
    return hashlib.sha1(payload, usedforsecurity=False).hexdigest()


@pytest.mark.parametrize('case', CASES, ids=lambda case: case.project)
def test_fullprof_project_uses_pinned_fractional_occupancy_and_scale(
    case: ConversionCase,
) -> None:
    """Gate the exact #218 inputs and the non-trivial closed-form conversion."""
    factor = (case.general_multiplicity / Decimal(8)) ** 2
    assert (case.old_scale * factor).quantize(case.new_scale) == case.new_scale, (
        ' historical scale conversion must retain its closed-form factor'
    )

    path = FULLPROF / case.project / case.pcr_file
    lines = path.read_text(encoding='utf-8').splitlines()
    provenance = (path.parent / 'PROVENANCE.md').read_text()
    records = [
        json.loads(block) for block in re.findall(r'```json\s*\n(.*?)\n```', provenance, re.DOTALL)
    ]
    record = next(row for row in records if row.get('schema') == 'fullprof-evidence-1')
    assert record['old_scales'] == [float(case.new_scale)], (
        ' must retain the  scale as the pre-fit input'
    )
    assert float(_pcr_scale(lines)) == record['new_scales'][0], (
        ' seeded scale must equal the recorded scale fit result'
    )
    for label, old_occupancy in case.old_occupancies.items():
        expected = (old_occupancy * Decimal(8) / case.general_multiplicity).quantize(
            Decimal('0.00001')
        )
        expected_text = case.new_occupancies[label]
        assert expected == Decimal(expected_text), ' fractional Occ must retain its source ratio'
        assert _pcr_occupancy(lines, label) == expected_text, (
            ' must retain the already normalized  occupancies'
        )


@pytest.mark.parametrize('case', CASES, ids=lambda case: case.project)
def test_original_pcr_pin_survives_in_c34_t25_historical_inputs(case: ConversionCase) -> None:
    """Preserve the upstream input pin;  reruns prove the new matched pairs."""
    baseline = json.loads((ROOT / 'tests/fixtures/c34_t25_fullprof/baseline.json').read_text())
    content = baseline[case.project]['pcr'].encode()
    digest = hashlib.sha1(
        b'blob ' + str(len(content)).encode() + b'\0' + content, usedforsecurity=False
    ).hexdigest()
    assert digest == case.pcr_blob, (
        ' must retain the original independently published  PCR input pin'
    )
