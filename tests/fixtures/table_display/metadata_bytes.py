"""Retain complete old byte witnesses across declared example presentation edits.

The archive contains source bytes only, never output from a new serializer.
Every admitted input must equal its complete archived copy; the whitelist is
checked again when replayed. Historical input and saved pins remain unchanged.
"""

import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

import gemmi

from tests.fixtures.metadata_transition.source_bytes import previous_bytes
from tests.fixtures.project_categories.historical_bytes import units

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BEFORE = '1c36f7824a07eb2a3a5cca88f93ff87b8dc1518a^'
AFTER = '02541e468048dc7acb1513912332e8ecb279623a'
FIELDS = {
    '_metadata.title',
    '_metadata.description',
    '_metadata.purpose',
    '_metadata.dimensionality',
    '_metadata.instrument',
    '_metadata.facility',
    '_metadata.polarisation',
    '_experiment_type.sample_form',
    '_experiment_type.beam_mode',
    '_experiment_type.radiation_probe',
    '_experiment_type.scattering_type',
    '_fitting_mode.type',
}
SAVED_FIELDS = {'_metadata.title', '_metadata.description'}
EXPERIMENT_DESCRIPTORS = {
    '_experiment_type.dimensionality',
    '_experiment_type.polarisation',
    '_instrument.name',
    '_instrument.facility',
}


def without_experiment_descriptors(data):
    # Category order and spacing are separately gated. Retain all other item and
    # loop payload bytes; remove exactly the independently declared scalar fields.
    head, entries, _prefix, _tail = units(data)
    return head, [
        (key, value) for key, value in entries if key.decode() not in EXPERIMENT_DESCRIPTORS
    ]


def record_spans(data, fields):
    lines = data.decode().splitlines(keepends=True)
    prefix = '' if re.search(r'(?mi)^data_', data.decode()) else 'data_records\n'
    try:
        block = gemmi.cif.read_string(prefix + data.decode()).sole_block()
    except RuntimeError as error:
        raise AssertionError(
            'Descriptive records require unambiguous valid CIF scalars'
        ) from error
    seen = set()
    for item in block:
        if item.pair is None or item.pair[0] not in fields:
            continue
        key, raw = item.pair
        assert key not in seen, 'Descriptive source records must be unique scalar declarations'
        seen.add(key)
        start = item.line_number - 1 - bool(prefix)
        value_line = start
        if len(lines[start].strip().split(maxsplit=1)) == 1:
            value_line += 1
            while not lines[value_line].strip() or lines[value_line].lstrip().startswith('#'):
                value_line += 1
        value = gemmi.cif.as_string(raw)
        if raw.startswith(';\n'):
            # The declared plain-text format puts the delimiter on its own line;
            # a single wrapped newline reads as a space, an empty line as a paragraph.
            value = value.removeprefix('\n')
            value = re.sub(r'(?<!\n)\n(?!\n)', ' ', value)
        yield key, value, start, value_line + raw.count('\n') + 1


def records(data, fields=FIELDS):
    return {key: value for key, value, _start, _end in record_spans(data, fields)}


def remainder(data, fields=FIELDS):
    removed = {
        i for _key, _value, start, end in record_spans(data, fields) for i in range(start, end)
    }
    return b''.join(
        line for i, line in enumerate(data.splitlines(keepends=True)) if i not in removed
    )


def unchanged_effective_types(before, after):
    old, new = records(before), records(after)
    peak = records(before, {'_peak.type'}).get('_peak.type', '')
    defaults = {
        '_experiment_type.sample_form': 'powder',
        '_experiment_type.beam_mode': (
            'time-of-flight' if peak.startswith('tof-') else 'constant wavelength'
        ),
        '_experiment_type.radiation_probe': 'neutron',
        '_experiment_type.scattering_type': 'bragg',
        '_fitting_mode.type': 'single',
    }
    for key, default in defaults.items():
        if key in old or key in new:
            assert old.get(key, default) == new.get(key, default), (
                'Explicit catalogue types must retain the prior effective experiment '
                'and fitting modes'
            )


def pair(name):
    with zipfile.ZipFile(HERE / 'metadata-inputs.zip') as archive:
        before, after = archive.read('before/' + name), archive.read('after/' + name)
    pins = json.loads((HERE / 'metadata-inputs.json').read_text())['files'][name]
    assert [hashlib.sha256(data).hexdigest() for data in (before, after)] == pins, (
        'Metadata source copies must retain both complete independently committed byte identities'
    )
    records(before)
    records(after)
    unchanged_effective_types(before, after)
    assert remainder(before) == remainder(after), (
        'Example presentation changes must preserve every byte outside declared descriptive fields'
    )
    return before, after


# Exact source-only transition from accepted5ee12a7b, not a saved-output pin.
# Old archive/JSON identities remain untouched and still own the next stage.
_DESCRIPTION_INPUTS = {
    'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project/project.edi': {
        'before': 'b47088ce8a1198fba99f4cca2fdee1b317230e0c66fbdc2602273344bdbab721',
        'after': 'e32ac6ec6bcb5f5e793fd830ec0674abba9981663077bd86560adf3cf252cee5',
        'remove': (),
        'restore': (
            b'_metadata.purpose "refinement"\n'
            b'_metadata.dimensionality "1D"\n'
            b'_metadata.instrument "HRPT"\n'
            b'_metadata.facility "PSI"\n'
            b'_metadata.polarisation "none"\n'
        ),
    },
    'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-4/project/experiments/hrpt.edi': {
        'before': 'c7a093e4cdee2aeca6553b84cca81293b748caeb6270d2083b5a043724128c26',
        'after': '645318644c24043b73c2aff1878a59720dd509b47db16a559b3c01ffeb0a545e',
        'remove': (
            b'_experiment_type.dimensionality 1d\n',
            b'_experiment_type.polarisation unpolarised\n',
            b'_instrument.name HRPT\n',
            b'_instrument.facility PSI\n',
        ),
        'restore': b'',
    },
    'docs/user/cli/pd-neut-cwl_lbco-hrpt/project/experiments/hrpt.edi': {
        'before': '502941566652e6acfff532d1c9a4b5b73e7827a66d22d3fb8903078d2d310286',
        'after': 'f0c0e3839ffa3b6043992fb768eef3794ced6c869ceb7da52a57b8a387cac3f2',
        'remove': (
            b'_experiment_type.dimensionality 1d\n',
            b'_experiment_type.polarisation unpolarised\n',
            b'_instrument.name HRPT\n',
            b'_instrument.facility PSI\n',
        ),
        'restore': b'',
    },
    'docs/user/cli/pd-neut-cwl_lbco-hrpt/project/project.edi': {
        'before': '55a1f672b1825145203ea9e39399e8cb3f9df106ac390a8b58258a03ba222aa2',
        'after': '5898148607293d5d298bd619d43bf7bda5bb19b808b5d25f16eae690690d89e1',
        'remove': (),
        'restore': (
            b'_metadata.purpose "refinement"\n'
            b'_metadata.dimensionality "1D"\n'
            b'_metadata.instrument "HRPT"\n'
            b'_metadata.facility "PSI"\n'
            b'_metadata.polarisation "none"\n'
        ),
    },
    'docs/user/cli/pd-neut-tof_ncaf-wish/project/experiments/wish_1_10.edi': {
        'before': '24dd6b5278ac7369ad528da944b324e3a5d0472cd2f448c289faeb57ec78bd27',
        'after': '2b9be49af490454d817f78e200852c640a025a14607efe41ff0b18683c9e918b',
        'remove': (
            b'_experiment_type.dimensionality 1d\n',
            b'_experiment_type.polarisation unpolarised\n',
            b'_instrument.name WISH\n',
            b'_instrument.facility ISIS\n',
        ),
        'restore': b'',
    },
    'docs/user/cli/pd-neut-tof_ncaf-wish/project/experiments/wish_2_9.edi': {
        'before': 'cc447addb349b2956750e4e8d4da74e42325acd3be70163c533f2a2b76beca65',
        'after': '2e921f4c31ed9dd39f7a26475cf0798db7fcfe34fcfca2e34479de26d5644012',
        'remove': (
            b'_experiment_type.dimensionality 1d\n',
            b'_experiment_type.polarisation unpolarised\n',
            b'_instrument.name WISH\n',
            b'_instrument.facility ISIS\n',
        ),
        'restore': b'',
    },
    'docs/user/cli/pd-neut-tof_ncaf-wish/project/experiments/wish_3_8.edi': {
        'before': '14265d219fe6a6efa50b4b074d33ac8713ad6cb7d3cd7b013f13085cb976857f',
        'after': 'f42e3b7a75128300f69a93d4e1c0628f160ef1c42f998f8b86c2f3227d5ce3c0',
        'remove': (
            b'_experiment_type.dimensionality 1d\n',
            b'_experiment_type.polarisation unpolarised\n',
            b'_instrument.name WISH\n',
            b'_instrument.facility ISIS\n',
        ),
        'restore': b'',
    },
    'docs/user/cli/pd-neut-tof_ncaf-wish/project/experiments/wish_4_7.edi': {
        'before': 'a3833fabd3d3c4b59403d5c0d995e7ece5db4e40efcdc208024d1f0fd19c8c5f',
        'after': '21dbc4f9632d817bdba4bb0cc27529535a964ad1805d358454d05ccedebc861c',
        'remove': (
            b'_experiment_type.dimensionality 1d\n',
            b'_experiment_type.polarisation unpolarised\n',
            b'_instrument.name WISH\n',
            b'_instrument.facility ISIS\n',
        ),
        'restore': b'',
    },
    'docs/user/cli/pd-neut-tof_ncaf-wish/project/experiments/wish_5_6.edi': {
        'before': '2db147368b28fac20b85d9dd62479e73cf6c1c620e3d97c7a65224f34a29836d',
        'after': '710d2a36a973081d25cec22d09c159684ed0df8b38a08951fd948f3d8c888556',
        'remove': (
            b'_experiment_type.dimensionality 1d\n',
            b'_experiment_type.polarisation unpolarised\n',
            b'_instrument.name WISH\n',
            b'_instrument.facility ISIS\n',
        ),
        'restore': b'',
    },
    'docs/user/cli/pd-neut-tof_ncaf-wish/project/project.edi': {
        'before': '075fc2c6b70a7588dd716e34b83a9deb965592bf3fa04dfcd77ba602887c465f',
        'after': 'e2b045f18bd1be45f64da214a3ec30bdf21a642924f48f21f709ee1e88997af0',
        'remove': (),
        'restore': (
            b'_metadata.purpose "refinement"\n'
            b'_metadata.dimensionality "1D"\n'
            b'_metadata.instrument "WISH"\n'
            b'_metadata.facility "ISIS"\n'
            b'_metadata.polarisation "none"\n'
        ),
    },
}


def pre_description_bytes(name, data):
    """Reverse only individually source-proven, complete metadata migrations."""
    row = _DESCRIPTION_INPUTS.get(name)
    if row is None:
        return data
    assert hashlib.sha256(data).hexdigest() == row['after'], (
        'A complete committed description-migration input is required before retaining old bytes'
    )
    for line in row['remove']:
        assert data.count(line) == 1, 'Each declared migrated experiment field occurs exactly once'
        data = data.replace(line, b'', 1)
    data += row['restore']
    assert hashlib.sha256(data).hexdigest() == row['before'], (
        'Metadata reversal must recover the complete independently committed prior source'
    )
    return data


def pre_catalogue_bytes(path):
    """Bind a live descriptive file to its whole source pair before retaining old bytes."""
    data = path.read_bytes()
    if path.suffix != '.edi' or not path.is_relative_to(ROOT):
        return data
    name = path.relative_to(ROOT).as_posix()
    data = previous_bytes(name, data)
    pins = json.loads((HERE / 'metadata-inputs.json').read_text())['files']
    if name not in pins:
        return data
    before, after = pair(name)
    if name == 'docs/user/cli/pd-xray-cwl_latp_scan-4f/project/project.edi':
        # Keep the older archive and scientific byte pins; only the origin changed.
        for old, new in (
            (b'Unknown instrument @ SNBL', b'BM01 @ ESRF'),
            (b'_metadata.instrument ?', b'_metadata.instrument "BM01"'),
            (b'_metadata.facility "SNBL"', b'_metadata.facility "ESRF"'),
        ):
            assert after.count(old) == 1, 'The retained LATP origin has one exact old field'
            after = after.replace(old, new, 1)
    assert data == after, (
        'A live descriptive input must match its entire independently archived source, '
        'including every scientific byte'
    )
    return before


def restore(source, destination):
    shutil.copytree(source, destination)
    if not source.is_relative_to(ROOT):
        return destination
    pins = json.loads((HERE / 'metadata-inputs.json').read_text())['files']
    migration = json.loads((ROOT / 'tests/fixtures/metadata_transition/sources.json').read_text())[
        'files'
    ]
    for path in source.rglob('*'):
        if not path.is_file():
            continue
        name = path.relative_to(ROOT).as_posix()
        if name not in pins and name not in migration:
            continue
        (destination / path.relative_to(source)).write_bytes(pre_catalogue_bytes(path))
    return destination


def check_saved(live_input, old_saved, new_saved):
    old = {
        p.relative_to(old_saved).as_posix(): p.read_bytes()
        for p in old_saved.rglob('*')
        if p.is_file()
    }
    new = {
        p.relative_to(new_saved).as_posix(): p.read_bytes()
        for p in new_saved.rglob('*')
        if p.is_file()
    }
    assert old.keys() == new.keys(), (
        'Descriptive edits must preserve the complete saved file inventory'
    )
    for name, old_data in old.items():
        if name != 'project.edi':
            expected_data = old_data
            actual = new[name]
            relative = (
                (live_input / name).relative_to(ROOT).as_posix()
                if live_input.is_relative_to(ROOT)
                else None
            )
            pins = json.loads((HERE / 'metadata-inputs.json').read_text())['files']
            if relative in pins and name.startswith('experiments/'):
                before_input, after_input = pair(relative)
                before_fields, after_fields = records(before_input), records(after_input)
                added = after_fields.keys() - before_fields.keys()
                assert records(actual) == after_fields, (
                    'Added experiment descriptors must save exactly their supplied scalar values'
                )
                for key in added:
                    line = (key + ' "' + after_fields[key] + '"\n').encode()
                    assert actual.count(line) == 1, (
                        'Each added experiment descriptor must have one canonical saved line'
                    )
                    actual = actual.replace(line, b'', 1)
            if name.startswith('experiments/') and name.endswith('.edi'):
                expected_descriptors = records(
                    (live_input / name).read_bytes(), EXPERIMENT_DESCRIPTORS
                )
                assert records(actual, EXPERIMENT_DESCRIPTORS) == expected_descriptors, (
                    'Saved experiment descriptions must equal the complete migrated input fields'
                )
                expected_data = without_experiment_descriptors(old_data)
                actual = without_experiment_descriptors(actual)
            assert expected_data == actual, (
                'Descriptive edits must preserve every saved scientific and measured-data byte'
            )
            continue
        # The retained writer contract owns title and description. Catalogue
        # descriptors are input records, not additions to that frozen contract.
        expected = records((live_input / name).read_bytes(), SAVED_FIELDS)
        actual = records(new[name], SAVED_FIELDS)
        assert actual == expected, (
            'The live save must preserve every declared descriptive value '
            'without missing, extra or duplicate fields'
        )
        assert remainder(old_data, SAVED_FIELDS) == remainder(new[name], SAVED_FIELDS), (
            'Descriptive edits must preserve every other project record and byte'
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', action='store_true', required=True)
    parser.parse_args()
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'archive', BEFORE, 'docs/user/cli'])
    files = {}
    with (
        tarfile.open(fileobj=io.BytesIO(raw)) as source,
        zipfile.ZipFile(
            HERE / 'metadata-inputs.zip', 'w', compression=zipfile.ZIP_DEFLATED
        ) as archive,
    ):
        for member in source.getmembers():
            if not member.isfile() or not member.name.endswith('.edi'):
                continue
            before = source.extractfile(member).read()
            after = subprocess.check_output([
                'git',
                '-C',
                str(ROOT),
                'show',
                AFTER + ':' + member.name,
            ])
            if before == after:
                continue
            records(before)
            records(after)
            unchanged_effective_types(before, after)
            assert remainder(before) == remainder(after), (
                'Source archive authoring must refuse changes outside declared descriptive fields'
            )
            files[member.name] = [hashlib.sha256(data).hexdigest() for data in (before, after)]
            for label, data in (('before', before), ('after', after)):
                info = zipfile.ZipInfo(label + '/' + member.name, date_time=(2026, 10, 9, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
    (HERE / 'metadata-inputs.json').write_text(
        json.dumps(
            {
                'claim': 'INPUT BYTES: descriptive source adaptation; '
                'no generated saved-output oracle',
                'before': BEFORE,
                'after': AFTER,
                'files': files,
            },
            indent=2,
            sort_keys=True,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
