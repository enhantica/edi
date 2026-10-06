"""gate 5: retain the immutable pre-move byte pins.

Before : raw corpus inputs and saved bytes equalled the old hashes.
After inherited main cf5d5253: reverse only the six declared seed changes,
check/remove exactly one canonical calculator block per saved experiment,
and compare every other byte and the full file inventory to the same pins.
"""

import importlib.util
import json
from pathlib import Path

import pytest

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

#  projects postdate the immutable  pre-move source closure.
# Their serialization is checked by a second-save fixed point, never a rewritten old pin.
POLYNOMIAL_CASES = [
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
    assert set(REFERENCE.inputs()) == (
        set(BASELINE['cases'])
        | additions
        | set(POLYNOMIAL_CASES)
        | (set(RELATION_CASES) & set(REFERENCE.inputs()))
    ), (
        ' I22 every project must retain its pre-move byte witness, labelled '
        ' LiF pin or explicit  serialization fixed-point witness; '
        'or a declared relation-corpus fixed point; no unknown project may be omitted'
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
    (tmp_path / 'project.edi').write_bytes(canonical)
    assert (
        REFERENCE.saved_hashes(tmp_path)['project.edi']
        == REFERENCE.hashes(tmp_path)['project.edi']
    ), ' I22 calculator-like bytes outside experiments are never masked'
    experiment.write_bytes(ordinary.replace(b'0.125', b'0.126') + canonical)
    assert (
        REFERENCE.saved_hashes(tmp_path)['experiments/d20.edi'] != old_saved['experiments/d20.edi']
    ), ' I22 a non-calculator change still refuses the retained output oracle'


@pytest.mark.parametrize('case', sorted(BASELINE['cases']))
def test_save_matches_the_labelled_pre_move_regression_pin(tmp_path, case):
    source = REFERENCE.inputs()[case]
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
        assert REFERENCE.hashes(source) == expected['input_sha256'], (
            'the current model must match the explicitly labelled post-change regression pin'
        )
        assert (
            REFERENCE.observe(source, tmp_path / 'saved', calculator=True)
            == expected['saved_sha256']
        ), 'the complete saved project must match the labelled model-change regression pin'
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
        # Main's independently merged example edits cannot rewrite a storage
        # regression pin. Check their provenance and still save the old input.
        main = REFERENCE.committed_input(source, tmp_path / 'main', 'origin/main')
        live_hashes, main_hashes = REFERENCE.hashes(source), REFERENCE.hashes(main)
        metadata = json.loads(
            (ROOT / 'tests/fixtures/e04_t12_public_release/project-metadata.json').read_text()
        )
        assert live_hashes.keys() == main_hashes.keys(), (
            'public metadata adaptation must retain the entire main project inventory'
        )
        for name, digest in live_hashes.items():
            if digest == main_hashes[name]:
                continue
            adaptation = metadata.get((source / name).relative_to(ROOT).as_posix(), {})
            assert (
                adaptation.get('after_sha256') == digest
                and adaptation.get('before_sha256') == main_hashes[name]
            ), (
                'changed live example bytes must equal the exact reviewed descriptive '
                'adaptation of independently merged main'
            )
        source = REFERENCE.committed_input(source, tmp_path / 'pre-move')
    assert REFERENCE.legacy_input_hashes(source, case) == expected['input_sha256'], (
        ' I22 the storage move cannot alter inputs to hide a serialization regression'
    )
    assert (
        REFERENCE.observe(source, tmp_path / 'saved', calculator=True) == expected['saved_sha256']
    ), ' I22 save must retain the pre-move bytes of every file in this project'


@pytest.mark.parametrize('case', sorted(EXTENSION['cases']))
def test_new_lif_project_matches_labelled_post_feature_byte_pin(tmp_path, case):
    source = REFERENCE.inputs()[case]
    expected = EXTENSION['cases'][case]
    assert REFERENCE.hashes(source) == expected['input_sha256'], (
        ' post-feature regression pin retains all input bytes and measured files'
    )
    assert REFERENCE.observe(source, tmp_path / 'saved') == expected['saved_sha256'], (
        ' post-feature serialization regression pin retains the full saved inventory and bytes'
    )


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


@pytest.mark.parametrize('case', POLYNOMIAL_CASES + RELATION_CASES)
def test_c13_t6_new_projects_have_a_second_save_fixed_point(tmp_path, case):
    inputs = REFERENCE.inputs()
    assert case in inputs, ' every new declared project needs its serialization witness'
    before = REFERENCE.hashes(inputs[case])
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
