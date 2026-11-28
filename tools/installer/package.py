# SPDX-License-Identifier: BSD-3-Clause
"""Build, package and exercise native offline installers (ADR-0071)."""

import argparse
import datetime
import hashlib
import json
import os
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import xml.etree.ElementTree as ET  # noqa: S405 - generated XML only, never external XML
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/release'))
import versions  # noqa: E402
from assistants import (  # noqa: E402
    CHATGPT_COMPONENT,
    CLAUDE_COMPONENT,
    COPILOT_COMPONENT,
    distributed_assistants,
)
from promote import require_archive_size  # noqa: E402

sys.path.insert(0, str(ROOT / 'tools/installer'))
import maintenance_resource  # noqa: E402

SYSTEM = {'Linux': 'linux', 'Darwin': 'macos', 'Windows': 'windows'}[platform.system()]
APP_COMPONENT = 'org.easydiffraction.app'
ASSISTANT_COMPONENT = CHATGPT_COMPONENT
ASSISTANT_RUNTIME = Path('libexec/edi/codex')
# The optional assistant components, one per provider, in the pages' order (edi ADR-0108): the
# runtime each holds, the name the pages show, its payload manifest and its sorting priority.
ASSISTANT_COMPONENTS = {
    ASSISTANT_COMPONENT: {
        'runtime': ASSISTANT_RUNTIME,
        'name': 'ChatGPT',
        'description': 'Optional runtime for the ChatGPT assistant in EasyDiffraction.',
        'manifest': 'assistant-payload-manifest.json',
        'priority': '100',
    },
    CLAUDE_COMPONENT: {
        'runtime': Path('libexec/edi/claude'),
        'name': 'Claude',
        'description': 'Optional runtime for the Claude assistant in EasyDiffraction.',
        'manifest': 'claude-payload-manifest.json',
        'priority': '90',
    },
    COPILOT_COMPONENT: {
        'runtime': Path('libexec/edi/copilot'),
        'name': 'GitHub Copilot',
        'description': 'Optional runtime for the GitHub Copilot assistant in EasyDiffraction.',
        'manifest': 'copilot-payload-manifest.json',
        'priority': '80',
    },
}
# macOS and Windows ship their maintenance tool as a signed, app-versioned component (ADR-0091).
MAINTENANCE_COMPONENT = 'org.easydiffraction.app.maintenancetool'
# The id each component replaced, so an install made before edi ADR-0091 updates in place.
REPLACED_COMPONENTS = {
    APP_COMPONENT: 'org.easyscience.edi',
    ASSISTANT_COMPONENT: 'org.easyscience.edi.assistant',
    MAINTENANCE_COMPONENT: 'org.easyscience.edi.maintenancetool',
}
# What each component is built from besides its metadata folder, as a build number and paths in
# this repository (edi ADR-0111). A release ships a component again only when these change, so
# raise its build number when its build changes in a way the files do not show. The app is not
# listed: its build number is the release version, so every release ships it.
COMPONENT_INPUTS = {
    # The recipe pins the runtime's version and archive checksums.
    ASSISTANT_COMPONENT: (1, ('tools/deps/assistant-runtime', 'data/assistant/runtime')),
    CLAUDE_COMPONENT: (1, ('tools/deps/claude-runtime',)),
    COPILOT_COMPONENT: (1, ('tools/deps/copilot-runtime',)),
    # The Framework pin, and the pages and resources the tool is built with.
    MAINTENANCE_COMPONENT: (
        1,
        (
            'tools/installer/ifw.json',
            'tools/installer/Installer.qs',
            'tools/installer/Installer.qss',
            'tools/installer/InstallerChrome.qss',
            'tools/installer/ifw_en.qm',
            'tools/installer/CheckMark.png',
            'tools/installer/icons',
            'tools/installer/Installer.icns',
            'tools/installer/Installer.ico',
            'tools/installer/windows_icon.py',
        ),
    ),
}
SUFFIX = '.exe' if SYSTEM == 'windows' else ''
PLATFORM_ID = {'linux': 'linux-x86_64', 'macos': 'macos-arm64', 'windows': 'windows-x86_64'}[
    SYSTEM
]
# The platform as the download names show it (tools/release/promote.py installer_name).
INSTALLER_PLATFORM = {'linux': 'Linux-x64', 'macos': 'macOS-arm64', 'windows': 'Windows-x64'}[
    SYSTEM
]
# The installer app's name inside the macOS disk image, and the image's volume name.
MACOS_INSTALLER_NAME = 'EasyDiffraction Installer'


def installer_stem(version: str, kind: str) -> str:
    """The download's name without its suffix; the online installer is the default one."""
    return versions.installer_stem(version, INSTALLER_PLATFORM, kind)


def read_release_plan(directory: Path, source_commit: str | None = None) -> dict:
    """Require one immutable identity shared by prepared metadata and source."""
    documents = {}
    for name in ['plan.json', 'release.json', 'release-history.json']:
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
            raise RuntimeError('Release inputs must be bounded regular metadata files')
        documents[name] = json.loads(path.read_text(encoding='utf-8'))
    plan, release, history = (
        documents[name] for name in ['plan.json', 'release.json', 'release-history.json']
    )
    version = plan['version']
    if not versions.is_version(version):
        raise RuntimeError('Prepared release requires a calendar identity')
    if plan.get('reused'):
        raise RuntimeError('This release already exists; reuse its published artifacts')
    if (
        not re.fullmatch(r'[0-9a-f]{40}', plan['commit'])
        or release['version'] != version
        or release['commit'] != plan['commit']
    ):
        raise RuntimeError('Prepared release identities disagree')
    if source_commit is not None and plan['commit'] != source_commit:
        raise RuntimeError('Prepared release does not match this source commit')
    matches = [item for item in history['releases'] if item['version'] == version]
    if history['schema'] != 'edi.releases/1' or matches != [release]:
        raise RuntimeError('Prepared release is not uniquely recorded in its history')
    return release


def repository_urls(channel: str) -> tuple[str, ...]:
    """Return the primary repository and its mirrors for this build platform.

    The feed mirrors (mirror_bases) are not listed: a mirror without the archives, or with older
    metadata, would fail or hold back an update (edi ADR-0071).
    """
    policy = json.loads((ROOT / 'data/distribution.json').read_text(encoding='utf-8'))
    tail = policy['repository_paths'][channel].format(platform=PLATFORM_ID)
    bases = [policy['primary_base'], *policy['repository_mirror_bases']]
    return tuple(base.rstrip('/') + '/' + tail for base in bases)


def run(args, **kwargs: object) -> None:
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True, **kwargs)


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch_tools(destination: Path) -> Path:
    pin = json.loads((ROOT / 'tools/installer/ifw.json').read_text(encoding='utf-8'))['platforms'][
        SYSTEM
    ]
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / 'ifw.7z'
    if not archive.exists() or sha256(archive) != pin['sha256']:
        if not pin['url'].startswith('https://download.qt.io/'):
            raise RuntimeError('Installer tools must come from the official HTTPS feed')
        with (
            urllib.request.urlopen(pin['url'], timeout=30) as response,  # noqa: S310
            archive.open('wb') as stream,
        ):
            shutil.copyfileobj(response, stream)
    if sha256(archive) != pin['sha256']:
        raise RuntimeError('Installer Framework archive checksum differs')
    tools = destination / 'tools'
    if tools.exists():
        shutil.rmtree(tools)
    # Only the app environment has py7zr; the default one imports this module to collect tests.
    import py7zr  # noqa: PLC0415

    with py7zr.SevenZipFile(archive) as package:
        for name in package.getnames():
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise RuntimeError('Installer Framework archive escapes its tool directory')
        package.extractall(tools)  # noqa: S202 - verified archive with checked member paths
    creator = tools / ('bin/binarycreator' + SUFFIX)
    if not creator.is_file():
        raise RuntimeError('Installer Framework has no binarycreator')
    if SYSTEM == 'linux':
        acquire_installer_licenses(tools, destination)
    return tools


def xml_file(path, root_name, values) -> ET.ElementTree:
    root = ET.Element(root_name)
    for name, value in values.items():
        ET.SubElement(root, name).text = str(value)
    ET.indent(root)
    tree = ET.ElementTree(root)
    tree.write(path, encoding='utf-8', xml_declaration=True)
    return tree


def payload_manifest(stage: Path) -> dict:
    result = {}
    for path in sorted(stage.rglob('*')):
        relative = path.relative_to(stage).as_posix()
        if path.is_symlink():
            if (
                path.readlink().is_absolute()
                or not path.resolve().is_relative_to(stage.resolve())
                or not path.exists()
            ):
                raise RuntimeError(f'Payload link escapes or is broken: {relative}')
            result[relative] = {'link': str(path.readlink())}
        elif path.is_file():
            result[relative] = {'sha256': sha256(path), 'bytes': path.stat().st_size}
        elif not path.is_dir():
            raise RuntimeError(f'Payload contains a special file: {relative}')
    if not result:
        raise RuntimeError('Application stage is empty')
    return result


# The app's theme (gui-components' Gui/Style Colors.qml and Sizes.qml, at a 14 px font) for the
# installer's stylesheet (Installer.qss): Qt darker() written out, #AARRGGBB colours as rgba().
_SIZES = {
    'FONT_PX': '14',
    'HALF_FONT_PX': '7',
    'CONTROL_INNER_PX': '37',  # sideBarButtonHeight 39, less a 1 px border on each side
    'FIELD_PADDING_PX': '8',  # TextField padding: fontPixelSize * 0.5 + 1
    # The progress bar: a 14 px line with about 5 px above and below it.
    'PROGRESS_PX': '28',
}
INSTALLER_THEMES = {
    'light': _SIZES
    | {
        'BACKGROUND': '#e9e9e9',
        'BACKGROUND_HOVERED': '#fefefe',
        'BACKGROUND_DISABLED': '#e9e9e9',
        'FOREGROUND': '#333333',
        'FOREGROUND_MINOR': '#aaaaaa',
        'FOREGROUND_DISABLED': '#bbbbbb',
        'ACCENT': '#00a3e3',
        'ACCENT_TRACK': 'rgba(0, 163, 227, 0.17)',
        'BORDER': '#dedede',  # appBarComboBoxBorder: darker(themeBackground, 1.05)
        'FIELD_BACKGROUND': 'rgba(255, 255, 255, 0.44)',  # appBarComboBoxBackground #70ffffff
        'CHECK_BACKGROUND': '#f7f7f7',
        'WARNING': '#FF5722',  # red, the app's warning orange-red
    },
    'dark': _SIZES
    | {
        'BACKGROUND': '#303030',
        'BACKGROUND_HOVERED': '#353535',
        'BACKGROUND_DISABLED': '#333333',
        'FOREGROUND': '#eeeeee',
        'FOREGROUND_MINOR': '#888888',
        'FOREGROUND_DISABLED': '#666666',
        'ACCENT': '#4ec1ef',
        'ACCENT_TRACK': 'rgba(78, 193, 239, 0.17)',
        # Lighter than the app's appBarComboBoxBorder (#2c2c2c, 1.1 to 1 against a field), so
        # fields, buttons and boxes stand out from the dark window (1.4 to 1.5 to 1).
        'BORDER': '#4a4a4a',
        'FIELD_BACKGROUND': 'rgba(102, 102, 102, 0.06)',  # appBarComboBoxBackground #10666666
        'CHECK_BACKGROUND': '#3a3a3a',
        'WARNING': '#FFAB91',  # red
    },
}


# The system's own monospace font, for the licence text.
MONO_FAMILY = {'macos': 'Menlo', 'windows': 'Consolas'}.get(SYSTEM, 'DejaVu Sans Mono')


def installer_stylesheet(theme: str, name: str = 'Installer.qss') -> str:
    """An installer stylesheet with one theme's values filled in."""
    text = (ROOT / 'tools/installer' / name).read_text(encoding='utf-8')
    values = INSTALLER_THEMES[theme] | {
        'STEP_LIST_INSET': '23' if SYSTEM == 'macos' else '9',
        # The system's own sans serif: the app's PT Sans is not available to the installer.
        'FONT_FAMILY': {'macos': 'Helvetica Neue', 'windows': 'Segoe UI'}.get(
            SYSTEM, 'DejaVu Sans'
        ),
        # Monospace for the licence, whose headings are centred with spaces (the app's PT Mono is
        # not available to the installer).
        'MONO_FAMILY': MONO_FAMILY,
    }
    for key, value in values.items():
        text = text.replace(f'@{key}@', value)
    if '@' in re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL):
        raise RuntimeError('Installer.qss names a value INSTALLER_THEMES does not have')
    return text


def qt_tool(name: str) -> Path:
    """A Qt build tool of the packaging environment (conda-forge's qt6-main)."""
    prefix = Path(sys.prefix)
    for path in (
        prefix / 'lib/qt6' / name,
        prefix / 'lib/qt6/bin' / name,
        prefix / 'bin' / (name + '6'),
        prefix / 'Library/lib/qt6' / (name + '.exe'),
        prefix / 'Library/bin' / (name + '.exe'),
        prefix / 'bin' / name,
    ):
        if path.is_file():
            return path
    # conda-forge's Windows layout has moved between builds: look once under Library.
    found = sorted((prefix / 'Library').rglob(name + '.exe')) if SYSTEM == 'windows' else []
    if found:
        return found[0]
    raise RuntimeError(f'Qt {name} is not in the packaging environment')


def write_resources(config: Path, configuration: ET.ElementTree) -> Path:
    """The resource list binarycreator compiles in (-r, a .qrc): our English text and the tick.

    Named translations replace the Framework's built-in ones, so the text is English everywhere, as
    the pages are. The tick is the check box's image (Installer.qss).
    """
    work = config / 'resources'
    (work / 'translations').mkdir(parents=True, exist_ok=True)
    # ifw_en.qm is committed beside its source, so packaging needs no Qt tools; where lrelease is
    # at hand (the packaging environment), a stale one is refused.
    compiled = ROOT / 'tools/installer/ifw_en.qm'
    try:
        lrelease = qt_tool('lrelease')
    except RuntimeError:
        lrelease = None
    if lrelease is not None:
        fresh = work / 'ifw_en-fresh.qm'
        run([lrelease, ROOT / 'tools/installer/ifw_en.ts', '-qm', fresh])
        if fresh.read_bytes() != compiled.read_bytes():
            raise RuntimeError('tools/installer/ifw_en.qm is stale: rebuild it from ifw_en.ts')
    shutil.copy2(compiled, work / 'translations/ifw_en.qm')
    shutil.copy2(ROOT / 'tools/installer/CheckMark.png', work / 'CheckMark.png')
    # The app's own icons (Font Awesome 5 Solid, as gui-components draws them), the ticked check
    # box the update summary shows (Installer.qss's indicator), drawn large and shown at 16 px, and
    # the logo with its icons at 1x, 2x and 3x (render_images.qml).
    icons = sorted((ROOT / 'tools/installer/icons').glob('*.png'))
    for icon in icons:
        shutil.copy2(icon, work / icon.name)
    files = ''.join(f'<file alias="edi/{icon.name}">{icon.name}</file>' for icon in icons)
    (work / 'resources.qrc').write_text(
        '<RCC><qresource prefix="/">'
        '<file>translations/ifw_en.qm</file><file alias="edi/CheckMark.png">CheckMark.png</file>'
        f'{files}</qresource></RCC>\n',
        encoding='utf-8',
    )
    translations = ET.SubElement(configuration.getroot(), 'Translations')
    # The Framework maps a -r resource file under :/metadata; a full path is used as it is.
    ET.SubElement(translations, 'Translation').text = ':/metadata/translations/ifw_en.qm'
    ET.indent(configuration)
    configuration.write(config / 'config.xml', encoding='utf-8', xml_declaration=True)
    return work / 'resources.qrc'


def write_controller(config: Path, tool_bytes: int = 0) -> None:
    """Write the window's stylesheet and the controller, holding both wordmarks and page themes.

    `tool_bytes` is the maintenance tool's size, which its component (it has no payload on Linux)
    cannot say: the pages show it on the tool's row.

    The Framework loads one stylesheet for the whole app, before scripts run, so the window around
    the pages follows the system palette (InstallerChrome.qss); the controller gives each page
    edi's light or dark theme (Installer.qss).
    """
    style = ROOT / 'tools/installer'
    (config / 'Installer.qss').write_text(
        installer_stylesheet('light', 'InstallerChrome.qss'), encoding='utf-8'
    )
    controller = (style / 'Installer.qs').read_text(encoding='utf-8')
    for theme in ('light', 'dark'):
        controller = controller.replace(
            f'"@{theme.upper()}_STYLESHEET@"', json.dumps(installer_stylesheet(theme))
        )
    controller = controller.replace('"@TOOL_BYTES@"', str(tool_bytes))
    (config / 'Installer.qs').write_text(controller, encoding='utf-8')


def write_metadata(
    config: Path,
    meta: Path,
    version: str,
    repository_url: str | None,
    mirrors: tuple[str, ...] = (),
    *,
    enable_mirrors: bool = False,
    tool_bytes: int = 0,
) -> None:
    """Write the installer configuration and component metadata for either transport."""
    shutil.copy2(ROOT / 'LICENSE', meta / 'LICENSE')
    shutil.copy2(ROOT / 'COPYING', meta / 'COPYING')
    configuration = xml_file(
        config / 'config.xml',
        'Installer',
        {
            'Name': 'EasyDiffraction',
            'Version': version,
            'Title': 'EasyDiffraction',
            'Publisher': 'EasyScience',
            'ProductUrl': 'https://easydiffraction.org/',
            'TargetDir': {
                'macos': '/Applications/EasyDiffraction',
                'windows': '@ApplicationsDirUser@/EasyDiffraction',
            }.get(SYSTEM, '@HomeDir@/EasyDiffraction'),
            'MaintenanceToolName': 'MaintenanceTool',
            'AllowNonAsciiCharacters': 'true',
            'AllowSpaceInPath': 'true',
            # Qt's Modern wizard style: no page titles (so no header), its footer line hidden
            # (InstallerChrome.qss), the logo heading each page's content (Installer.qs).
            'WizardStyle': 'Modern',
            'WizardDefaultWidth': '640',
            # The tallest page, the install page, at 14 px text (a 19 px line in Segoe UI, 17 in
            # DejaVu Sans and Helvetica Neue): the logo 44 and its 32 px step, "Install to", 8, the
            # folder 39, 8, the space line, 24, two check box rows with 8 between, 24, the licence
            # and shortcut rows: 309 px on Windows. An installation already in the folder adds its
            # two-line warning and 24 (62 on Windows). Qt's margins around the page and its buttons
            # (11 and 9 px, the buttons 39) add 101: 472 on Windows with the warning.
            'WizardDefaultHeight': '480',
            # One centred column, no step list (the owner's three-page design, edi ADR-0071).
            'WizardShowPageList': 'false',
            'ControlScript': 'Installer.qs',
            'StyleSheet': 'Installer.qss',
        },
    )
    style = ROOT / 'tools/installer'
    write_controller(config, tool_bytes)
    write_resources(config, configuration)
    # The installer's own icon, the app logo coming out of a box, distinct from the app's.
    if SYSTEM in {'macos', 'windows'}:
        icon = 'Installer.icns' if SYSTEM == 'macos' else 'Installer.ico'
        shutil.copy2(style / icon, config / icon)
        ET.SubElement(configuration.getroot(), 'InstallerApplicationIcon').text = 'Installer'
        ET.SubElement(configuration.getroot(), 'StartMenuDir').text = 'EasyDiffraction'
    # No RunProgram: the last page's "Open EasyDiffraction now" is ours, and Installer.qs starts
    # the program itself on Finish instead of relying on the Framework's hidden box.
    if SYSTEM == 'windows':
        # Run as administrator, the installer suggests Program Files (Installer.qs, edi ADR-0071).
        ET.SubElement(
            configuration.getroot(), 'AdminTargetDir'
        ).text = '@ApplicationsDirX64@/EasyDiffraction'
    if SYSTEM in {'linux', 'windows'}:
        shutil.copy2(style / 'Installer.png', config / 'Installer.png')
        ET.SubElement(configuration.getroot(), 'InstallerWindowIcon').text = 'Installer.png'
    if repository_url:
        if not repository_url.startswith(('https://', 'file://')):
            raise RuntimeError('Online repositories require HTTPS or a local fixture URL')
        remote = ET.SubElement(configuration.getroot(), 'RemoteRepositories')
        repository = ET.SubElement(remote, 'Repository')
        ET.SubElement(repository, 'Url').text = repository_url
        ET.SubElement(repository, 'Enabled').text = '1'
        for mirror_url in mirrors:
            mirror = ET.SubElement(remote, 'Repository')
            ET.SubElement(mirror, 'Url').text = mirror_url
            ET.SubElement(mirror, 'Enabled').text = '1' if enable_mirrors else '0'
    ET.indent(configuration)
    configuration.write(config / 'config.xml', encoding='utf-8', xml_declaration=True)
    root = xml_file(
        meta / 'package.xml',
        'Package',
        {
            'DisplayName': 'EasyDiffraction',
            # As the installer's pages say it (Installer.qs).
            'Description': (
                'Calculate diffraction patterns and fit a structural model to your data.'
            ),
            'Version': version,
            'ReleaseDate': datetime.datetime.now(datetime.UTC).date().isoformat(),
            'Default': 'true',
            'ForcedInstallation': 'true',
            'RequiresAdminRights': 'false',
            'Replaces': REPLACED_COMPONENTS[APP_COMPONENT],
            # Listed first wherever components are (the Framework orders by this, higher first).
            'SortingPriority': '200',
            'Script': 'installscript.qs',
        },
    )
    shutil.copy2(ROOT / 'tools/installer/installscript.qs', meta / 'installscript.qs')
    # No <Licenses>: the GPL needs no acceptance page, so the install page has a ticked box and a
    # link to read it (Installer.qs); the licence text ships with the app.
    ET.indent(root)
    root.write(meta / 'package.xml', encoding='utf-8', xml_declaration=True)


def write_assistant_metadata(
    meta: Path, version: str, component: str = ASSISTANT_COMPONENT
) -> None:
    """One optional assistant component; ChatGPT's carries the pages' forms and their script."""
    details = ASSISTANT_COMPONENTS[component]
    fields = {
        'DisplayName': details['name'],
        'Description': details['description'],
        'Version': version,
        'ReleaseDate': datetime.datetime.now(datetime.UTC).date().isoformat(),
        'Dependencies': APP_COMPONENT,
        'Default': 'false',
        'RequiresAdminRights': 'false',
    }
    if component in REPLACED_COMPONENTS:
        fields['Replaces'] = REPLACED_COMPONENTS[component]
    fields['SortingPriority'] = details['priority']  # after EasyDiffraction
    if component == ASSISTANT_COMPONENT:
        fields['Script'] = 'assistantscript.qs'
    root = xml_file(meta / 'package.xml', 'Package', fields)
    if component == ASSISTANT_COMPONENT:
        # The checkboxes that replace the component tree (edi ADR-0071).
        interfaces = ET.SubElement(root.getroot(), 'UserInterfaces')
        ET.SubElement(interfaces, 'UserInterface').text = 'AssistantForm.ui'
        ET.SubElement(interfaces, 'UserInterface').text = 'ProgressForm.ui'
        ET.SubElement(interfaces, 'UserInterface').text = 'DoneForm.ui'
    ET.indent(root)
    root.write(meta / 'package.xml', encoding='utf-8', xml_declaration=True)
    if component == ASSISTANT_COMPONENT:
        for name in ('assistantscript.qs', 'AssistantForm.ui', 'ProgressForm.ui', 'DoneForm.ui'):
            shutil.copy2(ROOT / 'tools/installer' / name, meta / name)


def write_maintenance_tool_metadata(meta: Path, version: str) -> None:
    xml_file(
        meta / 'package.xml',
        'Package',
        {
            'DisplayName': 'Maintenance tool',
            'Description': 'Updates and removes EasyDiffraction.',
            'Version': version,
            'ReleaseDate': datetime.datetime.now(datetime.UTC).date().isoformat(),
            'Virtual': 'true',
            'ForcedInstallation': 'true',
            'RequiresAdminRights': 'false',
            'Replaces': REPLACED_COMPONENTS[MAINTENANCE_COMPONENT],
            # Between EasyDiffraction (200) and the assistants (100 and lower) in a capture.
            'SortingPriority': '150',
            'Script': 'maintenancescript.qs',
        },
    )
    (meta / 'maintenancescript.qs').write_text(maintenance_script(), encoding='utf-8')


def maintenance_script() -> str:
    """The tool component's script, the macOS swap and its undo written in as string literals."""
    folder = ROOT / 'tools/installer'
    script = (folder / 'maintenancescript.qs').read_text(encoding='utf-8')
    for marker, name in (
        ('EDI_SWAP_SCRIPT', 'maintenance_swap.sh'),
        ('EDI_RESTORE_SCRIPT', 'maintenance_restore.sh'),
    ):
        quoted = f'"@{marker}@"'
        if script.count(quoted) != 1:
            raise RuntimeError(f'maintenancescript.qs must name {quoted} once')
        script = script.replace(quoted, json.dumps((folder / name).read_text(encoding='utf-8')))
    return script


def maintenance_tool_name() -> str:
    return 'MaintenanceTool.app' if SYSTEM == 'macos' else 'MaintenanceTool.exe'


def maintenance_tool_executable(bundle: Path) -> Path:
    return bundle / 'Contents/MacOS/MaintenanceTool' if SYSTEM == 'macos' else bundle


def build_maintenance_tool(tools: Path, output: Path, variant: str = '') -> Path:
    """Build the maintenance tool on its own and sign it (edi ADR-0091).

    Without it the installer writes the tool from its own binary, which breaks a real signature:
    macOS kills it, and Windows runs it unsigned. Release builds sign with the Developer ID and
    notarise on macOS and sign through KeyLocker on Windows; others sign ad hoc on macOS only.
    A numeric variant, used only by the protocol check, makes the executable's bytes differ.
    """
    if SYSTEM not in {'macos', 'windows'}:
        raise RuntimeError('Only macOS and Windows build the maintenance tool separately')
    tools, work = tools.resolve(), output.resolve() / 'maintenance-tool'
    if work.exists():
        raise RuntimeError(
            'Maintenance tool output already exists; choose a fresh output directory'
        )
    if SYSTEM == 'windows':
        # binarycreator on Windows has no --mt. The maintenance tool is the Framework's
        # installerbase.exe, unchanged: the installer keeps its pages and data beside it in
        # maintenancetool.dat, so the signed binary stays as shipped.
        work.mkdir(parents=True)
        bundle = work / maintenance_tool_name()
        shutil.copy2(tools / 'bin/installerbase.exe', bundle)
        # The installer's icon, as the macOS tool gets, set before signing.
        sys.path.insert(0, str(ROOT / 'tools/installer'))
        import windows_icon  # noqa: PLC0415 - Windows only

        windows_icon.set_icon(bundle, ROOT / 'tools/installer/Installer.ico')
        if variant:
            with bundle.open('ab') as stream:
                stream.write(variant.encode())
        if windows_signing():
            sign_windows(bundle)
        return bundle
    config = work / 'config'
    config.mkdir(parents=True)
    # The installer's icon: the tool belongs to the installer, not to the app.
    icon = 'Installer.icns'
    shutil.copy2(ROOT / 'tools/installer' / icon, config / icon)
    configuration = xml_file(
        config / 'config.xml',
        'Installer',
        {
            'Name': 'EasyDiffraction',
            'Version': f'1.0.{variant}' if variant else '1.0.0',
            'Title': 'EasyDiffraction',
            'Publisher': 'EasyScience',
            'MaintenanceToolName': 'MaintenanceTool',
            'InstallerApplicationIcon': 'Installer',
            # The installer's look, light and dark, for the maintenance tool's pages too.
            'ControlScript': 'Installer.qs',
            'StyleSheet': 'Installer.qss',
        },
    )
    write_controller(config)
    write_resources(config, configuration)
    # --mt writes the tool named by MaintenanceToolName into the working directory.
    template = ['-t', macos_installer_template(tools, work)] if SYSTEM == 'macos' else []
    run(
        [
            tools / ('bin/binarycreator' + SUFFIX),
            '--verbose',
            *template,
            '--mt',
            '-r',
            config / 'resources/resources.qrc',
            '-c',
            config / 'config.xml',
        ],
        cwd=work,
    )
    bundle = work / maintenance_tool_name()
    set_bundle_identifier(
        bundle,
        'org.easydiffraction.maintenancetool',
        'EasyDiffraction Maintenance Tool',
        installer_icon=True,
        display_only=True,
    )
    if macos_signing():
        notarise_macos(bundle)
    elif windows_signing():
        sign_windows(bundle)
    elif SYSTEM == 'macos':
        run(['codesign', '--force', '--sign', '-', bundle])
    check_maintenance_tool(bundle)
    return bundle


def check_maintenance_tool(bundle: Path) -> None:
    """Require a valid signature: ad hoc or the Developer ID on macOS, KeyLocker's on Windows."""
    if not maintenance_tool_executable(bundle).is_file():
        raise RuntimeError(f'Maintenance tool is missing: {bundle}')
    if SYSTEM == 'windows':
        if os.environ.get('EDI_CODESIGN') == '1':
            verify_windows_signature(bundle)
        return
    run(['codesign', '--verify', '--strict', '--verbose=2', bundle])
    if os.environ.get('EDI_CODESIGN') != '1':
        return
    result = subprocess.run(
        ['codesign', '--display', '--verbose=2', str(bundle)],
        check=True, capture_output=True, text=True,
    )  # fmt: skip
    authorities = [
        line.removeprefix('Authority=')
        for line in (result.stdout + result.stderr).splitlines()
        if line.startswith('Authority=')
    ]
    identity = os.environ.get('EDI_CODESIGN_MAC_IDENTITY', '')
    if not authorities or not authorities[0].startswith('Developer ID Application:'):
        raise RuntimeError(f'Maintenance tool is not signed with a Developer ID: {authorities}')
    if identity.startswith('Developer ID Application:') and authorities[0] != identity:
        raise RuntimeError(f'Maintenance tool is signed by {authorities[0]}, not {identity}')


def add_maintenance_tool(
    packages: Path, bundle: Path | None, tools: Path, output: Path, version: str
) -> str:
    """Put the signed maintenance tool into its component; return its executable's checksum."""
    if bundle is None:
        if macos_signing() or windows_signing():
            raise RuntimeError('Signing needs the separately signed maintenance tool')
        bundle = build_maintenance_tool(tools, output)
    check_maintenance_tool(bundle)
    meta = packages / MAINTENANCE_COMPONENT / 'meta'
    meta.mkdir(parents=True)
    write_maintenance_tool_metadata(meta, version)
    target = meta.parent / 'data/maintenancetool' / maintenance_tool_name()
    target.parent.mkdir(parents=True)
    if SYSTEM == 'macos':
        run(['ditto', bundle, target])
    else:
        shutil.copy2(bundle, target)
    return sha256(maintenance_tool_executable(target))


def add_maintenance_resource(source: Path, tools: Path, environment: dict | None) -> None:
    """Ship the maintenance tool's pages with the app component, for updates to put in place."""
    meta = source / 'packages' / APP_COMPONENT / 'meta'
    maintenance_resource.build(
        tools / ('bin/binarycreator' + SUFFIX),
        qt_tool('rcc'),
        source / 'config/config.xml',
        source / 'config/resources/resources.qrc',
        meta.parent / 'data' / maintenance_resource.RESOURCE_NAME,
        environment,
    )
    script = meta / 'installscript.qs'
    text = script.read_text(encoding='utf-8')
    unnamed = 'var MAINTENANCE_RESOURCE = "";'
    if text.count(unnamed) != 1:
        raise RuntimeError(f'installscript.qs must hold {unnamed} once')
    named = f'var MAINTENANCE_RESOURCE = "{maintenance_resource.RESOURCE_NAME}";'
    script.write_text(text.replace(unnamed, named), encoding='utf-8')


def verify_installed_maintenance_tool(target: Path, metadata: dict) -> None:
    """Before running it, require the installed tool to be the shipped one (edi ADR-0091)."""
    if SYSTEM not in {'macos', 'windows'}:
        return
    bundle = target / maintenance_tool_name()
    check_maintenance_tool(bundle)
    expected = metadata.get('maintenance_tool_sha256')
    if expected and sha256(maintenance_tool_executable(bundle)) != expected:
        raise RuntimeError(
            'The installer wrote its own maintenance tool instead of the signed one'
        )
    if SYSTEM == 'macos' and (target / 'maintenancetool').exists():
        raise RuntimeError('The installer left the shipped maintenance tool in place')
    if SYSTEM == 'macos' and (target / 'MaintenanceTool.app.old').exists():
        raise RuntimeError('The update left the replaced maintenance tool behind')


def acquire_installer_licenses(tools: Path, destination: Path) -> None:
    """Acquire pinned licence files before the network-free installer checks."""
    value = os.environ.get('PIXI_ENVIRONMENT_PREFIX') or os.environ.get('CONDA_PREFIX')
    if not value:
        raise RuntimeError('Acquire installer tools inside the packaging workspace')
    prefix = Path(value).resolve()
    probe = destination / 'license-probe'
    probe.mkdir()
    env = clean_environment(destination / 'tool-home')
    env['LD_LIBRARY_PATH'] = str(probe)
    copied = collect_linux_installer_libraries(
        tools / 'bin/installerbase', probe, prefix, shutil.which('patchelf'), env
    )
    for record in (prefix / 'conda-meta').glob('*.json'):
        metadata = json.loads(record.read_text(encoding='utf-8'))
        files = set(metadata.get('files', []))
        if not any(
            Path(source).is_relative_to(prefix)
            and Path(source).relative_to(prefix).as_posix() in files
            for source in copied.values()
        ):
            continue
        cached = Path(metadata.get('link', {}).get('source', '')) / 'info/licenses'
        target = tools / 'licenses' / metadata['name']
        if cached.is_dir():
            shutil.copytree(cached, target)
        else:
            acquire_package_licenses(metadata, destination, target)
    shutil.rmtree(probe)


def bundled_runtime_licenses(metadata: dict, target: Path) -> bool:
    """Supply verified upstream notices omitted by known split runtime packages."""
    root = ROOT / 'tools/installer/licenses'
    policy = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    package = policy['packages'].get(metadata['name'])
    if (
        not package
        or metadata['version'] != package['version']
        or metadata['license'] != package['license']
    ):
        return False
    target.mkdir(parents=True)
    for name in package['files']:
        source = root / name
        if source.is_symlink() or sha256(source) != policy['files'][name]['sha256']:
            raise RuntimeError('Pinned upstream dependency licence differs')
        shutil.copy2(source, target / name)
    shutil.copy2(root / 'NOTICE', target / 'NOTICE')
    return True


def deployed_package_names(files: list[Path], records: list[dict]) -> set[str]:
    """Resolve deployed paths to their nearest package path, refusing ambiguous ownership."""
    candidates = {}
    for record in records:
        for name in record.get('files', []):
            path = Path(name)
            candidates.setdefault(path.name, []).append((path.parts, record['name']))
    owners = set()
    for path in files:
        matches = {}
        for parts, owner in candidates.get(path.name, []):
            score = 0
            for left, right in zip(reversed(path.parts), reversed(parts), strict=False):
                if left != right:
                    break
                score += 1
            matches[owner] = max(matches.get(owner, 0), score)
        if not matches:
            continue
        best = max(matches.values())
        selected = [owner for owner, score in matches.items() if score == best]
        if len(selected) != 1:
            raise RuntimeError(f'Ambiguous deployed dependency ownership: {path}')
        owners.add(selected[0])
    return owners


def collect_dependency_licenses(
    deployed_files: list[Path],
    records: Path,
    notices: Path,
    inputs: Path,
    *,
    require_owned: bool = False,
) -> None:
    """Carry the actual locked packages' licences for the deployed runtime files."""
    if not records.is_dir():
        raise RuntimeError(
            'Packaging requires locked dependency records for its licence inventory'
        )
    notices.mkdir(parents=True, exist_ok=True)
    metadata_records = [
        json.loads(record.read_text(encoding='utf-8')) for record in records.glob('*.json')
    ]
    if require_owned:
        for path in deployed_files:
            if not deployed_package_names([path], metadata_records):
                raise RuntimeError(f'Missing deployed dependency ownership: {path}')
    owners = deployed_package_names(deployed_files, metadata_records)
    inputs.mkdir(parents=True, exist_ok=True)
    for metadata in metadata_records:
        if metadata['name'] not in owners:
            continue
        licenses = Path(metadata.get('link', {}).get('source', '')) / 'info/licenses'
        if not licenses.is_dir():
            licenses = inputs / metadata['name']
            if not licenses.is_dir():
                acquire_package_licenses(metadata, inputs, licenses)
        if not any(path.is_file() for path in licenses.rglob('*')):
            raise RuntimeError(f'Missing deployed dependency licences: {metadata["name"]}')
        shutil.copytree(licenses, notices / metadata['name'])


def acquire_package_licenses(metadata: dict, destination: Path, target: Path) -> None:
    """Recover pinned licence files when CI restores the environment without its cache."""
    if bundled_runtime_licenses(metadata, target):
        return
    print('Acquire dependency licences:', metadata['name'], flush=True)
    url = metadata['url']
    if not url.startswith('https://conda.anaconda.org/conda-forge/'):
        raise RuntimeError('Dependency licences must use the pinned conda-forge archive')
    archive = destination / (metadata['name'] + '.conda')
    with urllib.request.urlopen(url, timeout=30) as response, archive.open('wb') as stream:  # noqa: S310
        shutil.copyfileobj(response, stream)
    if sha256(archive) != metadata['sha256']:
        raise RuntimeError('Dependency licence archive checksum differs')
    target.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zipped:
        members = [name for name in zipped.namelist() if name.endswith('.tar.zst')]
        if (
            sum(name.startswith('info-') for name in members) != 1
            or sum(name.startswith('pkg-') for name in members) != 1
            or len(members) != 2
        ):
            raise RuntimeError('Dependency archive has no unique info and payload members')
        for name in members:
            extract_license_member(zipped, name, target)

    if not any(target.rglob('*')):
        raise RuntimeError(f'Dependency archive contains no licence files: {metadata["name"]}')


def extract_license_member(zipped: zipfile.ZipFile, name: str, target: Path) -> None:
    """Read licence files from either conda member without extracting executable payloads."""
    with zipped.open(name) as stream, tarfile.open(fileobj=stream, mode='r|zst') as info:
        for member in info:
            relative = Path(member.name)
            if relative.parts[:2] != ('info', 'licenses'):
                continue
            if '..' in relative.parts or not (member.isdir() or member.isfile()):
                raise RuntimeError('Dependency licence archive contains an unsafe member')
            if member.isfile():
                path = target / Path(*relative.parts[2:])
                path.parent.mkdir(parents=True, exist_ok=True)
                with info.extractfile(member) as source, path.open('wb') as sink:
                    shutil.copyfileobj(source, sink)


def installer_runtime_notices(
    copied: dict, prefix: Path | None, notices: Path, acquired: Path
) -> None:
    """Collect the licence files for every bundled installer library."""
    for name, source_path in copied.items():
        source = Path(source_path)
        if prefix and source.is_relative_to(prefix.resolve()):
            found = False
            for record in (prefix / 'conda-meta').glob('*.json'):
                metadata = json.loads(record.read_text(encoding='utf-8'))
                if source.relative_to(prefix.resolve()).as_posix() in metadata.get('files', []):
                    licenses = Path(metadata.get('link', {}).get('source', '')) / 'info/licenses'
                    if not licenses.is_dir():
                        licenses = acquired / metadata['name']
                    if licenses.is_dir():
                        shutil.copytree(licenses, notices / metadata['name'], dirs_exist_ok=True)
                        found = True
            if not found:
                raise RuntimeError(f'No dependency licence files found for {name}')
        else:
            result = subprocess.run(
                ['dpkg-query', '-S', str(source)], capture_output=True, text=True, check=False
            )
            if result.returncode and str(source).startswith('/usr/lib/'):
                result = subprocess.run(
                    ['dpkg-query', '-S', str(source).removeprefix('/usr')],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            packages = [
                line.split(': ', 1)[0].split(':', 1)[0] for line in result.stdout.splitlines()
            ]
            licenses = [Path('/usr/share/doc') / package / 'copyright' for package in packages]
            if not licenses or not any(path.is_file() for path in licenses):
                raise RuntimeError(f'No operating-system dependency licence found for {name}')
            for path in licenses:
                if path.is_file():
                    shutil.copy2(path, notices / (path.parent.name + '-copyright'))


def collect_linux_installer_libraries(
    template: Path, libraries: Path, prefix: Path | None, patchelf: str, env: dict
) -> dict:
    """Resolve and relocate the non-glibc dependency closure of the IFW template."""
    core = re.compile(r'lib(?:c|m|dl|pthread|rt|resolv|util|anl)\.so\.')
    copied = {}
    for _ in range(32):
        result = subprocess.run(
            ['/usr/bin/ldd', str(template)], env=env, capture_output=True, text=True, check=False
        )
        missing = []
        progress = False
        for line in result.stdout.splitlines():
            match = re.fullmatch(r'\s*(\S+) => (not found|/\S+)(?: \(.*\))?\s*', line)
            if not match:
                continue
            name, resolved = match.groups()
            if core.match(name):
                continue
            destination = libraries / name
            if destination.exists():
                if resolved == 'not found':
                    raise RuntimeError(f'Installer cannot load its bundled library: {name}')
                continue
            if resolved == 'not found':
                candidate = prefix / 'lib' / name if prefix else None
                if not candidate or not candidate.is_file():
                    missing.append(name)
                    continue
                source = candidate.resolve()
            else:
                source = Path(resolved).resolve()
            shutil.copy2(source, destination)
            run([patchelf, '--set-rpath', '$ORIGIN', destination])
            copied[name] = str(source)
            progress = True
        if not progress:
            if result.returncode or missing or 'not found' in result.stdout + result.stderr:
                raise RuntimeError(
                    f'Unresolved installer dependency: {result.stdout}{result.stderr}'
                )
            break
    else:
        raise RuntimeError('Installer dependency closure did not converge')
    return copied


def linux_installer_runtime(tools: Path, output: Path) -> tuple[Path, Path, dict]:
    """Relocate the IFW template before payload append; leave glibc to the OS."""
    template = output / 'installerbase'
    shutil.copy2(tools / 'bin/installerbase', template)
    libraries = output / 'installer-runtime/lib'
    notices = output / 'installer-runtime/licenses'
    libraries.mkdir(parents=True)
    notices.mkdir()
    patchelf = shutil.which('patchelf')
    if not patchelf:
        raise RuntimeError('Linux installer packaging requires patchelf')
    env = clean_environment(output / 'tool-home')
    env['LD_LIBRARY_PATH'] = str(libraries)
    prefix_value = os.environ.get('PIXI_ENVIRONMENT_PREFIX') or os.environ.get('CONDA_PREFIX')
    prefix = Path(prefix_value) if prefix_value else None
    copied = collect_linux_installer_libraries(template, libraries, prefix, patchelf, env)
    installer_runtime_notices(copied, prefix, notices, tools / 'licenses')
    run([patchelf, '--set-rpath', '$ORIGIN/installer-runtime/lib', template])
    (output / 'installer-runtime/dependencies.json').write_text(
        json.dumps({name: sha256(libraries / name) for name in copied}, indent=2) + '\n'
    )
    return template, libraries.parent, env


def set_bundle_identifier(
    bundle: Path,
    identifier: str,
    name: str,
    *,
    installer_icon: bool = False,
    display_only: bool = False,
) -> None:
    """Our identifier and name in place of the Installer Framework's, before the bundle is signed.

    binarycreator writes com.yourcompany.installerbase into every macOS bundle it makes and names
    it after its executable, and macOS shows both in crash reports, privacy settings, the menu bar
    and the Dock. The installer also takes the enlarged icon (standard_icns).
    """
    if SYSTEM != 'macos':
        return
    info = bundle / 'Contents/Info.plist'
    with info.open('rb') as handle:
        values = plistlib.load(handle)
    values['CFBundleIdentifier'] = identifier
    # The maintenance tool keeps its bundle name: the Framework names the bundle it rewrites on an
    # update after it, so only the name shown changes there.
    values['CFBundleDisplayName'] = name
    if not display_only:
        values['CFBundleName'] = name
    icon = values.get('CFBundleIconFile')
    if installer_icon and icon:
        name_on_disk = icon if icon.endswith('.icns') else icon + '.icns'
        shutil.copy2(
            standard_icns(Path(tempfile.mkdtemp())), bundle / 'Contents/Resources' / name_on_disk
        )
    with info.open('wb') as handle:
        plistlib.dump(values, handle)


def macos_installer_template(tools: Path, output: Path) -> Path:
    """Select the arm64 installer template before IFW attaches its payload."""
    template = tools / 'bin/installerbase'
    architectures = subprocess.check_output(['lipo', '-archs', template], text=True).split()
    if architectures == ['arm64']:
        return template
    if 'arm64' not in architectures:
        raise RuntimeError('The macOS installer template has no arm64 slice')
    thin = output / 'installerbase-arm64'
    run(['lipo', template, '-thin', 'arm64', '-output', thin])
    thin.chmod(template.stat().st_mode & 0o777)
    return thin


# The disk image window in points: its content 400 wide and 250 high under a 28-point title bar,
# centred on a 1440 by 900 screen, and the installer's icon in the window's middle, under the
# background's "Double-click to install" (disk_image_background.qml), its label below.
DISK_IMAGE_WINDOW = ((520, 311), (400, 278))
DISK_IMAGE_ICON = (200, 125)


def build_disk_image(image: Path, app: Path) -> None:
    """The disk image with its Finder window laid out and the installer's icon as its volume icon.

    dmgbuild writes the window's layout (.DS_Store) and .VolumeIcon.icns into the image itself, so
    Finder opens it the same way on every Mac without scripting Finder at build time. Every bar is
    off, the tab bar included, but a Finder set to show its tab bar (View, Show Tab Bar) still
    shows it, taking its height off the window's bottom, which is why the icon sits high.
    """
    # The background in both resolutions as one TIFF, which Finder reads for normal and Retina
    # screens; the PNGs come from disk_image_background.qml.
    background = Path(tempfile.mkdtemp()) / 'background.tiff'
    style = ROOT / 'tools/installer'
    run([
        'tiffutil', '-cathidpicheck', style / 'DiskImageBackground.png',
        style / 'DiskImageBackground@2x.png', '-out', background,
    ])  # fmt: skip
    settings = {
        'files': [str(app)],
        'icon': str(standard_icns(Path(tempfile.mkdtemp()))),
        'background': str(background),
        'format': 'UDZO',
        'filesystem': 'HFS+',
        'default_view': 'icon-view',
        'window_rect': DISK_IMAGE_WINDOW,
        'show_toolbar': False,
        'show_status_bar': False,
        'show_tab_view': False,
        'show_pathbar': False,
        'show_sidebar': False,
        'show_icon_preview': False,
        'arrange_by': None,
        'icon_size': 96,
        'text_size': 12,
        'label_pos': 'bottom',
        'grid_spacing': 100,
        'icon_locations': {app.name: DISK_IMAGE_ICON},
        # Finder's label reads "EasyDiffraction Installer", without ".app".
        'hide_extension': [app.name],
    }
    # dmgbuild reads its settings as a Python file; it is in the macOS packaging environment only.
    script = Path(tempfile.mkdtemp()) / 'dmg_settings.py'
    script.write_text(
        ''.join(f'{key} = {value!r}\n' for key, value in settings.items()), encoding='utf-8'
    )
    run([sys.executable, '-m', 'dmgbuild', '-s', script, MACOS_INSTALLER_NAME, image])
    check_volume_icon(image)


def check_volume_icon(image: Path) -> None:
    """The mounted volume shows the installer's icon: .VolumeIcon.icns and the custom icon flag.

    Being part of the image, it survives a download, unlike the file's own icon (set_file_icon).
    """
    with tempfile.TemporaryDirectory() as folder:
        mount = Path(folder) / 'volume'
        mount.mkdir()
        run(['hdiutil', 'attach', '-nobrowse', '-readonly', '-mountpoint', mount, image])
        try:
            if not (mount / '.VolumeIcon.icns').is_file():
                raise RuntimeError('The disk image has no volume icon')
            info = subprocess.run(
                ['xattr', '-px', 'com.apple.FinderInfo', mount],
                capture_output=True, text=True, check=False,
            )  # fmt: skip
            flags = bytes.fromhex(''.join(info.stdout.split()))[8:10]
            # Finder's kHasCustomIcon flag, without which it ignores .VolumeIcon.icns.
            if info.returncode or len(flags) < 2 or not flags[0] & 0x04:
                raise RuntimeError('The disk image volume lacks the custom icon flag')
        finally:
            run(['hdiutil', 'detach', mount])


# The installer art's height as a share of its icon: a document icon's in Finder (87 of 96
# points), so the installer reads as large as the files beside it in a folder.
INSTALLER_ICON_HEIGHT = 0.906


def standard_icns(work: Path) -> Path:
    """Installer.icns for Finder: the same art, cropped to it and enlarged, written by iconutil.

    Installer.icns draws its art inside wide margins and keeps its small sizes as PNG, which Finder
    draws garbled in a title bar; iconutil stores every size in the formats Finder expects.
    """
    data = (ROOT / 'tools/installer/Installer.icns').read_bytes()
    largest, offset = None, 8
    while offset < len(data):
        kind, size = data[offset : offset + 4], int.from_bytes(data[offset + 4 : offset + 8])
        if kind == b'ic10':  # 1024 px
            largest = data[offset + 8 : offset + size]
        offset += size
    if largest is None:
        raise RuntimeError('Installer.icns has no 1024 px image')
    work.mkdir(parents=True, exist_ok=True)
    source = work / 'Installer-1024.png'
    source.write_bytes(largest)
    iconset = work / 'Installer.iconset'
    run([
        'swift', ROOT / 'tools/installer/scale_icon.swift', source, str(INSTALLER_ICON_HEIGHT),
        iconset,
    ])  # fmt: skip
    icns = work / 'Installer.icns'
    run(['iconutil', '-c', 'icns', '-o', icns, iconset])
    return icns


def set_file_icon(image: Path) -> None:
    """The installer's icon on the disk image file itself.

    Kept in the file's extended attributes, which a browser download does not carry, so it shows on
    the build machine and on Finder copies only. Set after any signing, which refuses them.
    """
    icon = json.dumps(str(standard_icns(Path(tempfile.mkdtemp()))))
    script = (
        "ObjC.import('AppKit');"
        f'var icon = $.NSImage.alloc.initWithContentsOfFile({icon});'
        f'$.NSWorkspace.sharedWorkspace.setIconForFileOptions(icon, {json.dumps(str(image))}, 0);'
    )
    run(['osascript', '-l', 'JavaScript', '-e', script])


def deliver_installer(installer: Path, runtime: Path | None, *, ad_hoc: bool = True) -> Path:
    """The one file users download (edi ADR-0071).

    macOS: a disk image holding the installer app, so the app and its maintenance tool stay
    intact; Windows: the self-contained installer itself; Linux: a ZIP of the installer with its
    portable runtime libraries.
    """
    if SYSTEM == 'windows':
        return installer
    if SYSTEM == 'macos':
        image = installer.with_suffix('.dmg')
        image.unlink(missing_ok=True)
        if ad_hoc:
            run(['codesign', '--force', '--deep', '--sign', '-', installer])
        folder = installer.parent / (installer.stem + '-image')
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir()
        app = folder / (MACOS_INSTALLER_NAME + '.app')
        run(['ditto', installer, app])
        try:
            build_disk_image(image, app)
        finally:
            shutil.rmtree(folder)
        if ad_hoc:
            set_file_icon(image)
        return image
    archive = installer.with_suffix('.zip')
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
        zipped.write(installer, installer.name)
        if runtime:
            for path in sorted(runtime.rglob('*')):
                if path.is_file():
                    zipped.write(path, path.relative_to(installer.parent))
        zipped.write(ROOT / 'website/BRANDING-LICENSE', 'BRANDING-LICENSE.txt')
    return archive


def write_repository(
    tools: Path,
    packages: Path,
    repository: Path,
    environment: dict,
    excluded: list[str] = (),
    *,
    public: bool = True,
) -> None:
    """The online repository, every component with its content checksum (edi ADR-0106).

    repogen takes the argument after --sha-update as the components to checksum: every package of
    this platform's repository, by its id. Excluded components (withheld_components) stay out.
    A public repository also meets the download site's file size limit, so an oversized
    component fails here instead of at release staging; an internal one is never published.
    """
    names = sorted(
        path.name for path in packages.iterdir() if path.is_dir() and path.name not in excluded
    )
    run(
        [
            tools / ('bin/repogen' + SUFFIX),
            '--verbose',
            '--sha-update',
            ','.join(names),
            '--component-metadata',
            '--compression',
            '5',
            *(['--exclude', ','.join(excluded)] if excluded else []),
            '-p',
            packages,
            repository,
        ],
        env=environment,
    )
    require_content_checksums(repository / 'Updates.xml', names)
    if public:
        for path in sorted(repository.rglob('*')):
            if path.is_file():
                require_archive_size(path)


def component_identity(package: Path, version: str) -> str:
    """The input identity of one component's package folder (edi ADR-0111).

    A sha256 over its metadata without the release's version and date, the files COMPONENT_INPUTS
    declares for it and its build number. Built bytes are left out: archive times and signing
    change them when nothing else did.
    """
    build, declared = COMPONENT_INPUTS.get(package.name, (version, ()))
    files = {}
    for path in sorted(p for p in (package / 'meta').rglob('*') if p.is_file()):
        data = path.read_bytes()
        if path.name == 'package.xml':
            root = ET.fromstring(data)  # noqa: S314 - written by this script
            for name in ('Version', 'ReleaseDate'):
                for item in root.findall(name):
                    root.remove(item)
            data = ET.tostring(root)
        files['meta/' + path.relative_to(package / 'meta').as_posix()] = hashlib.sha256(
            data
        ).hexdigest()
    for name in declared:
        # Tracked files only, so stray local files cannot change the identity.
        tracked = subprocess.check_output(['git', 'ls-files', '-z', '--', name], cwd=ROOT)
        if not tracked:
            raise RuntimeError(f'{package.name} declares {name}, which holds no tracked file')
        for relative in sorted(tracked.decode().split('\0')[:-1]):
            files[relative] = sha256(ROOT / relative)
    document = json.dumps({'build': build, 'files': files}, sort_keys=True)
    return hashlib.sha256(document.encode()).hexdigest()


def require_content_checksums(updates: Path, packages: list) -> None:
    """Every component of the repository carries its content checksum (repogen --sha-update)."""
    root = ET.parse(updates).getroot()  # noqa: S314 - repogen's own output
    found = {
        package.findtext('Name'): (package.findtext('ContentSha1') or '').strip()
        for package in root.findall('PackageUpdate')
    }
    missing = sorted(name for name in packages if not found.get(name))
    if sorted(found) != packages or missing:
        raise RuntimeError(
            f'The update repository lacks content checksums for {missing or sorted(found)}'
        )


def withheld_components(packages: Path, *, internal: bool = False) -> list[str]:
    """Built components this installer and its repository leave out.

    That is each assistant whose distribution is not public yet (Claude, GitHub Copilot), except
    in an internal build.
    """
    carried = distributed_assistants(internal=internal)
    return [
        name for name in ASSISTANT_COMPONENTS if name not in carried and (packages / name).is_dir()
    ]


def installerbase_bytes(tools: Path) -> int:
    """The Framework's installerbase, which the installation writes as its maintenance tool."""
    base = tools / 'bin' / ('installerbase.exe' if SYSTEM == 'windows' else 'installerbase')
    return base.stat().st_size if base.exists() else 0


def prepare_installer_source(
    stage: Path,
    tools: Path,
    output: Path,
    version: str,
    repository_url: str | None,
    mirrors: tuple[str, ...],
    channel: str,
) -> tuple:
    """Prepare the payload and platform bootstrap runtime before framework packaging.

    Each assistant runtime in the stage becomes its own optional component and never stays in
    the required one. Every component is built; package_app decides which ones ship.
    """
    source = output / 'source'
    if source.exists():
        raise RuntimeError('Installer source already exists; choose a fresh output directory')
    config = source / 'config'
    packages = source / 'packages'
    meta = packages / APP_COMPONENT / 'meta'
    data = meta.parent / 'data'
    config.mkdir(parents=True)
    meta.mkdir(parents=True)
    shutil.copytree(stage, data, symlinks=True)
    for component, details in ASSISTANT_COMPONENTS.items():
        runtime = data / details['runtime']
        if not runtime.is_dir():
            if component == ASSISTANT_COMPONENT:
                raise RuntimeError('Stage does not contain the ChatGPT assistant runtime')
            continue
        component_meta = packages / component / 'meta'
        component_data = component_meta.parent / 'data'
        component_meta.mkdir(parents=True)
        (component_data / details['runtime']).parent.mkdir(parents=True)
        shutil.move(runtime, component_data / details['runtime'])
        (component_data / details['manifest']).write_text(
            json.dumps(payload_manifest(component_data), indent=2) + '\n'
        )
        write_assistant_metadata(component_meta, version, component)
    template_args, tool_environment = [], None
    runtime = None
    if SYSTEM == 'linux':
        template, runtime, tool_environment = linux_installer_runtime(tools, output)
        template_args = ['-t', template]
        shutil.copytree(runtime, data / runtime.name)
    elif SYSTEM == 'macos':
        template_args = ['-t', macos_installer_template(tools, output)]
    (data / 'update-channel.txt').write_text(channel + '\n', encoding='utf-8')
    (data / 'payload-manifest.json').write_text(
        json.dumps(payload_manifest(data), indent=2) + '\n'
    )
    if repository_url is None:
        repository_url, *default_mirrors = repository_urls(channel)
        mirrors = tuple(default_mirrors)
    write_metadata(
        config,
        meta,
        version,
        repository_url,
        mirrors,
        enable_mirrors=channel == 'stable',
        tool_bytes=installerbase_bytes(tools),
    )
    return source, template_args, tool_environment, runtime


def package_app(  # noqa: PLR0913, PLR0914 - the stage's identity and how it ships
    stage: Path,
    tools: Path,
    output: Path,
    version: str,
    repository_url: str | None = None,
    mirrors: tuple[str, ...] = (),
    maintenance_tool: Path | None = None,
    *,
    internal: bool = False,
) -> Path:
    """Package the stage; an internal build carries every assistant, distributed or not."""
    if not re.fullmatch(r'[0-9]+(?:[.-][0-9]+)*', version):
        raise RuntimeError('Installer version must contain only numeric components')
    stage, tools, output = stage.resolve(), tools.resolve(), output.resolve()
    if not (
        stage
        / (
            'EasyDiffraction.app/Contents/MacOS/EasyDiffraction'
            if SYSTEM == 'macos'
            else 'bin/EasyDiffraction' + SUFFIX
        )
    ).is_file():
        raise RuntimeError('Stage does not contain the native application')
    if output.is_relative_to(stage):
        raise RuntimeError('Installer output must be outside the application stage')
    payload_manifest(stage)
    inputs_path = stage / 'build-inputs.json'
    inputs = json.loads(inputs_path.read_text(encoding='utf-8')) if inputs_path.is_file() else {}
    if inputs.get('release_version') and inputs['release_version'] != version:
        raise RuntimeError('Application and installer release versions disagree')
    output.mkdir(parents=True, exist_ok=True)
    channel = 'stable' if inputs.get('release_history_sha256') else 'testing'
    source, template_args, tool_environment, runtime = prepare_installer_source(
        stage, tools, output, version, repository_url, mirrors, channel
    )
    excluded = withheld_components(source / 'packages', internal=internal)
    maintenance_sha256 = (
        add_maintenance_tool(source / 'packages', maintenance_tool, tools, output, version)
        if SYSTEM in {'macos', 'windows'}
        else None
    )
    if repository_url:
        # Every online release, Linux included: only an update can refresh the tool's pages.
        add_maintenance_resource(source, tools, tool_environment)
        # --sha-update writes each component's content checksum into the feed, and the Maintenance
        # Tool then offers a component whose checksum differs from the installed one instead of
        # one with a higher version. That is how 2026.11.x installs take 26.17, a lower number
        # (edi ADR-0106). The checksum is the archive's, which a rebuild changes, so promotion
        # publishes an unchanged component's earlier copy instead (edi ADR-0111).
        write_repository(
            tools,
            source / 'packages',
            output / 'repository',
            tool_environment,
            excluded,
            public=not internal,
        )
    kind = 'online' if repository_url else 'offline'
    name = installer_stem(version, kind)
    installer = output / (
        name + ('.app' if SYSTEM == 'macos' else '.exe' if SYSTEM == 'windows' else '.run')
    )
    run(
        [
            tools / ('bin/binarycreator' + SUFFIX),
            '--verbose',
            *template_args,
            '--compression',
            '1',
            '--online-only' if repository_url else '--hybrid',
            # An online-only installer carries no component, and binarycreator refuses --exclude
            # with it; its repository already leaves the withheld ones out.
            *(['--exclude', ','.join(excluded)] if excluded and not repository_url else []),
            '-r',
            source / 'config/resources/resources.qrc',
            '-c',
            source / 'config/config.xml',
            '-p',
            source / 'packages',
            installer,
        ],
        env=tool_environment,
    )
    # The menu bar and Dock show this name, not the download's file name; the icon is enlarged.
    set_bundle_identifier(
        installer, 'org.easydiffraction.installer', MACOS_INSTALLER_NAME, installer_icon=True
    )
    if SYSTEM == 'macos':
        # The installer's icon is drawn from the EasyDiffraction branding, whose BSD licence asks
        # for its notice with the binaries: it travels inside the app, not loose in the disk image.
        (installer / 'Contents/Resources').mkdir(parents=True, exist_ok=True)
        shutil.copy2(
            ROOT / 'website/BRANDING-LICENSE',
            installer / 'Contents/Resources/BRANDING-LICENSE.txt',
        )
    download = deliver_installer(installer, runtime)
    (output / 'installer.json').write_text(
        json.dumps(
            {
                'installer': installer.name,
                'download': download.name,
                'download_sha256': sha256(download),
                'ifw': '4.11.0',
                'platform': PLATFORM_ID,
                'version': version,
                'kind': kind,
                'repository_url': repository_url,
                'edi_commit': inputs.get('edi_commit'),
                'release_history_sha256': inputs.get('release_history_sha256'),
                'maintenance_tool_sha256': maintenance_sha256,
                # An internal build may carry an assistant before its distribution is public,
                # so publication refuses it (tools/release/assistants.py).
                'internal': internal,
                'assistants': [
                    name
                    for name in ASSISTANT_COMPONENTS
                    if (source / 'packages' / name).is_dir() and name not in excluded
                ],
                # Promotion keeps an earlier copy of a component whose identity is unchanged.
                'component_identities': {
                    package.name: component_identity(package, version)
                    for package in sorted((source / 'packages').iterdir())
                    if package.is_dir() and package.name not in excluded
                },
            },
            indent=2,
        )
        + '\n'
    )
    return installer


def required_environment(*names: str) -> list[str]:
    values = [os.environ.get(name, '') for name in names]
    missing = [name for name, value in zip(names, values, strict=True) if not value]
    if missing:
        raise RuntimeError('Signing needs ' + ', '.join(missing))
    return values


def macos_signing() -> bool:
    """Signing is on for this macOS run (set by the installers workflow on main only)."""
    return SYSTEM == 'macos' and os.environ.get('EDI_CODESIGN') == '1'


def sign_macos_runtime(path: Path) -> None:
    """Sign with the Developer ID, the hardened runtime and a timestamp, as notarisation needs."""
    (identity,) = required_environment('EDI_CODESIGN_MAC_IDENTITY')
    run([
        'codesign', '--force', '--options', 'runtime', '--timestamp', '--sign', identity, path,
    ])  # fmt: skip
    run(['codesign', '--verify', '--strict', '--verbose=2', path])


def submit_for_notarisation(archive: Path) -> None:
    """Send a ZIP to Apple's notary service and require the status Accepted."""
    apple_id, password, team = required_environment(
        'EDI_NOTARY_APPLE_ID', 'EDI_NOTARY_PASSWORD', 'EDI_NOTARY_TEAM_ID'
    )
    result = subprocess.run(
        [
            'xcrun', 'notarytool', 'submit', archive, '--wait', '--output-format', 'json',
            '--apple-id', apple_id, '--password', password, '--team-id', team,
        ],
        check=False, capture_output=True, text=True,
    )  # fmt: skip
    print(result.stdout, result.stderr, sep='\n', flush=True)
    try:
        status = json.loads(result.stdout).get('status')
    except json.JSONDecodeError:
        status = None
    if result.returncode != 0 or status != 'Accepted':
        raise RuntimeError(f'Notarisation was not accepted: {status}')


def notarise_macos(installer: Path) -> None:
    """Sign an app bundle with the hardened runtime, notarise and staple it (ADR-0091)."""
    (identity,) = required_environment('EDI_CODESIGN_MAC_IDENTITY')
    run([
        'codesign', '--force', '--deep', '--options', 'runtime', '--timestamp',
        '--sign', identity, installer,
    ])  # fmt: skip
    run(['codesign', '--verify', '--deep', '--strict', '--verbose=2', installer])
    upload = installer.with_name(installer.stem + '-notarise.zip')
    run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', installer, upload])
    try:
        submit_for_notarisation(upload)
    finally:
        upload.unlink()
    run(['xcrun', 'stapler', 'staple', installer])
    run(['xcrun', 'stapler', 'validate', installer])
    run(['spctl', '--assess', '--type', 'execute', '--verbose=4', installer])


def signtool() -> Path:
    found = shutil.which('signtool')
    if found:
        return Path(found)
    kits = Path(os.environ.get('PROGRAMFILES(X86)', r'C:\Program Files (x86)'))
    kits /= 'Windows Kits/10/bin'
    candidates = sorted(kits.glob('*/x64/signtool.exe'))
    if not candidates:
        raise RuntimeError('signtool is not installed')
    return candidates[-1]


def verify_windows_signature(path: Path) -> None:
    run([signtool(), 'verify', '/pa', '/v', path])


def windows_signing() -> bool:
    """Signing is on for this Windows run (set by the installers workflow on main only)."""
    return SYSTEM == 'windows' and os.environ.get('EDI_CODESIGN') == '1'


def sign_windows(path: Path) -> None:
    """Sign through DigiCert KeyLocker with the smctl the signing action installed, then verify."""
    (alias,) = required_environment('EDI_CODESIGN_WIN_KEYPAIR_ALIAS')
    run([
        'smctl', 'sign', '--simple', '--input', path, '--keypair-alias', alias,
        '--exit-non-zero-on-fail', '--failfast',
    ])  # fmt: skip
    verify_windows_signature(path)


def seal_disk_image(image: Path) -> None:
    """Sign, notarise and staple the disk image itself, so Gatekeeper accepts the download."""
    (identity,) = required_environment('EDI_CODESIGN_MAC_IDENTITY')
    run(['codesign', '--force', '--timestamp', '--sign', identity, image])
    run(['codesign', '--verify', '--strict', '--verbose=2', image])
    submit_for_notarisation(image)
    run(['xcrun', 'stapler', 'staple', image])
    run(['xcrun', 'stapler', 'validate', image])
    run([
        'spctl', '--assess', '--type', 'open', '--context', 'context:primary-signature',
        '--verbose=4', image,
    ])  # fmt: skip


def seal_installer(output: Path) -> None:
    """Finish a signed installer after packaging and make its download again.

    macOS signs, notarises and staples the installer app and then its disk image; Windows signs
    and verifies the installer, which is the download.
    """
    output = output.resolve()
    metadata_path = output / 'installer.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    installer = output / metadata['installer']
    if SYSTEM == 'macos':
        notarise_macos(installer)
    elif SYSTEM == 'windows':
        sign_windows(installer)
    else:
        raise RuntimeError('Linux installers are not signed')
    download = deliver_installer(installer, None, ad_hoc=False)
    if SYSTEM == 'macos':
        seal_disk_image(download)
        set_file_icon(download)
    metadata.update({'download': download.name, 'download_sha256': sha256(download)})
    metadata_path.write_text(json.dumps(metadata, indent=2) + '\n')


def clean_environment(home: Path) -> dict:
    temporary = home / 'tmp'
    temporary.mkdir(parents=True, exist_ok=True)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(('CONDA', 'PIXI', 'QT_', 'QML', 'EDI_', 'LD_', 'DYLD_', 'PYTHON'))
    }
    if SYSTEM == 'windows':
        system_root = next(
            (value for key, value in env.items() if key.casefold() == 'systemroot'), None
        )
        if not system_root:
            raise RuntimeError('Windows installer check requires the operating-system directory')
        system = Path(system_root)
        env['PATH'] = str(system / 'System32') + os.pathsep + str(system)
    else:
        env['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'
    env.update(
        HOME=str(home),
        TMP=str(temporary),
        TEMP=str(temporary),
        TMPDIR=str(temporary),
        USERPROFILE=str(home),
        XDG_CONFIG_HOME=str(home / 'config'),
        XDG_DATA_HOME=str(home / 'data'),
        XDG_CACHE_HOME=str(home / 'cache'),
        CODEX_HOME=str(home / 'codex'),
        APPDATA=str(home / 'appdata/roaming'),
        LOCALAPPDATA=str(home / 'appdata/local'),
        QML_DISABLE_DISK_CACHE='1',
    )
    if SYSTEM == 'linux':
        env.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software')
    return env


def check_linux_dependencies(root: Path, env: dict) -> dict:
    receipts = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                continue
        result = subprocess.run(
            ['/usr/bin/ldd', str(path)], env=env, capture_output=True, text=True, check=False
        )
        text = result.stdout + result.stderr
        if result.returncode and (
            'not a dynamic executable' in text or 'statically linked' in text
        ):
            continue
        if result.returncode or 'not found' in text:
            raise RuntimeError(f'Unresolved installed dependency: {path}\n{text}')
        for line in text.splitlines():
            if '=> /' in line:
                resolved = Path(line.split('=>', 1)[1].strip().split(' (', 1)[0])
                if not resolved.is_relative_to(root) and not any(
                    resolved.is_relative_to(Path(prefix))
                    for prefix in ['/usr/lib', '/lib', '/lib64']
                ):
                    raise RuntimeError(f'Installed dependency escapes the package: {line}')
        receipts[path.relative_to(root).as_posix()] = text
    return receipts


def unpack_installer(download: Path, output: Path) -> Path:
    """Take the installer out of its download: the disk image or the ZIP."""
    output.mkdir(parents=True)
    suffix = '.app' if SYSTEM == 'macos' else '.exe' if SYSTEM == 'windows' else '.run'
    if download.suffix == '.dmg':
        mount = output.parent / (output.name + ' image')
        run(['hdiutil', 'attach', '-nobrowse', '-readonly', '-mountpoint', mount, download])
        try:
            found = list(mount.glob('*' + suffix))
            if len(found) != 1:
                raise RuntimeError('Disk image must contain one installer app')
            run(['ditto', found[0], output / found[0].name])
        finally:
            run(['hdiutil', 'detach', mount])
    else:
        with zipfile.ZipFile(download) as zipped:
            for member in zipped.infolist():
                if Path(member.filename).is_absolute() or '..' in Path(member.filename).parts:
                    raise RuntimeError('Installer archive escapes its extraction directory')
            zipped.extractall(output)  # noqa: S202 - validated paths; zip extraction creates no links
            for member in zipped.infolist():
                path = output / member.filename
                if path.is_file():
                    path.chmod((member.external_attr >> 16) & 0o777)
    candidates = list(output.glob('*' + suffix))
    if len(candidates) != 1:
        raise RuntimeError('Installer download must contain one platform bootstrap')
    return candidates[0]


def installer_from_download(download: Path, output: Path) -> Path:
    """The installer itself: unpacked from a disk image or ZIP, or the download on Windows."""
    if download.suffix in {'.zip', '.dmg'}:
        return unpack_installer(download, output)
    return download


def verify_installed_payload(
    target: Path, *, with_assistant: bool = False, assistants: tuple[str, ...] = ()
) -> None:
    """The installed bytes with exactly the chosen assistants (with_assistant: ChatGPT)."""
    chosen = set(assistants) | ({ASSISTANT_COMPONENT} if with_assistant else set())
    manifest = json.loads((target / 'payload-manifest.json').read_text(encoding='utf-8'))
    for component, details in ASSISTANT_COMPONENTS.items():
        optional_manifest = target / details['manifest']
        if component in chosen:
            manifest.update(json.loads(optional_manifest.read_text(encoding='utf-8')))
        elif optional_manifest.exists() or (target / details['runtime']).exists():
            raise RuntimeError(
                f'The installation includes the unselected {details["name"]} assistant'
            )
    for name, expected in manifest.items():
        path = target / name
        if 'sha256' in expected and (not path.is_file() or sha256(path) != expected['sha256']):
            raise RuntimeError(f'Installed bytes differ: {name}')
        if 'link' in expected and (
            not path.is_symlink() or str(path.readlink()) != expected['link']
        ):
            raise RuntimeError(f'Installed link differs: {name}')


def verify_installed_identity(metadata: dict, receipt: dict) -> None:
    version = metadata.get('version', '')
    if versions.is_version(version) and receipt.get('app_version') != version:
        raise RuntimeError('Installed application and installer calendar versions differ')
    history = metadata.get('release_history_sha256')
    if history and receipt.get('release_history_sha256') != history:
        raise RuntimeError('Installed release history differs')


def exercise_installer(
    installer: Path,
    output: Path,
    repository: str | None = None,
    *,
    with_assistant: bool = False,
    assistants: tuple[str, ...] = (),
) -> None:
    chosen = tuple(
        name
        for name in ASSISTANT_COMPONENTS
        if name in assistants or (with_assistant and name == ASSISTANT_COMPONENT)
    )
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    metadata_path = installer.parent / 'installer.json'
    metadata = (
        json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.is_file() else {}
    )
    installer = installer_from_download(installer, output / 'downloaded installer')
    home, target = output / 'isolated home', output / 'installed app'
    home.mkdir(exist_ok=True)
    if target.exists():
        raise RuntimeError('Installation target already exists; choose a fresh test directory')
    env = clean_environment(home)
    command = installer.resolve()
    if SYSTEM == 'macos':
        command = next((command / 'Contents/MacOS').iterdir())
    repository_args = ['--set-temp-repository', repository] if repository else []
    with (output / 'install.log').open('w') as log:
        run(
            [
                command,
                *repository_args,
                '--root',
                target,
                '--accept-licenses',
                '--default-answer',
                '--confirm-command',
                'install',
                *chosen,
            ],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
    app = target / (
        'EasyDiffraction.app/Contents/MacOS/EasyDiffraction'
        if SYSTEM == 'macos'
        else 'bin/EasyDiffraction' + SUFFIX
    )
    try:
        verify_installed_payload(target, assistants=chosen)
        app = target / (
            'EasyDiffraction.app/Contents/MacOS/EasyDiffraction'
            if SYSTEM == 'macos'
            else 'bin/EasyDiffraction' + SUFFIX
        )
        smoke_installed_app(app, output, env, home)
        receipt = json.loads((output / 'smoke/result.json').read_text(encoding='utf-8'))
        verify_installed_identity(metadata, receipt)
        # The app finds exactly the assistant runtimes installed (installer_smoke.cpp).
        available = {
            name: receipt.get(key)
            for name, key in (
                (ASSISTANT_COMPONENT, 'assistant_available'),
                (CLAUDE_COMPONENT, 'claude_available'),
                (COPILOT_COMPONENT, 'copilot_available'),
            )
        }
        if (
            not receipt.get('passed')
            or available != {name: name in chosen for name in available}
            or not receipt.get('svg_images')
            or not (output / 'smoke/window.png').is_file()
        ):
            raise RuntimeError('Installed application smoke check failed')
        if windows_signing():
            verify_windows_signature(app)
        if SYSTEM == 'linux':
            dependencies = check_linux_dependencies(target, env)
            (output / 'dependencies.json').write_text(json.dumps(dependencies, indent=2) + '\n')
    finally:
        maintenance = target / (
            'MaintenanceTool.app/Contents/MacOS/MaintenanceTool'
            if SYSTEM == 'macos'
            else 'MaintenanceTool' + SUFFIX
        )
        verify_installed_maintenance_tool(target, metadata)
        with (output / 'uninstall.log').open('w') as log:
            run(
                [maintenance, '--confirm-command', '--default-answer', 'purge'],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=120,
            )
    if app.exists():
        raise RuntimeError('Uninstaller left the application installed')
    (output / 'passed.json').write_text(
        json.dumps({'passed': True, 'smoke': receipt}, indent=2) + '\n'
    )


# A hosted runner's first start of a freshly installed app can take long (a cold disk, a font
# cache, a macOS signature check), so the smoke run has two minutes and one more try after a
# timeout; a failure is not retried.
SMOKE_TIMEOUT = 120
SMOKE_TRIES = 2


def smoke_installed_app(app: Path, output: Path, env: dict, home: Path) -> None:
    for attempt in range(1, SMOKE_TRIES + 1):
        shutil.rmtree(output / 'smoke', ignore_errors=True)
        with (output / 'app.log').open('w' if attempt == 1 else 'a') as log:
            log.write(f'--- smoke run {attempt} of {SMOKE_TRIES}\n')
            log.flush()
            try:
                run(
                    [app, '--testmode', output / 'smoke'],
                    env=env,
                    cwd=home,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=SMOKE_TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                if attempt == SMOKE_TRIES:
                    raise
                print(f'smoke run timed out after {SMOKE_TIMEOUT} s; trying once more', flush=True)
            else:
                return


def relocate_linux(stage: Path, patchelf: Path, qt_prefix: Path) -> None:
    stage = stage.resolve()
    if SYSTEM != 'linux':
        raise RuntimeError('ELF relocation is Linux only')
    for name in ['libssl.so.3', 'libcrypto.so.3']:
        source = qt_prefix / 'lib' / name
        if source.is_file():
            shutil.copy2(source.resolve(), stage / 'lib' / name)
    if (stage / 'lib/libc.so.6').exists():
        raise RuntimeError('The application must not bundle the operating system C library')
    for path in sorted(stage.rglob('*')):
        if path.is_symlink() or not path.is_file():
            continue
        # The assistant runtimes keep their published bytes (edi ADR-0108).
        if any(
            path.is_relative_to(stage / details['runtime'])
            for details in ASSISTANT_COMPONENTS.values()
        ):
            continue
        with path.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                continue
        relative = os.path.relpath(stage / 'lib', path.parent)
        run([patchelf, '--set-rpath', '$ORIGIN/' + relative, path])


def main() -> None:  # noqa: PLR0915 - one parser and one branch per subcommand
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    relocate = commands.add_parser('relocate-linux')
    relocate.add_argument('--stage', type=Path, required=True)
    relocate.add_argument('--patchelf', type=Path, required=True)
    relocate.add_argument('--qt-prefix', type=Path, required=True)
    fetch = commands.add_parser('tools')
    fetch.add_argument('--output', type=Path, required=True)
    package = commands.add_parser('package')
    package.add_argument('--stage', type=Path, required=True)
    package.add_argument('--tools', type=Path, required=True)
    package.add_argument('--output', type=Path, required=True)
    package.add_argument('--version')
    package.add_argument(
        '--release-plan', type=Path, default=os.environ.get('EDI_RELEASE_PLAN') or None
    )
    package.add_argument('--kind', choices=['offline', 'online'], default='offline')
    package.add_argument('--repository-url')
    package.add_argument('--channel', choices=['testing', 'stable'])
    package.add_argument('--maintenance-tool', type=Path)
    package.add_argument(
        '--internal',
        action='store_true',
        help='Also carry the assistants whose distribution is internal; never published',
    )
    maintenance = commands.add_parser('maintenance-tool')
    for option in ['--tools', '--output']:
        maintenance.add_argument(option, type=Path, required=True)
    test = commands.add_parser('test')
    test.add_argument('--installer', type=Path, required=True)
    test.add_argument('--output', type=Path, required=True)
    test.add_argument('--repository')
    test.add_argument('--with-assistant', action='store_true', help='Install ChatGPT')
    test.add_argument(
        '--assistant',
        action='append',
        default=[],
        choices=list(ASSISTANT_COMPONENTS),
        help='Install this assistant component too (repeatable)',
    )
    seal = commands.add_parser('seal')
    seal.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'relocate-linux':
        relocate_linux(args.stage, args.patchelf, args.qt_prefix)
    elif args.command == 'tools':
        fetch_tools(args.output)
    elif args.command == 'package':
        urls = repository_urls(args.channel or ('stable' if args.release_plan else 'testing'))
        version = args.version or os.environ.get('EDI_INSTALLER_VERSION') or '0.0.0'
        if args.release_plan:
            release = read_release_plan(args.release_plan)
            if args.version and args.version != release['version']:
                raise RuntimeError('Explicit version disagrees with the prepared release')
            version = release['version']
            inputs = json.loads((args.stage / 'build-inputs.json').read_text(encoding='utf-8'))
            if inputs.get('edi_commit') != release['commit'] or inputs.get(
                'release_history_sha256'
            ) != sha256(args.release_plan / 'release-history.json'):
                raise RuntimeError('Staged application does not match the prepared release')
        package_app(
            args.stage,
            args.tools,
            args.output,
            version,
            (args.repository_url or urls[0]) if args.kind == 'online' else None,
            urls[1:] if args.kind == 'online' else (),
            args.maintenance_tool,
            internal=args.internal,
        )
    elif args.command == 'maintenance-tool':
        build_maintenance_tool(args.tools, args.output)
    elif args.command == 'seal':
        seal_installer(args.output)
    else:
        exercise_installer(
            args.installer,
            args.output,
            args.repository,
            with_assistant=args.with_assistant,
            assistants=tuple(args.assistant),
        )


if __name__ == '__main__':
    main()
