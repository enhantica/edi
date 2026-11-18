# SPDX-License-Identifier: BSD-3-Clause
"""User-visible regressions exercised in the real offline application host."""

import os
from pathlib import Path
from unittest import mock

import pytest

from tests.fixtures.post_release_stability.inputs import generate
from tests.integration.app.native_actor import NativeActor

CASES = [
    'a_series_survive_hover_and_analysis_switch',
    'b_broken_relation_is_a_reportable_popup',
    'd_asymmetric_unit_keeps_cobalt_sites',
    'e_magnetic_cif_menu_and_drop:0-menu',
    'e_magnetic_cif_menu_and_drop:1-drop',
]
NATIVE_FILE = 'tst_post_release_stability.qml'
NATIVE_SELECTORS = {
    f'test_user_stability[{case}]': 'PostReleaseStability::test_' + case for case in CASES
}


@pytest.fixture(scope='module')
def actor(request, tmp_path_factory):
    selected = [
        item.name
        for item in request.session.items
        if getattr(item, 'module', None) is request.module
    ]
    mapping = request.module.NATIVE_SELECTORS
    assert selected == [name for name in mapping if name in selected], (
        'The streamed native cases retain their declared Qt execution order'
    )
    root = Path(__file__).resolve().parents[3]
    collection = (root / 'tests/fixtures/online_sources/easydiffraction').as_uri()
    inputs = generate(tmp_path_factory.mktemp('stability-inputs'))
    with mock.patch.dict(
        os.environ,
        {
            'EDI_ONLINE_SOURCES': f'cod={collection};easydiffraction={collection}',
            'EDI_ACCEPTANCE_REFERENCE': str(inputs),
            'OMP_NUM_THREADS': '1',
            'OPENBLAS_NUM_THREADS': '1',
        },
    ):
        native = NativeActor(
            tmp_path_factory.mktemp('stability-owner'),
            NATIVE_FILE,
            [mapping[name] for name in selected],
            timeout=40,
        )
        try:
            yield native
        finally:
            native.close()


@pytest.mark.parametrize('case', CASES)
def test_user_stability(case, actor):
    actor.run('PostReleaseStability::test_' + case)
