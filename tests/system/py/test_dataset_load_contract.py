"""Batch organization and copy defaults use independent synthetic file inputs."""

import json
from pathlib import Path

import pytest

from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def dataset_host(tmp_path_factory):
    with run_online_host(
        tmp_path_factory.mktemp('dataset-loader'),
        load_groups_only=True,
        failure_entries=False,
        offline_http=True,
        session_type='DatasetLoadSession',
    ) as host:
        yield host


def inputs(host, folder, count, total_bytes=None):
    folder.mkdir()
    files, rows = [], []
    for index in range(count):
        values = [
            [21.5 + k * 0.7, 17.25 + index * 11 + k * 2.5, 0.75 + k * 0.25] for k in range(4)
        ]
        path = folder / f'sample{index}.xye'
        path.write_text(''.join(' '.join(map(str, row)) + '\n' for row in values))
        files.append(path.as_uri())
        rows.append(values)
    if total_bytes is not None:
        first = Path(folder / f'sample{count - 1}.xye')
        with first.open('r+b') as file:
            file.truncate(
                total_bytes
                - sum(path.stat().st_size for path in folder.glob('*.xye') if path != first)
            )
    record = {
        'files': files,
        'rows': rows,
        'bytes': sum(path.stat().st_size for path in folder.glob('*.xye')),
    }
    (host.mailbox / 'datasets.json').write_text(json.dumps(record))
    return record


@pytest.mark.parametrize('count', [4, 5, 6, 19, 20, 21])
def test_file_count_defaults_and_fit_wording(dataset_host, tmp_path, count):
    inputs(dataset_host, tmp_path / 'external-data', count)
    dataset_host.check('dataset_defaults')


@pytest.mark.parametrize('size', [50 * 1024 * 1024 - 1, 50 * 1024 * 1024, 50 * 1024 * 1024 + 1])
def test_copy_size_default_at_each_boundary(dataset_host, tmp_path, size):
    inputs(dataset_host, tmp_path / 'external-data', 2, size)
    dataset_host.check('dataset_defaults')


def test_separate_equals_individual_copies_and_switches_to_joint(dataset_host, tmp_path):
    inputs(dataset_host, tmp_path / 'external-data', 3)
    dataset_host.check('dataset_separate')


def test_scan_links_external_files_and_stays_single(dataset_host, tmp_path):
    inputs(dataset_host, tmp_path / 'external-data', 3)
    dataset_host.check('dataset_scan')


def test_scan_template_choice_is_undoable(dataset_host, tmp_path):
    inputs(dataset_host, tmp_path / 'external-data', 3)
    dataset_host.check('dataset_template')


def test_missing_external_scan_opens_and_locate_restores_it(dataset_host, tmp_path):
    folder = tmp_path / 'external-data'
    record = inputs(dataset_host, folder, 3)
    moved = tmp_path / 'moved-data'
    record['moved'] = moved.as_uri()
    (dataset_host.mailbox / 'datasets.json').write_text(json.dumps(record))
    dataset_host.check('linked_prepare')
    folder.rename(moved)
    dataset_host.check('linked_reopen')


@pytest.mark.parametrize(
    ('count', 'size'), [(20, None), (21, None), (2, 50 * 1024 * 1024), (2, 50 * 1024 * 1024 + 1)]
)
def test_include_data_on_save_follows_copy_defaults(dataset_host, tmp_path, count, size):
    inputs(dataset_host, tmp_path / 'external-data', count, size)
    dataset_host.check('save_policy')


@pytest.mark.parametrize('size', [100 * 1024 * 1024 - 1, 100 * 1024 * 1024, 100 * 1024 * 1024 + 1])
def test_large_save_warning_boundary_and_choices(dataset_host, tmp_path, size):
    record = inputs(dataset_host, tmp_path / 'external-data', 2, size)
    record['warning'] = True
    (dataset_host.mailbox / 'datasets.json').write_text(json.dumps(record))
    dataset_host.check('save_policy')
