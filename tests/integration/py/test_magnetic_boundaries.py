"""Admission cannot be bypassed by a CLI, a binding edit or a save."""

import subprocess
import sys

import edi as api
import numpy as np
import pytest

from tests.conftest import corpus_case_dir
from tests.fixtures.magnetic_pnma import commensurate as cases
from tests.fixtures.magnetic_pnma import reference as ref


def corpus_variant(root, structure):
    """A bounded magnetic admission variant of the pinned CoSiO D20 corpus data."""
    source = corpus_case_dir('cosio-d20-s4') / 'project'
    experiment = (source / 'experiments/d20.edi').read_text()
    # Freeze the nuclear experiment recipe; only explicitly chosen boundary parameters vary.
    experiment = experiment.replace('()', '')
    ref.project(root, structure, experiment)
    (root / 'analysis').mkdir()
    (root / 'analysis/analysis.edi').write_text(
        '_edi.schema_version 3\n_minimizer.type crysta\n_minimizer.max_iterations 1\n'
    )
    return root


@pytest.mark.parametrize('spelling', ['1/2,0,0', '0.5,0,0'])
def test_cli_accepts_equivalent_exact_and_decimal_commensurate_controls(tmp_path, spelling):
    root = ref.project(tmp_path / 'input', cases.structure(period=22, vectors=(spelling,)))
    command = [sys.executable, '-m', 'edi', 'calc', str(root), '--dry']
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
    assert result.returncode == 0, (
        'The CLI admits both exact and decimal valid controls through magnetic validation: '
        + result.stdout
        + result.stderr
    )


@pytest.mark.parametrize('case', sorted(cases.INVALID))
def test_cli_refuses_invalid_magnetic_input_before_calculation(tmp_path, case):
    root = ref.project(tmp_path / 'input', cases.structure(**cases.INVALID[case]))
    command = [sys.executable, '-m', 'edi', 'calc', str(root), '--dry']
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
    assert result.returncode != 0, 'The CLI applies the same magnetic admission rule as load'
    assert any(
        word in (result.stdout + result.stderr).lower()
        for word in [
            'magnetic',
            'propagation',
            'translation',
            'centring',
            'centering',
            'duplicate',
            'metric',
            'theta',
            'identity',
            'closed',
        ]
    ), 'The CLI refusal names the magnetic rule rather than a command syntax failure'
    assert not (root / 'analysis/results.csv').exists(), (
        'A refused magnetic input cannot persist a calculation or fit record'
    )


@pytest.mark.parametrize('case', sorted(cases.VALID))
def test_magnetic_cif_handoff_retains_admitted_propagation_rows(tmp_path, case):
    text = cases.magnetic_cif(cases.structure(**cases.VALID[case]))
    model = api.Project.load(ref.project(tmp_path / 'input', text))
    model.save_as(tmp_path / 'saved')
    saved = ref.columns((tmp_path / 'saved/structures/cosio.edi').read_text())
    assert '_parent_propagation_vector.kxkykz' in saved, (
        'The magCIF handoff admits exact commensurate characters and retains their rows'
    )


@pytest.mark.parametrize('case', sorted(cases.INVALID))
def test_magnetic_cif_handoff_refuses_the_same_invalid_characters(tmp_path, case):
    text = cases.magnetic_cif(cases.structure(**cases.INVALID[case]))
    with pytest.raises(
        (ValueError, RuntimeError),
        match=r'(?i)magnetic|propagation|translation|centring|centering|duplicate|metric|identity|closed|theta',
    ):
        api.Project.load(ref.project(tmp_path / 'input', text))


def test_operator_replacement_refuses_atomically_with_warm_caches(tmp_path):
    text = cases.structure(**cases.VALID['anti-translation-in-centring'])
    model = api.Project.load(ref.project(tmp_path / 'input', text))
    model.analysis.calculate()
    before = np.asarray(model.experiment.data.intensity_calc).copy()
    model.save_as(tmp_path / 'before')
    replace = getattr(model.structure, 'set_magnetic_symmetry', None)
    assert callable(replace), 'Both bindings expose validated operator replacement'
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)propagation|translation|character'):
        replace(['x,y,z,+1'], ['x,y,z,+1', 'x+1/2,y,z,+1'])
    model.analysis.calculate()
    assert np.array_equal(before, model.experiment.data.intensity_calc), (
        'A refused operator replacement preserves the previously warmed calculation'
    )
    model.save_as(tmp_path / 'after')
    old = ref.columns((tmp_path / 'before/structures/cosio.edi').read_text())
    new = ref.columns((tmp_path / 'after/structures/cosio.edi').read_text())
    for key, values in old.items():
        if key.startswith(('_parent_', '_space_group_symop_magn', '_refln.')):
            assert new.get(key) == values, (
                'Refusal preserves operators and exact propagation rows on save'
            )


def test_free_cell_and_metric_dependent_moment_fit_refuses_before_trials(tmp_path):
    text = cases.structure(b=4, gamma=60, operations=('x,y,z,+1', 'x+y,-y,z,+1'), moment='-.5 1 0')
    text = text.replace('_parent_space_group.derived false', '_parent_space_group.derived true')
    model = api.Project.load(corpus_variant(tmp_path / 'input', text))
    model.structure.cell.length_b.free = True
    model.structure.atom_site_moment['A'].crystalaxis_y.free = True
    with pytest.raises((ValueError, RuntimeError), match=r'(?i)metric|cell.*moment|moment.*cell'):
        model.analysis.fit()
    assert model.structure.cell.length_b.value == 4, (
        'The unsupported coupled cell and moment fit refuses before changing the cell'
    )


def test_binding_k_edit_refuses_without_mutating_the_warm_model(tmp_path):
    text = cases.structure(**cases.VALID['anti-translation-in-centring'])
    model = api.Project.load(ref.project(tmp_path / 'input', text))
    model.analysis.calculate()
    assert hasattr(model.structure, 'parent_propagation_vector'), (
        'Each binding exposes the validated keyed propagation rows'
    )
    vector = model.structure.parent_propagation_vector['1']
    before = vector.kxkykz
    profile = np.asarray(model.experiment.data.intensity_calc).copy()
    with pytest.raises(
        (ValueError, RuntimeError), match=r'(?i)propagation|translation|commensurate'
    ):
        vector.kxkykz = '1/3,0,0'
    assert vector.kxkykz == before, 'A refused k edit preserves its original exact row'
    model.analysis.calculate()
    assert np.array_equal(profile, model.experiment.data.intensity_calc), (
        'A refused propagation edit leaves the warmed reflection and value caches consistent'
    )


def test_post_fit_model_saves_and_reloads_its_validated_propagation(tmp_path):
    root = corpus_variant(
        tmp_path / 'input', cases.structure(**cases.VALID['anti-translation-in-centring'])
    )
    model = api.Project.load(root)
    model.structure.atom_site_moment['A'].crystalaxis_y.free = True
    # One bounded trial checks admission and persistence, never a fit-accuracy oracle.
    model.analysis.fit()
    model.analysis.calculate()
    profile = np.asarray(model.experiment.data.intensity_calc).copy()
    model.save_as(tmp_path / 'saved')
    restored = api.Project.load(tmp_path / 'saved')
    restored.analysis.calculate()
    assert np.array_equal(profile, restored.experiment.data.intensity_calc), (
        'A post-fit magnetic model is admitted unchanged by its save and reload boundaries'
    )
    columns = ref.columns((tmp_path / 'saved/structures/cosio.edi').read_text())
    assert columns['_parent_propagation_vector.kxkykz'] in [['1/2,0,0'], ['0.5,0,0']], (
        'A fit cannot drop or alter the admitted half-order propagation vector'
    )


def test_fullprof_dead_cell_mask_uses_its_own_printed_point_list():
    lines = (ref.ROOT / 'cosio/cosio.prf').read_text().splitlines()
    begin = next(i for i, line in enumerate(lines) if line.startswith(' 2Theta')) + 1
    grid = np.array([float(line.split()[0]) for line in lines[begin : begin + 1508]])
    bands = [[float(value) for value in line.split()] for line in lines[3:6]]
    mask = np.ones(len(grid), dtype=bool)
    # FullProf's reported rule drops the point immediately preceding each excluded interval.
    for lower, upper in bands:
        start = max(0, int(np.searchsorted(grid, lower)) - 1)
        stop = int(np.searchsorted(grid, upper))
        mask[start:stop] = False
    for angle, expected in [(64.5953, True), (64.6953, False), (64.7953, True)]:
        index = np.flatnonzero(np.abs(grid - angle) < 1e-5)
        assert len(index) == 1, 'Each detector control exists in FullProf own printed point list'
        assert bool(mask[index[0]]) is expected, (
            'The FullProf reference excludes just the dead detector cell and keeps its neighbours'
        )


@pytest.mark.parametrize('route', ['native', 'magcif'])
@pytest.mark.parametrize('unsupported', ['superspace', 'irrational'])
def test_modulated_or_incommensurate_input_refuses_by_name(tmp_path, route, unsupported):
    text = cases.structure()
    if unsupported == 'superspace':
        text += '\n_space_group_magn.ssg_name "P1(0b0)0"\n'
        reason = r'(?i)superspace|ssg|modulat'
    else:
        # Irrational sqrt(2)/10 at eleven decimal places cannot be a child-lattice character.
        text = cases.structure(vectors=('0.14142135624,0,0',))
        reason = r'(?i)incommensurate|propagation|translation|rational|commensurate'
    if route == 'magcif':
        text = cases.magnetic_cif(text)
    with pytest.raises((ValueError, RuntimeError), match=reason):
        api.Project.load(ref.project(tmp_path / 'input', text))


@pytest.mark.parametrize('route', ['native', 'magcif'])
def test_strained_parent_with_half_order_character_is_admitted(tmp_path, route):
    text = cases.structure(
        period=2,
        parent='P 4',
        parent_number=75,
        vectors=('1/2,0,0',),
        centrings=('x,y,z,+1', 'x+1/2,y,z,-1'),
    )
    if route == 'magcif':
        text = cases.magnetic_cif(text)
    model = api.Project.load(ref.project(tmp_path / 'input', text))
    model.save_as(tmp_path / 'saved')
    saved = ref.columns((tmp_path / 'saved/structures/cosio.edi').read_text())
    assert saved['_parent_propagation_vector.kxkykz'] in [['1/2,0,0'], ['0.5,0,0']], (
        'A strained declared tetragonal parent does not refuse a valid half-order child'
    )
    assert [float(saved['_cell.length_' + axis][0]) for axis in 'ab'] == [8, 5], (
        'Import retains the observed strained child metric rather than projecting onto the parent'
    )
