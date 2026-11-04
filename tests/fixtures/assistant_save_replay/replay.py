"""Offline native Save bisect driver; run this fixture against any compatible probe.

No model or network is used. The peer only delivers authored native tool calls.
The retained LBCO CIF and HRPT observations are inputs, not fit-result goldens.
"""

# ruff: noqa: PLR0915, PLR0914, B023, TRY301, S106, BLE001, PLW0717, E501
# This sequential manual driver keeps each native boundary beside its receipt.
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location(
        'save_native_driver', ROOT / 'tests/system/py/test_e11_t5_dev_native_integration.py'
    )
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    summary = {
        'binary': str(binary),
        'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
        'provider_used': False,
        'exact_owner_replay': False,
        'modes': [],
    }
    for show in (False, True):
        folder = output / ('on' if show else 'off')
        folder.mkdir()
        actor = None
        mode = {'show_actions': show, 'steps': []}
        summary['modes'].append(mode)

        def record(step, response=None):
            facts = driver.qml(
                actor,
                '({location:Session.locationText,path:Session.project ? Session.project.path : "",error:Session.lastError})',
            )
            path = facts.get('path', '')
            mode['steps'].append({
                'step': step,
                'response': response,
                **facts,
                'folder_exists': bool(path) and Path(path).is_dir(),
                'project_file_exists': bool(path) and (Path(path) / 'project.edi').is_file(),
                'project_tab_location': [
                    row
                    for row in actor.last['ui'].get('texts', [])
                    if row.get('name') == 'project.location'
                ],
            })
            (folder / 'steps.json').write_text(json.dumps(mode, indent=2) + '\n')

        try:
            actor = driver.MainActor(binary, folder, {'turns': [[]]}, show)
            actor.command('evaluate', expression='requestActivate()')
            # Open a genuine project first, establishing the ordinary last-open parent.
            previous = folder / 'last-open' / 'previous'
            shutil.copytree(
                ROOT / 'tests/fixtures/assistant_save_owner_20261029/project', previous
            )
            data = ROOT / 'tests/fixtures/background_estimate/meas-lbco-hrpt.xye'
            shutil.copyfile(data, previous / 'experiments/meas-lbco-hrpt.xye')
            opened = actor.command('open', path=str(previous))['reply']
            record('open_previous', opened)
            if not opened.get('opened'):
                raise RuntimeError('Original project Open refused; create entrance unreached')
            actor.until(lambda row: not row['ui']['project']['calculating'])
            token = actor.begin_current_file_selection()
            cif = Path(__file__).with_name('lbco.cif')
            admitted = actor.command('selected_add', token=token, paths=[str(cif), str(data)])[
                'reply'
            ]
            if not admitted.get('added'):
                raise RuntimeError('Original selected-file admission refused')
            files = actor.last['ui']['selected_files']

            def file_id(suffix):
                return next(row['id'] for row in files if suffix in json.dumps(row))

            def call(tool, **arguments):
                identity = 'save-bisect-' + str(len(mode['steps'])) + '-' + tool
                native = driver.tool_call(tool, identity, **arguments)
                if not any(
                    'method' in row and row['method'] == 'turn/start'
                    for row in (
                        map(json.loads, actor.trace.read_text().splitlines())
                        if actor.trace.exists()
                        else []
                    )
                ):
                    actor.configure_turns([[native]])
                else:
                    actor.append_turn([native])
                before = len(actor.responses())
                actor.connect()
                actor.until(
                    lambda _row: driver.qml(actor, 'Session.assistant.draftAdmissionReady')
                )
                actor.command(
                    'evaluate',
                    expression='Session.assistant.send("Exercise this authored native operation; report its actual result.")',
                )
                actor.until(
                    lambda row: len(actor.responses()) > before and row['ui']['state'] == 'idle',
                    visible_progress=show,
                )
                response = actor.responses()[-1]
                record(tool, response)
                return response

            call('create_project', name='lbco_save_bisect', title='LBCO neutron Save replay')
            mode['expected_parent'] = str(previous.parent)
            record('created_destination')
            call('load_structure', file_id=file_id('.cif'))
            call('create_experiment')
            # Discover actual current member identity instead of inventing its name.
            experiment = driver.qml(actor, 'Session.project.experiments.text(0, "name")')
            call(
                'set_experiment_type',
                experiment=experiment,
                axis='radiationProbe',
                token='neutron',
            )
            call('load_data', experiment=experiment, file_id=file_id('.xye'))
            call('save_project', destination='current')
            parameters = actor.last['ui']['project']['parameters']
            flags = [
                {'path': row['path'], 'free': row['path'].endswith('.scale')}
                for row in parameters
                if row.get('refinable') and row.get('dependence') == 0
            ]
            call('set_free', flags=flags)
            call('run_fit')
            call('undo_fit')
            call('save_project', destination='current')
        except Exception as error:
            mode['driver_error'] = str(error)
            if (
                actor
                and actor.process.poll() is None
                and not getattr(actor, '_stream_unusable', None)
            ):
                record('failure')
        finally:
            if actor:
                actor.close()
            (output / 'RESULT.json').write_text(json.dumps(summary, indent=2) + '\n')
    return int(any(mode.get('driver_error') for mode in summary['modes']))


if __name__ == '__main__':
    sys.exit(main())
