"""Compile the unchanged production frame/receipt methods against real Qt signals.

The sink only records calls. It contains no scheduling, identity or release rule.
No application build directory or application executable is used.
"""

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def methods(text):
    selected = []
    for name in ('handFollowed', 'presentedFollowed', 'awaitRender', 'followRendered'):
        match = re.search(
            r'(?:void|bool) ProjectViewModel::' + name + r'\([^\n]*\)(?: const)? \{', text
        )
        if match is None:
            raise RuntimeError('The receipt witness requires the actual production method ' + name)
        # These top-level methods use the product's ordinary unindented closing brace.
        end = text.index('\n}', match.end()) + 2
        selected.append(text[match.start() : end])
    return '\n\n'.join(selected)


def build(destination, *, source=None, header=None):
    if source is None:
        source = (ROOT / 'app/src/project_view_model.cpp').read_text()
    if header is None:
        header = (ROOT / 'app/src/project_view_model.hpp').read_text()
    # Copy new atomic identity declarations from the producer, not a guessed token rule.
    extra = '\n'.join(
        line.strip()
        for line in header.splitlines()
        if 'std::atomic<' in line
        and 'render_' in line
        and not any(field in line for field in ('render_armed_', 'render_synced_'))
    )
    driver = (Path(__file__).with_name('driver.cpp')).read_text()
    driver = driver.replace('// @IDENTITY_MEMBERS@', extra)
    driver = driver.replace('// @PRODUCTION_METHODS@', methods(source))
    path = destination / 'handover.cpp'
    path.write_text(driver)
    kit = Path(os.environ.get('EDI_QT_KIT', ROOT / '.pixi/envs/app'))
    environment = {**os.environ, 'PKG_CONFIG_PATH': str(kit / 'lib/pkgconfig')}
    flags = subprocess.check_output(
        ['pkg-config', '--cflags', '--libs', 'Qt6Quick'], env=environment, text=True
    )
    compiler = os.environ.get('CXX') or shutil.which('c++')
    if not compiler:
        raise RuntimeError('The source-level Qt receipt witness requires a native C++ compiler')
    binary = destination / 'handover'
    result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-fPIC',
            str(path),
            '-o',
            str(binary),
            '-Wl,-rpath,' + str(kit / 'lib'),
            *shlex.split(flags),
        ],
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            'The actual receipt methods must compile in the boundary witness: '
            + result.stdout
            + result.stderr
        )
    return binary
