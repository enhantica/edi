"""saved fitted ranges, independent frozen CoSiO CLI numbers.

Values/esds: edi d775b5fd author-time CLI fit, tests/fixtures/e05_t1/cli.json,
CoSiO start-1 record. Synthetic codec inputs keep those numbers verbatim;
this tests saved-value admission, not a fresh engine fit's accuracy.
"""

from __future__ import annotations

import shutil
import warnings
from pathlib import Path

import edi as model
import pytest

ROOT = Path(__file__).resolve().parents[3]


def _plant_frozen_values(original):
    lines = original.splitlines()
    tags = [line for line in lines if line.startswith('_atom_site.')]
    for index, line in enumerate(lines):
        tokens = line.split()
        if tokens and tokens[0] == 'Co1':
            tokens[tags.index('_atom_site.adp_iso')] = '-1.665546316(0.6071001618)'
            lines[index] = ' '.join(tokens)
        elif tokens and tokens[0] == 'O1':
            tokens[tags.index('_atom_site.occupancy')] = '1.047626796(0.08719823489)'
            lines[index] = ' '.join(tokens)
    changed = '\n'.join(lines) + '\n'
    assert changed != original, ' raw fixture mutation reaches both fitted parameter seams'
    return changed


def test_saved_fitted_ranges_warn_and_preserve_values_and_uncertainties(tmp_path, capfd):
    source = tmp_path / 'source'
    shutil.copytree(ROOT / 'docs/user/cli/pd-neut-cwl_cosio-d20_start-1/project', source)
    structure = source / 'structures/cosio.edi'
    changed = _plant_frozen_values(structure.read_text())
    structure.write_text(changed)
    analysis = source / 'analysis/analysis.edi'
    initial_analysis = analysis.read_text()
    for with_result in (False, True):
        analysis.write_text(
            initial_analysis
            + (
                '\n_fit_result.result_kind deterministic\n_fit_result.success true'
                '\n_fit_result.message done\n_fit_result.fitting_time 123.375\n'
                if with_result
                else ''
            )
        )
        before = {
            path.relative_to(source): path.read_bytes()
            for path in source.rglob('*')
            if path.is_file()
        }
        capfd.readouterr()
        with warnings.catch_warnings(record=True) as received:
            warnings.simplefilter('always')
            loaded = model.Project.load(source)
        messages = [str(item.message) for item in received] + capfd.readouterr().err.splitlines()
        for leaf in ('adp_iso', 'occupancy'):
            assert (
                sum(leaf in item and 'outside its admissible range' in item for item in messages)
                == 1
            ), (
                ' public load delivers one range warning for each raw fitted field',
                leaf,
            )
        assert before == {
            path.relative_to(source): path.read_bytes()
            for path in source.rglob('*')
            if path.is_file()
        }, ' successful warning admission never rewrites the input project bytes'
        saved = tmp_path / ('with-result' if with_result else 'legacy')
        loaded.save_as(saved)
        capfd.readouterr()
        with warnings.catch_warnings(record=True) as received:
            warnings.simplefilter('always')
            reopened = model.Project.load(saved)
        messages = [str(item.message) for item in received] + capfd.readouterr().err.splitlines()
        assert sum('outside its admissible range' in item for item in messages) == 2, (
            ' save/reopen delivers both warnings for legacy and result-bearing projects'
        )
        for project in (loaded, reopened):
            sites = {site.id: site for site in project.structure.atom_sites}
            for parameter, value, uncertainty in (
                (sites['Co1'].adp_iso, -1.665546316, 0.6071001618),
                (sites['O1'].occupancy, 1.047626796, 0.08719823489),
            ):
                assert parameter.value == pytest.approx(value, rel=0, abs=1e-12), (
                    ' loader and writer retain the frozen fitted value without clamping'
                )
                assert parameter.uncertainty == pytest.approx(uncertainty, rel=0, abs=1e-12), (
                    ' loader and writer retain the frozen fitted uncertainty'
                )
                assert parameter.free, ' saved free-parameter grammar remains intact'
        if with_result:
            second = tmp_path / 'second-save'
            reopened.save_as(second)
            record = (second / 'analysis/analysis.edi').read_text()
            assert '_fit_result.result_kind deterministic' in record, (
                ' admitting a fitted range preserves the held fit-result category'
            )
        for token in ('nan', 'inf', '-inf', '-1.665546316oops'):
            structure.write_text(changed.replace('-1.665546316(0.6071001618)', token))
            with pytest.raises((ValueError, model.IoError)):
                model.Project.load(source)
            assert token in structure.read_text(), (
                ' malformed or non-finite refusal never repairs the offending input bytes'
            )
        structure.write_text(changed)
