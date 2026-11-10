"""F07: a quote-only edit has one admission decision across semantic readers.

A source boundary may consistently narrow the pin form; a semantic reader cannot
independently disagree with the form that SDK acquisition admits.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from tests.integration.py.test_e09_t75_sdk_consumer import consumer
from tests.system.py.test_e09_t75_native_execution import restore
from tests.system.py.test_e09_t75_sdk_update import update


def sdk_form(base, quoted):
    base.mkdir()
    env, repo, _ = consumer(base, platform='linux-64', download=True, prepare_only=True)
    if quoted:
        pin = repo / 'pixi.toml'
        pin.write_text(pin.read_text().replace(chr(34), chr(39)))
    result = subprocess.run(
        [sys.executable, 'tools/ci/crysta_sdk.py', 'fetch', '--platform', 'linux-64'],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=3,
    )
    return result, env, repo


@pytest.mark.parametrize('reader', ['pairing', 'native', 'updater'])
def test_semantic_pin_readers_share_source_boundary_admission(tmp_path, reader, request):
    if reader == 'native':
        request.getfixturevalue('private_native_workflow')
    good, _, _ = sdk_form(tmp_path / 'source-control', False)
    assert good.returncode == 0, ' I26 canonical complete pin must acquire its SDK'
    source, env, repo = sdk_form(tmp_path / 'quoted-source', True)
    if reader == 'pairing':

        def run(root, childenv):
            return subprocess.run(
                ['bash', 'tools/ci/crysta-source.sh'],
                cwd=root,
                env={**childenv, 'GITHUB_EVENT_NAME': 'push'},
                capture_output=True,
                text=True,
                check=False,
                timeout=3,
            )

        _, control_env, control_repo = sdk_form(tmp_path / 'pair-control', False)
        control = run(control_repo, control_env)
        observed = run(repo, env)
    elif reader == 'native':
        control_home = tmp_path / 'native-control'
        control_home.mkdir()
        control = restore(control_home, 'core', 'linux-64')[0][-1]
        subject = tmp_path / 'native-subject'
        subject.mkdir()
        observed = restore(subject, 'core', 'linux-64', defect='single-quoted-pin')[0][-1]
    else:
        control_home = tmp_path / 'update-control'
        control_home.mkdir()
        control = update(control_home)[0][-1]
        subject = tmp_path / 'update-subject'
        subject.mkdir()
        observed = update(subject, 'single-quoted-main')[0][-1]
    assert control.returncode == 0, f' I26 canonical {reader} control must admit: {control.stderr}'
    assert (observed.returncode == 0) == (source.returncode == 0), (
        f' I26 {reader} must share SDK source admission after a quote-only pin edit'
    )
