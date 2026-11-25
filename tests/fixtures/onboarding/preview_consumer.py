"""Run the attributed preview consumer with the native popup and WebP interfaces."""

import ctypes
import re
import struct
from decimal import Decimal
from pathlib import Path

from tests.fixtures.tutorial_cases.screenshots import PNG, webp_library

WAVELENGTH = 'instrument.setup_wavelength'
POPUP_FILL = f'fill:{WAVELENGTH}.menu.popup.value='
WAVELENGTH_SCENE = '09-wavelength'


def image_dimensions(path):
    data = path.read_bytes()
    if data.startswith(PNG) and len(data) >= 24:
        return list(struct.unpack('>II', data[16:24]))
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        width, height = ctypes.c_int(), ctypes.c_int()
        if webp_library().WebPGetInfo(data, len(data), ctypes.byref(width), ctypes.byref(height)):
            return [width.value, height.value]
    raise ValueError('Invalid walkthrough image')


def preview_oracle():
    # Keep the attributed consumer bytes intact. Update only its editor and image format
    # interfaces, and let the unchanged checks read the actual bundle and its hashes.
    path = Path(__file__).with_name('preview_gui_capture.txt')
    source = path.read_text(encoding='utf-8')
    replacements = (
        (
            "            'fill:instrument.setup_wavelength=',",
            '\n'.join(
                f'            {action!r},' for action in (WAVELENGTH, POPUP_FILL, 'key:Return')
            ),
        ),
        (
            (
                '        header = image.read_bytes()[:24]\n'
                "        require(header[:8] == b'\\x89PNG\\r\\n\\x1a\\n' and len(header) == 24, "
                "'Invalid PNG')\n"
                "        pixels = list(struct.unpack('>II', header[16:24]))"
            ),
            '        pixels = image_dimensions(image)',
        ),
    )
    for previous, current in replacements:
        if source.count(previous) != 1:
            raise ValueError(
                'The attributed preview consumer no longer has its expected interface'
            )
        source = source.replace(previous, current)
    scope = {'__name__': __name__, 'image_dimensions': image_dimensions}
    exec(compile(source, str(path), 'exec'), scope)  # noqa: S102 - committed attributed consumer
    return scope['validate_bundle'], scope['local_file']


validate_preview, local_file = preview_oracle()


def edi_wavelength(path):
    values = re.findall(
        r'^_instrument\.setup_wavelength[ \t]+([0-9]+(?:\.[0-9]+)?)[ \t]*$',
        path.read_text(encoding='utf-8'),
        re.MULTILINE,
    )
    if len(values) != 1:
        raise ValueError('The experiment must declare one unambiguous wavelength')
    return Decimal(values[0])


def validate_wavelength_commit(root, manifest, scenes):
    experiment = local_file(root, manifest['inputs']['experiment']['file'])
    expected = edi_wavelength(experiment)
    events = manifest['actions']
    records = [event['action'] for event in events if event['scene'] == WAVELENGTH_SCENE]
    clicks = [index for index, action in enumerate(records) if action == WAVELENGTH]
    expected_edit = [WAVELENGTH, POPUP_FILL + str(expected), 'key:Return']
    if (
        len(clicks) != 1
        or records[clicks[0] : clicks[0] + len(expected_edit)] != expected_edit
        or sum(event['action'].startswith(POPUP_FILL) for event in events) != 1
        or any(event['action'].startswith(f'fill:{WAVELENGTH}=') for event in events)
    ):
        raise ValueError(
            'The wavelength scene must open the popup, replace the value and press Return'
        )

    scene = next((scene for scene in scenes if scene['id'] == WAVELENGTH_SCENE), None)
    observed = scene['layout']['items'][WAVELENGTH].get('label') if scene else None
    if observed != str(expected):
        raise ValueError('The closed wavelength field must display the committed replacement')

    checkpoint = local_file(root, 'checkpoints/starting/experiments/' + experiment.name)
    if edi_wavelength(checkpoint) != expected:
        raise ValueError('The starting project must persist the committed wavelength')


def validate_bundle(root, *, workflow='creation'):
    manifest, scenes = validate_preview(root, workflow=workflow)
    if workflow == 'creation' and 'data' in manifest['inputs']:
        validate_wavelength_commit(root, manifest, scenes)
    return manifest, scenes
