"""Portable catalogue identities do not inherit the host path separator."""

import json
from pathlib import PurePosixPath, PureWindowsPath

import pytest

from tools.dev import example_metadata


@pytest.mark.parametrize('path_type', [PurePosixPath, PureWindowsPath])
@pytest.mark.parametrize(
    'case',
    [
        'pd-neut-cwl_lbco-hrpt',
        'pd-neut-tof_ncaf-wish',
        'sc-neut-cwl_tb2ti2o7-heidi_simulation',
        'sc-neut-cwl_cosio-heidi',
    ],
)
def test_real_example_description_matches_committed_metadata_on_both_path_styles(
    monkeypatch, path_type, case
):
    expected = json.loads(example_metadata.CATALOG.read_text(encoding='utf-8'))['examples'][case]
    native = type(example_metadata.ROOT)
    relative_to = native.relative_to

    def relative_path(self, *args, **kwargs):
        relative = relative_to(self, *args, **kwargs)
        return path_type(*relative.parts)

    monkeypatch.setattr(native, 'relative_to', relative_path)
    actual = example_metadata.describe(case)
    assert actual == expected, 'Host separators cannot change source ids or any descriptive field'
    assert all('/' in item and '\\' not in item for item in actual['sources'])
