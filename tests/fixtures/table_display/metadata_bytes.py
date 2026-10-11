"""Retain complete old byte witnesses across declared example presentation edits.

The archive contains source bytes only, never output from a new serializer.
Every admitted input must equal its complete archived copy; the whitelist is
checked again when replayed. Historical input and saved pins remain unchanged.
"""

import argparse
import hashlib
import io
import json
import shlex
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

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


def records(data, fields=FIELDS):
    result = {}
    for line in data.decode().splitlines():
        tokens = shlex.split(line, comments=True)
        if tokens and tokens[0] in fields:
            assert len(tokens) == 2 and tokens[0] not in result, (
                'Descriptive source records must be unique scalar declarations'
            )
            result[tokens[0]] = tokens[1]
    return result


def remainder(data, fields=FIELDS):
    return b''.join(
        line
        for line in data.splitlines(keepends=True)
        if not line.split() or line.split()[0].decode() not in fields
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


def pre_catalogue_bytes(path):
    """Bind a live descriptive file to its whole source pair before retaining old bytes."""
    data = path.read_bytes()
    if path.suffix != '.edi' or not path.is_relative_to(ROOT):
        return data
    name = path.relative_to(ROOT).as_posix()
    pins = json.loads((HERE / 'metadata-inputs.json').read_text())['files']
    if name not in pins:
        return data
    before, after = pair(name)
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
    for path in source.rglob('*'):
        if not path.is_file():
            continue
        name = path.relative_to(ROOT).as_posix()
        if name not in pins:
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
                if added and not before_fields and b'_scattering_source.' not in old_data:
                    # A new category owns one canonical blank separator.
                    marker = b'_edi.schema_version 3\n\n\n'
                    assert actual.count(marker) == 1, (
                        'A newly added experiment category owns exactly one block separator'
                    )
                    actual = actual.replace(marker, b'_edi.schema_version 3\n\n', 1)
            assert old_data == actual, (
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
