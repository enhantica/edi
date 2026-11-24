#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""A local stand-in for the assistant's model: it calls every tool once.

tools/dev/assistant-tools.sh gives it to the app as the agent's executable. It
speaks the agent's protocol on its standard streams, has no network, and writes
each call and its reply to results.jsonl in EDI_ASSISTANT_PEER_DIR.
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
import time
from pathlib import Path

DIR = Path(os.environ['EDI_ASSISTANT_PEER_DIR'])
SCAN = bool(os.environ.get('EDI_ASSISTANT_PROJECT'))
SPOILED = os.environ.get('EDI_ASSISTANT_SPOILED') == '1'
# No call may take longer: the app gives up a wait on its own well before this.
LIMIT = float(os.environ.get('EDI_ASSISTANT_CALL_LIMIT', '420'))
THREAD, TURN = 'peer-thread', 'peer-turn'

incoming: queue.Queue = queue.Queue()


def write(row: dict) -> None:
    sys.stdout.write(json.dumps(row) + '\n')
    sys.stdout.flush()


def event(method: str, **params: object) -> None:
    write({'method': method, 'params': params})


def read_lines() -> None:
    for line in sys.stdin:
        incoming.put(json.loads(line))
    incoming.put(None)


ACCOUNT = {'type': 'chatgpt', 'email': 'peer@example.invalid', 'planType': 'plus'}
MODEL = {
    'id': 'local-peer',
    'model': 'local-peer',
    'displayName': 'Local peer',
    'hidden': False,
    'defaultReasoningEffort': 'medium',
    'supportedReasoningEfforts': [{'reasoningEffort': 'medium'}],
}
# The app's requests whose reply does not depend on what they ask.
FIXED = {
    'account/read': {'account': ACCOUNT, 'requiresOpenaiAuth': False},
    'model/list': {'data': [MODEL], 'nextCursor': None},
    'turn/start': {'turn': {'id': TURN, 'status': 'inProgress'}},
    'thread/list': {'data': [], 'nextCursor': None},
    'account/rateLimits/read': {'rateLimits': None},
}


def answer(request: dict) -> dict:
    """The reply to one of the app's own requests."""
    method, params = request['method'], request.get('params') or {}
    if method == 'skills/list':
        folder = (params.get('cwds') or [''])[0]
        skills = [
            {'name': path.parent.name, 'path': str(path), 'enabled': True}
            for path in sorted(Path(folder).glob('.agents/skills/*/SKILL.md'))
        ]
        return {'data': [{'cwd': folder, 'skills': skills, 'errors': []}]}
    if method == 'thread/start':
        return {
            'thread': {'id': THREAD, 'ephemeral': False},
            'cwd': params.get('cwd'),
            'modelProvider': 'openai',
            'model': params.get('model'),
            'reasoningEffort': (params.get('config') or {}).get('model_reasoning_effort'),
            'approvalPolicy': 'never',
            'approvalsReviewer': 'user',
            'sandbox': {'type': 'readOnly', 'networkAccess': False},
        }
    return FIXED.get(method, {})


class Tools:
    """Calls tools one at a time and keeps what they answered."""

    def __init__(self) -> None:
        self.number = 0

    def fold(self, spoil: str) -> None:
        ask = DIR / 'fold'
        part = DIR / 'fold.part'
        part.write_text(f'{self.number}\n{spoil}')
        part.rename(ask)
        for _ in range(250):
            if not ask.exists():
                return
            time.sleep(0.02)

    def call(
        self,
        tool: str,
        note: str = '',
        spoil: str = '',
        shown: tuple[str, ...] = (),
        limit: float = 15,
        met: str = '',
        **arguments: object,
    ) -> dict:
        self.number += 1
        self.fold(spoil)
        item = {
            'id': f'item-{self.number}',
            'type': 'dynamicToolCall',
            'tool': tool,
            'arguments': arguments,
            'status': 'inProgress',
        }
        event('item/started', threadId=THREAD, turnId=TURN, item=item)
        began = time.monotonic()
        write({
            'id': f'call-{self.number}',
            'method': 'item/tool/call',
            'params': {
                'threadId': THREAD,
                'turnId': TURN,
                'callId': item['id'],
                'tool': tool,
                'arguments': arguments,
            },
        })
        result = None
        while result is None:
            try:
                row = incoming.get(timeout=max(0.1, began + LIMIT - time.monotonic()))
            except queue.Empty:
                break
            if row is None:
                sys.exit(0)
            if row.get('method'):
                if 'id' in row:
                    write({'id': row['id'], 'result': answer(row)})
                continue
            if row.get('id') == f'call-{self.number}':
                result = row.get('result') or {'success': False, 'error': row.get('error')}
        seconds = round(time.monotonic() - began, 1)
        hung = result is None
        result = result or {'success': False, 'contentItems': []}
        content = result.get('contentItems') or [{}]
        text = content[0].get('text', '')
        try:
            reply = json.loads(text)
        except ValueError:
            reply = {'message': text, 'error': result.get('error')}
        record = {
            'call': self.number,
            'tool': tool,
            'note': note,
            'spoil': spoil,
            'shown': shown,
            'limit': limit,
            'met': met,
            'arguments': arguments,
            'success': bool(result.get('success')),
            'seconds': seconds,
            'hung': hung,
            'cue_skipped': reply.get('cue_skipped') or '',
            'status': reply.get('status', ''),
            'message': reply.get('message', ''),
            'error': reply.get('action_error', ''),
            'reply': {} if len(text) > 4000 else reply,
        }
        with (DIR / 'results.jsonl').open('a') as out:
            out.write(json.dumps(record) + '\n')
        item.update(status='completed', success=record['success'], contentItems=content)
        event('item/completed', threadId=THREAD, turnId=TURN, item=item)
        if hung:
            raise TimeoutError(tool)
        return reply

    def settled(self) -> dict:
        """The project once nothing is calculating."""
        for _ in range(60):
            context = self.call('inspect_project', 'settle')
            if not (context.get('native_state') or {}).get('calculating'):
                return context
            time.sleep(1)
        return context


def parameters(tools: Tools) -> dict:
    rows = tools.call('list_parameters').get('parameters', [])
    return {row['path']: row for row in rows}


def ending(rows: dict, *ends: str) -> list[str]:
    return [path for end in ends for path in rows if path.endswith(end)]


def files(context: dict) -> dict[str, str]:
    rows = (context.get('selected_files') or {}).get('files', [])
    return {row['name']: row['id'] for row in rows}


def by_suffix(names: dict[str, str], suffix: str) -> str:
    return next((value for name, value in names.items() if name.endswith(suffix)), '')


def lbco(tools: Tools) -> None:
    attached = files(tools.call('inspect_project'))
    cif, data = by_suffix(attached, '.cif'), by_suffix(attached, '.xye')
    tools.call('read_selected_file', file_id=cif, offset=0, max_bytes=500)
    tools.call('acquire_inputs', 'refused: nothing to acquire', scope_id='none')
    tools.call(
        'create_project',
        name=f'lbco-peer-{int(time.time())}',
        title='LBCO',
        description='Every tool',
    )
    tools.call('load_structure', file_id=cif)
    made = tools.call('create_experiment')
    experiment = (made.get('datasets') or [{'id': 'experiment1'}])[0]['id']
    for token in ('xray', 'neutron'):
        tools.call(
            'set_experiment_type', experiment=experiment, axis='radiationProbe', token=token
        )
    tools.settled()
    rows = parameters(tools)
    for path in ending(rows, 'instrument.setup_wavelength'):
        tools.call('set_parameters', 'before data', values=[{'path': path, 'value': 1.494}])
    loaded = tools.call('load_data', experiment=experiment, file_id=data)
    experiment = (loaded.get('datasets') or [{'id': experiment}])[0]['id']
    tools.settled()
    tools.call(
        'inspect_data', dataset_id=experiment, start=0, count=3098, partitions=4, view='summary'
    )
    tools.call('estimate_background', experiment=experiment)
    context = tools.settled()
    structure = (context.get('structures') or [{}])[0].get('id') or 'lbco'
    background(tools, experiment)
    shared(tools, experiment)
    tools.call('edit_structure', structure=structure, operation='rename', value='lbco_renamed')
    tools.call('edit_structure', structure='lbco_renamed', operation='rename', value=structure)
    atom = tools.call('edit_atom', structure=structure, operation='append')
    atom_id = atom.get('atom_id') or (atom.get('atom') or {}).get('id') or ''
    if atom_id:
        tools.call(
            'edit_atom',
            structure=structure,
            operation='text',
            atom=atom_id,
            field='typeSymbol',
            value='O',
        )
        tools.call(
            'edit_atom', structure=structure, operation='adp_type', atom=atom_id, value='Uiso'
        )
        tools.call('edit_atom', structure=structure, operation='remove', atom=atom_id)
    relations(tools)
    fit(tools)
    tools.call('create_structure')
    tools.call('edit_structure', structure=structure, operation='select')
    tools.call('diagnostics')
    tools.call('show_report')
    tools.settled()
    tools.call('save_project')


def background(tools: Tools, experiment: str) -> None:
    def edit(operation: str, **more: object) -> dict:
        return tools.call('edit_background', experiment=experiment, operation=operation, **more)

    added = edit('add', position=100.25, intensity=200.0, free=False)
    point = added.get('background_id', '')
    edit('update', id=point, position=100.5, intensity=210.0, free=True)
    edit('remove', id=point)
    edit('name_from_positions')


def shared(tools: Tools, experiment: str) -> None:
    """Edits any powder project takes."""
    rows = parameters(tools)
    number = [
        path
        for path in ending(
            rows,
            'cell.length_a',
            'instrument.setup_wavelength',
            'broad_gauss_u',
            '.adp_iso',
            'linked_structures[lbco].scale',
        )
        if rows[path]['refinable']
    ][:5]
    values = [
        {'path': path, 'value': float(f'{rows[path]["value"] * 1.0001 + 1e-5:.6g}')}
        for path in number
    ]
    tools.call('set_parameters', 'structure and experiment', values=values[:3])
    for value in values[3:]:
        tools.call('set_parameters', values=[value])

    def edit(operation: str, note: str = '', **more: object) -> dict:
        return tools.call(
            'edit_experiment', note, experiment=experiment, operation=operation, **more
        )

    region = edit('exclusion_append')
    name = region.get('region') or region.get('exclusion_id') or region.get('region_id') or ''
    if not name:
        context = tools.settled()
        regions = next(
            (
                row.get('excluded_regions') or row.get('regions') or []
                for row in context.get('datasets', [])
                if row.get('id') == experiment
            ),
            [],
        )
        name = regions[-1].get('id', '') if regions else '1'
    edit('exclusion_start', region=name, value=160.5)
    edit('exclusion_end', region=name, value=164.5)
    edit('exclusion_remove', region=name)
    edit('cutoff_fwhm', value=25.0)
    edit('absorption_type', value='cylinder-hewat')
    # Fields of two groups, one on each tab of the page.
    rows = parameters(tools)
    for note, ends in (('absorption', ('absorption.mu_r',)), ('linked structure', ('.scale',))):
        for path in [path for path in ending(rows, *ends) if rows[path]['refinable']][:1]:
            value = float(f'{rows[path]["value"] * 1.0001 + 1e-3:.6g}')
            tools.call('set_parameters', note, values=[{'path': path, 'value': value}])
    edit('absorption_type', value='none')
    edit('select')
    phases = next(
        (
            row.get('phases') or []
            for row in tools.settled().get('datasets', [])
            if row.get('id') == experiment
        ),
        [],
    )
    if phases:
        for value in (False, True):
            edit('phase_enabled', phase=phases[0]['structure_id'], value=value)
    rows = parameters(tools)
    flags = [p for p in ending(rows, 'cell.length_a', '.scale') if rows[p]['fittable']][:2]
    for free in (False, True):
        tools.call(
            'set_free', f'all {free}', flags=[{'path': path, 'free': free} for path in flags]
        )
    if flags:
        tools.call('set_free', 'one', flags=[{'path': flags[0], 'free': False}])
        tools.call('set_free', 'one back', flags=[{'path': flags[0], 'free': True}])
    # Analysis is the page shown now, so the same values go through its table.
    value = float(f'{rows[flags[0]]["value"] * 1.0001:.6g}') if flags else 0
    if flags:
        tools.call('set_parameters', 'on Analysis', values=[{'path': flags[0], 'value': value}])
    # The Free column's menu sets the parameters of a whole category.
    whole = [path for path in rows if '.peak.' in path and rows[path]['fittable']]
    for free in (True, False):
        tools.call(
            'set_free', f'category {free}', flags=[{'path': p, 'free': free} for p in whole]
        )


def relations(tools: Tools) -> None:
    rows = parameters(tools)
    sites = [path for path in ending(rows, '.adp_iso') if rows[path]['refinable']][:2]
    if len(sites) < 2:
        return
    aliases = [{'id': f'adp{i}', 'path': path} for i, path in enumerate(sites)]
    constraint = {'id': 'same', 'expression': 'adp1 = adp0', 'enabled': True}
    tools.call('add_relations', aliases=aliases, constraints=[constraint])

    def edit(operation: str, name: str, **more: object) -> None:
        tools.call('edit_relation', operation=operation, id=name, **more)

    # A switched-off constraint is not editable, so it is switched off last.
    edit('constraint_rename', 'same', value='equal')
    edit('constraint_expression', 'equal', value='adp1 = 1 * adp0')
    edit('constraint_enabled', 'equal', value=False)
    edit('constraint_remove', 'equal')
    edit('alias_rename', 'adp1', value='second')
    edit('alias_target', 'second', value=sites[0])
    edit('alias_remove', 'second')
    edit('alias_remove', 'adp0')


def fit(tools: Tools) -> None:
    tools.settled()
    tools.call('run_fit', purpose='Fit the free parameters')
    tools.settled()
    tools.call('undo_fit', purpose='Back to the start')
    tools.settled()


def unmet(wanted: dict, found: dict) -> None:
    """What an item done without showing left is what it was to leave."""
    for name, value in wanted.items():
        if found.get(name) != value:
            raise AssertionError(f'{name}: {found.get(name)}, not {value}')


def spoiled_items(tools: Tools, experiment: str) -> None:
    """The first item's control fails: it is done unshown, the call's other items are shown."""
    rows = parameters(tools)
    ends = ('cell.length_a', 'instrument.setup_wavelength', 'broad_gauss_u')
    paths = ending(rows, *ends)
    wanted = {path: float(f'{rows[path]["value"] * 1.0002 + 1e-5:.6g}') for path in paths}
    tools.call(
        'set_parameters',
        'first of three',
        spoil='once-absent cell.length_a',
        shown=('instrument.setup_wavelength', 'peak.broad_gauss_u'),
        limit=60,
        values=[{'path': path, 'value': value} for path, value in wanted.items()],
    )
    rows = parameters(tools)
    unmet(wanted, {path: rows[path]['value'] for path in paths})
    tools.settled()
    flags = [p for p in ending(rows, 'cell.length_a', '.scale') if rows[p]['fittable']][:2]
    wanted = {path: not rows[path]['free'] for path in flags}
    tools.call(
        'set_free',
        'first of two',
        spoil='once-absent parameters.value.*',
        shown=('parameters.value.',),
        limit=90,
        flags=[{'path': path, 'free': free} for path, free in wanted.items()],
    )
    rows = parameters(tools)
    unmet(wanted, {path: rows[path]['free'] for path in flags})
    tools.settled()
    sites = [path for path in ending(rows, '.adp_iso') if rows[path]['refinable']][:2]
    tools.call(
        'add_relations',
        'first of three',
        spoil='once-absent aliases.append',
        shown=('aliases.append', 'alias.id.1', 'constraints.append'),
        limit=90,
        aliases=[{'id': f'adp{i}', 'path': path} for i, path in enumerate(sites)],
        constraints=[{'id': 'same', 'expression': 'adp1 = adp0', 'enabled': True}],
    )
    tools.settled()

    def edit(operation: str, note: str = '', **more: object) -> dict:
        return tools.call(
            'edit_background', note, experiment=experiment, operation=operation, **more
        )

    added = edit('add', position=100.25, intensity=200.0, free=False)
    tools.settled()
    edit(
        'update',
        'first of three',
        spoil='once-absent background.position.*',
        shown=('background.intensity.', 'parameters.value.'),
        limit=90,
        id=added.get('background_id', ''),
        position=100.5,
        intensity=210.0,
        free=True,
    )
    tools.settled()


def spoiled(tools: Tools) -> None:
    """Steps whose control cannot be shown: each is done once, unshown, the next is shown."""
    attached = files(tools.call('inspect_project'))
    for control in ('project.create', 'createProject.accept'):
        name = f'{control.rpartition(".")[2]}-peer-{int(time.time())}'
        made = tools.call(
            'create_project',
            control,
            spoil=f'absent {control}',
            limit=30,
            name=name,
            title='',
            description='',
        )
        unmet({'name': name}, made)
    tools.call('load_structure', file_id=by_suffix(attached, '.cif'))
    made = tools.call('create_experiment')
    experiment = (made.get('datasets') or [{'id': 'experiment1'}])[0]['id']
    tools.settled()
    loaded = tools.call('load_data', experiment=experiment, file_id=by_suffix(attached, '.xye'))
    experiment = (loaded.get('datasets') or [{'id': experiment}])[0]['id']
    tools.settled()
    tools.call('estimate_background', experiment=experiment)
    tools.settled()
    spoiled_items(tools, experiment)

    def experiments() -> int:
        return len(tools.settled().get('datasets') or [])

    for spoil in ('covered', 'absent', 'disabled', 'late', 'mute'):
        before = experiments()
        tools.call('create_experiment', spoil, spoil=f'{spoil} experiments.create')
        # Long enough for a press that was held back to land.
        time.sleep(12 if spoil == 'late' else 1)
        after = experiments()
        if after != before + 1:
            raise AssertionError(f'{spoil}: {after - before} experiments made, not 1')
        tools.call('create_experiment', f'shown after {spoil}')
    spoiled_clock(tools, experiment)
    spoiled_pages(tools)


def spoiled_clock(tools: Tools, experiment: str) -> None:
    """A control that does not answer has 10 s, and longer while the window is at work."""
    for spoil in ('gone', 'moving-gone', 'busy-gone'):
        tools.call(
            'edit_experiment',
            spoil,
            spoil=f'{spoil} excludedRegions.append',
            limit=45 if spoil == 'busy-gone' else 22,
            met='excludedRegions.append',
            experiment=experiment,
            operation='exclusion_append',
        )
        tools.settled()
    path = ending(parameters(tools), 'cell.length_a')[0]
    tools.call(
        'set_parameters',
        'a popup',
        spoil='disabled cell.length_a.menu.popup.value',
        limit=22,
        met='group group.cell; visible yes, enabled no',
        values=[{'path': path, 'value': 3.91}],
    )
    tools.settled()


def spoiled_pages(tools: Tools) -> None:
    """Save and Report: their control absent, late or covered."""
    for tool, control in (
        ('show_report', 'appBar.tab.report'),
        ('save_project', 'appBar.button.save'),
    ):
        tools.call(tool, 'absent', spoil=f'absent {control}', limit=22, met=control)
        tools.settled()
        # It comes within the step's time, or is covered: its cue presses nothing, so it is shown.
        for spoil in ('soon-absent', 'covered'):
            tools.call(tool, spoil, spoil=f'{spoil} {control}')
            tools.settled()
    tools.call('save_project', 'the folder keeps changing', spoil='folder')
    time.sleep(9)
    tools.call('save_project', 'after it')


def scan(tools: Tools) -> None:
    context = tools.settled()
    tools.call('inspect_project')
    experiment = (context.get('datasets') or [{}])[0].get('id', '')
    rows = parameters(tools)
    if experiment:
        tools.call('inspect_data', dataset_id=experiment, start=0, count=100, view='rows')
    ends = ('cell.length_a', '.adp_iso', 'broad_gauss_u', 'asym_fcj_1', 'scale')
    paths = [path for path in ending(rows, *ends) if rows[path]['refinable']][:6]
    for path in paths:
        value = float(f'{rows[path]["value"] * 1.0001 + 1e-5:.6g}')
        tools.call('set_parameters', values=[{'path': path, 'value': value}])
    tools.settled()
    flags = [path for path in paths if rows[path]['fittable']][:2]
    for free in (True, False):
        tools.call('set_free', flags=[{'path': path, 'free': free} for path in flags])
    if flags:
        tools.call('set_free', 'one', flags=[{'path': flags[0], 'free': True}])
    tools.call('estimate_background', 'scan', experiment=experiment)
    tools.call('edit_structure', structure='cosio', operation='space_group_setting', value='cab')
    tools.call('edit_structure', structure='cosio', operation='space_group_setting', value='abc')
    tools.call('run_fit', 'a scan is fitted by the user', purpose='Fit the scan')
    tools.call('undo_fit', 'refused: no fit', purpose='None')
    relations(tools)
    tools.call('diagnostics')
    tools.call('show_report')
    tools.settled()
    tools.call('save_project')


def main() -> None:
    threading.Thread(target=read_lines, daemon=True).start()
    while (row := incoming.get()) is not None:
        if not row.get('method') or 'id' not in row:
            continue
        write({'id': row['id'], 'result': answer(row)})
        if row['method'] != 'turn/start':
            continue
        turn = {'id': TURN, 'status': 'inProgress'}
        event('turn/started', threadId=THREAD, turn=turn)
        end, error = 'completed', None
        try:
            tools = Tools()
            (spoiled if SPOILED else scan if SCAN else lbco)(tools)
            # What the run left, to compare Show actions on and off.
            rows = parameters(tools).values()
            left = {row['unique_name']: [row['value'], row['free']] for row in rows}
            (DIR / 'parameters.json').write_text(json.dumps(left, indent=1) + '\n')
        except Exception as failure:  # noqa: BLE001 - reported, so a run never ends as a pass
            (DIR / 'peer-error').write_text(f'{type(failure).__name__}: {failure}\n')
        event('turn/completed', threadId=THREAD, turn={'id': TURN, 'status': end, 'error': error})


if __name__ == '__main__':
    main()
