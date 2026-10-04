"""Review-11 F10/F13/F15: independent locks, writer admission and qualified bytes."""

from __future__ import annotations

import json

import pytest
import yaml

from tests.integration.py.test_e09_t75_sdk_consumer import ABI_PACKAGES, ROOT, consumer
from tests.system.py.test_e09_t75_native_execution import assert_restored, native_producer, restore


def lock_packages(path, environment, platform):
    doc = yaml.safe_load(path.read_text())
    aliases = {p['name']: p.get('subdir', p['name']) for p in doc.get('platforms', [])}
    rows = doc['environments'][environment]['packages']
    out = {}
    for key, packages in rows.items():
        if aliases.get(key, key) != platform:
            continue
        for package in packages:
            if 'conda' not in package:
                continue
            filename = (
                package['conda'].rsplit('/', 1)[-1].removesuffix('.conda').removesuffix('.tar.bz2')
            )
            name, version, build = filename.rsplit('-', 2)
            out[name] = (version, build)
    return out


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
def test_f10_app_lock_consumes_the_same_independent_sdk_abi(platform):
    # Before: the sibling's live lock. After: the recorded independent producer lock,
    # regenerated only by tests/fixtures/e09_t75_sdk_abi/generate.py. CI has no sibling.
    producer = json.loads((ROOT / 'tests/fixtures/e09_t75_sdk_abi/producer-lock.json').read_text())
    assert producer['repo'] == 'enhantica/crysta' and producer['environment'] == 'cpp-ci', (
        ' F10 ABI reference must be the independent producer lock, never edi output'
    )
    sdk = {name: tuple(value) for name, value in producer['platforms'][platform].items()}
    app = lock_packages(ROOT / 'pixi.lock', 'app', platform)
    mismatch = {
        name: (sdk.get(name), app.get(name))
        for name in ABI_PACKAGES[platform]
        if sdk.get(name) != app.get(name) or name not in sdk
    }
    assert not mismatch, f' F10 actual app lock must consume the SDK ABI: {mismatch}'


@pytest.mark.parametrize('accident', ['worker', 'held-lock'])
def test_f13_direct_sdk_dependency_cannot_mutate_prefix_outside_writer_boundary(
    tmp_path, accident
):
    prefix = 'build/crysta-consumer-prefix'
    setup = f'mkdir -p {prefix}; echo previous-producer > {prefix}/sentinel\n'
    if accident == 'worker':
        setup += 'export PYTEST_XDIST_WORKER=gw0\n'
    else:
        setup += 'mkdir -p build/.core-build.lock.d\nexport EDI_CORE_BUILD_LOCK_WAIT_S=0\n'
    result, _ = consumer(tmp_path, command_override=setup + 'bash tools/ci/build-crysta.sh')
    sentinel = tmp_path / 'edi' / prefix / 'sentinel'
    assert sentinel.is_file(), (
        ' F13 worker and contending dependency must leave the active producer prefix intact'
    )
    assert result.returncode != 0, (
        ' F13 unauthorized prefix writers must refuse at the admission boundary'
    )


@pytest.mark.parametrize(
    'field', ['packages', 'schema', 'identity', 'source_tree', 'tested-bytes']
)
def test_f15_diagnostic_sdk_requires_independent_qualification(tmp_path, field):
    mutate = {
        'packages': "d['fingerprint']['packages']=[]",
        'schema': "d['schema']=0",
        'identity': "d['identity'] += '.dirty'",
        'source_tree': "d['source_tree']='unrecorded'",
        'tested-bytes': (
            "(p.parents[2]/'lib/libcrysta_core.a').write_bytes(b'changed after qualification')"
        ),
    }[field]
    command = (
        (
            "python3 - <<'INNER'\nimport json,os\nfrom pathlib import Path\np=Pat"
            "h(os.environ['CRYSTA_SDK_DIR'])/'share/crysta-sdk/manifest.json'\n"
            'd=json.loads(p.read_text())\n'
        )
        + mutate
        + '\np.write_text(json.dumps(d))\nINNER\nbash tools/ci/build-crysta.sh\n'
    )
    result, _ = consumer(tmp_path, command_override=command)
    assert result.returncode != 0, (
        f' F15 diagnostic SDK must refuse incomplete or stale {field} qualification'
    )


@pytest.mark.parametrize('accident', ['cache-cli', 'cache-tests', 'parent-member'])
@pytest.mark.usefixtures('private_native_workflow')
def test_f15_native_reuse_proves_current_bytes_and_its_extraction_root(tmp_path, accident):
    result = restore(tmp_path, 'audit', 'linux-64', defect=accident)
    runs = result[0]
    assert runs, ' F15 native consumer must execute its restore boundary'
    if accident == 'parent-member':
        assert runs[0].returncode != 0, ' F15 an archive rebased outside build/ci must refuse'
        assert not (tmp_path / 'edi/escaped.txt').exists(), (
            ' F15 rejected extraction cannot write outside its native tree'
        )
    elif all(r.returncode == 0 for r in runs):
        assert_restored(result)  # Restoring the original bytes is also an acceptable repair.
    else:
        assert runs[0].returncode == 0, (
            ' F15 cache challenge must first have a successfully restored control'
        )
        assert len(runs) == 2, (
            ' F15 cache challenge must first have a successfully restored control'
        )


@pytest.mark.usefixtures('private_native_workflow')
def test_f15_native_pack_observes_the_actual_linked_dependency(tmp_path):
    native_producer(tmp_path, 'linux-64', defect='linked-pin')
