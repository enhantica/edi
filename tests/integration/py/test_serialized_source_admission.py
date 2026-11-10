"""Every public serialized experiment entry admits exactly one declared data source."""

import importlib
import warnings

import pytest

from tests.fixtures import cif_import_cases as case
from tests.fixtures import serialized_sources as source

ROUTES = source.ROUTES if case.API == 'edi' else ('factory-str', 'factory-path', 'project')


def empty_project(api):
    project = api.Project()
    if case.API == 'edi':
        project.experiments.clear()
        project.structures.clear()
    project.structures.add(
        api.StructureFactory.from_cif_str(case.STRUCTURE.replace('data_witness', 'data_phase', 1))
    )
    return project


def invoke(api, route, text, directory, project=None):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ('source.edi' if '_edi.schema_version' in text else 'source.cif')
    path.write_text(text)
    if route == 'factory-str':
        return api.ExperimentFactory.from_cif_str(text), None
    if route == 'factory-path':
        return api.ExperimentFactory.from_cif_path(path), None
    if route == 'project':
        project = api.Project.load(case.project_input('experiment', text, directory, path.suffix))
        return project.experiments[0], project
    if project is None:
        project = empty_project(api)
    if route == 'collection-str':
        project.experiments.add_from_cif_str(text)
    elif route == 'collection-path':
        project.experiments.add_from_cif_path(path)
    else:
        project.experiments.add_from_edi_path(path)
    return project.experiments[0], project


@pytest.mark.parametrize('form', source.FORMS)
@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('declarations', source.CONFLICTS)
def test_each_public_parser_refuses_conflicting_sources_before_admission(
    tmp_path, form, route, declarations
):
    api = importlib.import_module(case.API)
    text, external = source.payload(form, tmp_path / 'independent', declarations.split('+'))
    before = external.read_bytes()
    project = None
    if route.startswith('collection'):
        project = empty_project(api)
        existing, _ = source.payload(form, tmp_path / 'existing', ['own'])
        existing = existing.replace('data_source_boundary', 'data_unchanged_survivor', 1)
        project.experiments.add(api.ExperimentFactory.from_cif_str(existing))
    admission = source.admission_pattern(form)
    with pytest.raises(ValueError, match=admission) as caught:
        invoke(api, route, text, tmp_path / 'entry', project)
    if project is not None:
        assert len(project.experiments) == 1, (
            'A refused serialized collection import leaves the original membership unchanged'
        )
        assert project.experiments[0].name == 'unchanged_survivor', (
            'A refused serialized collection import preserves its original experiment'
        )
    message = str(caught.value).lower()
    assert 'data' in message, 'The parser admission refusal identifies measured data'
    assert 'source' in message or 'linked' in message, (
        'The admission refusal identifies the competing measured-data sources'
    )
    assert external.read_bytes() == before, (
        'An ambiguous public parser cannot change the independently authored external measurements'
    )


@pytest.mark.parametrize(('form', 'declaration'), source.SINGLES)
@pytest.mark.parametrize('route', ROUTES)
def test_valid_individual_sources_still_enter_every_public_parser(
    tmp_path, form, route, declaration
):
    api = importlib.import_module(case.API)
    text, external = source.payload(form, tmp_path / 'independent', [declaration])
    before = external.read_bytes()
    experiment, _ = invoke(api, route, text, tmp_path / 'entry')
    assert experiment.name == 'source_boundary', (
        'A valid individual source still yields its independently named experiment'
    )
    if declaration == 'own':
        measured = experiment.data if form.startswith('powder') else experiment.refln
        assert list(measured.intensity_meas) == (
            [4, 9, 16] if form.startswith('powder') else [4, -9, 16]
        ), 'A valid embedded source preserves its independently authored signed measurements'
        assert list(measured.intensity_meas_su) == [0.5, 1.25, 2.5], (
            'A valid embedded source preserves each nonzero authored measurement uncertainty'
        )
        if form.startswith('reflections'):
            assert list(
                zip(measured.index_h, measured.index_k, measured.index_l, strict=True)
            ) == [(2, 1, 3), (1, 2, 3), (2, 1, 3)], (
                'Every embedded reflection control retains its independently '
                'authored Miller indices'
            )
            if form.endswith('tof'):
                assert list(measured.wavelength) == [1.3, 1.5, 1.7], (
                    'The supported TOF reflection control keeps every authored per-row wavelength'
                )

    assert external.read_bytes() == before, (
        'Valid read-only admission preserves the authored external measured bytes'
    )


@pytest.mark.parametrize('form', source.FORMS)
def test_a_legitimate_hydrated_link_is_not_a_serialized_source_conflict(tmp_path, form):
    api = importlib.import_module(case.API)
    text, external = source.payload(form, tmp_path / 'independent', ['path'])
    before = external.read_bytes()
    experiment, project = invoke(api, 'project', text, tmp_path / 'entry')
    measured = experiment.data if form.startswith('powder') else experiment.refln
    expected = [25, 36, 49] if form.startswith('powder') else [25, -36, 49]
    assert list(measured.intensity_meas) == expected, (
        'A single linked source hydrates exactly its authored external intensities'
    )
    assert list(measured.intensity_meas_su) == [0.75, 1.5, 2.75], (
        'Hydration preserves each independently supplied nonzero external uncertainty'
    )
    saved = tmp_path / 'hydrated-save'
    project.save_as(saved)
    reopened = api.Project.load(saved)
    again = reopened.experiments[0]
    measured_again = again.data if form.startswith('powder') else again.refln
    assert list(measured_again.intensity_meas) == expected, (
        'A legitimate in-memory hydrated link remains writable '
        'and survives its ordinary save policy'
    )
    assert external.read_bytes() == before, (
        'Hydration and saving a legitimate source preserve the original external measurements'
    )


@pytest.mark.parametrize('form', source.FORMS)
@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('ignored', source.CIF_IGNORED)
def test_cif_location_items_are_reported_unread_without_changing_embedded_data(
    tmp_path, form, route, ignored
):
    api = importlib.import_module(case.API)
    text, external = source.payload(form, tmp_path / 'independent', ['own', *ignored])
    text = source.as_cif(text)
    external.write_text('This file deliberately contains no numerical measurements.\n')
    before = external.read_bytes()
    with warnings.catch_warnings(record=True) as notes:
        warnings.simplefilter('always')
        experiment, _ = invoke(api, route, text, tmp_path / 'entry')
    measured = experiment.data if form.startswith('powder') else experiment.refln
    assert list(measured.intensity_meas) == (
        [4, 9, 16] if form.startswith('powder') else [4, -9, 16]
    ), 'CIF import keeps its complete authored embedded data rather than following a location item'
    assert list(measured.intensity_meas_su) == [0.5, 1.25, 2.5], (
        'CIF import preserves the independently authored nonzero uncertainty of every embedded row'
    )
    tags = ['path'] if 'path' in ignored else []
    if 'collection' in ignored:
        tags += ['collection_id', 'digest']
    messages = [str(note.message).lower() for note in notes]
    for tag in tags:
        assert any(
            '_edi_data_source.' + tag in message and 'not read' in message for message in messages
        ), 'Every deliberately unread CIF location declaration receives its actual named report'
    assert external.read_bytes() == before, (
        'Reporting unread CIF location items preserves the independently authored external file'
    )


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
@pytest.mark.parametrize('shape', ['single', 'plural', 'plain'])
def test_linked_reflection_project_preserves_whole_file_dataset_identity(tmp_path, beam, shape):
    api = importlib.import_module(case.API)
    text, _ = source.payload('reflections-' + beam, tmp_path / 'declared', [])
    external, rows = source.reflection_file(tmp_path / 'independent', beam, shape)
    text += '_data_source.path "' + str(external) + '"\n'
    before = external.read_bytes()
    if shape == 'plural':
        with pytest.raises(
            ValueError,
            match=source.MULTIPLE_DATASETS,
        ):
            invoke(api, 'project', text, tmp_path / 'entry')
    else:
        experiment, project = invoke(api, 'project', text, tmp_path / 'entry')
        assert list(experiment.refln.intensity_meas) == [row[3] for row in rows], (
            'A single-file link retains every authored signed reflection in its one actual dataset'
        )
        assert list(experiment.refln.intensity_meas_su) == [row[4] for row in rows], (
            'A single-file link preserves every independently supplied reflection uncertainty'
        )
        assert list(
            zip(
                experiment.refln.index_h,
                experiment.refln.index_k,
                experiment.refln.index_l,
                strict=True,
            )
        ) == [tuple(row[:3]) for row in rows], (
            'A one-dataset link retains every authored Miller index, '
            'including repeated reflections'
        )
        if beam == 'tof':
            assert list(experiment.refln.wavelength) == [row[6] for row in rows], (
                'A TOF file link retains each independently authored positive per-row wavelength'
            )
        saved = tmp_path / 'saved'
        project.save_as(saved)
        again = api.Project.load(saved).experiments[0]
        assert list(again.refln.intensity_meas) == [row[3] for row in rows], (
            'Saving and reopening a one-dataset reflection link preserves its authored membership'
        )
    assert external.read_bytes() == before, (
        'Admitting or refusing a linked reflection file never changes its original source bytes'
    )


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
def test_a_missing_reflection_link_keeps_its_project_open_and_measurements_absent(tmp_path, beam):
    api = importlib.import_module(case.API)
    text, external = source.payload('reflections-' + beam, tmp_path / 'independent', ['path'])
    external.unlink()
    experiment, project = invoke(api, 'project', text, tmp_path / 'entry')
    assert project is not None, 'A missing reflection source leaves the actual project open'
    assert experiment.name == 'source_boundary', (
        'A missing external reflection file retains its independently named original experiment'
    )
    assert len(experiment.refln.intensity_meas) == 0, (
        'A missing reflection link never manufactures embedded observations '
        'or borrows another source'
    )
    assert not external.exists(), (
        'Opening a missing reflection link never creates its external file'
    )
