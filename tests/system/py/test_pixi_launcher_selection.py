"""Exercise three installed Pixi versions through the actual manifest selector."""

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = ROOT / 'tools/ci/pixi-launcher.sh'


@pytest.mark.skipif(
    os.name == 'nt', reason='Multi-manifest CI uses the launcher on Linux and macOS'
)
def test_launcher_uses_three_exact_versions_and_refuses_a_range(tmp_path):
    assert LAUNCHER.is_file(), 'The CI checkout must supply the version-selecting launcher'
    home = tmp_path / 'home'
    tree_root = tmp_path / 'trees'
    tree_root.mkdir()
    versions = {'consumer': '0.76.2', 'engine': '0.76.3', 'baseline': '0.77.0'}
    manifests = {}
    for name, version in versions.items():
        installed = home / '.pixi/versions' / version / 'pixi'
        installed.parent.mkdir(parents=True)
        installed.write_text(f'#!/bin/sh\nprintf "%s\\n" "{version}"\n', encoding='utf-8')
        installed.chmod(0o755)
        manifest = tree_root / name / 'pixi.toml'
        manifest.parent.mkdir()
        manifest.write_text(f'requires-pixi = "=={version}"\n', encoding='utf-8')
        manifests[name] = manifest

    # A missing cache entry must fail here, rather than contacting any external host.
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    for program in ('curl', 'wget'):
        downloader = bin_dir / program
        downloader.write_text('#!/bin/sh\nexit 69\n', encoding='utf-8')
        downloader.chmod(0o755)

    env = {
        **os.environ,
        'HOME': str(home),
        'PATH': os.pathsep.join((str(bin_dir), os.environ['PATH'])),
    }
    env.pop('PIXI_PROJECT_MANIFEST', None)

    def invoke(cwd, *arguments, selected_manifest=None):
        child_env = dict(env)
        if selected_manifest is not None:
            child_env['PIXI_PROJECT_MANIFEST'] = str(selected_manifest)
        return subprocess.run(
            ['bash', LAUNCHER, *arguments, '--version'],
            cwd=cwd,
            env=child_env,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )

    child = manifests['baseline'].parent / 'child'
    child.mkdir()
    for result, wanted in [
        (invoke(child), versions['baseline']),
        (invoke(child, selected_manifest=manifests['engine']), versions['engine']),
        (
            invoke(
                child,
                '--manifest-path',
                manifests['consumer'],
                selected_manifest=manifests['engine'],
            ),
            versions['consumer'],
        ),
        (invoke(tree_root), versions['baseline']),
    ]:
        assert result.returncode == 0 and result.stdout.strip() == wanted, (
            f'The manifest must select launcher version {wanted}: {result.stderr}'
        )

    bad = tree_root / 'bad.toml'
    for declaration in ('>=0.76', '==0.77.1'):
        bad.write_text(f'requires-pixi = "{declaration}"\n', encoding='utf-8')
        result = invoke(tree_root, '--manifest-path', bad)
        assert result.returncode != 0 and result.stdout.strip() not in versions.values(), (
            f'A range or an unavailable pin must refuse without a fallback: {declaration}'
        )
