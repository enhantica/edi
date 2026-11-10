"""Execute the actual Qt shaping witness in the production app runner."""

import os
import subprocess

from tests.integration.app.test_e04_t1_projects import APP_TESTS, runner


def test_display_alphabet_uses_only_packaged_rendering_fonts():
    run = subprocess.run(
        [str(runner()), '-input', str(APP_TESTS / 'tst_display_fonts.qml'), '-o', '-,txt'],
        env={**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'software'},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = run.stdout + run.stderr
    assert run.returncode == 0, (
        'The actual Qt shaping of the complete display alphabet must never use a system face: '
        + output
    )
    for case in (
        'default-regular',
        'default-bold',
        'selected-noto',
        'mono',
        'light',
        'arrow',
        'icons',
    ):
        assert (
            'PASS   : edi_app::BundledDisplayFonts::'
            f'test_actual_shaping_uses_only_packaged_faces({case})'
        ) in output, 'Every selected rendering font must execute its actual Qt shaping witness'
    assert (
        'PASS   : edi_app::BundledDisplayFonts::test_unbundled_face_cannot_satisfy_coverage()'
        in output
    ), 'The unbundled-face escape must be attempted in the real shaping witness'
