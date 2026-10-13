"""Effective shared recipes, selected GUI source and served browser artifact identities."""

import hashlib
import subprocess
from pathlib import Path


def files(directory):
    result = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink() and not path.is_file():
            raise RuntimeError(
                'Qualified GUI/browser trees refuse linked directories or broken links'
            )
        if path.is_file():
            result[str(path.relative_to(directory))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return result


def dependencies(owner, root):
    gui = root / 'build/app/_deps/gui_components-src'
    selected = gui.is_dir()
    identity = {'selected': selected}
    if selected:
        identity.update(path=str(gui.resolve()), files=files(gui / 'src'))
        identity['git'] = (gui / '.git').exists()
        if identity['git']:
            identity['revision'] = subprocess.check_output(
                ['git', '-C', str(gui), 'rev-parse', 'HEAD'], text=True
            ).strip()
            identity['status'] = subprocess.check_output(
                ['git', '-C', str(gui), 'status', '--porcelain', '--', 'src'], text=True
            )
    recipes = [
        root / 'tests/fixtures/scan_app/build_probe.py',
        root / 'tests/conftest.py',
        root / 'tools/ci/app-platform.sh',
    ]
    recipes.extend((root / 'tests/fixtures/app_environment').glob('*.py'))
    if owner == 'selector':
        recipes.extend(
            root / 'tests/fixtures/scan_screen' / name for name in ('build.py', 'harness.py')
        )
    return {
        'gui': identity,
        'recipes': {
            str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            if path.is_file()
            else None
            for path in sorted(recipes)
        },
    }


def validate_dependencies(receipt, owner, root):
    if receipt.get('dependencies') != dependencies(owner, root):
        raise RuntimeError('App receipt refuses changed or unsealed GUI/shared recipe inputs')


def browser_bundle(executable):
    site = executable.parent
    for name in ('edi_app.html', 'edi_app.js', executable.name):
        if not (site / name).is_file():
            raise RuntimeError('Browser bundle requires its HTML, JavaScript and Wasm assets')
    # Both browser servers can serve any file below this directory, including workers/resources.
    return files(site)


def seal_bundle(receipt):
    if receipt['backend'] == 'browser':
        receipt['browser_bundle'] = browser_bundle(Path(receipt['executable']))


def validate_bundle(receipt):
    if receipt['backend'] == 'browser' and receipt.get('browser_bundle') != browser_bundle(
        Path(receipt['executable'])
    ):
        raise RuntimeError('App receipt refuses changed or unsealed served browser assets')
