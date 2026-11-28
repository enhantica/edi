# SPDX-License-Identifier: BSD-3-Clause
"""The prepared disk image leaves equal outer margins under Finder's tab bar."""

import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.fixtures.fast_chart_redraws.line_quality import read_png
from tests.fixtures.installer.disk_image.measure import TOLERANCE_POINTS, ink_rows
from tools.installer import package

CAPTURE = Path(__file__).resolve().parents[2] / 'fixtures/installer/disk_image/finder-tab-bar.json'


@pytest.mark.parametrize('scale', [1, 2], ids=['standard', 'retina'])
def test_disk_image_has_equal_margins_with_finder_tab_bar(tmp_path, monkeypatch, scale):
    finder = json.loads(CAPTURE.read_text(encoding='utf-8'))
    capture_scale = finder['pixels_per_point']
    chrome = (finder['content_top'] - finder['window_top']) / capture_scale
    label_below_icon = (finder['label_bottom'] - finder['icon_center']) / capture_scale
    settings = {}
    backgrounds = []

    def command(argv, **_kwargs):
        if argv[0] == 'tiffutil':
            backgrounds.extend(Path(argument) for argument in argv[2:-2])
        else:
            settings.update(runpy.run_path(str(argv[argv.index('-s') + 1])))

    monkeypatch.setattr(package, 'tempfile', SimpleNamespace(mkdtemp=lambda: str(tmp_path)))
    monkeypatch.setattr(package, 'run', command)
    monkeypatch.setattr(package, 'standard_icns', lambda _work: tmp_path / 'Installer.icns')
    monkeypatch.setattr(package, 'check_volume_icon', lambda _image: None)
    installer = tmp_path / 'EasyDiffraction Installer.app'
    package.build_disk_image(tmp_path / 'installer.dmg', installer)

    _, (width, height) = settings['window_rect']
    _, icon_center = settings['icon_locations'][installer.name]
    assert settings['label_pos'] == 'bottom', (
        'The packaged Finder name is displayed below the installer icon as in the capture'
    )
    assert len(backgrounds) == 2, 'The disk image supplies both standard and Retina Finder artwork'
    artwork = read_png(backgrounds[scale - 1])
    assert artwork.shape[1] == width * scale and artwork.shape[0] >= (height - chrome) * scale, (
        'The authored background fills the visible Finder view at the intended pixel density'
    )
    top, _ = ink_rows(artwork)
    bottom = height - chrome - icon_center - label_below_icon
    assert top > 0 and bottom > 0 and abs(top / scale - bottom) <= TOLERANCE_POINTS, (
        f'Finder needs equal outer margins around the instruction and label, '
        f'got {top / scale:g} pt above and {bottom:g} pt below'
    )
