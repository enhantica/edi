"""gate 5: retain the immutable pre-move byte pins.

Before : raw corpus inputs and saved bytes equalled the old hashes.
After inherited main cf5d5253: reverse only the six declared seed changes,
check/remove exactly one canonical calculator block per saved experiment,
and compare every other byte and the full file inventory to the same pins.
The later manual estimate category has a separately labelled exact byte extension.
"""

import hashlib
import importlib.util
import json
import math
import shutil
import zipfile
from pathlib import Path

import pytest

from tests.fixtures.background_estimate import manual_bytes as estimate_bytes
from tests.fixtures.excluded_display.historical_bytes import (
    current_excluded_bytes,
    historical_excluded_bytes,
    retained_hashes,
)
from tests.fixtures.fitting_modes.historical_bytes import historical_analysis
from tests.fixtures.loop_parameter_ids.historical_fit_ids import historical_fit_ids
from tests.fixtures.report_units.iucr_reference import without_default_rule
from tests.fixtures.report_units.saved_iucr import rounded_pins
from tests.fixtures.table_display import metadata_bytes, stored_id_bytes
from tests.fixtures.weight_fractions.single_phase_bytes import historical_single_fraction

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c34_t28_baseline'
BASELINE = json.loads((FIXTURE / 'saved-bytes.json').read_text())
SPEC = importlib.util.spec_from_file_location('c34_bytes', FIXTURE / 'generate_bytes.py')
REFERENCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REFERENCE)
EXTENSION = json.loads(
    (ROOT / 'tests/fixtures/c15_t2_polarization/regression-pins.json').read_text()
)

RELATIONS = json.loads((ROOT / 'tests/fixtures/constraint_expressions/byte-pins.json').read_text())
NEW_FIXED_POINTS = BASELINE.get('post_feature_fixed_points', {})
SINGLE_CRYSTAL_FIXED_POINTS = {
    'repo:docs/user/cli/sc-neut-tof_taurine-unknown_basic/project',
    'corpus:single-crystal-page-cwl-tbti-isotropic-extinction/project',
    'corpus:single-crystal-page-tof-taurine-basic/project',
    'corpus:single-crystal-tof-taurine-basic/project',
    'corpus:single-crystal-page-cwl-pr2nio4-basic/project',
    'repo:docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_basic/project',
    'corpus:single-crystal-cwl-tbti-anisotropic-adp/project',
    'corpus:single-crystal-page-cwl-tbti-anisotropic-adp/project',
    'repo:docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_anisotropic-adp/project',
    'repo:docs/user/cli/sc-neut-cwl_pr2nio4-5c2_fit/project',
    'repo:docs/user/cli/sc-neut-cwl_pr2nio4-5c2_basic/project',
    'corpus:single-crystal-cwl-tbti-basic/project',
    'repo:docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_fit/project',
    'corpus:single-crystal-cwl-pr2nio4-basic/project',
    'repo:docs/user/cli/sc-neut-tof_taurine_fit/project',
    'repo:docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_isotropic-extinction/project',
    'corpus:single-crystal-page-cwl-tbti-basic/project',
}


def restored_source(source, tmp_path):
    restored = metadata_bytes.restore(source, tmp_path / 'descriptive-input')
    if REFERENCE.hashes(restored) != REFERENCE.hashes(source):
        old_saved, new_saved = tmp_path / 'descriptive-old', tmp_path / 'descriptive-new'
        REFERENCE.observe(restored, old_saved)
        REFERENCE.observe(source, new_saved)
        metadata_bytes.check_saved(source, old_saved, new_saved)
    else:
        restored = source
    return current_source(restored, tmp_path)


def current_source(source, tmp_path):
    changes = {}
    for path in (source / 'experiments').glob('*.edi'):
        changed = current_excluded_bytes('experiments/' + path.name, path.read_bytes())
        if changed != path.read_bytes():
            changes[path.name] = changed
    if not changes:
        return source
    destination = tmp_path / 'current-input'
    shutil.copytree(source, destination)
    for name, contents in changes.items():
        (destination / 'experiments' / name).write_bytes(contents)
    return destination


def historical_copy(source, destination):
    shutil.copytree(source, destination)
    for path in (destination / 'experiments').glob('*.edi'):
        path.write_bytes(historical_excluded_bytes('experiments/' + path.name, path.read_bytes()))
    return destination


def historical_input_hashes(source, *, excluded=False):
    result = REFERENCE.hashes(source, excluded=excluded)
    analysis = source / 'analysis/analysis.edi'
    if analysis.is_file():
        result['analysis/analysis.edi'] = hashlib.sha256(
            historical_fit_ids(source, analysis.read_bytes())
        ).hexdigest()
    return result


def observe_legacy_pin(source, destination, *, calculator=False, excluded=False):
    destination.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE.observe(source, destination, calculator=calculator)
    legacy = stored_id_bytes.ordinal_copy(
        source, destination, destination.with_name('ordinal-pin')
    )
    for path in (legacy / 'experiments').glob('*.edi'):
        path.write_bytes(historical_single_fraction('experiments/' + path.name, path.read_bytes()))
    analysis = legacy / 'analysis/analysis.edi'
    if analysis.is_file():
        analysis.write_bytes(
            historical_analysis(source, historical_fit_ids(source, analysis.read_bytes()))
        )
    if not calculator:
        record = legacy / 'project.edi'
        record.write_bytes(without_default_rule('project.edi', record.read_bytes()))
    return (
        REFERENCE.saved_hashes(legacy, excluded=excluded)
        if calculator
        else REFERENCE.hashes(legacy, excluded=excluded)
    )


#  projects postdate the immutable  pre-move source closure.
# Their serialization is checked by a second-save fixed point, never a rewritten old pin.
POLYNOMIAL_CASES = [
    'repo:docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project',
    'repo:docs/user/cli/pd-neut-tof_ferrite-austenite-beer_joint/project',
    'corpus:beer-ferrite-austenite/project',
    'corpus:yap-spodi-3k/project',
    'repo:docs/user/cli/pd-neut-cwl_yap-spodi_3k/project',
    'corpus:background-cecoal/project',
    'corpus:background-lab6/project',
    'corpus:background-pearl/project',
    'repo:docs/user/cli/pd-neut-cwl_lab6-11b-echidna_tch-fcj/project',
    'repo:docs/user/cli/pd-neut-tof_cecoal-polaris_chebyshev/project',
    'repo:docs/user/cli/pd-neut-tof_ceo2-pearl_polynomial/project',
]


# New relation data keeps its own fixed-point witness and never replaces an old pin.
RELATION_CASES = ['corpus:constraint-covariance/project']
FCJ_CASES = ['corpus:lab6-echidna-fcj/project']

# New CLI subjects retain all source bytes and the complete second-save fixed point;
# they do not replace or regenerate any historical serialization pin.
ADP_AND_SCAN_CASES = [
    'repo:docs/user/cli/pd-neut-cwl_y2o3_beta-adp/project',
    'repo:docs/user/cli/pd-neut-cwl_cosio-d20_scan-162f/project',
]


def test_saved_byte_inventory_covers_every_current_cli_and_corpus_project(tmp_path):
    # Before: all inputs existed before the move. After : preserve
    # every old witness, with separately labelled post-feature LiF pins.
    additions = {'corpus:lif-xray-s1/project'}
    if REFERENCE.PACKAGE == 'edi':
        additions.add('repo:docs/user/cli/pd-xray-cwl_lif_single/project')
    assert set(EXTENSION['cases']) == additions, '/ only new LiF projects use post-feature pins'
    assert additions.isdisjoint(BASELINE['cases']), (
        '/ no old byte witness is replaced by a post-feature pin'
    )
    assert set(NEW_FIXED_POINTS) == {
        'repo:docs/user/cli/pd-xray-cwl_latp_scan-4f/project',
        'repo:docs/user/cli/pd-xray-cwl_lif_single/project',
        'repo:docs/user/cli/pd-xray-cwl_pbso4-lab_round-robin/project',
    } | SINGLE_CRYSTAL_FIXED_POINTS | {'corpus:multiphase-scales/project'}, (
        'every declared extended or new X-ray input retains its separate complete byte witness'
    )
    assert set(NEW_FIXED_POINTS).isdisjoint(BASELINE['cases']), (
        'a new project invariant cannot replace any old serialization oracle'
    )
    assert set(REFERENCE.inputs()) == (
        set(BASELINE['cases'])
        | additions
        | set(POLYNOMIAL_CASES)
        | set(ADP_AND_SCAN_CASES)
        | set(FCJ_CASES)
        | set(NEW_FIXED_POINTS)
        | (set(RELATION_CASES) & set(REFERENCE.inputs()))
    ), (
        ' I22 every project must retain its pre-move byte witness, labelled '
        ' LiF pin or explicit  serialization fixed-point witness; '
        'or a declared relation/FCJ-corpus fixed point; no unknown project may be omitted'
    )
    expected_cases = {
        'corpus:cosio-d20-scan-3f/project',
        'corpus:ncaf-wish-3bank-s5/project',
        *(
            'repo:docs/user/cli/' + name + '/project'
            for name in (
                'pd-neut-cwl_cosio-d20_scan-3f',
                'pd-neut-cwl_cosio-d20_scan-324f',
                'pd-neut-tof_ncaf-wish-3bank_start-5',
                'pd-neut-tof_ncaf-wish-5bank_start-5',
                'pd-neut-tof_ncaf-wish-5bank_start-fullprof',
            )
        ),
    }
    assert set(RELATIONS['cases']) == expected_cases, (
        'the byte extension must apply only to the seven declared model changes'
    )
    # Closed-form controls for the only inherited-byte mapping, independent of
    # the engine. Both input and output must refuse a missing, duplicate,
    # unsupported, or additional calculator declaration.
    experiment = tmp_path / 'experiments/d20.edi'
    experiment.parent.mkdir()
    ordinary = b'data_d20\n\n_peak.broad_gauss_u 0.125\n'
    canonical = b'_calculator.type crysta\n\n'
    experiment.write_bytes(ordinary + canonical)
    expected = REFERENCE.hashes(tmp_path)
    experiment.write_bytes(ordinary + canonical.replace(b'crysta', b'cryspy'))
    legacy = REFERENCE.hashes(tmp_path)
    experiment.write_bytes(ordinary + canonical)
    assert REFERENCE.legacy_input_hashes(tmp_path, 'corpus:cosio-d20-s1/project') == legacy, (
        ' I22 the inherited seed mapping preserves every non-calculator input byte'
    )
    for declaration in (
        b'',
        canonical * 2,
        canonical.replace(b'crysta', b'other'),
        canonical + b'_calculator.extra 0.375\n',
    ):
        experiment.write_bytes(ordinary + declaration)
        with pytest.raises(AssertionError, match=' I22'):
            REFERENCE.legacy_input_hashes(tmp_path, 'corpus:cosio-d20-s1/project')
        with pytest.raises(AssertionError, match=' I22'):
            REFERENCE.saved_hashes(tmp_path)
    experiment.write_bytes(ordinary + canonical)
    assert REFERENCE.hashes(tmp_path) == expected, (
        ' I22 calculator controls restore their independent supported input'
    )
    experiment.write_bytes(ordinary)
    old_saved = REFERENCE.hashes(tmp_path)
    experiment.write_bytes(ordinary + canonical)
    assert REFERENCE.saved_hashes(tmp_path) == old_saved, (
        ' I22 removing the required calculator block preserves every old output byte'
    )
    record = tmp_path / 'project.edi'
    rule = b'_su_format.rule iucr_19\n'
    record.write_bytes(canonical + rule)
    assert (
        REFERENCE.saved_hashes(tmp_path)['project.edi'] == hashlib.sha256(canonical).hexdigest()
    ), 'I22 calculator-like bytes outside experiments survive the checked default IUCr declaration'
    for setting in (
        b'',
        rule * 2,
        rule.replace(b'iucr_19', b'iucr_99'),
        rule + b'_su_format.extra invalid\n',
    ):
        record.write_bytes(canonical + setting)
        with pytest.raises(AssertionError, match=r'IUCr|s\.u\.'):
            REFERENCE.saved_hashes(tmp_path)
    record.write_bytes(canonical + rule)
    experiment.write_bytes(ordinary.replace(b'0.125', b'0.126') + canonical)
    assert (
        REFERENCE.saved_hashes(tmp_path)['experiments/d20.edi'] != old_saved['experiments/d20.edi']
    ), ' I22 a non-calculator change still refuses the retained output oracle'
    check_excluded_transition()


def check_excluded_transition():
    d = 1.54 / (2 * math.sin(math.radians(15)))
    header = (
        b'_instrument.setup_wavelength 1.54\nloop_\n_data.two_theta\n'
        b'_data.d_spacing\n_data.intensity_meas\n_data.intensity_calc\n'
        b'_data.intensity_bkg\n_data.calc_status\n'
    )
    row = f'30 {d:.17g} 123 . . excl\n'.encode()
    included = b'31 2.9 124 125 126 incl\n'
    modern = header + row + included
    legacy = header + b'30 0. 123 0. 0. excl\n' + included
    assert historical_excluded_bytes('experiments/d20.edi', modern) == legacy, (
        'ADR-0096 historical comparison changes only the three authorized excluded tokens'
    )
    assert (
        historical_excluded_bytes(
            'experiments/d20.edi', current_excluded_bytes('experiments/d20.edi', legacy)
        )
        == legacy
    ), 'The copy-only current-input conversion retains the complete original byte pin'
    with pytest.raises(ValueError, match='Only old excluded zeros'):
        current_excluded_bytes(
            'experiments/d20.edi', legacy.replace(b'0. 0. excl', b'7.75 0. excl')
        )
    for damaged in (
        row.replace(f'{d:.17g}'.encode(), b'9.75'),
        row.replace(b'. . excl', b'0. . excl'),
    ):
        with pytest.raises(ValueError, match=r'conversion|dots'):
            historical_excluded_bytes('experiments/d20.edi', header + damaged + included)
    for damaged in (
        modern.replace(b'123', b'124'),
        modern.replace(b'125', b'127'),
        modern + b'# changed companion byte\n',
    ):
        assert historical_excluded_bytes('experiments/d20.edi', damaged) != legacy, (
            'The excluded-cell transition cannot mask measured, included or unrelated byte changes'
        )


@pytest.mark.parametrize('case', sorted(BASELINE['cases']))
def test_save_matches_the_labelled_pre_move_regression_pin(tmp_path, case):
    source = restored_source(REFERENCE.inputs()[case], tmp_path)
    expected = BASELINE['cases'][case]
    public_rows = json.loads(
        (ROOT / 'tests/fixtures/e04_t12_public_release/saved-metadata.json').read_text()
    )
    if case in public_rows:
        public = public_rows[case]
        assert public['prior_input_sha256'] == expected['input_sha256'], (
            'the public adaptation must retain every historical input pin'
        )
        assert public['prior_saved_sha256'] == expected['saved_sha256'], (
            'the public adaptation must prove all original saved bytes first'
        )
        expected = public
    # Before: no estimate category. After: exact manual/arpls category, with
    # every prior non-category byte and the complete input/output inventory retained.
    if case in estimate_bytes.CASES:
        expected = estimate_bytes.adapted_pin(
            expected, historical_copy(source, tmp_path / 'manual-input')
        )
    if case in RELATIONS['cases']:
        extension = RELATIONS['cases'][case]
        assert RELATIONS['claim'].startswith('REGRESSION PIN:'), (
            'engine-generated byte identities must explicitly declare a regression claim'
        )
        assert extension['before'] == expected, (
            'the declared model extension must preserve its immutable historical witness'
        )
        allowed = (
            {'analysis/analysis.edi', 'structures/cosio.edi'}
            if 'cosio' in case
            else {'structures/ncaf.edi'}
        )
        assert set(extension['allowed_files']) == allowed, (
            'the declared model extension may change only its relation or follower files'
        )
        for channel in ('input_sha256', 'saved_sha256'):
            after = extension['after_' + channel]
            assert set(after) == set(expected[channel]), (
                'a model extension must preserve the entire historical byte inventory'
            )
            assert all(
                after[name] == expected[channel][name] for name in after if name not in allowed
            ), 'a model extension must preserve every byte outside the declared changed files'
        expected = {
            'input_sha256': extension['after_input_sha256'],
            'saved_sha256': extension['after_saved_sha256'],
        }
        assert (
            retained_hashes(
                historical_input_hashes(source),
                historical_input_hashes(source, excluded=True),
                expected['input_sha256'],
            )
            == expected['input_sha256']
        ), 'the current model must match the explicitly labelled post-change regression pin'
        assert retained_hashes(
            observe_legacy_pin(source, tmp_path / 'saved', calculator=True),
            observe_legacy_pin(
                source, tmp_path / 'transition' / 'converted', calculator=True, excluded=True
            ),
            rounded_pins(expected['saved_sha256']),
        ) == rounded_pins(expected['saved_sha256']), (
            'the complete saved project must match the labelled model-change regression pin'
        )
        return
    if case == 'repo:docs/user/cli/pd-neut-cwl_pbso4_beba-asymmetry/project':
        first, second = tmp_path / 'first', tmp_path / 'second'
        once = REFERENCE.observe(source, first)
        assert REFERENCE.observe(first, second) == once, (
            'The replacement Npr5 PbSO4 model must reach a byte-exact save fixed point'
        )
        assert hasattr(
            __import__('edi').Project.load(first).experiments[0].peak, 'mixing_eta_0'
        ), 'The retired TCH plus asymmetry byte subject is replaced by the declared Npr5 model'
        return
    if case.startswith('repo:') and REFERENCE.hashes(source) != expected['input_sha256']:
        reviewed = json.loads(
            (ROOT / 'tests/fixtures/table_display/regression-inputs.json').read_text()
        )
        relative = case.removeprefix('repo:') + '/'
        expected_live = {
            name.removeprefix(relative): digest
            for name, digest in reviewed['files'].items()
            if name.startswith(relative)
        }
        assert expected_live, 'Every adapted input must have a committed reviewed byte witness'
        with zipfile.ZipFile(
            ROOT / 'tests/fixtures/table_display/regression-inputs.zip'
        ) as archive:
            for name, digest in expected_live.items():
                assert hashlib.sha256(archive.read(relative + name)).hexdigest() == digest, (
                    'Reviewed input bytes and the full inventory must retain the committed pin'
                )
        live_source = REFERENCE.inputs()[case]
        live_raw = {
            path.relative_to(live_source).as_posix(): hashlib.sha256(
                estimate_bytes.without_category(path.read_bytes())
                if case in estimate_bytes.CASES
                and path.relative_to(live_source).as_posix() == estimate_bytes.EXPERIMENT
                else metadata_bytes.pre_catalogue_bytes(path)
            ).hexdigest()
            for path in live_source.rglob('*')
            if path.is_file()
        }
        assert live_raw == expected_live, (
            'changed live example bytes must equal the complete reviewed pre-catalogue input, '
            'independently of the position of main'
        )
        source = REFERENCE.committed_input(
            ROOT / case.removeprefix('repo:'), tmp_path / 'pre-move'
        )
        if case in estimate_bytes.CASES:
            (source / estimate_bytes.EXPERIMENT).write_bytes(
                (live_source / estimate_bytes.EXPERIMENT).read_bytes()
            )
        source = current_source(source, tmp_path / 'history')
    assert (
        retained_hashes(
            REFERENCE.legacy_input_hashes(source, case),
            REFERENCE.legacy_input_hashes(source, case, excluded=True),
            expected['input_sha256'],
        )
        == expected['input_sha256']
    ), ' I22 the storage move cannot alter inputs to hide a serialization regression'
    assert retained_hashes(
        observe_legacy_pin(source, tmp_path / 'saved', calculator=True),
        observe_legacy_pin(
            source, tmp_path / 'transition' / 'converted', calculator=True, excluded=True
        ),
        rounded_pins(expected['saved_sha256']),
    ) == rounded_pins(expected['saved_sha256']), (
        ' I22 save must retain the pre-move bytes of every file in this project'
    )
    if case in estimate_bytes.CASES:
        estimate_bytes.require_saved(
            historical_copy(tmp_path / 'saved', tmp_path / 'manual-output'),
            BASELINE['cases'][case]['saved_sha256'][estimate_bytes.EXPERIMENT],
            expected['saved_sha256'][estimate_bytes.EXPERIMENT],
        )


@pytest.mark.parametrize('case', sorted(EXTENSION['cases']))
def test_new_lif_project_matches_labelled_post_feature_byte_pin(tmp_path, case):
    inputs = REFERENCE.inputs()
    if case in NEW_FIXED_POINTS:
        require_current_input(case, inputs[case])
        # The original corpus and CLI LiF subjects have identical complete pins.
        # Replay that retained input while testing the extended CLI input separately.
        original = 'corpus:lif-xray-s1/project'
        assert (
            EXTENSION['cases'][case]['input_sha256']
            == EXTENSION['cases'][original]['input_sha256']
        ), 'the retained LiF replay must match every original CLI input byte'
        source = restored_source(inputs[original], tmp_path)
    else:
        source = restored_source(inputs[case], tmp_path)
    expected = EXTENSION['cases'][case]
    assert REFERENCE.hashes(source) == expected['input_sha256'], (
        ' post-feature regression pin retains all input bytes and measured files'
    )
    assert observe_legacy_pin(source, tmp_path / 'saved') == rounded_pins(
        expected['saved_sha256']
    ), ' post-feature serialization regression pin retains the full saved inventory and bytes'


@pytest.mark.parametrize('damage', ['value', 'row-order', 'missing', 'extra', 'data'])
def test_byte_witness_observes_value_order_inventory_and_measured_files(tmp_path, damage):
    project = tmp_path / 'project'
    project.mkdir()
    model = project / 'project.edi'
    model.write_bytes(b'data_sample\nloop_\n_atom_site.id\n_atom_site.fract_x\na 0.125\nb 0.375\n')
    data = project / 'measured.dat'
    data.write_bytes(b'12.5 31.25 0.75\n13.75 44.5 1.25\n')
    expected = REFERENCE.hashes(project)
    assert set(expected) == {'project.edi', 'measured.dat'}, (
        ' I22 data files belong to the byte witness, not just model metadata'
    )
    if damage == 'value':
        model.write_bytes(model.read_bytes().replace(b'0.125', b'0.126'))
    elif damage == 'row-order':
        model.write_bytes(model.read_bytes().replace(b'a 0.125\nb 0.375', b'b 0.375\na 0.125'))
    elif damage == 'missing':
        model.unlink()
    elif damage == 'extra':
        (project / 'unexpected.edi').write_bytes(b'data_unexpected\n')
    else:
        data.write_bytes(data.read_bytes().replace(b'31.25', b'31.26'))
    assert REFERENCE.hashes(project) != expected, (
        ' I22 a changed value, row order, file inventory or measured byte must be visible'
    )


def require_current_input(case, source):
    assert REFERENCE.hashes(source) == NEW_FIXED_POINTS[case]['input_sha256'], (
        'the current fixed-point witness retains the complete independently recorded input bytes'
    )


@pytest.mark.parametrize('damage', ['value', 'row-order', 'missing', 'extra', 'data'])
def test_extended_lif_input_cannot_escape_its_complete_byte_witness(tmp_path, monkeypatch, damage):
    case = 'repo:docs/user/cli/pd-xray-cwl_lif_single/project'
    inputs = REFERENCE.inputs()
    require_current_input(case, inputs[case])
    changed = tmp_path / 'changed'
    shutil.copytree(inputs[case], changed)
    experiment = changed / 'experiments/cu_ka.edi'
    text = experiment.read_text()
    if damage == 'value':
        experiment.write_text(
            text.replace(
                '_instrument.setup_wavelength_2 1.5444', '_instrument.setup_wavelength_2 1.5451', 1
            )
        )
    elif damage == 'row-order':
        experiment.write_text(text.replace('10 1 0 1\n10.025 2 0 1', '10.025 2 0 1\n10 1 0 1', 1))
    elif damage == 'missing':
        experiment.unlink()
    elif damage == 'extra':
        (changed / 'unexpected.dat').write_text('12.5 31.25 0.75\n')
    else:
        experiment.write_text(text.replace('10.025 2 0 1', '10.025 2 0.375 1', 1))
    assert REFERENCE.hashes(changed) != REFERENCE.hashes(inputs[case]), (
        'each current-input escape must change real scientific or inventory bytes'
    )
    monkeypatch.setattr(REFERENCE, 'inputs', lambda: {**inputs, case: changed})
    with pytest.raises(AssertionError, match='current fixed-point witness'):
        test_new_lif_project_matches_labelled_post_feature_byte_pin(tmp_path / 'replay', case)
    with pytest.raises(AssertionError, match='current fixed-point witness'):
        test_c13_t6_new_projects_have_a_second_save_fixed_point(tmp_path / 'fixed-point', case)


@pytest.mark.parametrize(
    'case',
    POLYNOMIAL_CASES + RELATION_CASES + ADP_AND_SCAN_CASES + sorted(NEW_FIXED_POINTS) + FCJ_CASES,
)
def test_c13_t6_new_projects_have_a_second_save_fixed_point(tmp_path, case):
    inputs = REFERENCE.inputs()
    assert case in inputs, ' every new declared project needs its serialization witness'
    before = REFERENCE.hashes(inputs[case])
    if case in NEW_FIXED_POINTS:
        retained = (
            restored_source(inputs[case], tmp_path)
            if case == 'repo:docs/user/cli/pd-xray-cwl_latp_scan-4f/project'
            else inputs[case]
        )
        require_current_input(case, retained)
    first = tmp_path / 'first'
    second = tmp_path / 'second'
    once = REFERENCE.observe(inputs[case], first)
    twice = REFERENCE.observe(first, second)
    assert once == twice, (
        ' canonical serialization must reach a byte-exact fixed point on the second save'
    )
    assert REFERENCE.hashes(inputs[case]) == before, (
        ' saving the new projects must preserve every source model and measured-data byte'
    )


def test_c34_t28_live_main_provenance_cannot_hide_changed_scientific_input(tmp_path, monkeypatch):
    case = 'repo:docs/user/cli/pd-neut-cwl_cosio-d20_start-4/project'
    source = REFERENCE.inputs()[case]
    # The main boundary must reach the live tree before any historical metadata projection.
    test_save_matches_the_labelled_pre_move_regression_pin(tmp_path / 'ordinary', case)
    changed = tmp_path / 'changed-input'
    shutil.copytree(source, changed)
    structure = changed / 'structures/cosio.edi'
    text = structure.read_text()
    line = next(line for line in text.splitlines() if line.startswith('_cell.length_a'))
    structure.write_text(text.replace(line, '_cell.length_a 12.375', 1))
    assert structure.read_text() != text, (
        'I22 the provenance escape must really alter a scientific input before saving'
    )
    monkeypatch.setattr(REFERENCE, 'inputs', lambda: {case: changed})
    with pytest.raises(AssertionError, match='changed live example bytes'):
        test_save_matches_the_labelled_pre_move_regression_pin(tmp_path / 'damaged', case)


@pytest.mark.parametrize('damage', ['mode', 'method', 'missing', 'duplicate', 'extra', 'value'])
def test_manual_estimate_byte_extension_refuses_rebanked_unrelated_changes(damage):
    before = b'data_hrpt\n\n_background.intensity 37.125\n'
    after = before + estimate_bytes.BLOCK
    old_hash = hashlib.sha256(before).hexdigest()
    estimate_bytes.require_bytes(after, old_hash, hashlib.sha256(after).hexdigest())
    if damage == 'mode':
        after = after.replace(b'manual', b'auto')
    elif damage == 'method':
        after = after.replace(b'arpls', b'snip')
    elif damage == 'missing':
        after = after.replace(b'_background_estimate.method arpls\n', b'')
    elif damage == 'duplicate':
        after += estimate_bytes.BLOCK
    elif damage == 'extra':
        after += b'_background_estimate.width 3.125\n'
    else:
        after = after.replace(b'37.125', b'37.126')
    with pytest.raises(AssertionError, match='manual estimate'):
        estimate_bytes.require_bytes(after, old_hash, hashlib.sha256(after).hexdigest())
