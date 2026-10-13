"""Freeze the tab underline and row colours from the pinned GUI archive."""

import argparse
import hashlib
import json
import re
from pathlib import Path

from tests.fixtures.table_display.gui_base import PIN, SOURCE_SHA256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gui_source', type=Path)
    args = parser.parse_args()
    source = args.gui_source / 'src'
    digest = ''.join(
        f'{path.relative_to(source).as_posix()} {hashlib.sha256(path.read_bytes()).hexdigest()}\n'
        for path in sorted(source.rglob('*'), key=lambda path: path.relative_to(source).as_posix())
        if path.is_file()
    )
    if hashlib.sha256(digest.encode()).hexdigest() != SOURCE_SHA256:
        raise ValueError('The style reference requires the complete pinned GUI source tree')
    gui = source / 'EasyApplication/Gui'
    tab = (gui / 'Elements/TabBar.qml').read_text()
    colours = (gui / 'Style/Colors.qml').read_text()
    sizes = (gui / 'Style/Sizes.qml').read_text()
    reference = {
        'gui_pin': PIN,
        'source_tree_sha256': SOURCE_SHA256,
        'sources': ['Elements/TabBar.qml', 'Style/Colors.qml', 'Style/Sizes.qml'],
        'border': int(re.search(r'property int borderThickness:\s*(\d+)', sizes)[1]),
        'width': int(re.search(r'height:\s*(\d+)', tab)[1]),
        'move_duration': int(re.search(r'highlightMoveDuration:\s*(\d+)', tab)[1]),
    }
    for name, field in (
        ('themeAccent', 'accent'),
        ('themeBackgroundHovered1', 'odd'),
        ('themeBackgroundHovered2', 'even'),
        ('themeRowHovered', 'hover'),
    ):
        match = re.search(
            r'property color ' + name + r':[^\n]+"(#[0-9a-fA-F]+)"\s*:\s*"(#[0-9a-fA-F]+)"',
            colours,
        )
        reference[field] = {'dark': match[1].lower(), 'light': match[2].lower()}
    text = json.dumps(reference, indent=2)
    (Path(__file__).with_name('reference.json')).write_text(text + '\n')
    (Path(__file__).with_name('reference.js')).write_text(
        '.pragma library\n\nvar reference = ' + text + ';\n'
    )


if __name__ == '__main__':
    main()
