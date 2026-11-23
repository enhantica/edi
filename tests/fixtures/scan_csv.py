"""Authored scan CSV fixtures from the ADR-0053 and ADR-0132 columns."""

import csv
import math
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

CONDITION_COLUMNS = [
    'fit_result.descent',
    'fit_result.chi_square_tolerance',
    'fit_result.max_iterations',
    'fit_result.termination',
]


# ADR-0133: this authored two-phase scan records both Hill-Howard fractions.
DERIVED_COLUMNS = [
    'linked_structure.alpha.weight_fraction',
    'linked_structure.alpha.weight_fraction.uncertainty',
    'linked_structure.beta.weight_fraction',
    'linked_structure.beta.weight_fraction.uncertainty',
]


# ADR-0132: linked phases occur in the input loop order, after the profile factors.
PROFILE_AGREEMENT_COLUMNS = ['fit_result.r_p', 'fit_result.r_wp', 'fit_result.r_exp']
COSIO_AGREEMENT_COLUMNS = [*PROFILE_AGREEMENT_COLUMNS, 'fit_result.r_bragg.cosio']
TWO_PHASE_AGREEMENT_COLUMNS = [
    *PROFILE_AGREEMENT_COLUMNS,
    'fit_result.r_bragg.alpha',
    'fit_result.r_bragg.beta',
]
TWO_PHASE_SUFFIX = [*CONDITION_COLUMNS, *DERIVED_COLUMNS, *TWO_PHASE_AGREEMENT_COLUMNS]


def legacy_scan(project):
    """Split a fresh combined CSV into the historical results and provenance files."""
    path = project / 'analysis/results.csv'
    sidecar = project / 'analysis/results-provenance.csv'
    assert not sidecar.exists(), 'A fresh scan stores its conditions in results.csv'
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        header, rows = reader.fieldnames, list(reader)
    condition_at = header.index(CONDITION_COLUMNS[0])
    assert header[condition_at:] in (
        [*CONDITION_COLUMNS, *COSIO_AGREEMENT_COLUMNS],
        TWO_PHASE_SUFFIX,
    ), 'Legacy migration starts from ordered conditions, derived values and agreement factors'
    old_header = header[:condition_at]
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=old_header, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    with sidecar.open('w', newline='') as stream:
        fields = ['file_path', *[name.removeprefix('fit_result.') for name in CONDITION_COLUMNS]]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            {
                'file_path': row['file_path'],
                **{name.removeprefix('fit_result.'): row[name] for name in CONDITION_COLUMNS},
            }
            for row in rows
        )


def reported_pair(value, uncertainty):
    """Apply the owner-declared two-significant-digit reporting rule to an oracle pair."""
    original = Decimal(str(uncertainty))
    quantum = Decimal(1).scaleb(original.adjusted() - 1)
    rounded = original.quantize(quantum, rounding=ROUND_CEILING)
    quantum = Decimal(1).scaleb(rounded.adjusted() - 1)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP)), float(rounded)


def assert_reported_legacy(actual, historical):
    """Check each retained row at its own ADR-0092 reporting precision."""
    paired = set()
    for name, text in historical.items():
        if name.endswith('.uncertainty'):
            parameter = name.removesuffix('.uncertainty')
            uncertainty = float(text)
            if math.isfinite(uncertainty) and uncertainty > 0:
                value, su = reported_pair(float(historical[parameter]), uncertainty)
                assert Decimal(actual[parameter]) == Decimal(str(value)), (
                    'Migration retains the reported value'
                )
                assert Decimal(actual[name]) == Decimal(str(su)), (
                    'Migration retains the reported uncertainty'
                )
                paired.update((name, parameter))
    for name, text in historical.items():
        if name in paired:
            continue
        if name == 'fit_result.reduced_chi_square':
            original = Decimal(text)
            quantum = Decimal(1).scaleb(original.adjusted() - 1)
            expected = original.quantize(quantum, rounding=ROUND_HALF_UP)
            assert Decimal(actual[name]) == expected
        else:
            assert actual[name] == text, 'Migration retains each metadata cell and file identity'


def assert_migrated_prefix(
    path, original_header, historical, *, allow_legacy=False, original_bytes=None
):
    """Retain historical identities and values at their declared reporting precision."""
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        header = reader.fieldnames
        retained = list(reader)
    if allow_legacy and header == original_header:
        assert retained == historical, 'A reader-only resume retains every original row'
        assert path.read_bytes() == original_bytes, 'A reader-only resume retains every byte'
        return
    assert header == [*original_header, *CONDITION_COLUMNS, *COSIO_AGREEMENT_COLUMNS], (
        'The migrated Co2SiO4 scan keeps its historical columns before conditions and factors'
    )
    assert len(retained) >= len(historical), 'Continue retains every historical result row'
    for actual, original in zip(retained[: len(historical)], historical, strict=True):
        assert_reported_legacy(actual, original)
        assert {actual[name] for name in COSIO_AGREEMENT_COLUMNS} == {''}, (
            'Migration leaves agreement factors empty for retained historical rows'
        )
