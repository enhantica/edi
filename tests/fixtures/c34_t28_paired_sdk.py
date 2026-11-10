"""Real stale-pin Git inputs for 's cache and native handoff witnesses.

Only the addressed GitHub transport is substituted. These planted SDK bytes are
protocol witnesses; the separate live producer-built artifact remains outstanding.
"""

import base64
import contextlib
import importlib
import inspect
import io
import json
import os
import shutil
import subprocess
import sys
from unittest.mock import patch

from tests.integration.py.test_c34_t28_pr_artifact import ArtifactAPI, acquisition
from tests.system.py.test_e09_t75_pin_currency import currency_world


def paired_sdk(tmp_path, platform, event):
    history, stale = currency_world(tmp_path / 'history', 'paired-stale')
    head = history._git('rev-parse', 'paired-topic').strip()
    tree = history._git('rev-parse', head + '^{tree}').strip()
    assert head != stale, ' the intermediate witness must contain a genuinely stale pin'
    producer = importlib.import_module('tests.integration.py.test_c34_t28_pr_artifact')
    consumer = importlib.import_module('tests.integration.py.test_e09_t75_sdk_consumer')
    home = tmp_path / 'acquire'
    home.mkdir()
    with (
        patch.object(producer, 'SHA', head),
        patch.object(consumer, 'SHA', head),
        patch.object(consumer, 'TREE', tree),
    ):
        context = acquisition(home, platform=platform, prepare_only=True)
    declared_home = tmp_path / 'declared'
    declared_home.mkdir()
    with (
        patch.object(producer, 'SHA', stale),
        patch.object(consumer, 'SHA', stale),
        patch.object(consumer, 'TREE', history._git('rev-parse', f'{stale}^{{tree}}').strip()),
    ):
        declared = acquisition(declared_home, platform=platform, prepare_only=True)
    with patch.dict(os.environ, declared['env'], clear=True):
        manifest = declared['module'].check(declared_home / 'sdk', platform)
    assert manifest['source_sha'] == stale, (
        ' the declared pin digest belongs to its independently qualified old SDK'
    )
    root = context['root']
    pin = root / 'pixi.toml'
    pin.write_text(
        pin.read_text().replace(head, stale).replace(context['digest'], declared['digest'])
    )
    shutil.copytree(history.edi / '.git', root / '.git')
    commit(root, history.git, 'Commit the independently prescribed stale pin', 'pixi.toml')
    git = home / 'bin/git'
    git.unlink()
    git.symlink_to(history.git)
    env = {
        **context['env'],
        'GIT_CONFIG_GLOBAL': history.env['GIT_CONFIG_GLOBAL'],
        'GIT_CONFIG_NOSYSTEM': '1',
        'GITHUB_EVENT_NAME': event,
        'GITHUB_HEAD_REF': 'paired-topic' if event == 'pull_request' else '',
        'GITHUB_REF_NAME': 'paired-topic',
        'GITHUB_TOKEN': 'fixture-token',  # inert, public transport credential
        'CRYSTA_SOURCE_SHA': head,
    }
    env.pop('CRYSTA_SDK_DIR', None)
    return {
        **context,
        'env': env,
        'head': head,
        'stale': stale,
        'history': history,
        'declared_digest': declared['digest'],
        'home': home,
    }


def commit(root, realgit, subject, *paths):
    for args in [('add', '--', *paths), ('commit', '-qm', subject)]:
        subprocess.run(
            [
                realgit,
                '-C',
                str(root),
                '-c',
                'user.name=Fixture',
                '-c',
                'user.email=fixture@example.invalid',
                '-c',
                'core.hooksPath=/dev/null',
                *args,
            ],
            check=True,
            capture_output=True,
            timeout=2,
        )


def fetch(context):
    output = io.StringIO()
    with (
        patch.dict(os.environ, context['env'], clear=True),
        patch.object(context['module'], 'curl', context['api']),
        contextlib.redirect_stdout(output),
        contextlib.redirect_stderr(output),
    ):
        code = context['module'].main(['fetch', '--platform', context['platform']])
    assert not context['api'].refusals, (
        ' F5 the artifact consumer cannot swallow an addressed transport refusal'
    )
    return code, output.getvalue()


def install_transport(context, env):
    """Serve subprocess GETs from the same independently addressed records."""
    api = context['api']
    path = context['home'] / 'paired-api.json'
    record = {
        'runs': api.runs,
        'selectors': api.selectors,
        'jobs': api.jobs,
        'artifacts': api.artifacts,
        'archives': {key: base64.b64encode(value).decode() for key, value in api.archives.items()},
        'calls': [],
        'refusals': [],
        'releases': api.releases,
    }
    path.write_text(json.dumps(record))
    env['C34_PAIRED_API_RECORDS'] = str(path)
    curl = context['home'] / 'bin/curl'
    curl.write_text(
        '#!'
        + sys.executable
        + '\n'
        + 'import base64,json,os,re,sys\nfrom pathlib import Path\n'
        + 'from urllib.parse import parse_qs,urlsplit\nfrom types import SimpleNamespace\n'
        + 'SHA = '
        + repr(context['head'])
        + '\n'
        + inspect.getsource(ArtifactAPI)
        + r"""
p = Path(os.environ['C34_PAIRED_API_RECORDS'])
r = json.loads(p.read_text())
def refused(message):
    raise RuntimeError(message)
api = object.__new__(ArtifactAPI)
api.module = SimpleNamespace(refuse=refused)
for key in ('runs','calls','refusals','releases'):
    setattr(api,key,r[key])
api.selectors = {int(k):tuple(v) for k,v in r['selectors'].items()}
api.jobs = {int(k):v for k,v in r['jobs'].items()}
api.artifacts = {int(k):v for k,v in r['artifacts'].items()}
api.archives = {k:base64.b64decode(v) for k,v in r['archives'].items()}
a = sys.argv[1:]
urls = [v for v in a if v.startswith('https://')]
headers = [a[i+1] for i,v in enumerate(a[:-1]) if v in ('-H','--header')]
accepts = [v.partition(':')[2].strip() for v in headers if v.lower().startswith('accept:')]
out = next((a[i+1] for i,v in enumerate(a[:-1]) if v in ('-o','--output')),None)
try:
    if (len(urls)!=1 or len(accepts)!=1
        or any(v in a for v in ('-X','--request','--data','-d','-I','--head'))):
        api.reject(repr(a))
    data = api(urls[0],accept=accepts[0],out=Path(out) if out else None,
               absent_ok='/releases/tags/' in urls[0])
    if data is None:
        raise RuntimeError('HTTP 404: release absent')
    if out is None:
        sys.stdout.buffer.write(data)
except RuntimeError as refusal:
    print(str(refusal),file=sys.stderr)
    sys.exit(22 if str(refusal).startswith('HTTP 404') else 92)
finally:
    r['calls'],r['refusals'] = api.calls,api.refusals
    p.write_text(json.dumps(r))
"""
    )
    curl.chmod(0o755)
