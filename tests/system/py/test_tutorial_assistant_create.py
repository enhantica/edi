"""Whole native Create/replace/save journeys retain their nightly system cadence."""

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

from tests.system.py import test_e11_t5_dev_native_integration as native_fixture
from tests.system.py.test_e11_t5_dev_native_integration import (
    FINAL,
    ROOT,
    _assert_exact_original_admitted_user_input,  # noqa: PLC2701 - retain original lifecycle fixture helpers
    _new_project_file_hashes,  # noqa: PLC2701 - retain original lifecycle fixture helpers
    _new_project_scientific_bytes,  # noqa: PLC2701 - retain original lifecycle fixture helpers
    _scene_control_expression,  # noqa: PLC2701 - retain original lifecycle fixture helpers
    _session_configure,  # noqa: PLC2701 - retain original lifecycle fixture helpers
    _session_request_with_original_disclosure,  # noqa: PLC2701 - retain original lifecycle fixture helpers
    _session_state,  # noqa: PLC2701 - retain original lifecycle fixture helpers
    _watch_original_project_open,  # noqa: PLC2701 - retain original lifecycle fixture helpers
    copied_estimate_project,
    history_poll,
    native_result,
    objects,
    qml,
    tool_call,
)

main_actor = native_fixture.main_actor


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_empty_current_session_uses_normal_create_load_and_current_save(  # noqa: PLR0914, PLR0915
    main_actor, tmp_path, show_actions
):
    actor = main_actor([[]], show_actions=show_actions)
    initial = actor.last['ui']
    assert not initial['project'], (
        'Normal app Create starts from the actual empty current Session without a seeded project'
    )
    environment = initial['environment']
    documents = Path(environment['documents_root'])
    assert documents == Path(environment['temporary_documents_root']) and documents.is_dir(), (
        'Normal Create uses the isolated ordinary OS Documents parent without real-user writes'
    )
    project_name = 'e11_native_' + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    project_title = 'Independent published-cell continuation'
    project_description = 'Native Create followed by selected CIF import and ordinary current Save'
    assert re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_\-.]{1,30}', project_name), (
        'The autonomous Create fixture supplies a valid name under the unchanged original '
        'dialog validator'
    )
    destination = documents / project_name
    assert not destination.exists(), (
        'The native ordinary Create action owns creating its previously absent project destination'
    )
    offered = {row['name']: row for row in actor.command('tool_specs')['reply']['tools']}
    schema = offered['create_project']['inputSchema']
    assert set(schema['required']) == set() and set(schema['properties']) == {
        'purpose',
        'name',
        'title',
        'description',
    }, 'Normal current-session Create exposes the complete ordinary project metadata contract'
    cif = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    actor.connect()
    token = qml(actor, 'Session.assistant.beginFileSelection(true)')
    assert actor.command('selected_add', token=token, paths=[str(cif)])['reply']['added'], (
        'The empty current Session admits the genuine published selected CIF before native Create'
    )
    selected = actor.last['ui']['selected_files']
    assert len(selected) == 1 and selected[0]['id'], (
        'Native Create and subsequent import retain the actually admitted selected-input identity'
    )
    actor.configure_turns([
        [
            tool_call(
                'create_project',
                'ordinary-empty-create',
                name=project_name,
                title=project_title,
                description=project_description,
            ),
            tool_call('load_structure', 'ordinary-created-cif', file_id=selected[0]['id']),
            tool_call('save_project', 'ordinary-created-current-save', destination='current'),
        ]
    ])
    actor.connect()
    actor.command('clear_ui_sequence')
    actor.request('Create a new project, import the attached CIF and save it.')
    actor.until(
        lambda row: len(actor.responses()) == 3 and row['ui']['state'] == 'idle',
        visible_progress=show_actions,
    )
    outcomes = [native_result(response) for response in actor.responses()]
    created = outcomes[0]
    assert (
        created['status'] == 'created'
        and created['adopted']
        and created['complete']
        and created['presentation_complete']
        and created['saved'] is True
        and created['name'] == project_name
        and Path(created['path']) == destination
        and created['title'] == project_title
        and created['description'] == project_description
    ), (
        'Normal Create reports actual adopted current-owner completion and its immediately '
        'saved destination'
    )
    assert actor.last['ui']['singleton_identity'] and actor.last['ui']['engine_parent'], (
        'Create, Load and Save retain the one actual current Main engine-owned Session'
    )
    events = actor.last['ui']['ui_sequence']
    before_adoption = []
    for event in events:
        if event['project_present']:
            break
        before_adoption.append(event)
    if show_actions:
        pointers = [row for row in before_adoption if row['kind'].startswith('pointer_')]
        assert pointers and all(
            not row['assistant_visible'] and row['create_visible'] and row['create_exposed']
            for row in pointers
        ), (
            'Show ON exposes the actual normal Project control and hides Assistant before '
            'locating or cueing Create'
        )
        # FIRST77 Main.qml175 defines assistantSelected as the return/preference
        # icon state. It may stay true while native presentation hides Assistant.
        # Preserve that observation and check its documented formula separately.
        assert qml(
            actor,
            'assistantToggle.assistantSelected === (assistantPanel.shown || '
            '(Session.assistant.showingActions && Preferences.assistantShown))',
        ), (
            'The original selected-bit observation retains its documented return/preference '
            'icon semantics'
        )
        assert any(
            row['kind'] == 'mouse_press'
            and row.get('create_contains_press')
            and not row['dialog_visible']
            for row in before_adoption
        ), 'Show ON actually clicks the original normal-sidebar Create control before popup input'
        assert any(
            row['dialog_visible']
            and row['kind'] in {'key_press', 'input_method'}
            and row['focus'] == 'createProject.name'
            for row in before_adoption
        ), 'Show ON enters the original Create dialog through its genuine focused name control'
        for field in ('createProject.title', 'createProject.description'):
            assert any(
                row['dialog_visible']
                and row['kind'] in {'key_press', 'input_method'}
                and row['focus'] == field
                for row in before_adoption
            ), (
                'Show ON enters each supplied metadata field through its actual original '
                'dialog editor'
            )
        assert any(
            row['kind'] == 'mouse_press'
            and row['dialog_visible']
            and row['dialog_name'] == project_name
            and row['dialog_title'] == project_title
            and row['dialog_description'] == project_description
            and row.get('confirm_contains_press')
            for row in before_adoption
        ), 'Show ON confirms the actual original Create popup before ordinary Session adoption'
    else:
        assert before_adoption and all(
            not row['kind'].startswith('pointer_')
            and not row['dialog_visible']
            and row['assistant_preference']
            for row in before_adoption
        ), 'Show OFF keeps assistant presentation unchanged before ordinary project adoption'
    owner = actor.last['ui']['project']
    assert owner['name'] == project_name and Path(owner['path']) == destination, (
        'Normal native Create retains its actual requested name and ordinary Documents destination'
    )
    assert (
        qml(actor, 'Session.project.title') == project_title
        and qml(actor, 'Session.project.description') == project_description
    ), (
        'The actual ordinary owner retains supplied title and description after native Create '
        'and Save'
    )
    assert (destination / 'project.edi').is_file(), (
        'Native ordinary Create and current Save write the actual owned project rather than a '
        'receipt only'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    rows = actor.last['ui']['project']['structure_rows']
    imported = [row for row in rows if row['length_a'] == 3.20927 and row['length_c'] == 5.21033]
    assert len(imported) == 1 and imported[0]['gamma'] == 120, (
        'The actual native CIF import preserves independent COD9008506 cell facts after normal '
        'Create'
    )
    assert imported[0]['sites'], (
        'The published native CIF contributes actual sites after ordinary Create'
    )
    assert json.loads(actor.last['ui']['context'])['datasets'] == [], (
        'The original Create CIF Save sequence retains its actual partial state without '
        'silently adding science'
    )
    assert actor.command('open', path=str(destination))['reply']['opened'], (
        'Ordinary desktop Open uses Construction mode and reopens the genuinely saved partial '
        'project without inventing an experiment'
    )
    assert json.loads(actor.last['ui']['context'])['datasets'] == [], (
        'Reopening the saved construction retains the actual absent measured dataset'
    )
    assert actor.last['ui']['project']['structure_rows'] == rows, (
        'The actual partial-project Open round trip preserves all native imported structure '
        'values and identities'
    )
    # Ordinary Open adopts a new current owner; reconnect the explicit subsequent
    # persistence request before asking it to create its separate simulation.
    actor.connect()
    actor.until(lambda row: row['ui']['state'] == 'idle')
    # Explicit separate prerequisite, owner interpretation69121c6c2: no observed
    # measurements are invented to make an isolated structure reopenable.
    actor.append_turn([
        tool_call('create_experiment', 'explicit-structure-persistence-simulation')
    ])
    actor.request(
        'For this separate persistence check add one ordinary calculation-only experiment; add '
        'no measured data.'
    )
    actor.until(
        lambda row: len(actor.responses()) == 4 and row['ui']['state'] == 'idle',
        visible_progress=show_actions,
    )
    native_result(actor.responses()[-1])
    actor.until(lambda row: not row['ui']['project']['calculating'])
    simulation = json.loads(actor.last['ui']['context'])['datasets'][0]
    assert (
        simulation['calculation_only']
        and simulation['axis']['count'] > 0
        and (simulation['observations']['intensity_count'] == 0)
    ), (
        'The explicit whole-project prerequisite is a real ordinary simulation grid, not '
        'fabricated observations'
    )
    flags = [
        (row['path'], row['free'], row['dependence'])
        for row in actor.last['ui']['project']['parameters']
    ]
    assert actor.command('save')['reply']['saved'], (
        'The ordinary owner saves the explicitly complete calculation-only project after '
        'retaining partial-stage evidence'
    )
    assert actor.command('open', path=str(destination))['reply']['opened'], (
        'Independent ordinary Open reads the genuinely complete simulation project from its '
        'real saved destination'
    )
    actor.until(lambda row: not row['ui']['project']['calculating'])
    assert actor.last['ui']['project']['structure_rows'] == rows, (
        'Normal current Save conserves every original imported structure value through '
        'complete ordinary reopen'
    )
    assert [
        (row['path'], row['free'], row['dependence'])
        for row in actor.last['ui']['project']['parameters']
    ] == flags, (
        'The separate complete-project readback preserves the actual simulation parameter '
        'membership and free/dependent flags'
    )

    assert (
        qml(actor, 'Session.project.title') == project_title
        and qml(actor, 'Session.project.description') == project_description
    ), (
        'Independent ordinary reopen reads the actually saved title and description without '
        'receipt derivation'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
def test_ordinary_empty_to_created_transition_retains_original_task_and_approved_inputs(  # noqa: PLR0914 - preserve complete lifecycle witness
    main_actor, tmp_path, show_actions
):
    actor = main_actor([[]], show_actions=show_actions)
    assert not actor.last['ui']['project'], (
        'The ordinary manual Create continuity witness starts with the actual empty Session'
    )
    files = [
        ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif',
        ROOT / 'tests/fixtures/background_estimate/meas-lbco-hrpt.xye',
    ]
    actor.connect()
    token = qml(actor, 'Session.assistant.beginFileSelection(true)')
    assert actor.command('selected_add', token=token, paths=list(map(str, files)))['reply'][
        'added'
    ], 'The pending original task admits its real selected inputs before ordinary project creation'
    manifest = actor.last['ui']['selected_files']
    assert len(manifest) == 2, 'The original task owns both selected scientific inputs'
    cif_id = next(row['id'] for row in manifest if row['name'] == files[0].name)
    expected_text = files[0].read_text(encoding='utf-8')
    actor.configure_turns([
        [],
        [
            tool_call(
                'read_selected_file',
                'after-ordinary-create',
                file_id=cif_id,
                offset=0,
                max_bytes=len(files[0].read_bytes()),
            )
        ],
    ])
    original = (
        'Create and save a new project using the attached files. One phase, NPD, '
        'wavelength 1.49 Å. Fit the structure and show the report.'
    )
    actor.connect()
    actor.request(original)
    actor.until(
        lambda row: row['ui']['state'] == 'idle' and FINAL in json.dumps(row['ui']['messages'])
    )
    # Accepted Send consumes composer presentation, while retaining each admitted file.
    # Record that actual post-Send manifest before ordinary Create (2026-10-28 record).
    sent_manifest = actor.last['ui']['selected_files']
    assert sent_manifest == [{**row, 'pending': False} for row in manifest], (
        'Accepted Send consumes the exact admitted files, retaining every identity and byte'
    )
    manifest = sent_manifest
    before = actor.last['ui']['messages']
    assert original in json.dumps(before, ensure_ascii=False), (
        'The original complete scientific objective is retained before the ordinary Create action'
    )
    actor.command('click', name='assistant.toggle')
    actor.until(lambda _row: not qml(actor, 'assistantPanelVisible'))
    actor.command('click', name='project.create')
    actor.until(
        lambda row: any(
            c['name'] == 'createProject.name' and c['visible'] for c in row['ui']['controls']
        )
    )
    name = 'e11_manual_' + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    assert re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_\-.]{1,30}', name), (
        'The ordinary manual Create continuity fixture preserves unchanged native name validation'
    )
    actor.command('click', name='createProject.name')
    actor.command('manual_key', key='select_all')
    actor.command('manual_text', text=name)
    actor.command('dialog_ok', name='createProject.dialog')
    actor.until(lambda row: row['ui']['project'].get('name') == name)
    after = actor.last['ui']
    assert original in json.dumps(after['messages'], ensure_ascii=False), (
        'Ordinary empty-to-created replacement retains the full prior task rather than chat '
        'decoration alone'
    )
    assert after['selected_files'] == manifest, (
        'The same pending task retains its genuinely admitted attachment manifest across '
        'ordinary Create'
    )
    actor.command('click', name='assistant.toggle')
    actor.request('Continue the original request.')
    actor.until(
        lambda row: len(actor.responses()) == 1 and row['ui']['state'] == 'idle',
        visible_progress=show_actions,
    )
    readback = native_result(actor.responses()[0])
    assert any(
        value == expected_text
        for row in objects(readback)
        for value in row.values()
        if isinstance(value, str)
    ), (
        'The actual new native Controller can read the retained approved file bytes, not just '
        'display its manifest'
    )
    wire = list(map(json.loads, actor.trace.read_text().splitlines()))
    turns = [row['params'] for row in wire if row.get('method') == 'turn/start']
    assert len(turns) == 2, (
        'The actual followup continues after the original task and ordinary Create'
    )
    if turns[0]['threadId'] != turns[1]['threadId']:
        assert original in json.dumps(turns[1], ensure_ascii=False), (
            'A replacement provider thread receives the original objective rather than only '
            'the word Continue'
        )
    visible_inputs = turns if turns[0]['threadId'] == turns[1]['threadId'] else [turns[1]]
    actual_context = json.dumps(visible_inputs, ensure_ascii=False)
    assert all(path.name in actual_context for path in files), (
        'The actual provider followup can see the retained scientific input manifest after '
        'ordinary Create'
    )


@pytest.mark.parametrize('show_actions', [False, True], ids=['off', 'on'])
@pytest.mark.parametrize('old_choice', ['saved'])
def test_explicit_new_project_never_reuses_current_and_preserves_original_choices_inputs_and_task(  # noqa: PLR0914, PLR0915
    main_actor, tmp_path, show_actions, old_choice
):
    description = 'An explicit unsaved description belonging only to the original project.'
    # A separate original ordinary Save provides the byte-level transition
    # baseline when the user elects Save. No output from native Create supplies
    # scientific expected values, and no new numerical correctness is claimed.
    expected_saved = None
    if old_choice == 'modified_save':
        reference = main_actor([[]])
        reference_root = copied_estimate_project(tmp_path / 'ordinary-save-reference')
        assert reference.command('open', path=str(reference_root))['reply']['opened'], (
            'The Save reference opens an independent complete source through the original '
            'ordinary owner'
        )
        reference.until(lambda value: not value['ui']['project']['calculating'])
        qml(reference, 'Session.project.description=' + json.dumps(description))
        assert reference.command('save')['reply']['saved'], (
            'The independent original Save owner persists the explicit old-project edit '
            'without native New'
        )
        reference.until(lambda value: not value['ui']['project']['calculating'])
        expected_saved = _new_project_scientific_bytes(reference_root)
        reference.close()
    actor = main_actor([[]], show_actions=show_actions)
    _session_configure(
        actor, session_fixture={'threads': [], 'page_size': 12}, observe_context_continuity=True
    )
    old_root = copied_estimate_project(tmp_path / 'original-current')
    assert actor.command('open', path=str(old_root))['reply']['opened'], (
        'Explicit New begins with a genuinely already-open complete project instead of a '
        'seeded empty Session'
    )
    actor.until(lambda value: not value['ui']['project']['calculating'])
    original_bytes = _new_project_scientific_bytes(old_root)
    shutil.copytree(old_root, actor.folder / 'original-project-byte-preimage')
    current_old_root = old_root
    if old_choice != 'saved':
        qml(actor, 'Session.project.description=' + json.dumps(description))
        assert qml(actor, 'Session.project.modified'), (
            'Modified-state branches reach a genuine ordinary metadata edit before the '
            'new-project request'
        )
    if old_choice == 'ordinary_save_as_before_new':
        # Explicit driver fixture preparation through the public original owner,
        # never fabricated native chooser acceptance. This is NOT a claim that
        # queued Create->SaveAs chooser continuation has been exercised.
        current_old_root = tmp_path / 'ordinary-user-selected-save-as-copy'
        assert not current_old_root.exists(), (
            'The actual original SaveAs owner creates its absent fixture destination'
        )
        assert actor.command('save_as', path=str(current_old_root))['reply']['saved'], (
            'The explicitly elected ordinary SaveAs uses the existing Session API and actual '
            'write result'
        )
        assert _new_project_scientific_bytes(old_root) == original_bytes, (
            'Ordinary SaveAs preserves the prior source project bytes instead of overwriting '
            'the old location'
        )
    before_new = _new_project_scientific_bytes(current_old_root)
    _original_project = actor.last['ui']['project']
    source = ROOT / 'tests/fixtures/dictionary_display/published_cod_9008506.cif'
    original_input = source.stat()
    input_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    token = actor.begin_current_file_selection()
    assert actor.command('selected_add', token=token, paths=[str(source)])['reply']['added'], (
        'Explicit New retains a genuinely admitted unchanged source input rather than '
        'substituting copied or inferred attachments'
    )
    selected = actor.last['ui']['selected_files']
    original_files = [{key: row[key] for key in ('id', 'name', 'bytes')} for row in selected]
    name = 'new_' + hashlib.sha256(str(tmp_path).encode()).hexdigest()[:16]
    title = 'Explicitly requested distinct new project'
    new_description = 'Independent original-current-project preservation gate.'
    # The ordinary form remembers its selected parent; OS Documents is only its
    # empty-profile default. Observe the real original form before requesting New.
    defaults = qml(
        actor,
        '('
        + _scene_control_expression('group.getStarted')
        + ').nativeCreateDefaults('
        + json.dumps(name)
        + ', '
        + json.dumps(new_description)
        + ', '
        + json.dumps(title)
        + ')',
    )
    assert defaults.get('name') == name and defaults.get('location'), (
        'Explicit New has one valid ordinary Create destination before any write is requested'
    )
    destination = Path(defaults['location'])
    assert not destination.exists() and destination != current_old_root, (
        'The native new-project action owns its absent ordinary form destination distinct '
        'from the original project'
    )
    actor.configure_turns([
        [
            tool_call(
                'create_project',
                'explicit-new-from-existing',
                name=name,
                title=title,
                description=new_description,
            ),
            tool_call(
                'read_selected_file',
                'same-original-file-after-new-choice',
                file_id=original_files[0]['id'],
                offset=0,
                max_bytes=source.stat().st_size,
            ),
        ]
    ])
    actor.connect()
    marker = 'e11.new.original-project-change'
    _watch_original_project_open(actor, marker)
    actor.command('clear_ui_sequence')
    task = (
        'Create and save a new project using the attached files. One phase, NPD, wavelength 1.49 '
        'Å. Fit the structure and show the report.'
    )
    _session_request_with_original_disclosure(actor, task)
    if old_choice == 'saved':
        actor.until(
            lambda value: (
                (
                    native_fixture._unique_input_control(value, 'unsavedChanges.close', fully=True)
                    is not None
                    and qml(actor, 'unsavedChanges.opened')
                )
                or bool(actor.responses())
            ),
            visible_progress=show_actions,
        )
        assert (
            not actor.responses()
            and Path(actor.last['ui']['project']['path']).resolve() == current_old_root.resolve()
            and qml(actor, '(' + _scene_control_expression(marker) + ').changes') == 0
            and not destination.exists()
        ), 'The saved project and pending New action wait for the user to agree to close'
        actor.command('click', name='unsavedChanges.close')
    if old_choice in {'modified_save', 'modified_cancel'}:
        actor.until(
            lambda value: any(
                c['name'] == 'unsavedChanges' and c['fully_exposed'] and c['enabled']
                for c in value['ui']['controls']
            )
        )
        assert (
            Path(actor.last['ui']['project']['path']).resolve() == current_old_root.resolve()
            and qml(actor, '(' + _scene_control_expression(marker) + ').changes') == 0
        ), (
            'The original unsaved-work decision is reached before New can retire or replace '
            'the still-current original project'
        )
        assert (
            _new_project_scientific_bytes(old_root) == original_bytes and not destination.exists()
        ), (
            'Pending user choice neither silently saves/discards old work nor precreates the '
            'requested new destination'
        )
        role = 'save' if old_choice == 'modified_save' else 'cancel'
        button = actor.command('dialog_ok', name='unsavedChanges', role=role)['reply']
        assert (
            button['pressed_changes'] > 0 and button['actual_dialog_name'] == 'unsavedChanges'
        ), (
            'Only genuine input on the original standard Save or Cancel button settles the '
            'old-work choice'
        )
    if old_choice == 'saved' and show_actions:
        # Shown Create types the metadata before pressing OK. Use the same
        # finite receipt budget as the other shown Create journey.
        history_poll(lambda: len(actor.responses()) == 2, seconds=120)
    actor.until(
        lambda value: len(actor.responses()) == 2 and value['ui']['state'] == 'idle',
        visible_progress=show_actions,
    )
    current = actor.last['ui']['project']
    actual_create = actor.responses()[0]['result']
    create_body = json.loads(actual_create['contentItems'][0]['text'])
    if old_choice == 'modified_cancel':
        assert (
            not create_body.get('adopted')
            and not create_body.get('complete')
            and create_body.get('status') != 'created'
        ), (
            'Cancel cannot be published as successful adoption or completed New merely because '
            'old science remains usable'
        )
        assert (
            Path(current['path']).resolve() == current_old_root.resolve()
            and qml(actor, 'Session.project.modified')
            and qml(actor, 'Session.project.description') == description
        ), (
            'Cancel retains the same original modified scientific owner and its unsaved edit '
            'rather than silently reusing it as New'
        )
        assert (
            qml(actor, '(' + _scene_control_expression(marker) + ').changes') == 0
            and not destination.exists()
            and _new_project_scientific_bytes(old_root) == original_bytes
        ), (
            'Canceled explicit New performs no project replacement or write to old/new science '
            'destinations'
        )
    else:
        assert actual_create['success'] and create_body['adopted'] and create_body['complete'], (
            'A genuine new current project also settles its original Create call truthfully '
            'rather than hiding an unconfirmed applied prefix'
        )
        assert (
            Path(current['path']).resolve() == destination.resolve()
            and destination != current_old_root
        ), (
            'Explicit New adopts a genuinely distinct actual project at the requested normal '
            'destination, never the matching old project'
        )
        assert (
            current['structures'] == 0
            and current['backgrounds'] == []
            and qml(actor, 'Session.project.name') == name
            and qml(actor, 'Session.project.title') == title
            and qml(actor, 'Session.project.description') == new_description
        ), (
            'The new ordinary project owns only its requested metadata and original empty '
            'scientific defaults, not old structures or data'
        )
        assert (destination / 'project.edi').is_file(), (
            'The original ordinary Create actually saves its new project rather than reporting '
            'a boolean alone'
        )
        if old_choice == 'modified_save':
            assert _new_project_scientific_bytes(old_root) == expected_saved, (
                'Choosing Save before New matches the independently exercised original Save '
                'owner for every old source byte'
            )
        else:
            assert (
                _new_project_scientific_bytes(current_old_root) == before_new
                and _new_project_scientific_bytes(old_root) == original_bytes
            ), (
                'A saved old project and any real ordinary SaveAs source remain byte-exact '
                'after explicit New'
            )
    assert [
        {key: row[key] for key in ('id', 'name', 'bytes')}
        for row in actor.last['ui']['selected_files']
    ] == original_files, (
        'The explicitly delegated original task retains all actual selected-input identities '
        'across either New or Cancel'
    )
    readback = native_result(actor.responses()[1])
    assert any(
        value == source.read_text()
        for row in objects(readback)
        for value in row.values()
        if isinstance(value, str)
    ), (
        'The continuing real native reader still reaches the original approved source bytes '
        'without reattachment or substitute input'
    )
    assert (
        source.stat().st_ino == original_input.st_ino
        and hashlib.sha256(source.read_bytes()).hexdigest() == input_sha
    ), 'Neither project transition changes the physical original source identity or byte authority'
    inputs = _session_state(actor)['inputs']
    assert len(inputs) == 1 and _assert_exact_original_admitted_user_input(
        actor, inputs[0], task, expected_thread_prior_inputs=0
    ), (
        'The original captured New objective is one genuine model input, not a fresh injected '
        'continuation or an added placeholder task'
    )
    events = actor.last['ui']['ui_sequence']
    if show_actions and old_choice != 'modified_cancel':
        assert any(
            e['kind'] == 'mouse_press' and e.get('create_contains_press') for e in events
        ), (
            'Show ON genuinely clicks the FIRST normal current-window Create control even '
            'while an old project was open'
        )
        assert any(
            e['kind'] in {'key_press', 'input_method'}
            and e.get('focus') == 'createProject.name'
            and e.get('dialog_visible')
            for e in events
        ), 'Show ON enters the supplied new name through the actual original Create dialog editor'
        assert any(
            e['kind'] == 'mouse_press'
            and e.get('confirm_contains_press')
            and e.get('dialog_name') == name
            and e.get('dialog_title') == title
            and e.get('dialog_description') == new_description
            for e in events
        ), (
            'Show ON confirms the real original form with all requested new metadata instead '
            'of a hidden backend shortcut'
        )
    elif not show_actions:
        assert not any(
            e['kind'].startswith('pointer_') or e.get('dialog_visible') for e in events
        ), (
            'Show OFF retains ordinary required unsaved-work choice while avoiding '
            'assistant-driven Create presentation'
        )
    (actor.folder / 'explicit-new-from-original-current.json').write_text(
        json.dumps(
            {
                'old_choice': old_choice,
                'mode': show_actions,
                'original_path': str(old_root),
                'current_before_new': str(current_old_root),
                'requested_new': str(destination),
                'original_byte_hashes': _new_project_file_hashes(original_bytes),
                'current_old_byte_hashes': _new_project_file_hashes(
                    _new_project_scientific_bytes(current_old_root)
                ),
                'actual_create_reply': actual_create,
                'original_selected_files': original_files,
                'task_input': inputs[0],
                'normal_save_as_qualification': (
                    'explicit ordinary API preparation only; queued native chooser continuation '
                    'not exercised'
                ),
                'workflow_qualification': (
                    'creation/choice/task-input transition only; no '
                    'fit/provider/scientific matrix '
                    'acceptance'
                ),
            },
            indent=2,
        )
    )
