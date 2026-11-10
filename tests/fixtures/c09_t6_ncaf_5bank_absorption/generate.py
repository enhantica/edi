"""Freeze  inputs, the crysta CLI oracle, and real-writer snapshots.

Run the default mode from the pre-task edi commit recorded below to regenerate the
source project, normative CLI JSON, key-absent derivative, and old-writer output.
Run ``--desired-writer-only`` from the implemented task branch to re-freeze the
reviewed post-task snapshots with edi's real writer.
Run ``--crysta-oracle-only`` after an intentional crysta-main advance to regenerate only
the crysta-produced regression oracle from edi's recorded build and update its
manifest provenance, without rewriting the pre-task edi writer snapshots.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from argparse import ArgumentParser
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path(__file__).resolve().parent
CRYSTA_ROOT = ROOT.parent / 'crysta'
SOURCE_RELATIVE = Path('tests/fitting/ncaf-5bank-absorption-perturbed-tof/project')
SOURCE_PROJECT = CRYSTA_ROOT / SOURCE_RELATIVE
FIT_READY_SOURCE = CRYSTA_ROOT / 'tests/fitting/ncaf-wish-3bank-s5/project'
#  (Q3): the fixture's committed project/ copy was DEDUPLICATED — the
# authoritative home is crysta tests/fitting/ncaf-5bank-absorption-perturbed-tof/
# (byte-identical, verified); regeneration materializes a TRANSIENT working copy
# here and the staying tests resolve the corpus case through the pin/override.
PROJECT = FIXTURE / 'project'
KEY_ABSENT = FIXTURE / 'key_absent_project'
PRE_TASK_WRITER = FIXTURE / 'expected/pre_task_writer'
DESIRED_WRITER = FIXTURE / 'expected/desired_writer'
TYPE_NONE_PROJECT = FIXTURE / 'type_none_project'
ORACLE = FIXTURE / 'crysta_cli_joint_fit.json'
RECORDED_CRYSTA_SHA = (
    (ROOT / 'build/crysta-src/CRYSTA_SOURCE_SHA').read_text(encoding='utf-8').strip()
)
EDI_BASE = '66ab62948e2c012d1c3ca81aaaf0385887017229'
CLI_OUTPUT = Path('/tmp/edi--crysta-cli.json')
INSTALLED_SHA_STAMP = ROOT / 'build/crysta-prefix/.crysta-sha'
RECORDED_CRYSTA_BINARY = ROOT / 'build/crysta-build/crysta'


def run(*command: str, cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_identities() -> Path:
    crysta_head = run('git', 'rev-parse', 'HEAD', cwd=CRYSTA_ROOT)
    if crysta_head != RECORDED_CRYSTA_SHA:
        raise RuntimeError(
            f'crysta identity mismatch: expected {RECORDED_CRYSTA_SHA}, found {crysta_head}'
        )
    pins = json.loads(
        (ROOT / 'tests/fixtures/e04_t12_public_release/history/manifest.json').read_text()
    )['absorption_closure']
    actual = {
        p.relative_to(ROOT).as_posix(): sha256(p)
        for prefix in ('core', 'lib')
        for p in (ROOT / prefix).rglob('*')
        if p.is_file() and '__pycache__' not in p.parts
    }
    if actual != pins:
        raise RuntimeError(
            'the absorption authoring writer must equal the retained historical source closure'
        )
    candidates = (
        CRYSTA_ROOT / 'build/quality/crysta',
        CRYSTA_ROOT / 'build/cp314-abi3-linux_x86_64/crysta',
    )
    binary = next((candidate for candidate in candidates if candidate.is_file()), None)
    if binary is None:
        raise RuntimeError('build the pinned crysta CLI before regenerating ')
    return binary


def verify_recorded_crysta_binary() -> Path:
    if INSTALLED_SHA_STAMP.read_text(encoding='utf-8').strip() != RECORDED_CRYSTA_SHA:
        raise RuntimeError(
            f'{INSTALLED_SHA_STAMP} does not prove recorded crysta {RECORDED_CRYSTA_SHA}'
        )
    if not RECORDED_CRYSTA_BINARY.is_file():
        raise RuntimeError(
            f'build the recorded crysta CLI before regenerating: {RECORDED_CRYSTA_BINARY}'
        )
    return RECORDED_CRYSTA_BINARY


def copy_source_project() -> None:
    if PROJECT.exists():
        shutil.rmtree(PROJECT)
    for source in sorted(SOURCE_PROJECT.rglob('*')):
        if not source.is_file() or source.name == 'README.md':
            continue
        destination = PROJECT / source.relative_to(SOURCE_PROJECT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def freeze_cli_oracle(binary: Path) -> list[str]:
    command = [
        'crysta',
        'fit',
        SOURCE_RELATIVE.as_posix(),
        '--rung',
        'lm',
        '--out',
        CLI_OUTPUT.as_posix(),
    ]
    if CLI_OUTPUT.exists():
        CLI_OUTPUT.unlink()
    with tempfile.TemporaryDirectory(prefix='edi--cli-') as temporary:
        executable = Path(temporary) / 'crysta'
        executable.symlink_to(binary)
        environment = os.environ.copy()
        environment['PATH'] = os.pathsep.join((temporary, environment.get('PATH', '')))
        subprocess.run(command, cwd=CRYSTA_ROOT, env=environment, check=True)
    shutil.copyfile(CLI_OUTPUT, ORACLE)
    CLI_OUTPUT.unlink()
    return command


def derive_key_absent_project() -> None:
    source = TYPE_NONE_PROJECT
    if KEY_ABSENT.exists():
        shutil.rmtree(KEY_ABSENT)
    for path in sorted(source.rglob('*')):
        if not path.is_file():
            continue
        destination = KEY_ABSENT / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = path.read_text(encoding='utf-8')
        lines = [line for line in text.splitlines() if not line.startswith('_absorption.')]
        destination.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    absorption_lines = [
        line
        for path in KEY_ABSENT.rglob('*.edi')
        for line in path.read_text(encoding='utf-8').splitlines()
        if line.startswith('_absorption.')
    ]
    if absorption_lines:
        raise RuntimeError(f'key-absent derivative still has absorption keys: {absorption_lines}')


def declare_fit_ready(project: Path, *, source_experiment: str | None = None) -> None:
    """Give a writer/round-trip fixture the measured-data category it actually exercises."""
    for experiment in sorted((project / 'experiments').glob('*.edi')):
        text = experiment.read_text(encoding='utf-8')
        if source_experiment is None and ('\n_data.' in text or '\n_data_range.' in text):
            continue
        source = FIT_READY_SOURCE / 'experiments' / (source_experiment or experiment.name)
        if not source.is_file():
            raise RuntimeError(f'no fit-ready source data for {experiment.name}: {source}')
        source_lines = source.read_text(encoding='utf-8').splitlines()
        data_tag = source_lines.index('_data.time_of_flight')
        data_loop = max(
            index for index, line in enumerate(source_lines[:data_tag]) if line == 'loop_'
        )
        destination_lines = text.splitlines()
        existing_data = next(
            (index for index, line in enumerate(destination_lines) if line.startswith('_data.')),
            None,
        )
        if existing_data is not None:
            existing_loop = max(
                index
                for index, line in enumerate(destination_lines[:existing_data])
                if line == 'loop_'
            )
            destination_lines = destination_lines[:existing_loop]
        experiment.write_text(
            '\n'.join(destination_lines).rstrip()
            + '\n\n'
            + '\n'.join(source_lines[data_loop:])
            + '\n',
            encoding='utf-8',
        )


def freeze_one_loader_writer() -> None:
    """Realign the three writer pins to the one-loader fit-ready contract."""
    declare_fit_ready(TYPE_NONE_PROJECT, source_experiment='wish_2_9.edi')
    derive_key_absent_project()
    projects = {
        'type_none': TYPE_NONE_PROJECT,
        'key_absent': KEY_ABSENT,
    }
    for name, source in projects.items():
        destination = DESIRED_WRITER / name
        if destination.exists():
            shutil.rmtree(destination)
        edi.Project.load(source).save_as(destination)

    with tempfile.TemporaryDirectory(prefix='edi--one-loader-') as temporary:
        source = Path(temporary) / 'no-code-type-none'
        shutil.copytree(PRE_TASK_WRITER / 'type_none', source)
        declare_fit_ready(source)
        destination = DESIRED_WRITER / 'no_code_type_none'
        if destination.exists():
            shutil.rmtree(destination)
        edi.Project.load(source).save_as(destination)

    manifest = json.loads((FIXTURE / 'manifest.json').read_text(encoding='utf-8'))
    manifest['desired_writer']['one_loader'] = (
        'writer/round-trip fixtures declare fit-ready measured data from ncaf-wish-3bank-s5'
    )
    manifest['files'] = {str(path.relative_to(FIXTURE)): sha256(path) for path in frozen_files()}
    (FIXTURE / 'manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )


def freeze_pre_task_writer() -> None:
    projects = {
        'type_none': TYPE_NONE_PROJECT,
        'e02_t2_ncaf_5bank': ROOT / 'tests/fixtures/e02_t2_ncaf_5bank/project',
        'key_absent': KEY_ABSENT,
    }
    if PRE_TASK_WRITER.exists():
        shutil.rmtree(PRE_TASK_WRITER)
    for name, source in projects.items():
        edi.Project.load(source).save_as(PRE_TASK_WRITER / name)


def freeze_desired_writer() -> None:
    """Pin reviewed canonical output by running the implemented writer.

     deliberately retires schema 1, so the historical pre-task byte snapshots no longer
    describe an accepted writer. Keep their provenance intact and regenerate the three live
    schema-3 successor pins here: absent absorption, explicit ``none``, and the no-code fixed
    point. The five-bank JvD subject was retired by , so its historical snapshot is retained
    unchanged rather than silently re-anchored to a different corpus case.
    These are implementation-produced regression pins, never correctness oracles.
    """
    projects = {
        'type_none': TYPE_NONE_PROJECT,
        'key_absent': KEY_ABSENT,
    }
    for name, source in projects.items():
        destination = DESIRED_WRITER / name
        if destination.exists():
            shutil.rmtree(destination)
        edi.Project.load(source).save_as(destination)

    # 's no-code fixed point starts from a historical model-only snapshot. The one-loader
    # contract requires a measured-data category, so stage that declared input transiently before
    # canonicalising the rest of the schema-3 experiment tree.
    with tempfile.TemporaryDirectory(prefix='edi--no-code-') as temporary:
        source = Path(temporary) / 'no-code-type-none'
        shutil.copytree(PRE_TASK_WRITER / 'type_none', source)
        declare_fit_ready(source)
        destination = DESIRED_WRITER / 'no_code_type_none'
        if destination.exists():
            shutil.rmtree(destination)
        edi.Project.load(source).save_as(destination)


def frozen_files() -> list[Path]:
    roots = (PROJECT, KEY_ABSENT, FIXTURE / 'expected')
    files = [path for root in roots for path in root.rglob('*') if path.is_file()]
    return sorted(files) + [ORACLE]


def write_manifest(binary: Path, command: list[str]) -> None:
    oracle = json.loads(ORACLE.read_text(encoding='utf-8'))
    if len(oracle['parameters']) != 193:
        raise RuntimeError(f'expected 193 CLI parameters, found {len(oracle["parameters"])}')
    manifest = {
        'schema': 1,
        'crysta_cli_oracle': {
            'source_sha': RECORDED_CRYSTA_SHA,
            'binary': str(binary.relative_to(CRYSTA_ROOT)),
            'command': command,
            'cwd': 'crysta checkout root',
            'input': SOURCE_RELATIVE.as_posix(),
            'input_files': {
                str(path.relative_to(SOURCE_PROJECT)): sha256(path)
                for path in sorted(SOURCE_PROJECT.rglob('*.edi'))
            },
            'output': ORACLE.name,
            'output_sha256': sha256(ORACLE),
            'representation': 'published write_joint_results JSON, %.10g',
        },
        'edi_pre_task_writer': {
            'commit': EDI_BASE,
            'role': 'regression pin for canonical writer behaviour, not source-byte parity',
        },
        'key_absent_derivative': {
            'source': 'tests/fixtures/c09_t6_ncaf_5bank_absorption/type_none_project',
            'transform': 'remove every line beginning _absorption.',
        },
        'desired_writer': {
            'role': 'reviewed intended output pins, not independent correctness oracles',
            'type_none': 'preserve the explicit selector separately from key-absent invariance',
            'key_absent': 'preserve absence separately from the explicit none selector',
            'jvd_absorption': (
                'old-writer canonical bytes plus the accepted five JvD and three absorption fields'
            ),
        },
        'files': {str(path.relative_to(FIXTURE)): sha256(path) for path in frozen_files()},
    }
    (FIXTURE / 'manifest.json').write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )


def refresh_crysta_oracle_only() -> None:
    binary = verify_recorded_crysta_binary()
    command = freeze_cli_oracle(binary)
    oracle = json.loads(ORACLE.read_text(encoding='utf-8'))
    if len(oracle['parameters']) != 193:
        raise RuntimeError(f'expected 193 CLI parameters, found {len(oracle["parameters"])}')
    manifest_path = FIXTURE / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['crysta_cli_oracle'].update({
        'source_sha': RECORDED_CRYSTA_SHA,
        'binary': str(RECORDED_CRYSTA_BINARY.relative_to(ROOT)),
        'command': command,
        'input': SOURCE_RELATIVE.as_posix(),
        'input_files': {
            str(path.relative_to(SOURCE_PROJECT)): sha256(path)
            for path in sorted(SOURCE_PROJECT.rglob('*.edi'))
        },
        'output_sha256': sha256(ORACLE),
    })
    manifest['files'][ORACLE.name] = sha256(ORACLE)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8'
    )


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument(
        '--desired-writer-only',
        action='store_true',
        help='re-freeze post-task snapshots with the current real edi writer',
    )
    parser.add_argument(
        '--crysta-oracle-only',
        action='store_true',
        help='re-freeze only the crysta CLI regression oracle from the stamped pinned build',
    )
    parser.add_argument(
        '--one-loader-only',
        action='store_true',
        help='realign only the model-only writer pins to the one-loader fit-ready contract',
    )
    arguments = parser.parse_args()
    selected_modes = sum((
        arguments.desired_writer_only,
        arguments.crysta_oracle_only,
        arguments.one_loader_only,
    ))
    if selected_modes > 1:
        parser.error('choose only one regeneration mode')
    if arguments.crysta_oracle_only:
        refresh_crysta_oracle_only()
        return
    if arguments.one_loader_only:
        freeze_one_loader_writer()
        return
    if arguments.desired_writer_only:
        freeze_desired_writer()
        manifest = json.loads((FIXTURE / 'manifest.json').read_text(encoding='utf-8'))
        manifest['desired_writer']['generator'] = 'edi.Project.load(...).save_as(...)'
        manifest['desired_writer']['role'] = (
            'schema-3 implementation-produced regression pins, not correctness oracles'
        )
        manifest['desired_writer']['key_absent'] = (
            'preserve absence separately from the explicit none selector'
        )
        manifest['desired_writer']['c11_t48_refresh'] = (
            'regression pins refreshed solely for the declared fourth TOF calibration term; '
            'the added calib_d_to_tof_reciprocal row is not an independent correctness claim'
        )
        manifest['desired_writer']['e09_t58_refresh'] = (
            'regression pins advanced to schema 3 and the deliberate  canonical writer '
            'bytes; no generated value is an independent correctness claim'
        )
        manifest['desired_writer']['e09_t58_final_delegation'] = {
            'source_record': 'build/crysta-src/CRYSTA_SOURCE_SHA',
            'source_sha': RECORDED_CRYSTA_SHA,
            'moved_goldens': 6,
            'ruling_trace': {
                'F-a': (
                    'key_absent and no_code_type_none experiment bytes gain the default none '
                    'family token'
                ),
                'F-c': 'all three experiment bytes replace 2e+05 with 200000',
                'F-d': 'no_code_type_none structure bytes gain the model-held ADP type',
                'T-3': 'all three structure bytes gain derived multiplicities',
                'one-row-per-basic': (
                    'zero bytes move: these save-only fixtures contain no fitted-state rows'
                ),
            },
        }
        manifest['files'] = {
            str(path.relative_to(FIXTURE)): sha256(path) for path in frozen_files()
        }
        (FIXTURE / 'manifest.json').write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8'
        )
        return

    binary = verify_identities()
    copy_source_project()
    command = freeze_cli_oracle(binary)
    derive_key_absent_project()
    freeze_pre_task_writer()
    write_manifest(binary, command)


if __name__ == '__main__':
    main()
