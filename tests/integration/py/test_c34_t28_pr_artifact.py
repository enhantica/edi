"""G6: acquisition binds API provenance, pin, tested bytes and ABI.

Independent  byte/lock fixtures are wrapped in synthetic GitHub REST
records. They are executable protocol controls, not a captured GitHub run or the
separate pack-sdk-at-main integration witness required by the reviewed plan.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import tarfile
import zipfile
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest

from tests.integration.py.test_e09_t75_sdk_consumer import SHA, consumer


class ArtifactAPI:
    """An addressed REST store. It records unsupported calls even if a caller catches them."""

    def __init__(self, module, run, jobs, artifacts, archives):
        self.module = module
        self.runs = [run]
        self.selectors = {run['id']: (SHA, 'pull_request')}
        self.jobs = {run['id']: jobs}
        self.artifacts = {run['id']: artifacts}
        self.archives = archives
        self.calls = []
        self.refusals = []
        self.releases = {}

    def reject(self, url):
        self.refusals.append(url)
        self.module.refuse(' unsupported addressed artifact transport: ' + url)

    def __call__(self, url, *, accept, out=None, absent_ok=False):  # noqa: PLR0912, PLR0915
        self.calls.append(url)
        parsed = urlsplit(url)
        prefix = '/repos/enhantica/crysta'
        if (parsed.scheme, parsed.netloc) != ('https', 'api.github.com'):
            self.reject(url)
        if not parsed.path.startswith(prefix + '/') or accept != 'application/vnd.github+json':
            self.reject(url)
        path = parsed.path[len(prefix) :]
        query = parse_qs(parsed.query, keep_blank_values=True)
        if parsed.fragment or any(len(value) != 1 for value in query.values()):
            self.reject(url)
        if path.startswith('/releases/tags/build-'):
            if query or out is not None:
                self.reject(url)
            tag = path.rsplit('/', 1)[-1]
            if tag in self.releases:
                return json.dumps(self.releases[tag]).encode()
            if absent_ok:
                return None
            self.module.refuse('fixture release lookup returned HTTP 404')
        if absent_ok:
            self.reject(url)
        if path in self.archives:
            if out is None or query:
                self.reject(url)
            out.write_bytes(self.archives[path])
            return b''
        if out is not None:
            self.reject(url)
        query.setdefault('page', ['1'])
        if path == '/actions/runs':
            if set(query) != {'head_sha', 'event', 'page', 'per_page'}:
                self.reject(url)
            if query['event'][0] not in {'pull_request', 'push', 'workflow_dispatch'}:
                self.reject(url)
            rows = [
                r
                for r in self.runs
                if self.selectors.get(r['id'], (r['head_sha'], r['event']))
                == (query['head_sha'][0], query['event'][0])
            ]
            key = 'workflow_runs'
        else:
            match = re.fullmatch(r'/actions/runs/(\d+)/(jobs|artifacts)', path)
            if not match:
                self.reject(url)
            run_id, key = int(match[1]), match[2]
            store = self.jobs if key == 'jobs' else self.artifacts
            if run_id not in store:
                self.reject(url)
            allowed = {'page', 'per_page', 'filter'} if key == 'jobs' else {'page', 'per_page'}
            if set(query) != allowed or (key == 'jobs' and query['filter'] != ['all']):
                self.reject(url)
            rows = store[run_id]
        try:
            page, size = int(query['page'][0]), int(query['per_page'][0])
        except ValueError:
            self.reject(url)
        if not 1 <= size <= 100 or page < 1:
            self.reject(url)
        return json.dumps({
            'total_count': len(rows),
            key: rows[(page - 1) * size : page * size],
        }).encode()


def acquisition(tmp_path, defect=None, platform='osx-arm64', *, prepare_only=False):  # noqa: PLR0912, PLR0914, PLR0915
    env, root, sdk = consumer(tmp_path, platform=platform, prepare_only=True)
    manifest_path = sdk / 'share/crysta-sdk/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    job = 'checks (macOS)' if platform == 'osx-arm64' else 'checks (Linux)'
    manifest['tested']['job_name'] = job
    fields = {
        'manifest-sha': ('source_sha', 'c3' * 20),
        'manifest-run': ('run_id', 75091),
        'manifest-attempt': ('run_attempt', 1),
        'manifest-job': ('job_name', 'unrelated job'),
    }
    if defect in fields:
        key, value = fields[defect]
        (manifest if key == 'source_sha' else manifest['tested'])[key] = value
    if defect == 'abi':
        manifest['fingerprint']['packages'][0]['version'] = 'wrong-version'
    manifest_path.write_text(json.dumps(manifest))
    if defect == 'tested-file':
        (sdk / 'lib/libcrysta_core.a').write_bytes(b'different untested library')
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode='w:gz') as archive:
        for path in sorted(sdk.rglob('*')):
            if path.is_file():
                archive.add(path, arcname=path.relative_to(sdk).as_posix())
    blob = raw.getvalue()
    digest = hashlib.sha256(blob).hexdigest()
    pin = root / 'pixi.toml'
    pin.write_text(
        pin.read_text().replace('7' * 64, '8' * 64 if defect == 'pin-digest' else digest)
    )
    name = f'crysta-sdk-{SHA}-{platform}.tar.gz'
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, 'w') as archive:
        archive.writestr(name, blob)
        archive.writestr(
            name + '.sha256', ('9' * 64 if defect == 'sidecar' else digest) + '  ' + name + '\n'
        )
    run = {
        'id': 75090,
        'head_sha': SHA,
        'event': 'pull_request',
        'path': '.github/workflows/ci.yml',
        'run_attempt': 2,
        'status': 'in_progress',
        'conclusion': None,
    }
    jobs = [
        {
            'id': 7509001,
            'run_id': 75090,
            'run_attempt': 1,
            'name': job,
            'conclusion': 'failure',
            'status': 'completed',
        },
        {
            'id': 7509002,
            'run_id': 75090,
            'run_attempt': 2,
            'name': job,
            'conclusion': 'success',
            'status': 'completed',
        },
    ]
    artifact = {
        'id': 2806 if platform == 'osx-arm64' else 2807,
        'name': f'crysta-sdk-{platform}',
        'expired': False,
        'created_at': '2026-10-01T22:00:00Z',
        'workflow_run': {'id': 75090, 'head_sha': SHA, 'head_branch': 'paired-topic'},
    }
    if defect == 'run-head':
        run['head_sha'] = 'c3' * 20
    if defect == 'run-workflow':
        run['path'] = '.github/workflows/other.yml'
    if defect == 'run-event':
        run['event'] = 'push'
    if defect == 'failed-job':
        jobs[-1]['conclusion'] = 'failure'
    if defect == 'earlier-attempt':
        jobs[-1]['run_attempt'] = 3
    if defect == 'expired':
        artifact['expired'] = True
    if defect == 'artifact-head':
        artifact['workflow_run']['head_sha'] = 'c3' * 20
    if defect == 'artifact-run':
        artifact['workflow_run']['id'] = 75089
    spec = importlib.util.spec_from_file_location('c34_sdk', root / 'tools/ci/crysta_sdk.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    api = ArtifactAPI(
        module,
        run,
        jobs,
        [] if defect == 'missing' else [artifact],
        {f'/actions/artifacts/{artifact["id"]}/zip': zipped.getvalue()},
    )
    if prepare_only:
        return {
            'env': env,
            'root': root,
            'module': module,
            'api': api,
            'digest': digest,
            'blob': blob,
            'name': name,
            'platform': platform,
        }
    stdout, stderr = io.StringIO(), io.StringIO()
    with (
        patch.dict(os.environ, env, clear=True),
        patch.object(module, 'curl', api),
        contextlib.redirect_stdout(stdout),
        contextlib.redirect_stderr(stderr),
    ):
        code = module.main(['fetch', '--platform', platform])
    assert not api.refusals, ' F5 acquisition cannot swallow a transport refusal'
    return code, stdout.getvalue() + stderr.getvalue(), api.calls, root


@pytest.mark.parametrize('platform', ['linux-64', 'osx-arm64'])
def test_matching_pr_artifact_is_usable_before_the_whole_run_finishes(tmp_path, platform):
    code, output, calls, root = acquisition(tmp_path, platform=platform)
    assert code == 0, ' G6 the tested PR artifact must build without a release: ' + output
    installed = root / 'build/crysta-sdk' / f'{SHA}-{platform}'
    assert (
        installed / 'lib/libcrysta_core.a'
    ).read_bytes() == b'independent static library bytes\x00\x17', (
        ' G6 the consumer installs the exact qualified library from the addressed artifact'
    )
    assert any('/actions/artifacts/' in call and call.endswith('/zip') for call in calls), (
        ' G6 the positive control must traverse the artifact acquisition route'
    )


@pytest.mark.parametrize(
    'defect',
    [
        'run-head',
        'run-workflow',
        'run-event',
        'failed-job',
        'earlier-attempt',
        'manifest-sha',
        'manifest-run',
        'manifest-attempt',
        'manifest-job',
        'artifact-head',
        'artifact-run',
        'sidecar',
        'pin-digest',
        'tested-file',
        'abi',
        'missing',
        'expired',
    ],
)
def test_artifact_substitutions_refuse_after_the_matching_control(tmp_path, defect):
    good = tmp_path / 'control'
    good.mkdir()
    code, output, _, _ = acquisition(good)
    assert code == 0, ' G6 refusal controls must first admit the matching PR artifact: ' + output
    bad = tmp_path / defect
    bad.mkdir()
    code, output, _, _ = acquisition(bad, defect)
    assert code != 0, f' G6 {defect} cannot acquire an untested or unbound SDK: ' + output
    assert output.strip(), ' G6 every acquisition refusal must retain a named cause'
    if defect in {'missing', 'expired'}:
        assert 'crysta-sdk-osx-arm64' in output and 're-pin' in output and 're-run' in output, (
            ' I13 unavailable artifacts must name the artifact and the repair'
        )
