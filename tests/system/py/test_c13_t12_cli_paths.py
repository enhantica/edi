"""E18: real CLI writes preflight all targets, preserving project and external bytes."""

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tests/integration/py'))
from c13_t12_support import engine, loops, snapshot  # noqa: E402


def command():
    if engine.__name__ == 'edi':
        return [sys.executable, '-m', 'edi']
    override = os.environ.get('C13_T12_BASELINE_CLI')
    binaries = (
        [Path(override)] if override else sorted((ROOT / 'build').glob('cp312-abi3*/crysta'))
    )
    assert binaries, ' requires a built native CLI candidate'
    assert binaries[0].is_file(), ' CLI witness requires the built user executable'
    return [str(binaries[0])]


def vehicle(tmp_path, name, *, first_valid=False):
    structure, experiment, _, _ = loops._texts('data')
    root = tmp_path / 'project'
    (root / 'structures').mkdir(parents=True)
    (root / 'experiments').mkdir()
    (root / 'structures/structure.edi').write_text(structure)
    if first_valid:
        (root / 'experiments/a_valid.edi').write_text(
            experiment.replace('data_experiment', 'data_a_valid')
        )
    filename = 'z_bad' if first_valid else ('C:bank' if name == 'C:bank' else 'input')
    (root / 'experiments' / (filename + '.edi')).write_text(
        experiment.replace('data_experiment', 'data_' + name)
    )
    return root


def run_cli(root, *options):
    arguments = ['calc', str(root)] if engine.__name__ == 'edi' else [str(root), 'calc']
    return subprocess.run(
        [*command(), *arguments, *options],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=25,
        check=False,
    )


@pytest.mark.parametrize('shape', ['drive', 'absolute', 'valid-then-drive', 'valid-then-absolute'])
def test_cli_refuses_name_before_any_project_or_external_write(tmp_path, shape):
    external = tmp_path / 'absolute/target.edi'
    external.parent.mkdir()
    external.write_bytes(b'data_external\n# literal external sentinel\n')
    identity = str(external.with_suffix('')) if shape.endswith('absolute') else 'C:bank'
    root = vehicle(tmp_path, identity, first_valid=shape.startswith('valid-then'))
    before = snapshot(tmp_path)
    dry = run_cli(root, '--dry')
    assert dry.returncode == 0, (
        ' out-of-domain persisted names remain valid for CLI calculation without writing'
    )
    assert snapshot(tmp_path) == before, ' CLI --dry leaves all files unchanged'
    model = engine.Project.load(root)
    model.analysis.calculate()
    assert snapshot(tmp_path) == before, (
        ' model calculation on unusual names does not perform filesystem writes'
    )
    completed = run_cli(root)
    diagnostic = completed.stdout + completed.stderr
    assert completed.returncode != 0, ' CLI must refuse an out-of-domain write target'
    assert identity in diagnostic, ' CLI refusal names the exact supplied bank'
    assert 'experiment' in diagnostic.lower(), (
        ' CLI path refusal must name the experiment and supplied identity'
    )
    assert snapshot(tmp_path) == before, (
        ' all-target preflight must preserve earlier banks and every external target'
    )


def test_real_cli_valid_write_is_idempotent(tmp_path):
    root = vehicle(tmp_path, 'bank')
    (root / 'experiments/input.edi').rename(root / 'experiments/bank.edi')
    first = run_cli(root)
    assert first.returncode == 0, ' valid CLI control must perform a real successful calc write'
    text = (root / 'experiments/bank.edi').read_text()
    assert text.count('_data_calc.point_id') == 1, (
        ' valid CLI write adds exactly one calculated loop'
    )
    before = snapshot(root)
    second = run_cli(root)
    assert second.returncode == 0, ' repeated valid CLI calc must succeed'
    assert snapshot(root) == before, ' repeated CLI calc preserves exact bytes'


def platform_alias(path):
    if sys.platform == 'win32':
        buffer = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer))
        assert length, ' failure to query an alias is inability, never evidence of absence'
        assert length < len(buffer), ' alias buffer must contain the complete platform result'
        alias = Path(buffer.value)
    else:
        alias = path.with_name(path.name.upper())
    return alias if alias.name != path.name and alias.exists() and path.samefile(alias) else None


def test_platform_alias_evidence_and_linux_domain_limit(tmp_path, record_property):
    # Query the filesystem instead of assuming NTFS 8.3 generation or APFS case folding.
    root = vehicle(tmp_path, 'wish_1_10')
    model = engine.Project.load(root)
    model.save_as(tmp_path / 'saved')
    path = tmp_path / 'saved/experiments/wish_1_10.edi'
    before = path.read_bytes()
    alias = platform_alias(path)
    record_property('platform_alias', str(alias) if alias else 'none obtained on this volume')
    if alias is None:
        record_property(
            'evidence_limit', 'Windows path append and 8.3 generation are not proved on this host'
        )
    else:
        assert path.samefile(alias), (
            ' an alias witness must resolve to the original entity document'
        )
        assert alias.read_bytes() == before, (
            ' platform alias exposes exactly the original document bytes'
        )
    model.experiments[0].name = 'WISH_1~1'
    with pytest.raises((ValueError, RuntimeError)) as caught:
        model.save_as(tmp_path / 'refused')
    assert 'WISH_1~1' in str(caught.value), (
        ' the tilde-bearing domain witness refuses by name on every host'
    )
    assert path.read_bytes() == before, ' alias-domain refusal must preserve the original document'


def test_create_new_refuses_real_filesystem_alias_before_publication(tmp_path):
    if not sys.platform.startswith('linux'):
        pytest.skip(' Linux hard-link injection; native platform alias observation is separate')
    compiler = shutil.which('cc')
    assert compiler, ' alias witness requires the pinned C compiler'
    observer = tmp_path / 'alias.so'
    built = subprocess.run(
        [
            compiler,
            '-shared',
            '-fPIC',
            str(ROOT / 'tests/fixtures/c13_t12_ids/alias_observer.c'),
            '-ldl',
            '-o',
            str(observer),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    assert built.returncode == 0, (
        ' platform-alias observer must compile before its evidence is trusted'
    )
    root = tmp_path / 'input'
    loops._load(root, 'data', 'project')
    output = tmp_path / 'published'
    output.mkdir()
    (output / 'sentinel').write_bytes(b'literal destination before publication\x00')
    before = snapshot(output)
    marker = tmp_path / 'alias.marker'
    code = (
        'import sys; '
        'sys.meta_path[:]=[f for f in sys.meta_path '
        'if not ("editable" in type(f).__module__ '
        'and __import__("os").environ.get("C13_T12_BASELINE_CLI"))]; '
        'import ' + engine.__name__ + ' as engine; '
        'engine.Project.load(sys.argv[1]).save_as(sys.argv[2])'
    )
    environment = dict(os.environ, LD_PRELOAD=str(observer), C13_T12_ALIAS_MARKER=str(marker))
    completed = subprocess.run(
        [sys.executable, '-c', code, str(root), str(output)],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=25,
    )
    assert marker.is_file(), (
        ' alias escape must reach an actual entity write; absence is not a pass'
    )
    assert marker.read_text() == 'platform-equivalent hard-link obtained\n', (
        ' alias witness requires the platform to prove inode and device equality'
    )
    assert completed.returncode != 0, (
        ' create-new must refuse an already-existing filesystem alias'
    )
    assert snapshot(output) == before, (
        ' alias refusal cannot replace any published destination byte'
    )
    assert not [p for p in tmp_path.iterdir() if 'stage' in p.name or 'backup' in p.name], (
        ' alias refusal must discard the staging directory'
    )
