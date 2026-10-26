"""Exercise damaged forms and coordinated edits through the real catalogue check."""

import errno
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from tests.integration.py.test_example_catalogue import APP_ONLY, SELECTED, page_cases, selected

ROOT = Path(__file__).resolve().parents[3]
CHECKER = 'tools/checks/example_catalogue.py'


def replace(path, text):
    temporary = path.with_name(path.name + '.replacement')
    temporary.write_text(text)
    temporary.replace(path)


def write_json(path, value):
    replace(path, json.dumps(value, indent=2) + '\n')


def copy_fixture(source, destination):
    try:
        os.link(source, destination)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        shutil.copyfile(source, destination)


def clone(tmp_path):
    assert (ROOT / CHECKER).is_file(), 'The catalogue needs its executable consistency check'
    for name in ['docs/user/cli', 'docs/user/tutorials', 'app/examples', 'tools']:
        shutil.copytree(ROOT / name, tmp_path / name, copy_function=copy_fixture)
    for name in ['app/CMakeLists.txt', 'mkdocs.yml', 'pixi.toml']:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return tmp_path


def check(root):
    return subprocess.run(
        [sys.executable, str(root / CHECKER), '--check'],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


@pytest.mark.parametrize(
    'damage',
    [
        'missing-source',
        'missing-notebook',
        'wrong-load',
        'notebook-disagrees',
        'double-load',
        'wrong-project-name',
        'missing-page',
        'missing-provenance',
        'unknown-tutorial',
        'missing-exclusion',
        'unknown-exclusion',
        'yaml-capital-boolean',
        'yaml-extra-indent',
        'unlisted-dataset',
    ],
)
def test_check_refuses_each_broken_catalogue_form(tmp_path, damage):  # noqa: PLR0912, PLR0914 - damage matrix
    root = clone(tmp_path)
    baseline = check(root)
    assert baseline.returncode == 0, 'The intact catalogue must pass before each damage control'
    case = SELECTED[1]
    tutorial = root / f'docs/user/tutorials/{case}.py'
    notebook = tutorial.with_suffix('.ipynb')
    case_dir = root / 'docs/user/cli' / case
    registry = root / 'docs/user/cli/projects.yml'
    exclusions = root / 'docs/user/tutorials/execution-exclusions.yml'
    if damage == 'missing-source':
        tutorial.unlink()
    elif damage == 'missing-notebook':
        notebook.unlink()
    elif damage == 'wrong-load':
        replace(
            tutorial,
            tutorial.read_text().replace(
                f'../cli/{case}/project', f'../cli/{SELECTED[0]}/project'
            ),
        )
    elif damage == 'notebook-disagrees':
        replace(
            notebook,
            notebook.read_text().replace(
                f'../cli/{case}/project', f'../cli/{SELECTED[0]}/project'
            ),
        )
    elif damage == 'double-load':
        replace(
            tutorial,
            tutorial.read_text() + f"\nedi.Project.load('../cli/{SELECTED[0]}/project')\n",
        )
    elif damage == 'wrong-project-name':
        path = case_dir / 'project/project.edi'
        replace(path, path.read_text().replace(case, 'pd-neut-tof_unknown'))
    elif damage == 'missing-page':
        (case_dir / 'index.md').unlink()
    elif damage == 'missing-provenance':
        (case_dir / 'PROVENANCE.md').unlink()
    elif damage == 'unknown-tutorial':
        shutil.copyfile(tutorial, tutorial.with_name('pd-neut-tof_unknown.py'))
    elif damage in {'missing-exclusion', 'unknown-exclusion'}:
        record = yaml.safe_load(exclusions.read_text())
        if damage == 'missing-exclusion':
            record['excluded'] = [
                row for row in record['excluded'] if row['notebook'] != f'{case}.ipynb'
            ]
        else:
            record['excluded'].append({
                'notebook': 'pd-neut-tof_unknown.ipynb',
                'unblocked_by': 'tutorial-runner',
            })
        replace(exclusions, yaml.safe_dump(record, sort_keys=False))
    elif damage == 'yaml-capital-boolean':
        replace(
            registry, registry.read_text().replace('user-facing: true', 'user-facing: True', 1)
        )
    elif damage == 'yaml-extra-indent':
        text = registry.read_text()
        start = text.index(f'  - id: {case}\n')
        end = text.find('\n  - id:', start + 1)
        block = text[start:end].replace('\n    ', '\n     ')
        replace(registry, text[:start] + block + text[end:])
    else:
        data = case_dir / 'data'
        data.mkdir(exist_ok=True)
        (data / 'unlisted.dat').write_text('1 2 3\n')
    result = check(root)
    assert result.returncode != 0, 'Every damaged form must be refused by the executable check'
    assert 'Traceback' not in result.stderr, 'Invalid catalogue input must produce a diagnostic'


def read_selection(root):
    return {
        'registry': selected(root),
        'metadata': list(
            json.loads((root / 'app/examples/metadata.json').read_text())['examples']
        ),
        'cli': page_cases(root / 'docs/user/cli/index.md'),
        'tutorials': page_cases(root / 'docs/user/tutorials/index.md'),
    }


@pytest.mark.parametrize('change', ['deletion', 'substitution', 'permutation'])
def test_owner_selection_rejects_coordinated_consumer_changes(tmp_path, change):  # noqa: PLR0914 - coupled control
    root = clone(tmp_path)
    assert check(root).returncode == 0, 'Coordinated controls require an intact catalogue'
    original = SELECTED[1]
    replacement = 'pd-neut-cwl_lab6-11b-echidna_basic'
    registry = root / 'docs/user/cli/projects.yml'
    record = yaml.safe_load(registry.read_text())
    expected = list(SELECTED)
    if change == 'deletion':
        expected.remove(original)
    elif change == 'substitution':
        expected[1] = replacement
    else:
        expected[1], expected[2] = expected[2], expected[1]
    by_id = {row['id']: row for row in record['projects']}
    for row in record['projects']:
        row.pop('user-facing', None)
    fixtures = [row for row in record['projects'] if row['id'] not in expected]
    record['projects'] = fixtures + [{**by_id[case], 'user-facing': True} for case in expected]
    text = 'schema: 1\nprojects:\n'
    for row in record['projects']:
        text += f'  - id: {row["id"]}\n'
        text += ''.join(
            f'    {key}: {str(value).lower()}\n' for key, value in row.items() if key != 'id'
        )
    replace(registry, text)
    metadata = root / 'app/examples/metadata.json'
    data = json.loads(metadata.read_text())
    data['examples'] = {
        case: data['examples'].get(case, data['examples'][original]) for case in expected
    }
    write_json(metadata, data)
    for page in ['docs/user/cli/index.md', 'docs/user/tutorials/index.md']:
        path = root / page
        replace(
            path,
            '# Examples\n\n'
            + '\n'.join(f'- [{case}]({case}/index.md)' for case in expected)
            + '\n',
        )
    tutorials = root / 'docs/user/tutorials'
    if change != 'permutation':
        source_page = root / f'docs/user/cli/{original}/index.md'
        if change == 'substitution':
            for suffix in ['.py', '.ipynb']:
                source = tutorials / f'{original}{suffix}'
                target = tutorials / f'{replacement}{suffix}'
                replace(target, source.read_text().replace(original, replacement))
            target = root / f'docs/user/cli/{replacement}/index.md'
            replace(target, source_page.read_text().replace(original, replacement))
        source_page.rename(source_page.with_name('README.md'))
        for suffix in ['.py', '.ipynb']:
            (tutorials / f'{original}{suffix}').unlink()
    exclusions = tutorials / 'execution-exclusions.yml'
    excluded = {
        'excluded': [
            {
                'notebook': f'{case}.ipynb',
                'unblocked_by': 'sequential-scan-tutorial'
                if case.endswith('_scan')
                else 'tutorial-runner',
            }
            for case in expected
        ]
    }
    replace(exclusions, yaml.safe_dump(excluded, sort_keys=False))
    generated = subprocess.run(
        [sys.executable, str(root / 'tools/dev/example_metadata.py')],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert generated.returncode == 0, 'The mutation must regenerate the real app metadata'
    views = read_selection(root)
    assert all(
        view == expected + (APP_ONLY if name == 'metadata' else []) for name, view in views.items()
    ), 'The coordinated control reaches each catalogue reader and retains the app-only tail'
    assert all(
        view != SELECTED + (APP_ONLY if name == 'metadata' else []) for name, view in views.items()
    ), 'Agreement between consumers must not hide deletion, substitution or reordering'


def test_actual_cmake_configuration_emits_the_owner_selected_index(tmp_path):
    source = (ROOT / 'app/CMakeLists.txt').read_text()
    block = source[source.index('set(_cli ${PROJECT_SOURCE_DIR}/docs/user/cli)') :]
    end = (
        'file(CONFIGURE OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/examples/index.txt '
        'CONTENT "${_index}\\n")'
    )
    assert end in block, 'The app must materialize the example index during CMake configuration'
    block = block[: block.index(end) + len(end)]
    (tmp_path / 'app').mkdir()
    (tmp_path / 'app/examples').symlink_to(ROOT / 'app/examples', target_is_directory=True)
    (tmp_path / 'docs').symlink_to(ROOT / 'docs', target_is_directory=True)
    (tmp_path / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.22)\nproject(Catalogue NONE)\n'
        'function(qt_add_resources)\nendfunction()\nadd_subdirectory(app)\n'
    )
    (tmp_path / 'app/CMakeLists.txt').write_text(block)
    result = subprocess.run(
        ['cmake', '-S', str(tmp_path), '-B', str(tmp_path / 'build')],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, 'The actual example bundle configuration must succeed'
    assert (
        tmp_path / 'build/app/examples/index.txt'
    ).read_text().splitlines() == SELECTED + APP_ONLY, (
        'The built app index preserves the catalogue order followed by the declared app-only ids'
    )


@pytest.mark.parametrize(
    'damage',
    [
        'comment',
        'string',
        'dead-branch',
        'uninvoked-function',
        'uninvoked-lambda',
        'extra-nonliteral',
        'comparison',
        'slice-call',
        'slice-literal',
        'comprehension-call',
        'assignment-target',
        'annotated',
        'expression',
        'chained-target',
        'other-target',
        'bare-project',
    ],
)
def test_check_requires_an_executable_load_in_both_tutorial_forms(tmp_path, damage):
    root = clone(tmp_path)
    assert check(root).returncode == 0, 'The actual catalogue must pass before inert-load damage'
    case = SELECTED[1]
    tutorial = root / f'docs/user/tutorials/{case}.py'
    notebook = tutorial.with_suffix('.ipynb')
    line = next(
        line for line in tutorial.read_text().splitlines() if 'project = edi.Project.load(' in line
    )
    variants = {
        'comment': '# ' + line,
        'string': repr(line),
        'dead-branch': 'if False:\n    ' + line,
        'uninvoked-function': 'def never_called():\n    ' + line,
        'uninvoked-lambda': 'loader = lambda: ' + line.split(' = ', 1)[1],
        'extra-nonliteral': line + '\nother = edi.Project.load(project_path)',
    }
    load = line.split(' = ', 1)[1]
    wrong = f"edi.Project.load('../cli/{SELECTED[0]}/project')"
    variants.update({
        'comparison': 'project = 1 > 2 > ' + load,
        'slice-call': line + '\nextra = [0][(edi.Project.load(other_path), 0)[1]:]',
        'slice-literal': line + f'\nextra = [0][({wrong}, 0)[1]:]',
        'comprehension-call': line + '\nextra = [x for x in edi.Project.load(other_path)]',
        'assignment-target': line + '\nextra[edi.Project.load(other_path)] = 0',
        'annotated': 'project: object = ' + load,
        'expression': load,
        'chained-target': 'project = other = ' + load,
        'other-target': 'other = ' + load,
        'bare-project': line.replace('edi.Project.load', 'Project.load'),
    })
    replacement = variants[damage]
    replace(tutorial, tutorial.read_text().replace(line, replacement))
    document = json.loads(notebook.read_text())
    changed = False
    for cell in document['cells']:
        if cell['cell_type'] != 'code':
            continue
        code = ''.join(cell['source'])
        if line in code:
            cell['source'] = code.replace(line, replacement).splitlines(keepends=True)
            changed = True
    assert changed, 'The escape must remove the same executable load in both representations'
    write_json(notebook, document)
    result = check(root)
    assert result.returncode != 0, (
        'Tutorials require the fixed project assignment and refuse every other Project.load call'
    )
    assert 'Traceback' not in result.stderr, 'Inert tutorial forms require a normal diagnostic'
