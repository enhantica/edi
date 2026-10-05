"""declared selector, project seam and immutable external reference."""

import ast
import hashlib
import json
import math
import re
from pathlib import Path

import edi
import numpy as np
import pytest
from test_c09_t16_verification_notebooks import (
    _assert_calculated_candidate_flow,  # noqa: PLC2701
    _assert_fullprof_reference_flow,  # noqa: PLC2701
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c15_t1_xray'
MANIFEST = json.loads((FIXTURE / 'manifest.json').read_text())
PAGE = 'pd-xray-cwl_LiF_single'


def _assert_lif_reference_binding(tree):
    # ACCIDENT: an intact vendored oracle is unused, or the page loads a different project.
    values = {
        n.targets[0].id: n.value.value
        for n in tree.body
        if isinstance(n, ast.Assign)
        and len(n.targets) == 1
        and isinstance(n.targets[0], ast.Name)
        and isinstance(n.value, ast.Constant)
    }
    assert values.get('FULLPROF_PROJECT_DIR') == 'pd-xray-cwl_lif_single', (
        ' page must load the digest-pinned LiF project'
    )
    assert values.get('FULLPROF_PRF_FILE') == 'lif_single_unpolarized.prf', (
        ' page must use the unpolarized single-wavelength FullProf calculation'
    )
    _assert_fullprof_reference_flow(PAGE, tree)


def _write_project(tmp_path, selectors='', radiation='xray', model='model.edi', wavelength=None):
    structure, experiment = (FIXTURE / model).read_text().split('data_experiment', 1)
    (tmp_path / 'structures').mkdir()
    (tmp_path / 'experiments').mkdir()
    (tmp_path / 'structures/lif.edi').write_text(
        structure.replace('data_structure', 'data_structure\n_edi.schema_version 3')
    )
    grid = np.loadtxt(FIXTURE / 'reference.tsv')[::10, 0]
    experiment = 'data_experiment\n_edi.schema_version 3' + experiment
    if wavelength is not None:
        if '_instrument.setup_wavelength' in experiment:
            experiment = re.sub(
                r'(_instrument.setup_wavelength)\s+\S+',
                rf'\g<1> {wavelength}',
                experiment,
            )
        else:
            experiment += f'\n_instrument.setup_wavelength {wavelength}\n'
    experiment += '\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    experiment += ''.join(f'{x:.10g} 0 1\n' for x in grid)
    (tmp_path / 'experiments/lif.edi').write_text(experiment)
    if radiation == 'xray' and 'xray_dispersion' not in selectors:
        selectors += '\n_scattering_source.xray_dispersion none\n'
    path = tmp_path / 'experiments/lif.edi'
    path.write_text(
        path.read_text().replace('radiation_probe xray', 'radiation_probe ' + radiation)
        + selectors
    )
    return tmp_path


def test_xray_kind_is_selected_by_declared_probe_and_roundtrips(tmp_path):
    _write_project(tmp_path)
    try:
        project = edi.Project.load(tmp_path)
    except (edi.IoError, ValueError, RuntimeError) as error:
        pytest.fail(f' missing capability: declared X-ray CW experiment: {error}')
    item = project.experiments[0]
    assert type(item.instrument).__name__ == 'CwlPdXrayInstrument', (
        ' radiation_probe selects the X-ray instrument even with zero Lorentz width X'
    )
    project.analysis.calculate()
    before = np.asarray(item.data.intensity_calc).copy()
    assert np.isfinite(before).all() and np.max(before) > 0, (
        ' declared X-ray calculation must yield a finite nonzero pattern'
    )
    project.save_as(tmp_path / 'saved')
    emitted = '\n'.join(p.read_text() for p in (tmp_path / 'saved/experiments').glob('*.edi'))
    assert 'xray' in emitted, ' project save must preserve the radiation selector'
    restored = edi.Project.load(tmp_path / 'saved')
    assert type(restored.experiments[0].instrument).__name__ == 'CwlPdXrayInstrument', (
        ' saved X-ray project must restore its exact declared model type'
    )
    restored.analysis.calculate()
    np.testing.assert_array_equal(
        before,
        restored.experiments[0].data.intensity_calc,
        err_msg=' X-ray save/load must preserve calculated values',
    )


def test_lif_page_uses_byte_identical_fullprof_calculation_without_a_fit():
    page = ROOT / 'docs/dev/verification' / (PAGE + '.py')
    assert page.is_file(), ' missing capability: LiF single X-ray verification page'
    tree = ast.parse(page.read_text())
    _assert_lif_reference_binding(tree)
    calls = [ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)]
    assert any(c.endswith('assert_patterns_agree') for c in calls), (
        ' LiF page must execute its independent FullProf agreement assertion'
    )
    assert not any(c.endswith(('.fit', '.refine')) for c in calls), (
        ' LiF is calculator parity with zero fitted parameters; a scale fit hides errors'
    )
    assert 'fp2k' not in ast.unparse(tree), ' no gate may regenerate its oracle with fp2k'
    assert not any('skip' in c or 'xfail' in c for c in calls), (
        ' page must execute its comparison without skip or expected failure'
    )
    # Use the established upstream directory name; all page families follow this layout.
    directory = ROOT / 'knowledge/verification/fullprof/pd-xray-cwl_lif_single'
    for name, digest in MANIFEST['files'].items():
        path = directory / name
        assert path.is_file(), ' missing vendored independent LiF artifact: ' + name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, (
            ' vendored FullProf files must match committed diffraction-lib bytes'
        )
    assert 'diffraction-lib' in (directory / 'PROVENANCE.md').read_text(), (
        ' reference provenance must name the independent upstream'
    )


def test_c33_lif_counter_is_derived_from_filename_difference():
    before = set(MANIFEST['before_pages'])
    after = {p.stem for p in (ROOT / 'docs/dev/verification').glob('*.py')}
    after.discard('pd-neut-cwl_LBCO_preferred-orientation')
    #  owns the additional polarized page;  still owns exactly its baseline page.
    after.discard('pd-xray-cwl_LiF_single_polarization')
    # ADR-0078 adds its separately gated tied-Biso page; keep this task's delta exact.
    after.discard('pd-neut-cwl_cosio-d20_biso-tied')
    assert before <= after and after - before == {PAGE}, (
        ' C33 filename difference must contain exactly the owned LiF single page'
    )


@pytest.mark.parametrize('escape', ['oracle-assignment', 'other-experiment', 'no-calculation'])
def test_shared_candidate_flow_rejects_oracle_and_wrong_calculation(escape):
    # Sweep the existing shared-flow consumers before exercising the LiF-family substitution.
    pages = ROOT / 'docs/dev/verification'
    for path in pages.glob('*.py'):
        if path.stem != 'pd-neut-cwl_PbSO4_beba-asymmetry':
            _assert_calculated_candidate_flow(path.stem, ast.parse(path.read_text()))
    tree = ast.parse((pages / 'pd-neut-cwl_LaB6_basic.py').read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == 'calc_ed_crysta'
            for target in node.targets
        ):
            if escape == 'oracle-assignment':
                node.value.args[1] = ast.Name(id='calc_fullprof', ctx=ast.Load())
            elif escape == 'other-experiment':
                node.value.args[1] = ast.parse(
                    'other.experiment.data.intensity_calc', mode='eval'
                ).body
        if (
            escape == 'no-calculation'
            and isinstance(node, ast.Call)
            and ast.unparse(node.func) == 'project.analysis.calculate'
        ):
            node.func = ast.parse('other.analysis.calculate', mode='eval').body
    with pytest.raises(AssertionError, match='calculated candidate'):
        _assert_calculated_candidate_flow(PAGE, tree)


@pytest.mark.parametrize('f0', ['wk1995', 'it1992'])
@pytest.mark.parametrize('dispersion', ['none', 'sasaki1989', 'it1992'])
def test_source_selectors_roundtrip_as_written(tmp_path, f0, dispersion):
    # ACCIDENT: a loader tolerates a tag but the serializer silently discards its selection.
    selectors = (
        f'\n_scattering_source.xray_form_factor {f0}\n'
        f'_scattering_source.xray_dispersion {dispersion}\n'
    )
    project = edi.Project.load(_write_project(tmp_path, selectors))
    project.save_as(tmp_path / 'saved')
    emitted = '\n'.join(p.read_text() for p in (tmp_path / 'saved/experiments').glob('*.edi'))
    for field, value in [('xray_form_factor', f0), ('xray_dispersion', dispersion)]:
        lines = [
            line.split()
            for line in emitted.splitlines()
            if line.startswith('_scattering_source.' + field)
        ]
        assert len(lines) == 1 and lines[0][1].strip('"\'') == value, (
            ' source selector must round-trip its declared source name: ' + field
        )
    restored = edi.Project.load(tmp_path / 'saved')
    restored.save_as(tmp_path / 'again')
    again = '\n'.join(p.read_text() for p in (tmp_path / 'again/experiments').glob('*.edi'))
    for field, value in [('xray_form_factor', f0), ('xray_dispersion', dispersion)]:
        assert any(
            line.split()[1].strip('"\'') == value
            for line in again.splitlines()
            if line.startswith('_scattering_source.' + field)
        ), ' reloaded source must survive the second serialization: ' + field


@pytest.mark.parametrize(
    ('field', 'value'), [('xray_form_factor', 'it1992'), ('xray_dispersion', 'sasaki1989')]
)
@pytest.mark.parametrize('accident', ['neutron', 'unknown-source'])
def test_source_selectors_refuse_wrong_radiation_and_unknown_names(
    tmp_path, field, value, accident
):
    radiation = 'neutron' if accident == 'neutron' else 'xray'
    value = value if accident == 'neutron' else 'not-a-published-source'
    _write_project(tmp_path, f'\n_scattering_source.{field} {value}\n', radiation)
    with pytest.raises(edi.IoError) as raised:
        edi.Project.load(tmp_path)
    assert field in str(raised.value), (
        ' structured selector error must identify the offending field'
    )


@pytest.mark.parametrize('f0', ['wk1995', 'it1992'])
@pytest.mark.parametrize('dispersion', ['none', 'sasaki1989', 'it1992'])
def test_edi_adapter_preserves_complex_source_selected_intensity(tmp_path, f0, dispersion):
    reference = json.loads((FIXTURE / 'single_fe.json').read_text())
    structure, experiment = (FIXTURE / 'single_fe.edi').read_text().split('data_experiment', 1)
    (tmp_path / 'structures').mkdir()
    (tmp_path / 'experiments').mkdir()
    (tmp_path / 'structures/fe.edi').write_text(
        structure.replace('data_structure', 'data_structure\n_edi.schema_version 3')
    )
    experiment = 'data_experiment\n_edi.schema_version 3' + experiment
    experiment += (
        f'\n_instrument.setup_wavelength 1.54\n'
        f'_scattering_source.xray_form_factor {f0}\n'
        f'_scattering_source.xray_dispersion {dispersion}\n'
    )
    experiment += 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    experiment += ''.join(f'{x:.15g} 0 1\n' for x in reference['grid'])
    (tmp_path / 'experiments/fe.edi').write_text(experiment)
    project = edi.Project.load(tmp_path)
    project.analysis.calculate()
    np.testing.assert_allclose(
        project.experiments[0].data.intensity_calc,
        reference[f0 + ':' + dispersion],
        rtol=1e-7,
        atol=1e-7,
        err_msg=' edi carries both sources into complex single-site intensity',
    )


@pytest.mark.parametrize('explicit', [False, True])
@pytest.mark.parametrize('case', [0, 1])
def test_continuous_default_reaches_edi_at_nonlab_wavelength(tmp_path, explicit, case):
    # Independent DABAX quarter-interval probes: neither is a lab line or a table row.
    reference = json.loads((FIXTURE / 'cromer_liberman_fe.json').read_text())
    wavelength, fp, fpp = reference['cases'][case]
    structure, experiment = (FIXTURE / 'single_fe.edi').read_text().split('data_experiment', 1)
    (tmp_path / 'structures').mkdir()
    (tmp_path / 'experiments').mkdir()
    (tmp_path / 'structures/fe.edi').write_text(
        structure.replace('data_structure', 'data_structure\n_edi.schema_version 3')
    )
    experiment = 'data_experiment\n_edi.schema_version 3' + experiment
    experiment += f'\n_instrument.setup_wavelength {wavelength:.17g}\n'
    experiment += '_scattering_source.xray_form_factor it1992\n'
    if explicit:
        experiment += '_scattering_source.xray_dispersion cromer-liberman\n'
    theta = math.asin(wavelength / 4)
    grid = [2 * math.degrees(theta) + delta for delta in [-0.01, 0, 0.01]]
    experiment += 'loop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
    experiment += ''.join(f'{x:.17g} 0 1\n' for x in grid)
    (tmp_path / 'experiments/fe.edi').write_text(experiment)
    project = edi.Project.load(tmp_path)
    project.analysis.calculate()
    # IT1992 Fe at s=0.25; six {100} reflections, B=0.8, occupancy=0.7.
    f0 = 1.0369 + sum(
        a * math.exp(-b / 16)
        for a, b in zip(
            [11.7695, 7.3573, 3.5222, 2.3045], [4.7611, 0.3072, 15.3535, 76.8805], strict=True
        )
    )
    intensity = (
        6
        * 0.49
        * math.exp(-1.6 / 16)
        * ((f0 + fp) ** 2 + fpp**2)
        / (math.sin(theta) * math.sin(2 * theta))
    )
    expected = [
        intensity
        * math.sqrt(4 * math.log(2) / math.pi)
        / 0.1
        * math.exp(-4 * math.log(2) * delta**2 / 0.01)
        for delta in [-0.01, 0, 0.01]
    ]
    np.testing.assert_allclose(
        project.experiments[0].data.intensity_calc,
        expected,
        rtol=1e-7,
        atol=1e-7,
        err_msg=' edi default must be continuous Cromer-Liberman at nonlab wavelength',
    )
    project.save_as(tmp_path / 'saved')
    emitted = '\n'.join(p.read_text() for p in (tmp_path / 'saved/experiments').glob('*.edi'))
    assert ('_scattering_source.xray_dispersion' in emitted) == explicit, (
        ' default source preserves absence while an explicit source is written back'
    )


@pytest.mark.parametrize(
    ('source', 'wavelength'),
    [
        ('lab-kalpha', 1.54),
        ('sasaki1989', 1.74345),
        ('sasaki1989', 0.09),
        ('sasaki1989', 2.90),
        ('it1992', 1.0),
        *[
            ('cromer-liberman', value)
            for value in np.loadtxt(FIXTURE / 'cromer_liberman_refusals.tsv')
        ],
    ],
)
def test_dropped_or_outside_source_domain_refuses_in_edi(tmp_path, source, wavelength):
    # The source-domain witness contains Fe: Li/F have no edge at Fe K.
    if source != 'lab-kalpha':
        control_dir = tmp_path / 'control'
        control_dir.mkdir()
        control = edi.Project.load(
            _write_project(
                control_dir,
                f'\n_scattering_source.xray_dispersion {source}\n',
                model='single_fe.edi',
                wavelength=1.54,
            )
        )
        control.analysis.calculate()
        intensity = np.asarray(control.experiments[0].data.intensity_calc)
        assert np.isfinite(intensity).all() and np.max(intensity) > 0, (
            ' domain refusal requires the same Fe source to calculate off-edge first'
        )
    if source == 'sasaki1989' and wavelength == 1.74345:
        light_dir = tmp_path / 'light-elements'
        light_dir.mkdir()
        light = edi.Project.load(
            _write_project(
                light_dir,
                '\n_scattering_source.xray_dispersion sasaki1989\n',
                wavelength=wavelength,
            )
        )
        light.analysis.calculate()
        intensity = np.asarray(light.experiments[0].data.intensity_calc)
        assert np.isfinite(intensity).all() and np.max(intensity) > 0, (
            ' Fe-edge refusal is element-scoped: the Li/F control remains calculable'
        )
    _write_project(
        tmp_path,
        f'\n_scattering_source.xray_dispersion {source}\n',
        model='single_fe.edi',
        wavelength=wavelength,
    )

    def evaluate():
        project = edi.Project.load(tmp_path)
        project.analysis.calculate()

    with pytest.raises((edi.IoError, ValueError)):
        evaluate()
