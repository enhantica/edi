# SPDX-License-Identifier: BSD-3-Clause
"""Source, retry and archive boundaries for prepared release inputs."""

import importlib.util
import io
import zipfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    'download_plan', Path(__file__).resolve().parents[3] / 'tools/release/download_plan.py'
)
DOWNLOAD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOWNLOAD)


@pytest.mark.parametrize('damage', ['none', 'source', 'failed', 'workflow', 'expired', 'attempt'])
def test_prepared_artifact_is_bound_to_source_and_successful_attempt(damage):
    run = {
        'path': '.github/workflows/release-plan.yml',
        'status': 'completed',
        'conclusion': 'success',
        'head_sha': 'a' * 40,
        'event': 'workflow_dispatch',
        'run_attempt': 2,
    }
    artifacts = [{'id': 19, 'name': 'release-plan-2', 'expired': False, 'size_in_bytes': 200}]
    if damage == 'source':
        run['head_sha'] = 'b' * 40
    elif damage == 'failed':
        run['conclusion'] = 'failure'
    elif damage == 'workflow':
        run['path'] = '.github/workflows/other.yml'
    elif damage == 'expired':
        artifacts[0]['expired'] = True
    elif damage == 'attempt':
        artifacts[0]['name'] = 'release-plan-1'
    if damage == 'none':
        assert DOWNLOAD.select_plan(run, artifacts, 'a' * 40) == 19
    else:
        with pytest.raises(ValueError, match=r'preparation|artifact'):
            DOWNLOAD.select_plan(run, artifacts, 'a' * 40)


@pytest.mark.parametrize('damage', ['none', 'traversal', 'symlink', 'oversized'])
def test_prepared_archive_is_bounded_and_contains_only_regular_metadata(tmp_path, damage):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ['plan.json', 'release.json', 'release-history.json', 'notes.md']:
            info = zipfile.ZipInfo(
                '../plan.json' if damage == 'traversal' and name == 'plan.json' else name
            )
            info.external_attr = (0o120777 if damage == 'symlink' else 0o100644) << 16
            archive.writestr(info, b'x' * (1024 * 1024 + 1) if damage == 'oversized' else b'{}')
    if damage == 'none':
        DOWNLOAD.unpack_plan(stream.getvalue(), tmp_path / 'inputs')
        assert (tmp_path / 'inputs/plan.json').read_bytes() == b'{}'
    else:
        with pytest.raises(ValueError, match='artifact'):
            DOWNLOAD.unpack_plan(stream.getvalue(), tmp_path / 'inputs')
        assert not (tmp_path / 'inputs').exists()
