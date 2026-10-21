"""Check the licence material in real install trees and an unpacked Python wheel."""

import json
import os
import re
from pathlib import Path

import pytest

from tests.integration.py.test_table_and_about_contract import ROOT, dependency_matrix

# Positive filename witnesses are independent of the overview. Compiled-in
# components need their licence even when no standalone library file survives.
FILES = {
    'Qt': ('*Qt6Core*', '*Qt6Qml*', '*Qt6Quick.*'),
    'Qt Graphs': ('*Qt6Graphs*',),
    'Qt Quick 3D': ('*Qt6Quick3D*',),
    'Qt Shader Tools': ('*Qt6ShaderTools*',),
    'plotly.js': ('*plotly*.js',),
    'three.js': ('*three*.js', '*OrbitControls.js'),
}
ABSENT = {'', '-', '—', 'no', 'n/a'}


def section_texts(text):
    starts = list(re.finditer(r'^## (.+)$', text, re.MULTILINE))
    return {
        match[1]: text[match.end() : starts[i + 1].start() if i + 1 < len(starts) else None]
        for i, match in enumerate(starts)
    }


def require_actual_artifact(root, surface):
    if surface in {'desktop', 'cli'}:
        executable = 'edi_app' if surface == 'desktop' else 'easydiffraction'
        binaries = [
            path
            for path in root.rglob('*')
            if path.name in {executable, executable + '.exe'} and path.is_file()
        ]
        assert binaries and all(path.stat().st_size > 0 for path in binaries), (
            'The actual distribution contains its built executable, not only copied licence files'
        )
    elif surface == 'web':
        build_file = root / 'build.json'
        assert build_file.is_file(), 'The web distribution carries its real two-kit site manifest'
        builds = json.loads(build_file.read_text())
        for kit in ('singlethread', 'multithread'):
            assert isinstance(builds.get(kit), str), 'The delivered site names both Qt web kits'
            folder = (root / builds[kit]).resolve()
            assert folder.is_relative_to(root.resolve()), (
                'The delivered kit path remains inside its actual distribution'
            )
            wasm = folder / 'edi_app.wasm'
            assert wasm.is_file() and wasm.read_bytes().startswith(b'\0asm'), (
                'Each delivered kit contains a real WebAssembly module'
            )
            assert (folder / 'edi_app.js').is_file(), (
                'Each delivered WebAssembly module retains its matching JavaScript loader'
            )
        for source in (ROOT / 'data/report/vendor').glob('*.js'):
            target = root / 'report/vendor' / source.name
            assert target.is_file() and target.read_bytes() == source.read_bytes(), (
                'The delivered report libraries retain their actual vendored bytes: ' + source.name
            )
    else:
        assert list(root.glob('*.dist-info/WHEEL')) and list(root.glob('*.dist-info/RECORD')), (
            'The Python input is an unpacked built wheel, not the source licence directory'
        )


@pytest.mark.parametrize(
    ('surface', 'variable'),
    [
        ('desktop', 'EDI_DESKTOP_BUNDLE'),
        ('web', 'EDI_WEB_BUNDLE'),
        ('python', 'EDI_PYTHON_BUNDLE'),
        ('cli', 'EDI_CLI_BUNDLE'),
    ],
)
def test_delivered_surface_lists_only_its_bundled_components(surface, variable):
    matrix = dependency_matrix()
    root = Path(os.environ.get(variable, ROOT / 'build/distribution-licences' / surface))
    assert root.is_dir(), (
        'Build the licence packages with tests/fixtures/distribution_licences/stage.py; '
        'the licence-surfaces CI job supplies ' + variable + ': ' + str(root)
    )
    require_actual_artifact(root, surface)
    required = {name for name, row in matrix.items() if row[surface].casefold() not in ABSENT}
    assert 'diffraction-lib' not in required, (
        'A reference-only project does not appear among any delivered surface components'
    )
    if surface in {'desktop', 'web'}:
        manifests = list(root.rglob('DEPENDENCIES.md'))
        assert manifests, 'The delivered app carries its dependency overview for its About table'
        assert all(
            path.read_bytes() == (ROOT / 'DEPENDENCIES.md').read_bytes() for path in manifests
        ), 'The shipped overview agrees exactly with the source used for the About table'
        notices = list(root.rglob('THIRD-PARTY-NOTICES'))
        assert notices, 'Each delivered app carries the full third-party licence texts'
        reference = section_texts((ROOT / 'THIRD-PARTY-NOTICES').read_text())
        for notice in notices:
            sections = section_texts(notice.read_text())
            for name in required:
                assert name in sections and sections[name] == reference[name], (
                    'Every carried component retains its complete licence text: '
                    + surface
                    + '/'
                    + name
                )
        # The common legal-text document may contain other surfaces' texts. The
        # displayed app list is checked separately in the rendered About actor.
        assert 'plotly.js' in required and 'three.js' in required, (
            'Both app surfaces ship the report libraries and list their licences'
        )
    else:
        paths = [path for path in root.rglob('*-LICENSE') if 'licenses' in path.parts]
        names = {re.sub(r'[^A-Za-z0-9.+-]+', '-', name).strip('-'): name for name in matrix}
        listed = {names.get(path.name.removesuffix('-LICENSE'), path.name) for path in paths}
        notices = list(root.rglob('THIRD-PARTY-NOTICES'))
        for notice in notices:
            listed.update(section_texts(notice.read_text()))
        assert listed == required, (
            'The delivered package carries exactly its own component licences: '
            + surface
            + '/missing='
            + repr(sorted(required - listed))
            + '/extra='
            + repr(sorted(listed - required))
        )
        reference = section_texts((ROOT / 'THIRD-PARTY-NOTICES').read_text())
        for path in paths:
            name = names[path.name.removesuffix('-LICENSE')]
            indented = reference[name].splitlines()
            first = next(i for i, line in enumerate(indented) if line.startswith('    '))
            expected = (
                '\n'.join(line.removeprefix('    ') for line in indented[first:]).rstrip() + '\n'
            )
            assert path.read_text() == expected, (
                'The packaged component licence retains the complete original text: ' + name
            )
    for name, patterns in FILES.items():
        if any(any(root.rglob(pattern)) for pattern in patterns):
            assert name in required, (
                'A physically bundled library is declared on its surface: ' + surface + '/' + name
            )
