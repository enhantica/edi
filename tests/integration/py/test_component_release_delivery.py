# SPDX-License-Identifier: BSD-3-Clause
"""Release assets and IFW repository updates from independent release fixtures."""

import hashlib
import json
import re
import shutil
import subprocess
import tarfile
from xml.etree import ElementTree as ET  # noqa: S405 - synthetic fixture XML

import pytest

from tests.integration.py.test_installer_identity import PACKAGE
from tests.unit.py.test_release_promotion import PROMOTE, ROOT, module

DISTRIBUTION = module('distribution')
APP = 'org.easydiffraction.app'
CHATGPT = 'org.easydiffraction.app.assistant'
MAINTENANCE = 'org.easydiffraction.app.maintenancetool'
CLAUDE = 'org.easydiffraction.app.claude'
COPILOT = 'org.easydiffraction.app.copilot'
CURRENT, PREVIOUS, ORIGINAL = '26.20', '26.19', '26.17'
PLATFORM_COMPONENTS = {
    'linux-x86_64': (APP, CHATGPT),
    'macos-arm64': (APP, CHATGPT, MAINTENANCE),
    'windows-x86_64': (APP, CHATGPT, MAINTENANCE),
}
ARCHIVES = ('content.7z', 'translations-extra.7z')


def sha1(data):
    return hashlib.sha1(data).hexdigest()  # noqa: S324 - IFW repository checksum format


def contents(component, version, file):
    return f'{component} at {version}: {file}\n'.encode()


def asset_name(platform, component, version, archive):
    # ADR-0071 and GitHub's documented flat release asset name and browser_download_url.
    return f'component-{platform}-{component}-{version}{archive}'


def archive_url(platform, component, version, archive):
    name = asset_name(platform, component, version, archive)
    return f'https://github.com/enhantica/edi/releases/download/v{version}/{name}'


def repository(folder, versions):
    # Qt IFW 4.11 repositorygen.cpp: each data archive has a sidecar and the package
    # SHA1 field describes meta.7z. Distinct old bytes expose a rebuilt archive substitution.
    updates = ET.Element('Updates')
    for name, version in versions.items():
        component = folder / name
        component.mkdir(parents=True)
        digest = {}
        for file in (*ARCHIVES, 'meta.7z'):
            payload = contents(name, version, file)
            (component / f'{version}{file}').write_bytes(payload)
            digest[file] = sha1(payload)
            if file in ARCHIVES:
                (component / f'{version}{file}.sha1').write_text(digest[file] + '\n')
        package = ET.SubElement(updates, 'PackageUpdate')
        for key, value in {
            'Name': name,
            'Version': version,
            'DownloadableArchives': ','.join(ARCHIVES),
            'SHA1': digest['meta.7z'],
            'ContentSha1': digest[ARCHIVES[0]],
        }.items():
            ET.SubElement(package, key).text = value
    ET.ElementTree(updates).write(folder / 'Updates.xml')


def tar_files(path):
    with tarfile.open(path) as archive:
        return {
            item.name: archive.extractfile(item).read()
            for item in archive.getmembers()
            if item.isfile()
        }


def served_redirect(rules, path, *, file_exists):
    # Evaluate the documented mod_rewrite operations used in the generated per-directory
    # rules. Apache supplies paths without a leading slash and tests -f on the mapped file.
    # https://httpd.apache.org/docs/2.4/mod/mod_rewrite.html
    condition = True
    for line in rules.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        directive, *args = line.split()
        if directive == 'RewriteCond':
            assert args == ['%{REQUEST_FILENAME}', '!-f'], (
                'The archive redirect must honor whether the server already holds the file'
            )
            condition = condition and not file_exists
        elif directive == 'RewriteRule':
            pattern, target, flags = args
            if condition and (match := re.search(pattern, path)):
                assert 'R=302' in flags.strip('[]').split(','), (
                    'Component archives use a temporary HTTP redirect'
                )
                return re.sub(r'\$(\d+)', lambda backref: match[int(backref[1])], target)
            condition = True
        else:
            pytest.fail(f'Unexpected component rewrite directive: {directive}')
    return None


def copies(publication, output):
    (publication / 'assets').mkdir(exist_ok=True)
    (publication / 'release.json').write_text(json.dumps({'version': CURRENT}))
    feeds = publication / 'incoming/releases'
    feeds.mkdir()
    for name in ('stable-v2.json', 'stable.json'):
        (feeds / name).write_text('{}')
    DISTRIBUTION.build(publication, output)
    return output / 'release'


def check_index(release, platform, versions):
    where = f'repository/{platform}'
    index = tar_files(release / f'repoindex-stable-{platform}.tar.gz')
    prefix = f'{where}/'
    expected = {prefix + 'Updates.xml', prefix + 'redirect.htaccess'}
    for name, own in versions.items():
        expected.add(f'{where}/{name}/{own}meta.7z')
        expected.update(f'{where}/{name}/{own}{archive}.sha1' for archive in ARCHIVES)
    assert set(index) == expected, (
        'The index must contain only Updates.xml, metadata, checksums and the redirect file'
    )

    rules = index[prefix + 'redirect.htaccess'].decode()
    updates = ET.fromstring(index[prefix + 'Updates.xml'])  # noqa: S314 - synthetic fixture XML
    packages = {p.findtext('Name'): p for p in updates.findall('PackageUpdate')}
    assert {name: p.findtext('Version') for name, p in packages.items()} == versions, (
        'The release index must advertise each component at the tag that last changed it'
    )
    for path in expected:
        assert served_redirect(rules, path, file_exists=True) is None, (
            f'The download host must serve the indexed file {path} itself'
        )
        if path.endswith(('.sha1', '/Updates.xml')):
            assert served_redirect(rules, path, file_exists=False) is None, (
                f'IFW must never follow a redirect for {path}, even on a cache miss'
            )

    for name, own in versions.items():
        meta = index[f'{where}/{name}/{own}meta.7z']
        assert meta == contents(name, own, 'meta.7z') and sha1(meta) == packages[name].findtext(
            'SHA1'
        ), 'The local metadata archive must match the checksum in Updates.xml'
        assert packages[name].findtext('ContentSha1') == sha1(contents(name, own, ARCHIVES[0])), (
            'The advertised content checksum must remain the checksum of the owning release'
        )
        for archive in ARCHIVES:
            path = f'{where}/{name}/{own}{archive}'
            checksum_url = f'https://download.easydiffraction.org/{path}.sha1'
            # Qt IFW 4.11 src/libs/kdtools/filedownloader.cpp derives the next request
            # from the final checksum URL. Here the sidecar stays on the download host.
            archive_path = checksum_url.removesuffix('.sha1').split('/', 3)[-1]
            assert served_redirect(rules, archive_path, file_exists=False) == archive_url(
                platform, name, own, archive
            ), 'Every missing archive must redirect to its own flat asset at the owning tag'
            assert served_redirect(rules, archive_path, file_exists=True) is None, (
                'An archive served directly, including during rollback, must take precedence'
            )
            data = contents(name, own, archive)
            assert index[path + '.sha1'].decode().strip() == sha1(data), (
                'The local IFW sidecar must verify the exact bytes reached by the archive URL'
            )
            asset = release / asset_name(platform, name, own, archive)
            if own == CURRENT:
                assert asset.read_bytes() == data, (
                    'The flat GitHub asset must keep the exact bytes'
                )
            else:
                assert not asset.exists(), 'An earlier component archive must never reattach'
    for path in (
        f'{where}/unknown.txt',
        f'{where}/{APP}/{CURRENT}content.7z.bak',
        f'{where}/{APP}/content.7z',
        f'outside/{APP}/{CURRENT}content.7z',
    ):
        assert served_redirect(rules, path, file_exists=False) is None, (
            f'The component rule must leave unrelated paths alone: {path}'
        )


def test_release_attaches_flat_assets_and_serves_framework_index(tmp_path):
    publication = tmp_path / 'publication'
    for platform, names in PLATFORM_COMPONENTS.items():
        repository(
            publication / 'incoming/repository/stable' / platform, dict.fromkeys(names, CURRENT)
        )
    release = copies(publication, tmp_path / 'copies')
    assert {item.name for item in release.glob('component-*')} == {
        asset_name(platform, name, CURRENT, archive)
        for platform, names in PLATFORM_COMPONENTS.items()
        for name in names
        for archive in ARCHIVES
    }, 'A fresh release must attach exactly one flat asset for each current-version archive'
    for platform, names in PLATFORM_COMPONENTS.items():
        check_index(release, platform, dict.fromkeys(names, CURRENT))


def damage_installer_identities(metadata, damage):
    identities = metadata['component_identities']
    if damage == 'missing-identities':
        metadata.clear()
    elif damage == 'missing-identity':
        del identities[CHATGPT]
    elif damage == 'extra-identity':
        identities[COPILOT] = 'e' * 64
    elif damage == 'invalid-identity':
        identities[CHATGPT] = 'invalid'


@pytest.fixture
def promotion(tmp_path, request):
    damage = request.param
    platform = 'windows-x86_64'
    publication = tmp_path / 'publication'
    candidate = publication / 'incoming/repository/stable' / platform
    versions = dict.fromkeys(PLATFORM_COMPONENTS[platform], CURRENT)
    if damage == 'withheld-claude':
        versions[CLAUDE] = CURRENT
    if damage == 'withheld-copilot':
        versions[COPILOT] = CURRENT
    repository(candidate, versions)
    if damage in {'unlisted-claude', 'unlisted-copilot'}:
        hidden = CLAUDE if damage.endswith('claude') else COPILOT
        repository(tmp_path / 'withheld', {hidden: CURRENT})
        shutil.copytree(tmp_path / 'withheld' / hidden, candidate / hidden)

    identities = {APP: 'a' * 64, CHATGPT: 'b' * 64, MAINTENANCE: 'c' * 64}
    metadata = {'component_identities': identities.copy()}
    versions = {APP: PREVIOUS, CHATGPT: ORIGINAL, MAINTENANCE: PREVIOUS}
    prior_index = tmp_path / 'prior/repository' / platform
    repository(prior_index, versions)
    entries = {
        name: {
            'identity': 'd' * 64 if name == APP else identities[name],
            'version': own,
            'archives': [asset_name(platform, name, own, archive) for archive in ARCHIVES],
        }
        for name, own in versions.items()
    }
    if damage in {'record-archive', 'changed-record-archive'}:
        entries[APP if damage.startswith('changed') else CHATGPT]['archives'].pop()
    if damage == 'record-version':
        entries[CHATGPT]['version'] = PREVIOUS
    damage_installer_identities(metadata, damage)

    index_name = f'repoindex-stable-{platform}.tar.gz'
    index_file = tmp_path / index_name
    if damage == 'metadata':
        # The index is archived with damaged bytes and its original XML checksum.
        (prior_index / CHATGPT / f'{ORIGINAL}meta.7z').write_bytes(b'changed')
    with tarfile.open(index_file, 'w:gz') as bundle:
        for path in sorted(prior_index.rglob('*')):
            if path.name == 'Updates.xml' or path.name.endswith(('.sha1', 'meta.7z')):
                bundle.add(path, arcname=path.relative_to(tmp_path / 'prior').as_posix())
    fetches = []

    def fetch(tag, name, output):
        fetches.append((tag, name))
        if name == 'components.json':
            shutil.copyfile(tmp_path / name, output / name)
            return
        if name == index_name:
            assert tag == f'v{PREVIOUS}', 'Promotion must load the latest published index'
            shutil.copyfile(index_file, output / name)
            return
        # Fixture assets are keyed by the documented owning tag and flat asset name.
        for component, own in versions.items():
            for archive in ARCHIVES:
                if (tag, name) == (f'v{own}', asset_name(platform, component, own, archive)):
                    data = contents(component, own, archive)
                    (output / name).write_bytes(b'changed' if damage == 'archive' else data)
                    return
        pytest.fail(f'Unexpected release asset request: {tag}/{name}')

    record = {
        'schema': 'edi.components/1',
        'version': CURRENT if damage == 'too-new' else PREVIOUS,
        'platforms': {platform: entries},
    }
    (tmp_path / 'components.json').write_text(json.dumps(record))
    return publication, candidate, platform, metadata, record, fetch, fetches


@pytest.mark.parametrize('promotion', ['valid'], indirect=True)
def test_promotion_reuses_the_original_component_release(tmp_path, promotion):
    publication, candidate, platform, metadata, previous, fetch, fetches = promotion
    entries = PROMOTE.publish_components(candidate, platform, CURRENT, metadata, previous, fetch)
    record = {'schema': 'edi.components/1', 'version': CURRENT, 'platforms': {platform: entries}}
    (publication / 'assets').mkdir()
    (publication / 'assets/components.json').write_text(json.dumps(record))
    release = copies(publication, tmp_path / 'copies')
    versions = {APP: CURRENT, CHATGPT: ORIGINAL, MAINTENANCE: PREVIOUS}
    check_index(release, platform, versions)
    assert {item.name for item in release.glob('component-*')} == {
        asset_name(platform, APP, CURRENT, archive) for archive in ARCHIVES
    }, 'A release changing only the app must attach only the app content archives'
    assert json.loads((release / 'components.json').read_text()) == {
        'schema': 'edi.components/1',
        'version': CURRENT,
        'platforms': {
            platform: {
                name: {
                    'version': own,
                    'identity': metadata['component_identities'][name],
                    'archives': [asset_name(platform, name, own, archive) for archive in ARCHIVES],
                }
                for name, own in versions.items()
            }
        },
    }, 'The published component record must pair the current input identity with the owning tag'
    assert set(fetches) == {
        (f'v{PREVIOUS}', f'repoindex-stable-{platform}.tar.gz'),
        *(
            (f'v{own}', asset_name(platform, name, own, archive))
            for name, own in versions.items()
            if name != APP
            for archive in ARCHIVES
        ),
    }, 'Promotion must recover unchanged bytes only from the tags that originally shipped them'


@pytest.mark.parametrize(
    ('promotion', 'reason'),
    [
        ('missing-identities', 'identity'),
        ('missing-identity', 'identity'),
        ('extra-identity', 'identity'),
        ('invalid-identity', 'identity'),
        ('too-new', 'not older'),
        ('record-archive', 'disagrees with its index'),
        ('record-version', 'disagrees with its index'),
        ('changed-record-archive', 'disagrees with its index'),
        ('withheld-claude', 'does not match|withheld'),
        ('withheld-copilot', 'does not match|withheld'),
        ('unlisted-claude', 'does not match|withheld|unlisted'),
        ('unlisted-copilot', 'does not match|withheld|unlisted'),
        ('archive', 'archive checksum differs'),
        ('metadata', 'metadata archive checksum differs'),
    ],
    indirect=['promotion'],
    ids=[
        'missing-identities',
        'missing-identity',
        'extra-identity',
        'invalid-identity',
        'too-new',
        'record-archive',
        'record-version',
        'changed-record-archive',
        'withheld-claude',
        'withheld-copilot',
        'unlisted-claude',
        'unlisted-copilot',
        'archive',
        'metadata',
    ],
)
def test_promotion_refuses_a_damaged_release(tmp_path, promotion, reason, monkeypatch):
    publication, candidate, platform, metadata, record, fetch, _ = promotion
    monkeypatch.setattr(
        PROMOTE,
        'api',
        lambda *_: {'tag_name': f'v{record["version"]}', 'assets': [{'name': 'components.json'}]},
    )

    def stage_release():
        previous = PROMOTE.previous_record('enhantica/edi', CURRENT, fetch)
        PROMOTE.validate_repository(
            candidate, CURRENT, expected=frozenset(PLATFORM_COMPONENTS[platform])
        )
        PROMOTE.publish_components(candidate, platform, CURRENT, metadata, previous, fetch)
        copies(publication, tmp_path / 'copies')

    with pytest.raises(ValueError, match=reason):
        stage_release()


@pytest.fixture
def installer_input_tree(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    for relative in (
        'tools/installer',
        'tools/deps/assistant-runtime',
        'tools/deps/claude-runtime',
        'tools/deps/copilot-runtime',
        'data/assistant/runtime',
        'data/distribution.json',
    ):
        dest = source / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        original = ROOT / relative
        if original.is_dir():
            shutil.copytree(original, dest, ignore=shutil.ignore_patterns('__pycache__'))
        else:
            shutil.copyfile(original, dest)
    for command in (['git', 'init', '-q'], ['git', 'add', '--', '.']):
        subprocess.run(command, cwd=source, check=True, capture_output=True, timeout=10)
    monkeypatch.setattr(PACKAGE, 'ROOT', source)
    return source


def change_recipe_sha256(recipe):
    text = recipe.read_text()
    match = re.search(r'(?m)^  (?:archive|binary)_sha256: [^\n]*?"([0-9a-f]{64})"', text)
    assert match is not None, 'The fixture must change a real recipe checksum without its version'
    start, end = match.span(1)
    digest = '1' * 64 if match[1] == '0' * 64 else '0' * 64
    recipe.write_text(text[:start] + digest + text[end:])


@pytest.mark.parametrize(
    ('component', 'recipe'),
    [(CLAUDE, 'claude-runtime'), (COPILOT, 'copilot-runtime')],
)
def test_a_held_runtimes_recipe_checksum_still_governs_its_identity(
    tmp_path, installer_input_tree, component, recipe
):
    package = tmp_path / component
    (package / 'meta').mkdir(parents=True)
    PACKAGE.write_assistant_metadata(package / 'meta', CURRENT, component)
    before = PACKAGE.component_identity(package, CURRENT)
    change_recipe_sha256(installer_input_tree / 'tools/deps' / recipe / 'recipe.yaml')
    assert PACKAGE.component_identity(package, CURRENT) != before, (
        'A runtime must gain a new identity when its pinned checksum changes'
    )


@pytest.mark.parametrize(
    ('changed_input', 'changed_component'),
    [
        ('release-date-and-built-bytes', None),
        ('runtime-sha256', CHATGPT),
        ('maintenance-page', MAINTENANCE),
        ('build-number', MAINTENANCE),
    ],
)
@pytest.mark.parametrize('promotion', ['valid'], indirect=True)
def test_packaged_input_change_changes_only_its_component_version(
    tmp_path, monkeypatch, installer_input_tree, promotion, changed_input, changed_component
):
    _, candidate, platform, _, previous, fetch, _ = promotion
    # Use Windows package rules because its separately packaged Maintenance Tool is public.
    monkeypatch.setattr(PACKAGE, 'SYSTEM', 'windows')
    monkeypatch.setattr(PACKAGE, 'SUFFIX', '.exe')
    monkeypatch.setattr(PACKAGE, 'PLATFORM_ID', 'windows-x86_64')
    stage = tmp_path / 'stage'
    (stage / 'bin').mkdir(parents=True)
    (stage / 'bin/EasyDiffraction.exe').write_bytes(b'fixture app')
    source = tmp_path / 'packages-source'
    for name in (APP, CHATGPT, CLAUDE, COPILOT, MAINTENANCE):
        (source / 'packages' / name / 'meta').mkdir(parents=True)
    for function in (
        'payload_manifest',
        'add_maintenance_resource',
        'write_repository',
        'set_bundle_identifier',
    ):
        monkeypatch.setattr(PACKAGE, function, lambda *_args, **_kwargs: None)
    monkeypatch.setattr(PACKAGE, 'add_maintenance_tool', lambda *_: 'c' * 64)
    monkeypatch.setattr(PACKAGE, 'prepare_installer_source', lambda *_: (source, [], {}, None))
    monkeypatch.setattr(
        PACKAGE, 'run', lambda args, **_: args[-1].write_bytes(b'fixture installer')
    )
    monkeypatch.setattr(PACKAGE, 'deliver_installer', lambda installer, _: installer)

    def build(version, day):
        for name in (APP, CHATGPT, CLAUDE, COPILOT, MAINTENANCE):
            package = source / 'packages' / name
            (package / 'meta/package.xml').write_text(
                f'<Package><Name>{name}</Name><Version>{version}</Version>'
                f'<ReleaseDate>2026-11-{day}</ReleaseDate></Package>'
            )
            (package / 'data.bin').write_bytes(version.encode())
        output = tmp_path / f'built-{version}'
        PACKAGE.package_app(stage, tmp_path / 'ifw', output, version, 'https://fixture.invalid/')
        return json.loads((output / 'installer.json').read_text())

    baseline = build(PREVIOUS, '19')['component_identities']
    assert set(baseline) == {APP, CHATGPT, MAINTENANCE}, (
        'The public installer identity record must cover exactly the distributed components'
    )
    if changed_input == 'runtime-sha256':
        change_recipe_sha256(installer_input_tree / 'tools/deps/assistant-runtime/recipe.yaml')
    elif changed_input == 'maintenance-page':
        with (installer_input_tree / 'tools/installer/Installer.qs').open('a') as script:
            script.write('\n// New Maintenance Tool page fixture\n')
    elif changed_input == 'build-number':
        number, inputs = PACKAGE.COMPONENT_INPUTS[MAINTENANCE]
        monkeypatch.setitem(PACKAGE.COMPONENT_INPUTS, MAINTENANCE, (number + 1, inputs))

    metadata = build(CURRENT, '20')
    assert set(metadata['component_identities']) == set(baseline), (
        'Both held providers must stay absent from public installer.json on every build'
    )
    assert {
        name for name in baseline if baseline[name] != metadata['component_identities'][name]
    } == ({APP, changed_component} if changed_component else {APP}), (
        'Release dates and rebuilt bytes must preserve identity unless a declared input changes'
    )
    for name, entry in previous['platforms'][platform].items():
        entry['identity'] = baseline[name]
    entries = PROMOTE.publish_components(candidate, platform, CURRENT, metadata, previous, fetch)
    expected = {APP: CURRENT, CHATGPT: ORIGINAL, MAINTENANCE: PREVIOUS}
    if changed_component:
        expected[changed_component] = CURRENT
    assert {name: entry['version'] for name, entry in entries.items()} == expected, (
        'Changed inputs must select the new version and preserve the other optional versions'
    )
