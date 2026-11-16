"""The native public parser overloads enforce the same serialized-source boundary."""

import hashlib
import importlib
import json
import os
import re
import subprocess
from pathlib import Path

import gemmi
import pytest

from tests.fixtures import cif_import_cases as case
from tests.fixtures import serialized_sources as source
from tests.fixtures.serialized_admission import build as builder

ROOT = Path(__file__).resolve().parents[3]
ROUTES = ('text', 'file', 'legacy-file', 'batch', 'project', 'complete', 'construction')
if case.API == 'crysta':
    ROUTES = ('text', 'file', 'project')


@pytest.fixture(scope='module')
def native():
    selected = os.environ.get('SERIALIZED_ADMISSION_RECEIPT')
    if selected:
        receipt = json.loads(Path(selected).read_text(encoding='utf-8'))
        assert receipt['recipe']['backend'] == case.API, (
            'The native parser receipt belongs to the product whose entry points are exercised'
        )
        binary = builder.validate(receipt, ROOT)
    else:
        api = importlib.import_module(case.API)
        directory = (
            Path(api._edi.__file__).resolve().parents[2]
            if case.API == 'edi'
            else (ROOT / 'build/crysta').resolve().parent
        )
        relative = (
            'single_crystal_edges' if case.API == 'edi' else 'tests/fixtures/single_crystal_edges'
        )
        binary = (
            directory
            / relative
            / (
                'serialized_admission_probe.exe'
                if os.name == 'nt'
                else 'serialized_admission_probe'
            )
        )
        assert binary.is_file(), (
            'The ordinary public-model build prepares the native parser consumer before pytest'
        )
    identity = subprocess.check_output([str(binary), '--identity'], text=True).strip()
    assert (
        identity
        == hashlib.sha256(
            (ROOT / 'tests/fixtures/serialized_admission/probe.cpp').read_bytes()
        ).hexdigest()
    ), 'The native consumer runs the complete currently authored observer'
    return binary


def invoke(native, route, text, directory):
    suffix = '.edi' if '_edi.schema_version' in text else '.cif'
    folder = case.project_input('experiment', text, directory, suffix)
    path = folder / ('experiments/witness' + suffix)
    binary = native

    result = subprocess.run(
        [
            str(binary.resolve()),
            route,
            str(path),
            str(folder),
            str(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment'),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, (
        'A native parser witness reaches its actual entry, independently of setup or compilation: '
        + result.stdout
        + result.stderr
    )
    lines = [
        line
        for line in result.stdout.splitlines()
        if line.startswith(('ADMITTED ', 'REFUSED ')) or line == 'CONVERTED'
    ]
    assert len(lines) == 1, 'Each native entry produces one explicit admission outcome'
    details = dict(line.split(' ', 1) for line in result.stdout.splitlines() if ' ' in line)
    details['notes'] = (
        result.stderr
        + '\n'
        + '\n'.join(line[5:] for line in result.stdout.splitlines() if line.startswith('NOTE '))
    )
    if lines[0] == 'CONVERTED':
        details['serialized'] = result.stdout.partition('CONVERTED\n')[2]
    return lines[0], details


@pytest.mark.parametrize('form', source.FORMS)
@pytest.mark.parametrize('route', ROUTES)
@pytest.mark.parametrize('declarations', source.CONFLICTS)
def test_each_native_parser_refuses_competing_declared_sources(
    native, tmp_path, form, route, declarations
):
    text, external = source.payload(form, tmp_path / 'independent', declarations.split('+'))
    before = external.read_bytes()
    outcome, _ = invoke(native, route, text, tmp_path / 'entry')
    assert outcome.startswith('REFUSED '), (
        'Every native parser overload refuses ambiguous serialized measurements at admission'
    )
    message = outcome.lower()
    assert re.search(source.admission_pattern(form), message), (
        'The native parser names the source conflict before hydration'
    )
    assert 'data' in message, 'The native admission refusal identifies measured data'
    assert 'source' in message or 'linked' in message, (
        'The native refusal names the competing measured-data declaration'
    )
    assert external.read_bytes() == before, (
        'A native admission refusal preserves the independently authored linked data'
    )


@pytest.mark.parametrize(('form', 'declaration'), source.SINGLES)
@pytest.mark.parametrize('route', ROUTES)
def test_each_native_parser_still_admits_individual_sources(
    native, tmp_path, form, route, declaration
):
    text, external = source.payload(form, tmp_path / 'independent', [declaration])
    before = external.read_bytes()
    outcome, details = invoke(native, route, text, tmp_path / 'entry')
    assert outcome == 'ADMITTED source_boundary', (
        'Every native public parser keeps valid single-source input admissible'
    )
    if declaration == 'own':
        assert list(map(float, details['I'].split())) == (
            [4, 9, 16] if form.startswith('powder') else [4, -9, 16]
        ), 'A native embedded-source control retains its independently authored signed intensities'
        assert list(map(float, details['SU'].split())) == [0.5, 1.25, 2.5], (
            'A native embedded-source control retains every authored nonzero uncertainty'
        )
    elif declaration == 'path':
        assert Path(details['PATH']).resolve() == external.resolve(), (
            'A native single-file control retains its original external source declaration'
        )
    else:
        assert details['COLLECTION'] == 'independent-third-source', (
            'A native collection control retains its original declared collection entry'
        )
        declared = gemmi.cif.read_string(text).sole_block()
        tag = '_data_source.digest'
        assert details['DIGEST'] == gemmi.cif.as_string(declared.find_value(tag)), (
            'A native collection control retains its exact independently supplied digest'
        )
    assert external.read_bytes() == before, (
        'A native single-source admission is read-only with respect to external measurements'
    )


CIF_ROUTES = ROUTES + (('convert',) if case.API == 'crysta' else ())


@pytest.mark.parametrize('form', source.FORMS)
@pytest.mark.parametrize('route', CIF_ROUTES)
@pytest.mark.parametrize('ignored', source.CIF_IGNORED)
def test_every_native_cif_entry_reports_unread_locations_and_retains_its_own_rows(
    native, tmp_path, form, route, ignored
):
    text, external = source.payload(form, tmp_path / 'independent', ['own', *ignored])
    # A forbidden external read would fail; a CIF's own measured rows remain valid.
    external.write_text('This file deliberately contains no numerical measurements.\n')
    before = external.read_bytes()
    outcome, details = invoke(native, route, source.as_cif(text), tmp_path / 'entry')
    if route == 'convert':
        assert outcome == 'CONVERTED', (
            'The public CIF converter accepts embedded data and reports unread location items'
        )
        block = gemmi.cif.read_string(details['serialized']).sole_block()
        assert block.name == 'source_boundary', (
            'The public converter returns the actual independently named experiment'
        )
        category = '_data.' if form.startswith('powder') else '_refln.'
        intensities = list(map(float, block.find_values(category + 'intensity_meas')))
        uncertainties = list(map(float, block.find_values(category + 'intensity_meas_su')))
        for item in ('path', 'collection_id', 'digest'):
            assert not block.find_value('_data_source.' + item), (
                'A reported unread CIF location never becomes a serialized native data authority'
            )
    else:
        assert outcome == 'ADMITTED source_boundary', (
            'Every native CIF loader accepts valid embedded data without following a location item'
        )
        intensities = list(map(float, details['I'].split()))
        uncertainties = list(map(float, details['SU'].split()))
        assert not any(details[item] for item in ('PATH', 'COLLECTION', 'DIGEST')), (
            'Unread CIF locations never become actual model data-source declarations'
        )
    assert intensities == ([4, 9, 16] if form.startswith('powder') else [4, -9, 16]), (
        'Every public CIF entry retains the complete independently authored signed measured column'
    )
    assert uncertainties == [0.5, 1.25, 2.5], (
        'Every public CIF entry retains each independently authored nonzero uncertainty'
    )
    tags = ['path'] if 'path' in ignored else []
    if 'collection' in ignored:
        tags += ['collection_id', 'digest']
    for tag in tags:
        assert '_edi_data_source.' + tag in details['notes'], (
            'Each unread CIF location item has an actual named report '
            'from the public native parser'
        )
    assert external.read_bytes() == before, (
        'Public CIF readers leave deliberately unread external measured input bytes unchanged'
    )


PROJECT_ROUTES = tuple(
    route for route in ROUTES if route in {'project', 'complete', 'construction'}
)


@pytest.mark.parametrize('beam', ['cwl', 'tof'])
@pytest.mark.parametrize('shape', ['single', 'plural', 'plain'])
@pytest.mark.parametrize('route', PROJECT_ROUTES)
def test_native_linked_reflection_project_retains_file_dataset_identity(
    native, tmp_path, beam, shape, route
):
    text, _ = source.payload('reflections-' + beam, tmp_path / 'declared', [])
    external, rows = source.reflection_file(tmp_path / 'independent', beam, shape)
    text += '_data_source.path "' + str(external) + '"\n'
    before = external.read_bytes()
    outcome, details = invoke(native, route, text, tmp_path / 'entry')
    if shape == 'plural':
        assert outcome.startswith('REFUSED '), (
            'A whole-file link cannot silently merge independently authored FullProf dataset codes'
        )
        assert re.search(
            source.MULTIPLE_DATASETS,
            outcome,
        ), 'A multi-dataset link receives a specific dataset-identity refusal at actual admission'
    else:
        assert outcome == 'ADMITTED source_boundary', (
            'Every public project overload still admits a valid one-dataset reflection link'
        )
        assert list(map(float, details['I'].split())) == [row[3] for row in rows], (
            'Native project hydration preserves every authored signed reflection '
            'in its original dataset'
        )
        assert list(map(float, details['SU'].split())) == [row[4] for row in rows], (
            'Native project hydration retains each independently supplied nonzero uncertainty'
        )
    assert external.read_bytes() == before, (
        'Every actual native project route leaves the admitted external reflection bytes intact'
    )
