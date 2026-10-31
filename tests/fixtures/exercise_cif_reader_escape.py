"""Replay the saved-model witness against an isolated native reader mutant.

Usage: python exercise_cif_reader_escape.py REPO SCRATCH control|mutant [REF]
Run in the product's default environment. Scratch builds use four compiler jobs.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def mutate_reader(repo, source, mode, ref):
    product = repo.name
    relative = 'src/core/model.cpp' if product == 'crysta' else 'core/src/io.cpp'
    original = subprocess.check_output(
        [shutil.which('git'), '-C', str(repo), 'show', ref + ':' + relative], text=True
    )
    changed = original
    if mode == 'mutant':
        old = (
            'experiment.facility = description_text(block.get("_instrument.facility"));'
            if product == 'crysta'
            else 'experiment.instrument.facility = *facility;'
        )
        replacement = (
            '(void)block.get("_instrument.facility");'
            if product == 'crysta'
            else '(void)*facility;'
        )
        if original.count(old) != 1:
            message = 'The mutation must reach exactly one native facility reader'
            raise ValueError(message)
        changed = original.replace(old, replacement)
    (source / relative).write_text(changed)
    if product == 'crysta':
        relative = 'src/core/cif_import.cpp'
        original = subprocess.check_output(
            [shutil.which('git'), '-C', str(repo), 'show', ref + ':' + relative], text=True
        )
        if mode == 'mutant':
            old = 'for (const ExperimentDeclaration& declaration : declared) {'
            if original.count(old) != 1:
                message = 'The premature settlement mutation must reach the real comparer'
                raise ValueError(message)
            original = original.replace(
                old, old + '\n        if (declaration.edi == "_instrument.facility") continue;'
            )
        (source / relative).write_text(original)


def main():
    repo = Path(sys.argv[1]).resolve()
    work = Path(sys.argv[2]).resolve()
    mode = sys.argv[3]
    ref = sys.argv[4] if len(sys.argv) > 4 else 'HEAD'
    if mode not in {'control', 'mutant'}:
        raise ValueError(mode)
    source = work / 'source'
    build = work / 'build'
    if not source.exists():
        source.mkdir(parents=True)
        subprocess.run(
            [shutil.which('git'), '-C', str(repo), 'archive', ref, '-o', str(work / 'source.tar')],
            check=True,
        )
        subprocess.run(
            [shutil.which('tar'), 'xf', str(work / 'source.tar'), '-C', str(source)], check=True
        )
        (work / 'source.tar').unlink()
    product = repo.name
    mutate_reader(repo, source, mode, ref)
    env = os.environ.copy()
    prefix = repo / '.pixi/envs/default'
    env['PATH'] = str(prefix / 'bin') + ':' + env['PATH']
    args = [
        shutil.which('cmake', path=env['PATH']),
        '-S',
        str(source),
        '-B',
        str(build),
        '-G',
        'Ninja',
        '-DCMAKE_BUILD_TYPE=Release',
        '-DCMAKE_POSITION_INDEPENDENT_CODE=ON',
        '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
        '-DPython_EXECUTABLE=' + str(prefix / 'bin/python'),
    ]
    if product == 'edi':
        args += ['-Dcrysta_DIR=' + str(repo / 'build/crysta-prefix/lib/cmake/crysta')]
    subprocess.run(args, env=env, check=True)
    subprocess.run(
        [
            shutil.which('cmake', path=env['PATH']),
            '--build',
            str(build),
            '--target',
            'crysta' if product == 'crysta' else '_edi',
            '-j',
            '4',
        ],
        env=env,
        check=True,
    )
    node = (
        'tests/integration/py/test_cif_import_contract.py::'
        'test_observer_rejects_lookup_only_and_partial_column_escapes'
    )
    options = ['-q', node, '--basetemp=' + str(work / 'pytest')]
    if product == 'edi':
        env['EDI_EXTENSION_DIR'] = str(build / 'python/edi')
        command = [str(prefix / 'bin/python'), '-m', 'pytest', *options]
    else:
        module = next(build.glob('_crysta*.so'))
        code = (
            'import importlib.util,sys; p=sys.argv.pop(1); '
            's=importlib.util.spec_from_file_location("_crysta",p); '
            'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
            'sys.modules["crysta"]=m; import pytest; sys.exit(pytest.main(sys.argv[1:]))'
        )
        command = [str(prefix / 'bin/python'), '-c', code, str(module), *options]
    return subprocess.run(command, cwd=repo, env=env, check=False).returncode


if __name__ == '__main__':
    sys.exit(main())
