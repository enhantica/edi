"""The magnetic worked examples retain their declared execution and fit records."""

import hashlib
import json
import re
from pathlib import Path

import edi
import numpy as np
import pytest
import yaml

from tests.fixtures.magnetic_pnma import reference

ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / 'docs/user/cli'


@pytest.mark.parametrize(
    ('name', 'execution'),
    [
        ('pd-neut-cwl_cosio-d20_2k', 'executing'),
        ('pd-neut-cwl_cosio-d20_scan-213f', 'offline'),
    ],
)
def test_magnetic_examples_have_records_and_documentation(name, execution):
    directory = CLI / name
    assert directory.is_dir(), 'Both promised magnetic cobalt examples must be delivered'
    registry = yaml.safe_load((CLI / 'projects.yml').read_text())['projects']
    rows = [row for row in registry if row.get('id') == name]
    assert len(rows) == 1, 'Every magnetic example has exactly one registered identity'
    assert any((directory / name).is_file() for name in ['README.md', 'index.md']), (
        'Each magnetic example explains its inputs and scope'
    )
    assert (directory / 'expected.json').is_file(), (
        'Each magnetic fit carries its recorded outcomes'
    )
    record = json.loads((directory / 'expected.json').read_text())
    assert record.get('source'), 'Magnetic fit records name the calculation that produced them'
    quantities = record.get('quantities', {})
    assert quantities, 'Magnetic examples carry nonempty fit-result records'
    if name.endswith('_2k'):
        assert all(value.get('kind') == 'reference' for value in quantities.values()), (
            'The low-temperature example names independent FullProf reference quantities'
        )
    else:
        assert any(value.get('kind') == 'regression-pin' for value in quantities.values()), (
            'The scan labels its engine-generated outcomes as regression pins'
        )
    if execution == 'offline':
        assert rows[0].get('offline') is True, (
            'The extended temperature scan explicitly records its offline execution status'
        )
    else:
        assert rows[0].get('executing') is True and not rows[0].get('offline', False), (
            'The single low-temperature magnetic fit belongs to the executing example set'
        )


def test_low_temperature_fit_record_has_independent_moment_sanity_bounds():
    # Packet gate 10: these are broad physical sanity bounds, never powder-moment correctness pins.
    path = CLI / 'pd-neut-cwl_cosio-d20_2k/expected.json'
    assert path.is_file(), 'The low-temperature fit delivers a machine result record'
    record = json.loads(path.read_text())
    assert 'fullprof' in record['source']['engine'].lower(), (
        'The low-temperature correctness record identifies the independent FullProf engine'
    )
    folder = ROOT / 'knowledge/fitting/fullprof/pd-neut-cwl_cosio-d20_2k'
    assert (path.parent / record['source']['artifact']).resolve() == folder / 'cosio.sum', (
        'The reference record points to the independently authored FullProf summary'
    )
    provenance = (folder / 'PROVENANCE.md').read_text()
    pins = re.findall(r'^\s+([0-9a-f]{64})\s+(\S+)\s*$', provenance, re.MULTILINE)
    assert len(pins) == 5, (
        'The FullProf rerun identifies all five independent input and output files'
    )
    assert {filename for _, filename in pins} == {
        'cosio.pcr',
        'cosio.out',
        'cosio.sum',
        'cosio_1.prf',
        'cosio1.mcif',
    }, 'The authoring provenance covers the input, numeric output, profile and magnetic CIF'
    for digest, filename in pins:
        assert hashlib.sha256((folder / filename).read_bytes()).hexdigest() == digest, (
            'Each independent FullProf reference matches its committed authoring provenance'
        )
    summary = (folder / 'cosio.sum').read_text()
    moments = summary.split('=> Magnetic Moment Components and Standard Deviations', 1)[1]
    cobalt = {}
    for site in ['Co1', 'Co2']:
        row = re.search(r'^\s*' + site + r'_1\s+(.+)$', moments, re.MULTILINE)
        assert row, 'The independent FullProf summary contains each magnetic cobalt site'
        cobalt[site] = [float(value) for value in row[1].split()]
    quantities = record['quantities']
    rwp = float(re.search(r'Rwp:\s+([\d.]+)', summary)[1]) / 100
    assert quantities['rwp']['value'] == pytest.approx(rwp, abs=0.00005, rel=0), (
        'The Rwp target comes from the rerun with both apertures held at 0.0619'
    )
    for site, axis, index in [('Co1', 'x', 0), ('Co1', 'y', 2), ('Co2', 'y', 2)]:
        value = quantities[f'param.{site}.crystalaxis_{axis}.value']
        assert value['kind'] == 'reference', 'Each retained component is a FullProf reference'
        assert value['value'] == pytest.approx(cobalt[site][index], abs=0.00005, rel=0), (
            'The referenced component matches the independent FullProf printed result'
        )
    assert 'param.Co1.crystalaxis_z.value' not in quantities, (
        'The poorly determined powder Mz has no independent fit target'
    )
    assert 2.68 <= cobalt['Co1'][6] <= 3.87, (
        'Co1 magnitude lies between the declared report minimum and single-crystal value'
    )
    assert 2.620 <= cobalt['Co2'][2] <= 3.35, (
        'The fitted Co2 moment lies within the packet declared physical sanity interval'
    )


@pytest.mark.parametrize('name', ['pd-neut-cwl_cosio-d20_2k', 'pd-neut-cwl_cosio-d20_scan-213f'])
def test_magnetic_examples_share_cobalt_displacements_and_exclude_only_dead_cell(name, tmp_path):
    directory = CLI / name / 'project'
    assert directory.is_dir(), 'Each magnetic example delivers a loadable native project'
    model = edi.Project.load(directory)
    assert '_minimizer.descent' not in reference.columns(
        (directory / 'analysis/analysis.edi').read_text()
    ), 'The magnetic examples select the default descent through their saved recipe'
    model.analysis.calculate()
    peak = model.experiment.peak
    sample, detector = peak.asym_fcj_1, peak.asym_fcj_2
    assert sample.value == detector.value, 'The cobalt example uses equal axial apertures'
    if name.endswith('_2k'):
        assert sample.free and not detector.free, 'The single fit frees exactly one axial aperture'
        sample.value = 0.04
        model.analysis.calculate()
        assert detector.value == sample.value, 'The detector aperture follows the sample aperture'
    else:
        assert not sample.free and not detector.free, 'The scan fixes both axial apertures'
        assert sample.value == pytest.approx(0.0619, abs=1e-12), (
            'The scan holds the common aperture used in the committed FullProf rerun'
        )
    structure = model.structure
    structure.atom_sites['Co1'].adp_iso.value = 0.42
    model.analysis.calculate()
    assert structure.atom_sites['Co2'].adp_iso.value == pytest.approx(0.42), (
        'The magnetic examples tie both cobalt displacement parameters to one shared value'
    )
    moments = structure.atom_site_moment
    independent = [('Co1', 'x'), ('Co1', 'y'), ('Co1', 'z'), ('Co2', 'y')]
    assert all(getattr(moments[site], 'crystalaxis_' + axis).free for site, axis in independent), (
        'The magnetic examples free all four symmetry-independent moment components'
    )
    grid = np.asarray(model.experiment.data.two_theta)
    status = model.experiment.data.calc_status
    for angle, expected in [(64.5953, 'incl'), (64.6953, 'excl'), (64.7953, 'incl')]:
        index = np.flatnonzero(np.abs(grid - angle) < 1e-5)
        assert len(index) == 1, 'The mask controls occur on each examples own observed point list'
        assert str(status[int(index[0])]) == expected, (
            'Each example excludes the dead cell and retains both neighbours'
        )
    model.save_as(tmp_path / 'saved')
    original = reference.columns((directory / 'structures/cosio.edi').read_text())
    saved = reference.columns((tmp_path / 'saved/structures/cosio.edi').read_text())
    for key, values in original.items():
        if key.startswith(('_parent_', '_space_group_symop_magn')):
            assert saved.get(key) == values, (
                'The delivered fit record retains its validated magnetic symmetry and propagation'
            )


def test_extended_scan_retains_the_original_files_and_reverses_the_full_sequence():
    before = CLI / 'pd-neut-cwl_cosio-d20_scan-162f/project/experiments/d20_scan'
    after = CLI / 'pd-neut-cwl_cosio-d20_scan-213f/project'
    original = sorted(before.glob('*.dat'))
    extended = sorted((after / 'experiments/d20_scan').glob('*.dat'))
    assert len(original) == 162 and len(extended) == 213, (
        'The magnetic scan adds the declared low-temperature files to the complete earlier scan'
    )
    for source in original:
        assert (
            after / 'experiments/d20_scan' / source.name
        ).read_bytes() == source.read_bytes(), (
            'Extending the scan preserves every original observed file byte for byte'
        )
    analysis = reference.columns((after / 'analysis/analysis.edi').read_text())
    assert analysis['_sequential_fit.reverse'] == ['true'], (
        'The full magnetic sequence reverses the file ordering to start at the lowest temperature'
    )


def test_preview_example_background_leaves_the_first_magnetic_peak_unpinned():
    path = CLI / 'pd-neut-cwl_cosio-d20_2k/project/experiments/d20.edi'
    values = reference.columns(path.read_text())
    positions = [float(value.split('(')[0]) for value in values['_background.position']]
    assert not any(8 <= position <= 12 for position in positions), (
        'The preview background has no interpolation point in the first magnetic peak and rise'
    )
    assert sum(6 <= x < 8 for x in positions) >= 2 and sum(12 < x <= 16 for x in positions) >= 2, (
        'Background control points bracket the first magnetic peak on both sides'
    )
    assert values['_excluded_region.start'][0] == '0', 'The first exclusion starts at zero degrees'
    assert float(values['_excluded_region.end'][0]) == 6, (
        'The first example exclusion ends at six degrees instead of the preview eight'
    )


@pytest.mark.parametrize('name', ['pd-neut-cwl_cosio-d20_2k', 'pd-neut-cwl_cosio-d20_scan-213f'])
def test_magnetic_worked_examples_are_in_documentation_navigation(name):
    assert name in (ROOT / 'mkdocs.yml').read_text(), (
        'Both magnetic worked examples are reachable through the documentation navigation'
    )


def test_sequential_magnetic_example_has_a_tutorial_page():
    example = 'pd-neut-cwl_cosio-d20_scan-213f'
    docs = ROOT / 'docs'
    nav = yaml.load((ROOT / 'mkdocs.yml').read_text(), Loader=yaml.BaseLoader)['nav']

    def tutorial_sections(items):
        for item in items:
            if not isinstance(item, dict):
                continue
            for title, value in item.items():
                if title == 'Tutorials' and isinstance(value, list):
                    yield from value
                elif isinstance(value, list):
                    yield from tutorial_sections(value)

    pages = [
        next(iter(entry.values())) if isinstance(entry, dict) else entry
        for entry in tutorial_sections(nav)
    ]
    tutorial = [
        docs / page
        for page in pages
        if isinstance(page, str)
        and Path(page).parent == Path('user/tutorials')
        and Path(page).stem == example
    ]
    assert len(tutorial) == 1, 'The extended magnetic app example has one Tutorials page'
    assert example in tutorial[0].read_text(), 'The tutorial walks through the registered example'
