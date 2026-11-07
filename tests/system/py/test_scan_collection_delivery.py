"""Downloaded scan archives retain payload, metadata and resource-linkage contracts."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import re
import shlex
import shutil
import subprocess
import sys
import zipfile

import pytest

from tests.integration.py.test_example_catalogue import app_cases
from tests.integration.py.test_scan_app_contract import (
    APP,
    ROOT,
    block,
    item,
    property_value,
    require,
    source,
)
from tests.integration.py.test_scan_extended_contract import (
    assert_source_inventory,
    example_inventory,
)


def test_bundled_project_load_and_save_as_use_the_writable_copy_routes():
    session = source('src/session.cpp')
    wrapper = block(session, 'bool Session::openExample(')
    require(
        wrapper,
        r'openExampleNamed\(exampleId\)',
        'Working-copy wiring: the public example loader reaches its actual copy worker',
    )
    loader = block(session, 'bool Session::openExampleNamed(')
    require(
        loader,
        r'collection_examples_->fetchProject\(exampleId',
        'Working-copy wiring: the example loader fetches the selected collection archive',
    )
    require(
        loader,
        r'openProjectAt\(archive,\s*exampleId\)',
        'Working-copy wiring: the downloaded archive reaches the ordinary opener '
        'with its example identity',
    )
    download = block(
        source('src/collection_examples.cpp'), 'void CollectionExamples::fetchProject('
    )
    require(
        download,
        r'QTemporaryDir',
        'Working-copy wiring: downloads allocate independent temporary storage',
    )
    require(
        download,
        r'QFile out\(path\)',
        'Working-copy wiring: the downloaded bytes are written to their temporary target',
    )
    opened = block(session, 'bool Session::openProjectAt(')
    require(
        opened,
        r'edi::is_project_archive',
        'Working-copy wiring: the common opener recognizes downloaded ZIP projects',
    )
    require(
        opened,
        r'open\(source,\s*example,',
        'Working-copy wiring: the archive enters the common model opener '
        'preserving its example identity',
    )
    copied = block(session, 'bool Session::copyTree(')
    require(
        copied,
        r'QFile::copy\(file, destination\)',
        'Working-copy wiring: ordinary writable copies retain every input file',
    )
    require(
        copied,
        r'QFile::setPermissions\(destination, QFile::ReadOwner \| QFile::WriteOwner\)',
        'Working-copy wiring: the common copy helper retains owner read and write access',
    )
    require(
        copied,
        r'const QString destination = target \+ file\.mid\(source\.size\(\)\);',
        'Working-copy wiring: each copied destination preserves its path '
        'beneath the writable target',
    )
    allocator = block(session, 'QString Session::prepareCopyRoot(')
    require(
        allocator,
        r'edi::fresh_archive_directory\(kind\)',
        'Working-copy wiring: each native copy allocates a fresh independent root',
    )
    qml = source('qml/Main.qml')
    action = block(qml, 'function saveProjectAs(')
    require(
        action,
        r'ApplicationInfo\.saveCurrentProjectAs\(intent\)',
        'Save As wiring: the actual action enters the native chooser owner',
    )
    native = source('src/app_info.cpp')
    require(
        block(native, 'void ApplicationInfo::saveCurrentProjectAs('),
        r'projectInvoke\(frame, "saveAsChoice", "open"\)',
        'Save As wiring: every platform first opens the actual format dialog',
    )
    choice = item(qml, 'saveAs.choice')
    assert property_value(choice, 'onAccepted') == 'ApplicationInfo.acceptProjectSaveChoice()', (
        'Save As wiring: the actual choice acceptance enters its native destination router'
    )
    accepted = block(native, 'void ApplicationInfo::acceptProjectSaveChoice(')
    for route in (
        r'projectInvoke\(frame, "Session", "downloadWebProject"\)',
        r'projectInvoke\(frame, "Session", "saveWebProjectAs",',
        r'zip \? "saveZip" : "saveFolder"',
        r'projectInvoke\(frame, "Session", "suggestedSaveTarget",',
        r'panelUsageMemberCall\(frame, picker, "openAt", \{target\}\)',
    ):
        require(
            accepted,
            route,
            'Save As wiring: acceptance must reach each declared platform destination',
        )
    saver = block(session, 'bool Session::saveAs(')
    require(
        saver,
        r'saveInto\(directory\.toLocalFile\(\)\)',
        (
            'Save As wiring: the actual action passes the selected directory '
            'through the common writer'
        ),
    )
    require(
        block(session, 'bool Session::saveInto('),
        r'project_->saveTo\(folder\)',
        'Save As wiring: the common writer saves the current working project',
    )
    model = block(source('src/project_view_model.cpp'), 'QString ProjectViewModel::saveTo(')
    require(
        model,
        r'edi::Project& saved = scan_template_ \? \*scan_template_ : \*project_;',
        'Save As wiring: the writer selects the actual scan template or ordinary model',
    )
    require(
        model,
        r'edi::save_project_as\(saved, directory\.toStdString\(\)\)',
        'Save As wiring: the selected saved model reaches the core project writer',
    )
    staged = block(session, 'bool Session::stageCopy(')
    require(
        staged,
        r'std::make_shared<edi::Project>\(project_->savedModel\(\)\)',
        'Save As wiring: a staged archive or browser save copies the canonical saved model',
    )
    require(
        staged,
        r'edi::save_project_as\(\*copy, staged\.folder\.toStdString\(\)\)',
        'Save As wiring: the staged copy reaches the actual core project writer',
    )


def resource_inventory(tmp_path, web, production=None):
    cmake = production if production is not None else (APP / 'CMakeLists.txt').read_text()
    body = cmake
    scratch = tmp_path / ('web' if web else 'desktop')
    scratch.mkdir(parents=True)
    receipt = scratch / 'inventory.tsv'
    # The native runtime's executable/sidecar publication is outside this QRC
    # inventory; its own CMake publication suite exercises it. Refuse this
    # separation if it ever gains a resource or compilation-source producer.
    runtime = re.sub(r'#[^\n]*', '', (ROOT / 'cmake/assistant_runtime.cmake').read_text())
    assert not re.search(
        r'\b(?:qt_add_resources|qt_add_qml_module|target_sources)\s*\(', runtime
    ), 'The native runtime packager must remain outside the observed QRC/source inventory'
    harness = f"""cmake_minimum_required(VERSION 3.25)
project(ResourceProbe NONE)
set(PROJECT_SOURCE_DIR "{ROOT.as_posix()}")
set(CMAKE_CURRENT_SOURCE_DIR "{APP.as_posix()}")
set(EMSCRIPTEN {'TRUE' if web else 'FALSE'})
file(WRITE "{receipt.as_posix()}" "")
# This observer configures resources without a compiler or Qt installation.
# Resolve only the two current compilation-package declarations; resource
# producers, target edges, source reachability and payload bytes stay observed.
function(find_package package)
 if(package STREQUAL "crysta" AND "${{ARGN}}" STREQUAL "CONFIG;QUIET")
  return()
 elseif(package STREQUAL "Qt6QmlPrivate" AND "${{ARGN}}" STREQUAL "REQUIRED")
  return()
 endif()
 message(FATAL_ERROR "Examples: unexpected unobserved package ${{package}} ${{ARGN}}")
endfunction()
function(edi_bundle_assistant_runtime)
 if(NOT ARGC EQUAL 0)
  message(FATAL_ERROR "Examples: unexpected native runtime publication arguments")
 endif()
endfunction()
foreach(command include configure_file qt_add_library
 target_include_directories set_target_properties
 qt_add_executable target_compile_definitions add_custom_target add_dependencies
 target_link_options install)
 function(${{command}})
 endfunction()
endforeach()
function(target_sources target)
 foreach(source IN LISTS ARGN)
  if(source MATCHES "^(PRIVATE|PUBLIC|INTERFACE)$")
   continue()
  endif()
  if(NOT source MATCHES "[.](cpp|c|h|hpp|mm)$")
   message(FATAL_ERROR "Examples: unobserved non-compilation target source ${{source}}")
  endif()
 endforeach()
endfunction()
function(target_link_libraries target)
 set(scope PUBLIC)
 foreach(edge IN LISTS ARGN)
  if(edge MATCHES "^(PRIVATE|PUBLIC|INTERFACE)$")
   set(scope "${{edge}}")
  else()
   if(NOT scope STREQUAL "INTERFACE")
    set_property(GLOBAL APPEND PROPERTY "probe_own_${{target}}" "${{edge}}")
   endif()
   if(NOT scope STREQUAL "PRIVATE")
    set_property(GLOBAL APPEND PROPERTY "probe_interface_${{target}}" "${{edge}}")
   endif()
  endif()
 endforeach()
endfunction()
function(qt_add_shaders target resource)
 # ShaderTools compiles graphics assets, outside this example-resource inventory.
 # Production still calls the real required Qt command without a fallback.
endfunction()
function(qt_add_resources target resource)
 cmake_parse_arguments(ARG "" "PREFIX;BASE" "FILES;OPTIONS" ${{ARGN}})
 foreach(file IN LISTS ARG_FILES)
  get_filename_component(base "${{ARG_BASE}}" ABSOLUTE
   BASE_DIR "${{CMAKE_CURRENT_SOURCE_DIR}}")
  get_filename_component(absolute "${{file}}" ABSOLUTE
   BASE_DIR "${{CMAKE_CURRENT_SOURCE_DIR}}")
  file(RELATIVE_PATH relative "${{base}}" "${{absolute}}")
  get_source_file_property(alias "${{absolute}}" QT_RESOURCE_ALIAS)
  if(alias)
   set(relative "${{alias}}")
  endif()
  file(SHA256 "${{absolute}}" digest)
  set(row "${{target}}\\t${{resource}}\\t${{ARG_PREFIX}}/${{relative}}")
  file(APPEND "{receipt.as_posix()}" "${{row}}\\t${{digest}}\\n")
 endforeach()
endfunction()
function(qt_add_qml_module target)
 # Qt6QmlMacros forwards RESOURCES to qt_add_resources at its URI resource prefix.
 # edi uses QTP0001 NEW via qt_standard_project_setup(REQUIRES 6.8).
 cmake_parse_arguments(QML "NO_RESOURCE_TARGET_PATH"
  "URI;VERSION;RESOURCE_PREFIX;TARGET_PATH"
  "RESOURCES;QML_FILES;SOURCES;DEPENDENCIES;IMPORTS;OPTIONAL_IMPORTS" ${{ARGN}})
 if(NOT QML_RESOURCE_PREFIX)
  set(QML_RESOURCE_PREFIX "/qt/qml")
 endif()
 if(NOT QML_NO_RESOURCE_TARGET_PATH)
  if(NOT QML_TARGET_PATH)
   string(REPLACE "." "/" QML_TARGET_PATH "${{QML_URI}}")
  endif()
  string(REGEX REPLACE "/$" "" QML_RESOURCE_PREFIX "${{QML_RESOURCE_PREFIX}}")
  string(APPEND QML_RESOURCE_PREFIX "/${{QML_TARGET_PATH}}")
 endif()
 qt_add_resources(${{target}} "qml_resources"
  PREFIX "${{QML_RESOURCE_PREFIX}}" BASE "${{CMAKE_CURRENT_SOURCE_DIR}}"
  FILES ${{QML_RESOURCES}})
endfunction()
{body}
set(queue edi_app)
set(reachable)
while(queue)
 list(POP_FRONT queue target)
 if(target IN_LIST reachable)
  continue()
 endif()
 list(APPEND reachable "${{target}}")
 get_property(edges GLOBAL PROPERTY "probe_own_${{target}}")
 # A linked library's usage requirements reach its consumer. The executable's
 # INTERFACE is for a consumer of that executable, not its own deployment.
 if(NOT target STREQUAL "edi_app")
  get_property(exported GLOBAL PROPERTY "probe_interface_${{target}}")
  list(APPEND edges ${{exported}})
 endif()
 list(APPEND queue ${{edges}})
endwhile()
list(JOIN reachable "\\n" target_text)
file(WRITE "{(scratch / 'targets.txt').as_posix()}" "${{target_text}}\\n")
"""
    (scratch / 'CMakeLists.txt').write_text(harness)
    result = subprocess.run(
        ['cmake', '-S', str(scratch), '-B', str(scratch / 'build')],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, (
        'Examples: production resource configuration must execute: '
        + result.stdout
        + result.stderr
    )
    reachable = set((scratch / 'targets.txt').read_text().splitlines())
    effective = [
        line for line in receipt.read_text().splitlines() if line.split('\t')[0] in reachable
    ]
    return effective, (scratch / 'build/examples/index.txt').read_text().splitlines()


def bundled_inputs(files, project_id):
    records = [line.split('\t') for line in files]
    paths = [
        address
        for _target, _resource, address, _digest in records
        if address.startswith('/edi/examples/' + project_id + '/')
    ]
    assert len(paths) == len(set(paths)), (
        'Examples: each effective resource address has exactly one payload'
    )
    return {
        address: digest
        for target, _resource, address, digest in records
        if address.startswith('/edi/examples/' + project_id + '/')
    }


def assert_bundled_index(files, index):
    digest = hashlib.sha256(('\n'.join(index) + '\n').encode()).hexdigest()
    records = [line.split('\t') for line in files]
    actual = [
        payload
        for _target, _resource, address, payload in records
        if address == '/edi/examples/index.txt'
    ]
    assert actual == [digest], (
        'Examples: the advertised index has one payload at the address the loader opens'
    )


def assert_web_exclusion(files, index):
    full = 'pd-neut-cwl_cosio-d20_scan-324f'
    corpus = json.loads((ROOT / 'tests/fixtures/c11_t62/scan-inputs.json').read_text())['files']
    full_hashes = {
        digest for name, digest in corpus.items() if name.startswith('experiments/d20_scan/')
    }
    assert full not in index and not any(full in line.split('\t')[2] for line in files), (
        'Examples: the full scan has no resource address on web under any label or target'
    )
    # Selected cooling shares old full-run bytes; every other deployment address is excluded.
    approved = expected_bundle(155)
    assert not any(
        line.split('\t')[3] in full_hashes
        and approved.get(line.split('\t')[2]) != line.split('\t')[3]
        for line in files
    ), 'Examples: full-scan data cannot be rebundled under another label, path or target on web'


def expected_bundle(count):
    project_id = {155: 'pd-neut-cwl_cosio-d20_scan', 73: 'pd-xray-cwl_latp-bm01_scan'}.get(
        count, f'pd-neut-cwl_cosio-d20_scan-{count}f'
    )
    base = ROOT / 'docs/user/cli' / project_id / 'project'
    declaration = dict(
        shlex.split(line)
        for line in (base / 'analysis/analysis.edi').read_text().splitlines()
        if line.startswith('_sequential_fit.') and len(shlex.split(line)) == 2
    )
    if count in {155, 73}:
        inventory = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (base / declaration['_sequential_fit.data_dir']).glob(
                declaration['_sequential_fit.file_pattern']
            )
            if path.is_file()
        }
        assert len(inventory) == count, 'The selected scan retains every owner-declared dataset'
        if count == 155:
            legacy = example_inventory(162)
            assert inventory == dict(sorted(legacy.items())[:155]), (
                'The selected cooling scan retains the first 155 frozen nonmagnetic inputs'
            )
    else:
        inventory = example_inventory(count)
        assert_source_inventory(inventory, count)
    directory = declaration['_sequential_fit.data_dir']
    expected = {
        f'/edi/examples/{project_id}/project/{directory}/{name}': digest
        for name, digest in inventory.items()
    }
    metadata = sorted(base.rglob('*.edi'))
    assert (base / 'project.edi') in metadata and (base / 'analysis/analysis.edi') in metadata, (
        'Examples: each project supplies opening metadata'
    )
    assert any('/experiments/' in str(file) for file in metadata) and any(
        '/structures/' in str(file) for file in metadata
    ), 'Examples: each opening project carries its experiment and structure blocks'
    expected.update({
        f'/edi/examples/{project_id}/project/{file.relative_to(base).as_posix()}': hashlib.sha256(
            file.read_bytes()
        ).hexdigest()
        for file in metadata
    })
    return expected


@pytest.fixture(scope='module')
def downloaded_control(tmp_path_factory):
    root = tmp_path_factory.mktemp('downloaded-scan-control')
    selected = {'pd-neut-cwl_cosio-d20_scan', 'pd-xray-cwl_latp-bm01_scan'}
    metadata = json.loads((ROOT / 'app/examples/metadata.json').read_text())
    metadata['examples'] = {k: v for k, v in metadata['examples'].items() if k in selected}
    metadata_file = root / 'metadata.json'
    metadata_file.write_text(json.dumps(metadata))
    script = ROOT / 'tools/data/build_collection.py'
    spec = importlib.util.spec_from_file_location('scan_collection_producer', script)
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    producer.METADATA = metadata_file
    collection = root / 'collection'
    assert producer.populate(collection) == 0, (
        'The actual collection producer must publish the selected scan projects'
    )
    assert producer.index(collection) == 0, (
        'The actual collection index must advertise both selected scans'
    )
    return collection, metadata_file


def downloaded_inputs(collection, project_id):
    index = json.loads((collection / 'index.json').read_text())
    entries = [
        entry
        for entry in index['entries']
        if entry['id'] == project_id and entry['kind'] == 'project'
    ]
    assert len(entries) == 1, (
        'Downloaded examples: the selected project has one collection identity'
    )
    file = entries[0]['files'][0]
    payload = (collection / file['path']).read_bytes()
    assert (
        hashlib.sha256(payload).hexdigest() == file['sha256'] and len(payload) == file['bytes']
    ), 'Downloaded examples: the index claims must identify the actual archive bytes'
    with zipfile.ZipFile(collection / file['path']) as archive:
        names = [entry.filename for entry in archive.infolist() if not entry.is_dir()]
        assert len(names) == len(set(names)), (
            'Downloaded examples: each archive member has one payload'
        )
        assert names and all(name.startswith(project_id + '/') for name in names), (
            'Downloaded examples: every member retains the selected project root'
        )
        return {
            '/edi/examples/'
            + project_id
            + '/project/'
            + name[len(project_id) + 1 :]: hashlib.sha256(archive.read(name)).hexdigest()
            for name in names
        }


def assert_downloaded_scan(collection, count):
    project_id = {155: 'pd-neut-cwl_cosio-d20_scan', 73: 'pd-xray-cwl_latp-bm01_scan'}[count]
    assert downloaded_inputs(collection, project_id) == expected_bundle(count), (
        'Downloaded examples: the archive retains every selected dataset, filename, '
        'checksum and opening metadata block'
    )


def rewrite_download(collection, project_id, transform):
    index_file = collection / 'index.json'
    value = json.loads(index_file.read_text())
    entry = next(entry for entry in value['entries'] if entry['id'] == project_id)
    path = collection / entry['files'][0]['path']
    with zipfile.ZipFile(path) as archive:
        members = {
            name: archive.read(name) for name in archive.namelist() if not name.endswith('/')
        }
    members = transform(members)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, payload)
    payload = path.read_bytes()
    entry['files'][0]['sha256'] = hashlib.sha256(payload).hexdigest()
    entry['files'][0]['bytes'] = len(payload)
    index_file.write_text(json.dumps(value))


@pytest.mark.parametrize('web', [False, True], ids=['desktop', 'web'])
def test_effective_bundle_contains_selected_scan_payloads(tmp_path, web, downloaded_control):
    files, index = resource_inventory(tmp_path, web)
    assert_bundled_index(files, index)
    assert index == app_cases(ROOT), (
        'The deployed index retains catalogue order plus exactly '
        'the declared app-only cases on each platform'
    )
    for case, count in [('pd-neut-cwl_cosio-d20_scan', 155), ('pd-xray-cwl_latp-bm01_scan', 73)]:
        assert case in index, 'Each selected scan remains discoverable in the deployed catalogue'
        assert bundled_inputs(files, case) == {}, (
            'Example datasets are downloaded rather than embedded on either platform'
        )
        assert_downloaded_scan(downloaded_control[0], count)
    assert_web_exclusion(files, index)


def test_resource_observer_rejects_comment_only_and_inactive_bundle_calls(
    tmp_path, downloaded_control
):
    collection, metadata = downloaded_control
    assert_downloaded_scan(collection, 155)
    script = (ROOT / 'tools/data/build_collection.py').read_text()
    function = next(
        node
        for node in ast.parse(script).body
        if isinstance(node, ast.FunctionDef) and node.name == 'populate'
    )
    lines = script.splitlines(keepends=True)
    declaration = lines[function.lineno - 1]
    body = ''.join(lines[function.lineno : function.end_lineno])
    for label, replacement in [
        ('comment', declaration + '    # No archive-producing call executes.\n    return 0\n'),
        (
            'inactive',
            declaration
            + '    if False:\n'
            + ''.join('    ' + line for line in body.splitlines(keepends=True))
            + '    return 0\n',
        ),
    ]:
        root = tmp_path / label
        root.mkdir()
        changed = (
            ''.join(lines[: function.lineno - 1])
            + replacement
            + ''.join(lines[function.end_lineno :])
        )
        assert changed != script, (
            'The archive publication escape must alter the actual producer body'
        )
        changed = changed.replace(
            'ROOT = Path(__file__).resolve().parents[2]', 'ROOT = Path(' + repr(str(ROOT)) + ')'
        )
        changed = changed.replace(
            "METADATA = ROOT / 'app/examples/metadata.json'",
            'METADATA = Path(' + repr(str(metadata)) + ')',
        )
        producer = root / 'producer.py'
        producer.write_text(changed)
        for action in ('populate', 'index'):
            result = subprocess.run(
                [sys.executable, str(producer), action, str(root)],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            assert result.returncode == 0, (
                'The inactive producer control must execute successfully '
                'without producing an archive'
            )
        with pytest.raises(AssertionError, match='collection identity'):
            assert_downloaded_scan(root, 155)


@pytest.fixture(scope='module')
def bundle_control(tmp_path_factory):
    cmake = (APP / 'CMakeLists.txt').read_text()
    good, index = resource_inventory(
        tmp_path_factory.mktemp('live-resource-control'), False, cmake
    )
    return cmake, good, index


@pytest.fixture(scope='module', autouse=True)
def delivery_inputs(downloaded_control, bundle_control):
    """Pay the shared producer and resource graph cost together on the first case."""
    return downloaded_control, bundle_control


@pytest.mark.parametrize('dimension', ['prefix', 'target', 'metadata', 'alias', 'index', 'hidden'])
def test_resource_observer_rejects_wrong_prefix_target_metadata_index_and_hidden_web_payload(
    tmp_path, dimension, bundle_control, downloaded_control
):
    cmake, good, index = bundle_control
    assert_bundled_index(good, index)
    original = downloaded_control[0]
    assert_downloaded_scan(original, 155)
    full = 'pd-neut-cwl_cosio-d20_scan'
    if dimension == 'hidden':
        name = next(name for name in example_inventory(324) if name.startswith('02_'))
        injection = (
            '\nqt_add_resources(edi_app "other_label" PREFIX "/hidden" BASE ${_cli} '
            'FILES ${_cli}/pd-neut-cwl_cosio-d20_scan-324f/project/experiments/d20_scan/'
            + name
            + ')\n'
        )
        hidden, index = resource_inventory(tmp_path / 'hidden', True, cmake + injection)
        with pytest.raises(AssertionError, match='web'):
            assert_web_exclusion(hidden, index)
        return
    changed = tmp_path / 'changed'
    shutil.copytree(original, changed)
    if dimension == 'prefix':
        rewrite_download(
            changed,
            full,
            lambda members: {
                name.replace(full + '/', 'wrong/', 1): payload for name, payload in members.items()
            },
        )
    elif dimension == 'metadata':
        rewrite_download(
            changed,
            full,
            lambda members: {
                name: payload for name, payload in members.items() if not name.endswith('.edi')
            },
        )
        actual = downloaded_inputs(changed, full)
        assert actual == {
            address: digest
            for address, digest in expected_bundle(155).items()
            if not address.endswith('.edi')
        }, 'The opening-metadata escape must preserve every selected scan dataset'
    elif dimension == 'alias':
        rewrite_download(
            changed,
            full,
            lambda members: {
                name.replace('/analysis/analysis.edi', '/analysis/wrong.edi'): payload
                for name, payload in members.items()
            },
        )
    else:
        index_path = changed / 'index.json'
        document = json.loads(index_path.read_text())
        if dimension == 'index':
            document['entries'] = [entry for entry in document['entries'] if entry['id'] != full]
        else:
            entry = next(entry for entry in document['entries'] if entry['id'] == full)
            other = next(
                entry
                for entry in document['entries']
                if entry['id'] == 'pd-xray-cwl_latp-bm01_scan'
            )
            entry['files'] = copy.deepcopy(other['files'])
        index_path.write_text(json.dumps(document))
    with pytest.raises(AssertionError):
        assert_downloaded_scan(changed, 155)


@pytest.mark.parametrize(
    'sources', ['resource.dat', 'resource.qrc', '"$<IF:$<BOOL:1>,resource.dat,source.cpp>"']
)
def test_resource_observer_refuses_non_compilation_target_sources(
    tmp_path, bundle_control, sources
):
    cmake, _, _ = bundle_control
    good, index = resource_inventory(tmp_path / 'positive', True, cmake)
    assert_web_exclusion(good, index)
    unsupported = cmake + '\ntarget_sources(edi_app PRIVATE ' + sources + ')\n'
    with pytest.raises(AssertionError, match='unobserved non-compilation target source'):
        resource_inventory(tmp_path / 'unsupported', True, unsupported)


def test_working_copy_observer_rejects_copy_to_an_unrelated_destination(monkeypatch):
    original = source
    current = original('src/session.cpp')
    mutations = [
        current.replace(
            'const QString destination = target + file.mid(source.size());',
            'const QString destination = source + file.mid(source.size());',
        ),
        re.sub(
            r'openProjectAt\(archive,\s*exampleId\)', 'openProjectAt(archive)', current, count=1
        ),
        re.sub(r'open\(source,\s*example,', 'open(source, {},', current, count=1),
    ]
    for changed in mutations:
        assert current != changed, (
            'Working-copy wiring: each escape alters the actual copy destination '
            'or example identity forwarding'
        )
        monkeypatch.setattr(
            __import__(__name__, fromlist=['source']),
            'source',
            lambda path, changed=changed: changed if path == 'src/session.cpp' else original(path),
        )
        with pytest.raises(AssertionError):
            test_bundled_project_load_and_save_as_use_the_writable_copy_routes()


def test_resource_observer_accepts_a_separately_linked_example_library(
    tmp_path, downloaded_control
):
    live = (APP / 'CMakeLists.txt').read_text()
    cmake = live.replace('qt_add_resources(edi_app_module', 'qt_add_resources(example_layer')
    assert cmake != live, 'Examples: the control relocates the live resources to another target'
    cmake += '\nqt_add_library(example_layer STATIC)\n'
    cmake += '\ntarget_link_libraries(edi_app_module PRIVATE example_layer)\n'
    files, index = resource_inventory(tmp_path, False, cmake)
    assert_bundled_index(files, index)
    assert bundled_inputs(files, 'pd-neut-cwl_cosio-d20_scan') == {}, (
        'Examples: a linked metadata library must not embed downloaded scan inputs'
    )
    assert_downloaded_scan(downloaded_control[0], 155)


@pytest.mark.parametrize('placement', ['default', 'prefix', 'alias'])
def test_resource_observer_rejects_excluded_payload_in_the_live_qml_module(tmp_path, placement):
    cmake = (APP / 'CMakeLists.txt').read_text()
    good, index = resource_inventory(tmp_path / 'good', True, cmake)
    assert_web_exclusion(good, index)
    logo = '/qt/qml/edi/app/resources/logo/App.svg'
    assert any(row.split('\t')[2] == logo for row in good), (
        'Examples: the existing QML module resource route records its deployed address'
    )
    full = 'pd-neut-cwl_cosio-d20_scan-324f'
    name = next(name for name in example_inventory(324) if name.startswith('02_'))
    payload = ROOT / 'docs/user/cli' / full / 'project/experiments/d20_scan' / name
    declaration = 'resources/logo/App.svg'
    changed = cmake.replace(declaration, declaration + '\n        "' + str(payload) + '"', 1)
    assert changed != cmake, 'Examples: the escape reaches the existing QML RESOURCES list'
    # Qt aliases preserve the resource identity even for a source outside the module tree.
    alias = 'forbidden-scan.bin'
    changed = (
        'set_source_files_properties("'
        + str(payload)
        + '" PROPERTIES QT_RESOURCE_ALIAS '
        + alias
        + ')\n'
        + changed
    )
    address = '/qt/qml/edi/app/' + alias
    if placement == 'prefix':
        changed = changed.replace('URI edi.app', 'URI edi.app\n    RESOURCE_PREFIX "/other"', 1)
        address = '/other/edi/app/' + alias
    elif placement == 'alias':
        changed = changed.replace(alias, 'renamed.dat')
        address = '/qt/qml/edi/app/renamed.dat'
    bad, index = resource_inventory(tmp_path / 'bad', True, changed)
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    assert any(row.split('\t')[2:] == [address, digest] for row in bad), (
        'Examples: the live QML route includes the injected bytes at their effective address'
    )
    with pytest.raises(AssertionError, match='web'):
        assert_web_exclusion(bad, index)


@pytest.mark.parametrize('link', ['PRIVATE', 'PUBLIC', 'INTERFACE', 'library-interface'])
def test_resource_observer_distinguishes_executable_and_library_interfaces(
    tmp_path, link, downloaded_control
):
    cmake = (APP / 'CMakeLists.txt').read_text()
    relocated = cmake.replace('qt_add_resources(edi_app_module', 'qt_add_resources(example_layer')
    assert relocated != cmake, 'Examples: the linkage control relocates the production resources'
    relocated += '\nqt_add_library(example_layer STATIC)\n'
    if link == 'library-interface':
        relocated += '\ntarget_link_libraries(edi_app_module INTERFACE example_layer)\n'
    else:
        relocated += '\ntarget_link_libraries(edi_app ' + link + ' example_layer)\n'
    files, index = resource_inventory(tmp_path, False, relocated)
    full = 'pd-neut-cwl_cosio-d20_scan'
    if link == 'INTERFACE':
        assert bundled_inputs(files, full) == {}, (
            'Examples: an executable INTERFACE edge does not deploy its resources'
        )
        with pytest.raises(AssertionError, match='advertised index'):
            assert_bundled_index(files, index)
    else:
        assert bundled_inputs(files, full) == {}, (
            'Metadata linkage must not rebundle downloaded scan payloads'
        )
        assert_bundled_index(files, index)
        assert_downloaded_scan(downloaded_control[0], 155)


def test_resource_observer_rejects_a_second_payload_at_the_index_address(tmp_path):
    cmake = (APP / 'CMakeLists.txt').read_text()
    good, index = resource_inventory(tmp_path / 'good', False, cmake)
    assert_bundled_index(good, index)
    cmake += """
set_source_files_properties(${_cli}/pd-neut-cwl_cosio-d20_scan/project/analysis/analysis.edi
 PROPERTIES QT_RESOURCE_ALIAS index.txt)
qt_add_resources(edi_app "index_collision" PREFIX "/edi/examples" BASE ${_cli}
 FILES ${_cli}/pd-neut-cwl_cosio-d20_scan/project/analysis/analysis.edi)
"""
    bad, index = resource_inventory(tmp_path / 'bad', False, cmake)
    payloads = [
        row.split('\t')[3] for row in bad if row.split('\t')[2] == '/edi/examples/index.txt'
    ]
    assert len(payloads) == 2 and len(set(payloads)) == 2, (
        'Examples: the live collision carries two different payloads at the opening index address'
    )
    with pytest.raises(AssertionError, match='advertised index'):
        assert_bundled_index(bad, index)
