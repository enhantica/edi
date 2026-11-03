"""Main regression pins: exact inputs and numeric fitted outputs at parity precision."""

import importlib
import json
import re
import warnings
from decimal import Decimal
from pathlib import Path

import pytest

from tests.conftest import corpus_case_dir
from tests.fixtures.cif_import_baseline.canonical_positions import (
    PRASEODYMIUM,
    SILICON,
    restore_representative,
)
from tests.fixtures.fittability.saved_reference import fingerprints, fit_snapshot, snapshot, staged
from tests.fixtures.project_categories.historical_bytes import check_project_spacing, prior_digest

ROOT = Path(__file__).resolve().parents[3]
API = 'edi'
REFERENCE = json.loads((ROOT / 'tests/fixtures/fittability/saved-main.json').read_text())

ORIGINAL = json.loads((ROOT / 'tests/fixtures/fittability/saved-before-rounded.json').read_text())
TRANSITIONS = json.loads(
    (ROOT / 'tests/fixtures/fittability/rounded-save-transitions.json').read_text()
)['changes']


def _pin_fitted_line(content, prefix, expected):
    def numbers(token):
        parsed = re.fullmatch(
            rb'([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(?:\((\d+)\))?', token
        )
        assert parsed is not None, 'Fitted output is a finite numeric value with an optional s.u.'
        value = Decimal(parsed[1].decode())
        if parsed[2] is None:
            return (float(value),)
        uncertainty = Decimal(parsed[2].decode()).scaleb(value.as_tuple().exponent)
        return float(value), float(uncertainty)

    def restore(match):
        tokens = re.findall(rb'\S+', match[1])
        assert len(tokens) == len(expected), 'Fitted output retains every pinned numeric column'
        for token, pin in zip(tokens, expected, strict=True):
            assert numbers(token) == pytest.approx(numbers(pin), rel=5e-9, abs=5e-10), (
                'Fitted values and s.u. match the main regression pin at ADR-0057 precision: '
                + prefix.decode()
            )
        pins = iter(expected)
        return prefix + re.sub(rb'\S+', lambda _: next(pins), match[1])

    restored, count = re.subn(rb'(?m)^' + re.escape(prefix) + rb'([^\r\n]+)$', restore, content)
    assert count == 1, 'Each pinned fitted output row occurs exactly once: ' + prefix.decode()
    return restored


@pytest.mark.parametrize('case', tuple(REFERENCE['projects']))
@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
def test_main_saved_bytes_regression_pin(tmp_path, case, rule):
    transitioned = dict(ORIGINAL['projects'][case][rule])
    for change in TRANSITIONS:
        if (change['case'], change['rule']) == (case, rule):
            assert transitioned[change['path']] == change['before'], (
                'Each byte transition binds the exact preceding immutable regression hash'
            )
            transitioned[change['path']] = change['after']
    assert transitioned == REFERENCE['projects'][case][rule], (
        'The complete ordered transition chain must reach exactly the current saved-byte pins'
    )
    api = importlib.import_module(API)
    if case == 'tests/fixtures/e04_t1/reference/unused-free':
        with warnings.catch_warnings(record=True) as notes:
            warnings.simplefilter('always')
            project = api.Project.load(staged(ROOT / case, tmp_path / 'input', rule))
        assert (
            sum(
                'unfittable_free_ignored' in str(note.message)
                and 'broad_lorentz_gamma_1' in str(note.message)
                and "this fit's data cannot determine it" in str(note.message)
                for note in notes
            )
            == 1
        ), 'The unused free input emits exactly one coded not-measured note'
        project.save_as(tmp_path / 'saved')
        actual = fingerprints(
            tmp_path / 'saved', order_reference=REFERENCE['projects'][case][rule]
        )
        saved = (tmp_path / 'saved/experiments/dream.edi').read_bytes()
        fixed = b'_peak.broad_lorentz_gamma_1 0.1\n'
        assert saved.count(fixed) == 1, (
            'The saved unsupported Lorentzian coefficient has exactly one fixed spelling'
        )
        # Restore only the historical flag in memory to compare every other saved byte to main.
        actual['experiments/dream.edi'] = prior_digest(
            saved.replace(fixed, b'_peak.broad_lorentz_gamma_1 0.1()\n'),
            REFERENCE['projects'][case][rule]['experiments/dream.edi'],
            name='experiments/dream.edi',
        )
    else:
        actual = snapshot(
            api, ROOT / case, tmp_path, rule, order_reference=REFERENCE['projects'][case][rule]
        )
    if case == SILICON or case in PRASEODYMIUM:
        name = 'structures/si.edi' if case == SILICON else 'structures/structure.edi'
        actual[name] = prior_digest(
            restore_representative((tmp_path / 'saved' / name).read_bytes(), case),
            REFERENCE['projects'][case][rule][name],
            name=name,
        )
    check_project_spacing(tmp_path / 'saved')
    assert actual == REFERENCE['projects'][case][rule], (
        'The rounded-save regression preserves every saved path and byte under both s.u. rules; '
        'only independently checked orbit representatives, immutable-hash category movement, '
        'clocks and the checked free flag are normalized: ' + case + ' / ' + rule
    )


@pytest.mark.parametrize('case', tuple(REFERENCE['fit_projects']))
@pytest.mark.parametrize('rule', ['iucr_19', 'iucr_99'])
def test_main_fitted_descriptor_bytes_regression_pin(tmp_path, case, rule):
    actual = fit_snapshot(
        importlib.import_module(API),
        corpus_case_dir('single-crystal-page-cwl-tbti-isotropic-extinction') / 'project',
        tmp_path,
        rule,
        order_reference=REFERENCE['fit_projects'][case][rule],
    )
    check_project_spacing(tmp_path / 'saved')

    def pinned(relative, prefix):
        matches = [
            line[len(prefix) :].split()
            for line in REFERENCE['fitted_tokens'][rule][relative]
            if line.startswith(prefix)
        ]
        assert len(matches) == 1, 'The frozen main save contains exactly one fitted numeric row'
        return [token.encode() for token in matches[0]]

    analysis = (tmp_path / 'saved/analysis/analysis.edi').read_bytes()
    for name in (
        'reduced_chi_square',
        'objective_value',
        'prof_r_factor',
        'prof_wr_factor',
        'prof_wr_expected',
        'prof_cr_factor',
        'prof_cwr_factor',
    ):
        prefix = '_fit_result.' + name + ' '
        analysis = _pin_fitted_line(
            analysis, prefix.encode(), pinned('analysis/analysis.edi', prefix)
        )
    for prefix in (
        'experiment 220 ',
        (
            '1 deterministic experiment.linked_structure.structure.scale '
            'experiment.extinction.domain_radius '
        ),
    ):
        analysis = _pin_fitted_line(
            analysis, prefix.encode(), pinned('analysis/analysis.edi', prefix)
        )
    analysis = re.sub(rb'(?m)^(_fit_result.fitting_time[ \t]+)[^\r\n]+', rb'\1<CLOCK>', analysis)
    actual['analysis/analysis.edi'] = prior_digest(
        analysis,
        REFERENCE['fit_projects'][case][rule]['analysis/analysis.edi'],
        name='analysis/analysis.edi',
    )
    experiment = (tmp_path / 'saved/experiments/experiment.edi').read_bytes()
    for prefix in ('_extinction.domain_radius ', '_extinction.crystal_radius ', 'structure '):
        experiment = _pin_fitted_line(
            experiment, prefix.encode(), pinned('experiments/experiment.edi', prefix)
        )
    actual['experiments/experiment.edi'] = prior_digest(
        experiment,
        REFERENCE['fit_projects'][case][rule]['experiments/experiment.edi'],
        name='experiments/experiment.edi',
    )
    assert actual == REFERENCE['fit_projects'][case][rule], (
        'The fitted crystal-radius regression preserves every saved path and non-fitted byte '
        'under both s.u. rules, with checked fitted numbers, clocks and hash-verified '
        'category movement and description spelling'
    )
