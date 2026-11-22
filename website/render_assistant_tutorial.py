#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Write the Application's AI assistant tutorial from its capture.

    python website/render_assistant_tutorial.py BUNDLE --dark DARK --model NAME --result TEXT

The capture is tools/docs/assistant_tutorial.js run in the app (tools/docs/capture_assistant.sh).
Its images go to assets/gui/assistant/ with a capture.json naming the commit, the page to
application/tutorials/assistant.md, and its last frame to the AI assistant page. What the
assistant does differs from run to run, so `--result` says what this run gave.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from import_gui_captures import DOCS, figure, page, viewer  # noqa: E402
from render_app_tutorials import copy_bundle, scenes_of  # noqa: E402

COLLECTION = 'https://raw.githubusercontent.com/enhantica/edi-data/main'
FOLDER = 'assistant'
MARKER = ('<!-- assistant-result -->', '<!-- /assistant-result -->')


def shown(scene: dict, depth: int) -> str:
    return figure(scene, interactive=False).replace(
        '../assets/gui/', '../' * depth + 'assets/gui/'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--dark', type=Path, required=True)
    parser.add_argument('--model', required=True, help='the assistant model the run used')
    parser.add_argument('--result', required=True, help='what the assistant gave, one sentence')
    parser.add_argument('--date', required=True, help='the day of the run, YYYY-MM-DD')
    args = parser.parse_args()
    target = copy_bundle(args.bundle, args.dark, FOLDER)
    manifest = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))
    record = {
        'edi_build_commit': manifest['source_revision'],
        'model': args.model,
        'date': args.date,
        'result': args.result,
    }
    (target / 'capture.json').write_text(json.dumps(record, indent=1) + '\n', encoding='utf-8')
    by_id = scenes_of(target, FOLDER)
    body = [
        (
            'The app has an AI assistant built in. Give it a structure and a measured pattern '
            'and ask it to fit the structure: it asks for what the files do not say, then sets '
            'up the project and fits it in stages, as the tutorials do by hand. This page '
            'follows one run on '
            'La₀.₅Ba₀.₅CoO₃ measured on HRPT, the case of the '
            '[La₀.₅Ba₀.₅CoO₃ on HRPT](cases/pd-neut-cwl_lbco-hrpt.md) tutorial.\n'
        ),
        '## Get the two files\n',
        (
            "Download them from EasyDiffraction's collection:\n\n"
            f'- [tutorial-lbco.cif]({COLLECTION}/structures/tutorial-lbco.cif): the structure.\n'
            f'- [tutorial-hrpt.xye]({COLLECTION}/data/tutorial-hrpt.xye): the measured pattern.\n'
        ),
        '## Open and connect\n',
        (
            'The assistant needs the desktop app and a ChatGPT account (see '
            '[AI assistant](../../user-guide/ai-assistant/index.md)). Open it with the robot '
            'button in the toolbar and connect.\n'
        ),
        viewer([
            ('Panel', shown(by_id['assistant-panel'], 2)),
            ('Connect', shown(by_id['assistant-connect'], 2)),
        ]),
        '## Show actions\n',
        (
            'With **Show actions** on, the app shows each action the assistant takes as it works, '
            'on the control it uses. This run leaves it off, so the assistant works in the '
            'background and reports in the chat.\n'
        ),
        shown(by_id['assistant-ready'], 2),
        '## Ask for the fit\n',
        (
            'Attach both files with the **+** button, ask it to fit the crystal structure, and '
            'send. The app asks before it shares the project and the files.\n'
        ),
        viewer([
            ('Message', shown(by_id['assistant-ask'], 2)),
            ('Approve', shown(by_id['assistant-approve'], 2)),
        ]),
        '## Answer its question\n',
        (
            'The pattern does not say which radiation or wavelength was used, so the assistant '
            'asks. Answer, and it fits the structure.\n'
        ),
        viewer([
            ('Question', shown(by_id['assistant-question'], 2)),
            ('Fitted', shown(by_id['assistant-fitted'], 2)),
            ('Pattern', shown(by_id['assistant-result'], 2)),
        ]),
        '## What it did\n',
        (
            f'{args.result} Tried with {args.model} on {record["date"]}; another run can take '
            'other steps, so check the result against the '
            '[La₀.₅Ba₀.₅CoO₃ on HRPT](cases/pd-neut-cwl_lbco-hrpt.md) tutorial.\n'
        ),
    ]
    out = DOCS / 'application/tutorials/assistant.md'
    out.write_text(page('Fit with the AI assistant', '\n'.join(body)), encoding='utf-8')
    # The AI assistant page shows the run's result.
    assistant = DOCS / 'user-guide/ai-assistant/index.md'
    text = assistant.read_text(encoding='utf-8')
    block = (
        f'{MARKER[0]}\n'
        + shown(by_id['assistant-fitted'], 2)
        + '\nThe assistant after it fitted La₀.₅Ba₀.₅CoO₃ on HRPT '
        + '([the tutorial](../../application/tutorials/assistant.md)).\n'
        + f'{MARKER[1]}'
    )
    if MARKER[0] in text:
        text = re.sub(
            re.escape(MARKER[0]) + '.*?' + re.escape(MARKER[1]),
            lambda _: block,
            text,
            flags=re.DOTALL,
        )
    else:
        text = text.replace(
            '\n### Install and connect\n', f'\n{block}\n\n### Install and connect\n', 1
        )
    if 'template: gui.html' not in text:
        text = text.replace('---\n', '---\ntemplate: gui.html\n', 1)
    assistant.write_text(text, encoding='utf-8')
    print(out)


if __name__ == '__main__':
    main()
