"""Ephemeral ordinary-Save counterpart; immutable independent raw anchors stay FIRST.

This is a test-owned reference, not a golden generator. Old browser raw vectors
were not captured and are never reconstructed here. Only the two catalogue
cases are admitted. The additional written inventory closes three known holes
in scientific(); all other file/derived checks remain in the existing reopen owner.
"""

import argparse
import hashlib
import json
import math
import re
import sys
import tempfile
from pathlib import Path

import edi
import gemmi
import numpy as np

from tests.fixtures.e04_t11_wasm.generate_catalogue import CASES
from tests.fixtures.e04_t11_wasm.reopen import archive_files
from tests.fixtures.table_display.metadata_bytes import pre_catalogue_bytes
from tests.fixtures.web_parallel import numeric
from tests.fixtures.web_parallel import science_identity as identity
from tests.fixtures.web_parallel.numeric import (
    compare_scientific,
    scientific,
)

EXTRA = {'_instrument', '_linked_structure', '_absorption'}
ARRAY_FIELDS = (
    'intensity_meas',
    'intensity_meas_su',
    'intensity_calc',
    'intensity_bkg',
    'calc_status',
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def files(root):
    return {
        path.relative_to(root).as_posix(): sha(path)
        for path in sorted(Path(root).rglob('*'))
        if path.is_file()
    }


def document(path, name):
    text = path.read_text()
    return gemmi.cif.read_string(
        'data_written_observer\n' + text
        if name in {'project.edi', 'analysis/analysis.edi'}
        else text
    ).sole_block()


def blocks(root, names):
    return {
        name: '' if name == 'analysis/analysis.edi' else document(root / name, name).name
        for name in names
    }


def inputs(root, case):
    if case not in CASES:
        raise ValueError('written reference requires an admitted catalogue case')
    here = root / 'tests/fixtures/e04_t11_wasm/catalogue_scientific'
    fixture = json.loads((here / f'{case}-native.json').read_text())
    condition = json.loads((here / f'{case}-conditioning.json').read_text())
    raw_path = here / f'{case}-conditioning-raw.json'
    raw = json.loads(raw_path.read_text())
    if sha(raw_path) != condition['raw_capture_sha256']:
        raise ValueError('raw anchor bytes differ from the frozen conditioning capture')
    source = root / 'docs/user/cli' / CASES[case] / 'project'
    if source != root / fixture['project']:
        raise ValueError('written reference case cannot retarget the frozen input owner')
    digest = hashlib.sha256()
    for path in sorted(source.rglob('*')):
        if path.is_file():
            digest.update(path.relative_to(source).as_posix().encode() + b'\0')
            digest.update(pre_catalogue_bytes(path))
    if digest.hexdigest() != fixture['project_sha256']:
        raise ValueError('written reference requires the exact authenticated catalogue input')
    names = blocks(source, fixture['scientific'])
    identity.conditioning_semantics(fixture['scientific'], condition, names)
    if raw['labels'] != condition['labels'] or raw['n_data'] != condition['n_data']:
        raise ValueError('raw labels and point count must authenticate to conditioning')
    banks = {
        name: (
            block,
            tuple(document(source / name, name).find_values('_linked_structure.structure_id')),
        )
        for name, block in names.items()
        if name.startswith('experiments/')
    }
    return fixture, raw, source, names, banks


def raw_path(key, names):
    """Closed public storage spellings; no numeric identity matching or product resolver."""
    field = key.tag.split('.', 1)[1]
    row = dict(key.row)
    if key.document.startswith('structures/'):
        if sum(name.startswith('structures/') for name in names) != 1:
            raise ValueError('catalogue raw storage needs exactly one structure owner')
        if key.category == '_cell':
            return 'structure.cell.' + field
        for category, collection in (
            ('_atom_site', 'atom_sites'),
            ('_atom_site_aniso', 'atom_site_aniso'),
        ):
            if key.category == category:
                return 'structure.' + collection + '[' + row[category + '.id'] + '].' + field
    elif key.document.startswith('experiments/'):
        banks = [block for name, block in names.items() if name.startswith('experiments/')]
        prefix = 'experiment.' if len(banks) == 1 else 'experiments[' + key.block + '].'
        if key.category == '_background':
            return prefix + 'background[' + row['_background.id'] + '].' + field
        if key.category == '_linked_structure':
            return (
                prefix
                + 'linked_structures['
                + row['_linked_structure.structure_id']
                + '].'
                + field
            )
        if key.category in {'_peak', '_instrument', '_absorption'}:
            return prefix + key.category[1:] + '.' + field
    raise ValueError('raw fitted storage is outside the two declared catalogue cases')


def raw_candidates(fixture, old, names, banks, source):
    index = identity.semantic_index(fixture['scientific'], names)
    candidates = {}
    for doc, row, token, column, *_ in fixture['native_precision_bindings']:
        candidates.setdefault(column, set()).add(
            raw_path(index.coordinates[doc, row, token], names)
        )
    for anchor in identity.omitted_raw_parameters(old, banks).values():
        candidates.setdefault(anchor.column, set()).add(raw_path(anchor.key, names))
    for column, label in enumerate(old['labels']):
        if column in candidates:
            continue
        # FIRST optional table: only declared NCAF bank-owned abscor1 is omitted
        # by the original whitelist, never every unknown remaining label.
        bank, separator, field = label.rpartition('.')
        owner = [
            name
            for name, block in names.items()
            if name.startswith('experiments/') and block == bank
        ]
        if separator != '.' or field != 'abscor1' or len(owner) != 1:
            raise ValueError('raw column has no declared fitted storage identity')
        value = document(source / owner[0], owner[0]).find_value('_absorption.abscor1')
        if not value or value in {'?', '.'}:
            raise ValueError('optional absorption must exist in its original declared bank')
        key = identity.Cell(owner[0], bank, '_absorption', (), '_absorption.abscor1')
        candidates[column] = {raw_path(key, names)}
    if set(candidates) != set(range(len(old['labels']))):
        raise ValueError('every independent raw column needs its own storage candidates')
    return candidates


def background_label_owns(label, path, names, source, prefix):
    number = label[11:-1]
    if not number.isdecimal():
        return False
    owned = [
        name
        for name, block in names.items()
        if name.startswith('experiments/')
        and (not prefix or prefix == 'experiments[' + block + '].')
    ]
    if len(owned) != 1:
        return False
    block = document(source / owned[0], owned[0])
    ids = list(block.find_values('_background.id'))
    if int(number) >= len(ids):
        return False
    stem = prefix or 'experiment.'
    return path.startswith(stem + 'background[' + ids[int(number)] + '].')


def label_owns(label, path, names, source):
    banks = [block for name, block in names.items() if name.startswith('experiments/')]
    prefix = ''
    if len(banks) > 1 and any(label.startswith(bank + '.') for bank in banks):
        bank, label = label.split('.', 1)
        prefix = 'experiments[' + bank + '].'
    if label.startswith('cell_'):
        return path == 'structure.cell.' + label[5:]
    if label.startswith('background[') and label.endswith(']'):
        return background_label_owns(label, path, names, source, prefix)
    if '.' in label:
        site, field = label.rsplit('.', 1)
        return path == 'structure.atom_sites[' + site + '].' + field
    stem = prefix or 'experiment.'
    if label == 'scale':
        return path.startswith(stem + 'linked_structures[') and path.endswith('].scale')
    category = (
        'instrument'
        if label.startswith('calib_')
        else 'absorption'
        if label == 'abscor1'
        else 'peak'
    )
    return path == stem + category + '.' + label


def qualify_raw(fixture, old, raw, report, candidates, names, source):
    """Assert every anchor; no recorded acceptance booleans or complete=True shortcut."""
    values, uncertainty = raw['values'], raw['uncertainty']
    if (
        not isinstance(values, dict)
        or not isinstance(uncertainty, dict)
        or values.keys() != uncertainty.keys()
    ):
        raise ValueError('raw result needs complete value and SU path maps')
    selected = {}
    for column, choices in candidates.items():
        present = choices & values.keys()
        if len(present) != 1:
            raise ValueError('raw column must select exactly one actually fitted named path')
        path = present.pop()
        if not label_owns(old['labels'][column], path, names, source):
            raise ValueError('raw label differs from its declared bank/site/field owner')
        selected[column] = path
    if len(set(selected.values())) != len(selected) or set(selected.values()) != values.keys():
        raise ValueError('raw fitted population has missing, duplicate or unowned paths')
    qualify_raw_numbers(fixture, old, raw, selected)
    qualify_terminal(old, raw, report)
    return selected


def qualify_raw_numbers(fixture, old, raw, selected):
    values, uncertainty = raw['values'], raw['uncertainty']
    n = len(old['labels'])
    if len(old['values']) != n or len(old['covariance']) != n * n:
        raise ValueError('independent raw vectors must retain their original dimensions')
    for column, path in selected.items():
        av, au = values[path], uncertainty[path]
        diagonal = old['covariance'][column * n + column]
        if (
            diagonal < 0
            or any(type(x) not in {int, float} or not math.isfinite(x) for x in (av, au))
            or au < 0
        ):
            raise ValueError('raw fitted operands must be finite with nonnegative SU')
        sigma = math.sqrt(diagonal)
        if not math.isclose(
            av,
            old['values'][column],
            rel_tol=fixture['relative_tolerance'],
            abs_tol=fixture['absolute_tolerance'],
        ) or abs(au - sigma) > max(
            numeric._UNCERTAINTY_RELATIVE * abs(sigma), numeric._UNCERTAINTY_ABSOLUTE
        ):
            raise ValueError('raw value or SU differs from the independent original anchor')
    for name, expected in fixture['native_start_and_finish'].items():
        actual = raw[name]
        if (
            type(actual) not in {int, float}
            or not math.isfinite(actual)
            or not math.isclose(
                actual,
                expected,
                rel_tol=fixture['relative_tolerance'],
                abs_tol=fixture['absolute_tolerance'],
            )
        ):
            raise ValueError('raw global fit anchor differs from the independent capture')


def qualify_terminal(old, raw, report):
    fields = {}
    for line in report.splitlines():
        if '=' in line:
            name, value = line.split('=', 1)
            if name in fields:
                raise ValueError('machine report must not duplicate fields')
            fields[name] = value
    count = fields.get('n_points_fitted', '')
    if not re.fullmatch(r'[1-9][0-9]*', count) or int(count) != old['n_data']:
        raise ValueError('raw machine-report fitted point count must match conditioning exactly')
    if (
        raw.get('converged') is not True
        or raw.get('status') != 'FitStatus.DONE'
        or fields.get('status') != 'done'
        or fields.get('converged') != 'true'
    ):
        raise ValueError('written reference requires a genuinely completed converged native fit')


def extra_records(root):
    """All fields of the three named missing categories, with exact owned loop rows."""
    records, order = {}, {}
    for path in sorted(root.rglob('*.edi')):
        name = path.relative_to(root).as_posix()
        block = document(path, name)
        for item in block:
            if item.pair is not None:
                tag, value = item.pair
                if tag.partition('.')[0] in EXTRA:
                    key = name, block.name, (), tag
                    if key in records:
                        raise ValueError('written extra scalar is duplicated')
                    records[key] = value
            elif item.loop is not None:
                extra_loop(item.loop, name, block.name, records, order)
    return records, order


def extra_loop(loop, name, block_name, records, order):
    categories = {tag.partition('.')[0] for tag in loop.tags}
    if not categories & EXTRA:
        return
    if categories != {'_linked_structure'} or '_linked_structure.structure_id' not in loop.tags:
        raise ValueError('written extra category has an undeclared loop shape')
    tags = list(loop.tags)
    if len(set(tags)) != len(tags):
        raise ValueError('written linked storage has duplicate columns')
    column = tags.index('_linked_structure.structure_id')
    ids = []
    for row in range(loop.length()):
        values = loop.values[row * len(tags) : (row + 1) * len(tags)]
        link = values[column]
        if link in {'?', '.'} or link in ids:
            raise ValueError('written linked storage needs unique available structure IDs')
        ids.append(link)
        for tag, value in zip(tags, values, strict=True):
            key = name, block_name, (link,), tag
            if key in records:
                raise ValueError('written extra storage cell is duplicated')
            records[key] = value
    order[name, block_name] = tuple(ids)


def compare_written(actual_root, reference_root, fixture):
    actual, expected = scientific(actual_root), scientific(reference_root)
    aligned = identity.align_to_frozen(
        actual,
        expected,
        actual_blocks=blocks(actual_root, actual),
        frozen_blocks=blocks(reference_root, expected),
    )
    compare_scientific(
        aligned, expected, fixture['relative_tolerance'], fixture['absolute_tolerance']
    )
    actual_extra, actual_order = extra_records(actual_root)
    expected_extra, expected_order = extra_records(reference_root)
    if (
        not expected_extra
        or actual_extra.keys() != expected_extra.keys()
        or actual_order != expected_order
    ):
        raise ValueError('written instrument/link/absorption inventory or row order changed')
    compare_scientific(
        {'extras': [[key[-1], actual_extra[key]] for key in expected_extra]},
        {'extras': [[key[-1], value] for key, value in expected_extra.items()]},
        fixture['relative_tolerance'],
        fixture['absolute_tolerance'],
    )
    # Opaque assets and whole-file reopen semantics remain the existing owner;
    # this comparison does not invent parity rules for unrelated metadata.
    actual_files = {
        p.relative_to(actual_root).as_posix() for p in actual_root.rglob('*') if p.is_file()
    }
    expected_files = {
        p.relative_to(reference_root).as_posix() for p in reference_root.rglob('*') if p.is_file()
    }
    if actual_files != expected_files:
        raise ValueError('written project file inventory changed')
    return {'scientific_documents': len(expected), 'extra_cells': len(expected_extra)}


def validate_capture_flags(flags):
    required = {'raw', 'ordinary_save', 'reopen', 'arrays', 'source_unchanged'}
    if (
        not isinstance(flags, dict)
        or flags.keys() != required
        or any(value is not True for value in flags.values())
    ):
        raise ValueError('written reference is incomplete')


def admit(root, case, reference):
    fixture, old, source, names, banks = inputs(root, case)
    producer_path, result_path = reference / 'producer.json', reference / 'result.json'
    producer, result = json.loads(producer_path.read_text()), json.loads(result_path.read_text())
    expected = {
        'case': case,
        'project': fixture['project'],
        'source_files': files(source),
        'fixture_files': {
            name: sha(
                root / 'tests/fixtures/e04_t11_wasm/catalogue_scientific' / (case + '-' + name)
            )
            for name in ('native.json', 'conditioning.json', 'conditioning-raw.json')
        },
    }
    if producer.get('schema') != 'ordinary-native-written/1' or any(
        producer.get(k) != v for k, v in expected.items()
    ):
        raise ValueError('written reference producer does not own this authenticated input')
    if result.get('producer_sha256') != sha(producer_path) or result.get('files') != files(
        reference / 'project'
    ):
        raise ValueError('written reference capture custody changed')
    validate_capture_flags(result.get('capture_flags'))
    if producer.get('recorder_sha256') != sha(__file__):
        raise ValueError('written reference recorder differs from the reviewed source')
    for field in ('module_sha256', 'module_path', 'build_commit', 'python', 'recorder_path'):
        if not isinstance(producer.get(field), str) or not producer[field]:
            raise ValueError('written reference is missing early primitive producer identity')
    for name, digest in result['captures'].items():
        if (
            name
            not in {
                'loaded.json',
                'raw.json',
                'machine.txt',
                'raw-arrays.npz',
                'written-arrays.npz',
                'reopened-arrays.npz',
            }
            or sha(reference / name) != digest
        ):
            raise ValueError('written reference retained capture changed')
    if set(result['captures']) != {
        'loaded.json',
        'raw.json',
        'machine.txt',
        'raw-arrays.npz',
        'written-arrays.npz',
        'reopened-arrays.npz',
    }:
        raise ValueError('written reference requires every captured domain')
    loaded = json.loads((reference / 'loaded.json').read_text())
    analysis = document(source / 'analysis/analysis.edi', 'analysis/analysis.edi')
    if loaded != {
        'fitting_mode': 'single' if case == 'lbco' else 'joint',
        'su_rule': 'iucr_99',
        'free_count': len(old['labels']),
        'max_iterations': int(analysis.find_value('_minimizer.max_iterations') or '0'),
        'chi_square_tolerance': float(
            analysis.find_value('_minimizer.chi_square_tolerance') or '0'
        ),
    }:
        raise ValueError('written reference loaded state differs from the source declarations')
    raw = json.loads((reference / 'raw.json').read_text())
    qualify_raw(
        fixture,
        old,
        raw,
        (reference / 'machine.txt').read_text(),
        raw_candidates(fixture, old, names, banks, source),
        names,
        source,
    )
    validate_arrays(reference, banks, fixture)
    return fixture


def validate_arrays(reference, banks, fixture):
    expected = {
        bank + '__' + field for bank, _ in banks.values() for field in (*ARRAY_FIELDS, 'axis')
    }
    with (
        np.load(reference / 'raw-arrays.npz', allow_pickle=False) as raw,
        np.load(reference / 'written-arrays.npz', allow_pickle=False) as written,
        np.load(reference / 'reopened-arrays.npz', allow_pickle=False) as reopened,
    ):
        if any(set(capture.files) != expected for capture in (raw, written, reopened)):
            raise ValueError('native array captures must retain every bank and public field')
        for key in expected:
            a, b = written[key], reopened[key]
            if not a.size or a.shape != b.shape or a.dtype != b.dtype:
                raise ValueError('written/reopened native arrays changed dimensions or type')
            same = (
                np.allclose(
                    a,
                    b,
                    rtol=fixture['relative_tolerance'],
                    atol=fixture['absolute_tolerance'],
                    equal_nan=True,
                )
                if a.dtype.kind in 'biufc'
                else np.array_equal(a, b)
            )
            if not same:
                raise ValueError('ordinary written-model reopening changed native arrays')
            if key.endswith((
                '__axis',
                '__intensity_meas',
                '__intensity_meas_su',
                '__calc_status',
            )):
                original = raw[key]
                same_input = (
                    np.array_equal(original, a, equal_nan=True)
                    if a.dtype.kind in 'biufc'
                    else np.array_equal(original, a)
                )
                if original.shape != a.shape or original.dtype != a.dtype or not same_input:
                    raise ValueError('ordinary Save changed measured input or mask arrays')


def capture_arrays(owner, output, banks, name):
    data = {}
    if set(owner.experiments.keys()) != {block for block, _ in banks.values()}:
        raise ValueError('live native arrays changed experiment bank inventory')
    for bank, experiment in owner.experiments.items():
        for field in ARRAY_FIELDS:
            data[bank + '__' + field] = np.asarray(getattr(experiment.data, field)).copy()
        data[bank + '__axis'] = np.asarray(experiment.data.axis()).copy()
    np.savez_compressed(output / name, **data)
    return data


def capture_loaded(project, source, case, old, output):
    if (
        project.analysis.fitting_mode != ('single' if case == 'lbco' else 'joint')
        or project.su_rule != 'iucr_99'
    ):
        raise ValueError('native reference changed the declared case mode or uncertainty rule')
    analysis = document(source / 'analysis/analysis.edi', 'analysis/analysis.edi')
    expected_max = int(analysis.find_value('_minimizer.max_iterations') or '0')
    expected_tolerance = float(analysis.find_value('_minimizer.chi_square_tolerance') or '0')
    loaded = {
        'fitting_mode': project.analysis.fitting_mode,
        'su_rule': project.su_rule,
        'free_count': len(project.free_parameters),
        'max_iterations': project._minimizer_max_iterations,
        'chi_square_tolerance': project._minimizer_chi_square_tolerance,
    }
    if (
        loaded['free_count'] != len(old['labels'])
        or loaded['max_iterations'] != expected_max
        or loaded['chi_square_tolerance'] != expected_tolerance
    ):
        raise ValueError('reference changed the original free set or minimizer declarations')
    (output / 'loaded.json').write_text(json.dumps(loaded, indent=2, allow_nan=False) + '\n')


def capture(root, case, output, module_sha256, build_commit):
    fixture, old, source, names, banks = inputs(root, case)
    extension = Path(edi._edi.__file__).resolve()
    if (
        extension.suffix not in {'.so', '.pyd'}
        or sha(extension) != module_sha256
        or edi.__build_commit__ != build_commit
    ):
        raise ValueError('native module differs from the root-elected actual build identity')
    if not output.is_absolute() or output.resolve().is_relative_to(source.resolve()):
        raise ValueError('reference output must be absolute and outside the authenticated input')
    output.mkdir(mode=0o700)  # Exclusive, never reuse a previous failed/reference capture.
    producer = {
        'schema': 'ordinary-native-written/1',
        'case': case,
        'project': fixture['project'],
        'source_files': files(source),
        'module_path': str(extension),
        'module_sha256': sha(extension),
        'build_commit': str(edi.__build_commit__),
        'python': str(Path(sys.executable).resolve()),
        'recorder_path': str(Path(__file__).resolve()),
        'recorder_sha256': sha(__file__),
        'fixture_files': {
            name: sha(
                root / 'tests/fixtures/e04_t11_wasm/catalogue_scientific' / (case + '-' + name)
            )
            for name in ('native.json', 'conditioning.json', 'conditioning-raw.json')
        },
    }
    # Persist and serialize BEFORE load/fit/Save: enum-bearing late metadata cannot
    # discard actual producer custody as it did in root497.
    (output / 'producer.json').write_text(json.dumps(producer, indent=2) + '\n')
    project = edi.Project.load(source)
    capture_loaded(project, source, case, old, output)
    starts = []
    result = project.analysis.fit(
        on_start=lambda preamble: starts.append(preamble.pre_fit.reduced_chi_square)
    )
    if len(starts) != 1:
        raise ValueError('native reference needs exactly one actual fit preamble')
    raw = {
        'initial_reduced_chi_square': starts[0],
        'final_reduced_chi_square': result.reduced_chi_square,
        'rwp': result.rwp,
        'iterations': result.iterations,
        'converged': result.converged,
        'status': str(result.status),
        'values': dict(result.values),
        'uncertainty': dict(result.uncertainty),
    }
    (output / 'raw.json').write_text(json.dumps(raw, indent=2, allow_nan=False) + '\n')
    report = edi.machine_report(project, result, edi.VerbosityEnum.FULL)
    (output / 'machine.txt').write_text(report)
    qualify_raw(
        fixture,
        old,
        raw,
        report,
        raw_candidates(fixture, old, names, banks, source),
        names,
        source,
    )

    capture_arrays(project, output, banks, 'raw-arrays.npz')
    destination = output / 'project'
    project.save_as(destination)
    capture_arrays(project, output, banks, 'written-arrays.npz')
    opened = edi.Project.load(destination)
    capture_arrays(opened, output, banks, 'reopened-arrays.npz')
    validate_arrays(output, banks, fixture)
    if files(source) != producer['source_files']:
        raise ValueError('reference operations changed the original catalogue input')
    record = {
        'producer_sha256': sha(output / 'producer.json'),
        'files': files(destination),
        'captures': {
            name: sha(output / name)
            for name in (
                'loaded.json',
                'raw.json',
                'machine.txt',
                'raw-arrays.npz',
                'written-arrays.npz',
                'reopened-arrays.npz',
            )
        },
        'capture_flags': {
            'raw': True,
            'ordinary_save': True,
            'reopen': True,
            'arrays': True,
            'source_unchanged': True,
        },
    }
    (output / 'result.json').write_text(json.dumps(record, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('capture', 'admit', 'compare', 'offline'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--case', choices=tuple(CASES), required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--module-sha256')
    parser.add_argument('--build-commit')
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--raw', type=Path)
    parser.add_argument('--machine', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.operation == 'capture':
        capture(args.root, args.case, args.reference, args.module_sha256, args.build_commit)
    else:
        if args.operation == 'offline':
            fixture, old, source, names, banks = inputs(args.root, args.case)
            qualify_raw(
                fixture,
                old,
                json.loads(args.raw.read_text()),
                args.machine.read_text(),
                raw_candidates(fixture, old, names, banks, source),
                names,
                source,
            )
        else:
            fixture = admit(args.root, args.case, args.reference)
        if args.operation in {'compare', 'offline'}:
            with tempfile.TemporaryDirectory(prefix='written-browser-') as temp:
                actual = Path(temp)
                for name, data in archive_files(args.archive).items():
                    target = actual / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                compare_written(actual, args.reference / 'project', fixture)
                if args.output is not None:
                    args.output.write_text(json.dumps(scientific(actual)))
    print(
        'OFFLINE scientific relationships only; historical producer custody remains missing'
        if args.operation == 'offline'
        else 'Qualified ordinary native-written reference; '
        'browser raw vectors are not reconstructed'
    )


if __name__ == '__main__':
    main()
