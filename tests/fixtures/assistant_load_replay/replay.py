"""Offline native load_data replay after a parameter edit in another group, with Show actions off and on.

No model or network is used: the peer only delivers authored native tool calls. The sequence is the owner's
(2026-11-17): create a project, load a structure CIF, create an experiment, set its wavelength on the
Instrument group, then load measured data. Opening Instrument folds the Experiments group, so Show actions must
open that group again before the row's Data file cell can be clicked. Exits non-zero unless load_data completes in
both modes.
"""

# ruff: noqa: PLR0915, PLR0914, PLW0717, B023, TRY301, BLE001, S106, E501
from __future__ import annotations

import argparse
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
        'load_native_driver', ROOT / 'tests/system/py/test_e11_t5_dev_native_integration.py'
    )
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    summary = {'binary': str(binary), 'provider_used': False, 'modes': []}
    for show in (False, True):
        folder = output / ('on' if show else 'off')
        folder.mkdir()
        actor = None
        mode = {'show_actions': show, 'steps': []}
        summary['modes'].append(mode)
        try:
            actor = driver.MainActor(binary, folder, {'turns': [[]]}, show)
            actor.command('evaluate', expression='requestActivate()')
            previous = folder / 'last-open' / 'previous'
            shutil.copytree(
                ROOT / 'tests/fixtures/assistant_save_owner_20261029/project', previous
            )
            data = ROOT / 'tests/fixtures/background_estimate/meas-lbco-hrpt.xye'
            shutil.copyfile(data, previous / 'experiments/meas-lbco-hrpt.xye')
            opened = actor.command('open', path=str(previous))['reply']
            if not opened.get('opened'):
                raise RuntimeError('Original project Open refused')
            actor.until(lambda row: not row['ui']['project']['calculating'])
            cif = ROOT / 'tests/fixtures/assistant_save_replay/lbco.cif'
            files = []

            def admit():
                token = actor.begin_current_file_selection()
                admitted = actor.command('selected_add', token=token, paths=[str(cif), str(data)])[
                    'reply'
                ]
                if not admitted.get('added'):
                    raise RuntimeError('Original selected-file admission refused')
                files[:] = actor.last['ui']['selected_files']

            def file_id(suffix):
                return next(row['id'] for row in files if suffix in json.dumps(row))

            admit()

            def call(tool, **arguments):
                identity = 'load-replay-' + str(len(mode['steps'])) + '-' + tool
                native = driver.tool_call(tool, identity, **arguments)
                started = actor.trace.exists() and any(
                    'method' in row and row['method'] == 'turn/start'
                    for row in map(json.loads, actor.trace.read_text().splitlines())
                )
                if started:
                    actor.append_turn([native])
                else:
                    actor.configure_turns([[native]])
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
                mode['steps'].append({'step': tool, 'response': response})
                (folder / 'steps.json').write_text(json.dumps(mode, indent=2) + '\n')
                return response

            if show:
                # Show actions' Create dialog typing stalls on this harness (the save replay's create_project
                # too), so the empty project comes from the Session, as that dialog makes it.
                created = driver.qml(
                    actor,
                    'Session.createProject("lbco_load_replay", "LBCO load after a parameter edit")',
                )
                mode['steps'].append({'step': 'create_project_session', 'response': created})
                if not created:
                    raise RuntimeError('Session.createProject refused')
                # A new project starts with no admitted inputs: the files are selected again for it.
                admit()
            else:
                call(
                    'create_project',
                    name='lbco_load_replay',
                    title='LBCO load after a parameter edit',
                )
            call('load_structure', file_id=file_id('.cif'))
            call('create_experiment')
            experiment = driver.qml(actor, 'Session.project.experiments.text(0, "name")')
            call(
                'set_experiment_type',
                experiment=experiment,
                axis='radiationProbe',
                token='neutron',
            )
            wavelength = next(
                row['path']
                for row in actor.last['ui']['project']['parameters']
                if row['path'].endswith('instrument.setup_wavelength')
            )
            call('set_parameters', values=[{'path': wavelength, 'value': 1.49}])
            loaded = call('load_data', experiment=experiment, file_id=file_id('.xye'))
            mode['load_data'] = loaded
            mode['loaded'] = 'action_error' not in json.dumps(loaded)
        except Exception as error:
            mode['driver_error'] = str(error)
        finally:
            if actor:
                actor.close()
            (output / 'RESULT.json').write_text(json.dumps(summary, indent=2) + '\n')
    return int(
        any(mode.get('driver_error') or not mode.get('loaded') for mode in summary['modes'])
    )


if __name__ == '__main__':
    sys.exit(main())
