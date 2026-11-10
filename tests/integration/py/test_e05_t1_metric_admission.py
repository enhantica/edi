""": positive wavelength and representable metric at every entrance.

Independent witnesses: for an orthogonal cell V=abc and G*ii=1/li**2.
IEEE doubles overflow V at 1e200 cubed, underflow it at 1e-200 cubed,
and overflow G*aa for a=1e-200 even when V remains positive and finite.
Factory spelling conversion comes from the independently declared CIF aliases.
"""

import re
import warnings

import edi as model
import pytest
from test_c13_t12_loop_identity import _cif  # noqa: PLC2701 -- shared independent alias fixture
from test_e05_t1_physical_domain import (
    _input,  # noqa: PLC2701 -- retained LiF fixture
    _use,  # noqa: PLC2701 -- actual public consumers
)

OPERATIONS = ('load', 'calculate', 'fit', 'save')
METRICS = [
    ('volume-overflow', ('1e200', '1e200', '1e200'), ('90', '90', '90')),
    ('volume-underflow', ('1e-200', '1e-200', '1e-200'), ('90', '90', '90')),
    ('reciprocal-overflow-a', ('1e-200', '4', '4'), ('90', '90', '90')),
    ('reciprocal-overflow-b', ('4', '1e-200', '4'), ('90', '90', '90')),
    ('reciprocal-overflow-c', ('4', '4', '1e-200'), ('90', '90', '90')),
    ('zero-length', ('0', '4', '4'), ('90', '90', '90')),
    ('impossible-angles', ('4', '4', '4'), ('10', '10', '170')),
]
CASES = [(name, lengths, angles, None) for name, lengths, angles in METRICS] + [
    ('zero-wavelength', None, None, '0'),
    ('negative-wavelength', None, None, '-1'),
]


def _source(path, lengths=None, angles=None, wavelength=None):
    source = _input(path, 'triclinic')
    structure_path = source / 'structures/lif.edi'
    structure = structure_path.read_text()
    for names, values in (
        (('length_a', 'length_b', 'length_c'), lengths),
        (('angle_alpha', 'angle_beta', 'angle_gamma'), angles),
    ):
        if values is not None:
            for name, token in zip(names, values, strict=True):
                structure = re.sub(rf'(?m)^_cell\.{name} .+$', f'_cell.{name} {token}', structure)
    structure_path.write_text(structure)
    experiment_path = source / 'experiments/cu_ka.edi'
    experiment = experiment_path.read_text().replace('sasaki1989', 'none')
    if wavelength is not None:
        experiment = re.sub(
            r'(?m)^_instrument\.setup_wavelength .+$',
            f'_instrument.setup_wavelength {wavelength}',
            experiment,
        )
    experiment_path.write_text(experiment)
    return source


def _install_geometry(project, structure):
    # Classic CIF factories expose the metric but no public EDI identity setter.
    # Install that exact metric into the already named LiF consumer vehicle.
    for field in ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma'):
        getattr(project.structure.cell, field).value = getattr(structure.cell, field).value


def _continue(project, operation, destination):
    if operation == 'fit':
        result = project.analysis.fit()
        assert result is not None, ' valid geometry must reach the actual fit entry'
        return None
    if operation != 'save':
        return _use(project, operation, destination)
    # Classic CIF can omit the optional texture row. Compare the physical
    # payload under test rather than assuming that EDI-only row exists.
    fields = ('length_a', 'length_b', 'length_c', 'angle_alpha', 'angle_beta', 'angle_gamma')
    expected = tuple(getattr(project.structure.cell, field).value for field in fields)
    wavelength = project.experiments[0].instrument.setup_wavelength.value
    project.save_as(destination)
    restored = model.Project.load(destination)
    actual = tuple(getattr(restored.structure.cell, field).value for field in fields)
    assert actual == pytest.approx(expected, rel=0, abs=0), (
        ' admissible factory geometry must survive save/reload exactly'
    )
    assert restored.experiments[0].instrument.setup_wavelength.value == pytest.approx(
        wavelength, rel=0, abs=0
    ), ' admissible factory wavelength must survive save/reload exactly'
    return None


def _snapshot(path):
    return {p.relative_to(path): p.read_bytes() for p in path.rglob('*') if p.is_file()}


def _factory(source, spelling, entrance):
    text = (source / 'structures/lif.edi').read_text()
    if spelling == 'cif':
        text = _cif(text, 'structure')
    if entrance == 'text':
        return model.StructureFactory.from_cif_str(text)
    path = source / ('factory-input.' + spelling)
    path.write_text(text)
    return model.StructureFactory.from_cif_path(path)


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize(
    ('_name', 'lengths', 'angles', 'wavelength'), CASES, ids=[item[0] for item in CASES]
)
def test_f13_directory_refuses_before_each_continuation(
    tmp_path, _name, lengths, angles, wavelength, operation
):
    source = _source(tmp_path / 'source', lengths, angles, wavelength)
    before = _snapshot(source)
    stages = []

    def attempt():
        project = model.Project.load(source)
        stages.append('loaded')
        _continue(project, operation, tmp_path / 'output')

    with pytest.raises(model.ValidationError) as caught:
        attempt()
    assert not stages, ' invalid metric/wavelength must refuse at load before use'
    assert caught.value.diagnostics, ' directory refusal must carry diagnostics'
    assert any(str(d.severity).lower().endswith('error') for d in caught.value.diagnostics), (
        ' physical-domain refusal must be error severity, never editing warning'
    )
    assert _snapshot(source) == before, ' load refusal must preserve every input byte'
    assert not (tmp_path / 'output').exists(), ' refused load must publish no output'


@pytest.mark.parametrize(('_name', 'lengths', 'angles'), METRICS, ids=[m[0] for m in METRICS])
@pytest.mark.parametrize('spelling', ['edi', 'cif'])
@pytest.mark.parametrize('entrance', ['text', 'path'])
@pytest.mark.parametrize('operation', OPERATIONS)
def test_f13_factory_refuses_before_project_continuation(
    tmp_path, _name, lengths, angles, spelling, entrance, operation
):
    source = _source(tmp_path / 'source', lengths, angles)
    stages = []

    def attempt():
        structure = _factory(source, spelling, entrance)
        stages.append('constructed')
        project = model.Project.load(_source(tmp_path / 'valid'))
        _install_geometry(project, structure)
        _continue(project, operation, tmp_path / 'output')

    with pytest.raises((ValueError, RuntimeError)):
        attempt()
    assert not stages, ' every factory spelling/entrance must refuse before construction'
    assert not (tmp_path / 'output').exists(), ' refused factory must publish no output'


@pytest.mark.parametrize('operation', ['calculate', 'fit', 'save'])
@pytest.mark.parametrize(
    ('_name', 'lengths', 'angles', 'wavelength'), CASES, ids=[item[0] for item in CASES]
)
def test_f13_direct_mutation_cannot_publish_unusable_state(
    tmp_path, _name, lengths, angles, wavelength, operation
):
    project = model.Project.load(_source(tmp_path / 'valid'))

    def attempt():
        for names, values in (
            (('length_a', 'length_b', 'length_c'), lengths),
            (('angle_alpha', 'angle_beta', 'angle_gamma'), angles),
        ):
            if values is not None:
                for field, token in zip(names, values, strict=True):
                    getattr(project.structure.cell, field).value = float(token)
        if wavelength is not None:
            project.experiments[0].instrument.setup_wavelength.value = float(wavelength)
        _continue(project, operation, tmp_path / 'output')

    with pytest.raises((ValueError, RuntimeError, TypeError)):
        attempt()
    assert not (tmp_path / 'output').exists(), ' direct mutation must publish no bad save'


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('spelling', ['edi', 'cif'])
@pytest.mark.parametrize('entrance', ['text', 'path'])
def test_f13_factory_admits_nonidentity_valid_geometry(tmp_path, spelling, entrance, operation):
    source = _source(tmp_path / 'source', ('4.25', '5.5', '6.75'), ('81', '97', '112'))
    structure = _factory(source, spelling, entrance)
    assert tuple(getattr(structure.cell, 'length_' + a).value for a in 'abc') == (
        4.25,
        5.5,
        6.75,
    ), ' valid factory geometry must retain exact independent lengths'
    assert tuple(
        getattr(structure.cell, 'angle_' + a).value for a in ('alpha', 'beta', 'gamma')
    ) == (81, 97, 112), ' valid factory geometry must retain exact independent angles'

    project = model.Project.load(_source(tmp_path / 'valid'))
    _install_geometry(project, structure)
    _continue(project, operation, tmp_path / 'output')


@pytest.mark.parametrize('wavelength', ['0', '-1'])
@pytest.mark.parametrize('spelling', ['edi', 'cif'])
@pytest.mark.parametrize('entrance', ['text', 'path'])
def test_f13_experiment_factory_refuses_nonpositive_wavelength(
    tmp_path, wavelength, spelling, entrance
):
    source = _source(tmp_path / 'source', wavelength=wavelength)
    text = (source / 'experiments/cu_ka.edi').read_text()
    if spelling == 'cif':
        text = _cif(text, 'experiment')
    path = source / ('experiment-input.' + spelling)
    path.write_text(text)
    before = path.read_bytes()
    action = (
        model.ExperimentFactory.from_cif_str
        if entrance == 'text'
        else model.ExperimentFactory.from_cif_path
    )
    with pytest.raises((ValueError, RuntimeError)):
        action(text if entrance == 'text' else path)
    assert path.read_bytes() == before, ' factory refusal must retain wavelength input bytes'


@pytest.mark.parametrize('operation', OPERATIONS)
def test_f13_valid_beyond_edi_editing_ceiling_survives(tmp_path, capfd, operation):
    # Edi declares a 30 A editing ceiling; crysta declares no scalar ceiling.
    # This orthogonal cell has V=31.25*1.25*1.25 and finite G*ii=1/li**2.
    source = _source(tmp_path / 'source', ('31.25', '1.25', '1.25'), ('90', '90', '90'))
    before = _snapshot(source)
    capfd.readouterr()
    with warnings.catch_warnings(record=True) as received:
        warnings.simplefilter('always')
        project = model.Project.load(source)
    emitted = capfd.readouterr()
    evidence = '\n'.join(str(w.message) for w in received) + emitted.out + emitted.err
    if model.__name__ == 'edi':
        assert 'length_a' in evidence, ' load warning must identify the cell length'
        assert 'outside' in evidence.lower(), (
            ' valid beyond-editing-range cell must retain its load warning'
        )
    assert project.structure.cell.length_a.value == pytest.approx(31.25, rel=0, abs=0), (
        ' editing ceiling must never replace physical representability'
    )
    assert _snapshot(source) == before, ' warned load must preserve exact input bytes'
    _continue(project, operation, tmp_path / 'output')
    if operation == 'save':
        restored = model.Project.load(tmp_path / 'output')
        assert restored.structure.cell.length_a.value == pytest.approx(31.25, rel=0, abs=0), (
            ' save/reload must retain the exact valid beyond-range length'
        )


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('spelling', ['edi', 'cif'])
@pytest.mark.parametrize('entrance', ['text', 'path'])
def test_f13_experiment_factory_positive_control_reaches_consumers(
    tmp_path, spelling, entrance, operation
):
    source = _source(tmp_path / 'source', wavelength='1.375')
    text = (source / 'experiments/cu_ka.edi').read_text()
    if spelling == 'cif':
        text = _cif(text, 'experiment')
    if entrance == 'text':
        experiment = model.ExperimentFactory.from_cif_str(text)
    else:
        path = source / ('experiment-input.' + spelling)
        path.write_text(text)
        experiment = model.ExperimentFactory.from_cif_path(path)
    assert experiment.instrument.setup_wavelength.value == pytest.approx(1.375, rel=0, abs=0), (
        ' each experiment factory must admit a positive nonidentity wavelength exactly'
    )
    project = model.Project.load(source)
    project.experiment = experiment
    _continue(project, operation, tmp_path / 'output')
    if operation == 'save':
        restored = model.Project.load(tmp_path / 'output')
        assert restored.experiments[0].instrument.setup_wavelength.value == pytest.approx(
            1.375, rel=0, abs=0
        ), ' the factory wavelength must survive save/reload without clamping'
