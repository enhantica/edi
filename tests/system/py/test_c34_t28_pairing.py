"""G8/G10: branch existence is not unlanded paired work.

Real Git ancestry and independently planted equal trees prescribe the result.
"""

import subprocess

import pytest

from tests.system.py.test_e09_t75_pin_currency import currency_world, pin_text


@pytest.mark.parametrize('shape', ['main', 'behind', 'squashed', 'ahead-current', 'ahead-stale'])
def test_pairing_reports_unlanded_work_and_a_stale_pin_on_intermediate_rows(tmp_path, shape):
    original = 'unpaired-squashed' if shape == 'squashed' else 'unpaired-ancestor'
    build, _ = currency_world(tmp_path, original)
    candidate = build._git('rev-parse', 'candidate').strip()
    branch = build.first if shape == 'behind' else build.second
    if shape in {'squashed', 'ahead-current', 'ahead-stale'}:
        branch = candidate
    build._git('branch', 'paired-topic', branch)
    pin = build.second if shape == 'behind' else build.first
    if shape == 'ahead-current':
        pin = candidate
    (build.edi / 'pixi.toml').write_text(pin_text(pin))
    subprocess.run([build.git, '-C', str(build.edi), 'add', 'pixi.toml'], check=True)
    subprocess.run(
        [
            build.git,
            '-C',
            str(build.edi),
            '-c',
            'user.name=Fixture',
            '-c',
            'user.email=fixture@example.invalid',
            'commit',
            '--allow-empty',
            '-qm',
            'Commit independently prescribed consumer pin',
        ],
        check=True,
    )
    if shape == 'main':
        build.env['GITHUB_EVENT_NAME'] = 'push'
        build.env.pop('GITHUB_HEAD_REF', None)
    result = build.run('crysta-source.sh', '--currency')
    assert result.returncode == 0, (
        f' G8/G10 {shape}: intermediate pairing reports currency without failing the row: '
        + result.stdout
        + result.stderr
    )
    if shape == 'ahead-stale':
        assert pin in result.stderr and candidate in result.stderr, (
            ' G8 a stale paired pin must name both consumer pin and producer head'
        )
