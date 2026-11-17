# SPDX-License-Identifier: BSD-3-Clause
"""Refreshing the About page avatars replaces a file only with a whole image, moved into place.

A download cut off after its signature, an HTTP error, a timeout, a page that is not an image or a
failed write keeps the committed avatar and warns; the other avatars are still refreshed. The PNG
is built here from the format's definition and the JPEG is a committed avatar, so neither comes
from the code under test.
"""

import struct
import sys
import urllib.error
import zlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'website'))
import contributors  # noqa: E402

OLD = b'old avatar bytes'


def png(height: int = 1) -> bytes:
    """A 1-pixel-wide grey PNG with one row, chunk by chunk as the PNG specification lays it out;
    a taller `height` declares rows it does not hold."""

    def chunk(kind: bytes, body: bytes) -> bytes:
        return (
            struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body))
        )

    header = struct.pack('>IIBBBBB', 1, height, 8, 0, 0, 0, 0)
    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', header)
        + chunk(b'IDAT', zlib.compress(b'\x00\x80'))
        + chunk(b'IEND', b'')
    )


def jpeg() -> bytes:
    for path in sorted(contributors.AVATARS.glob('*.png')):
        data = path.read_bytes()
        if data.startswith(b'\xff\xd8\xff'):
            return data
    pytest.skip('no committed JPEG avatar')


def setup(tmp_path: Path, *logins: str) -> list[dict[str, str]]:
    for login in logins:
        (tmp_path / f'{login}.png').write_bytes(OLD)
    return [{'name': login, 'github': login} for login in logins]


def fetching(answers: dict[str, object]):
    def fetch(url: str) -> bytes:
        answer = answers[url.rsplit('/', 1)[-1].split('.png', 1)[0]]
        if isinstance(answer, BaseException):
            raise answer
        return answer

    return fetch


@pytest.mark.parametrize('image', [png, jpeg])
def test_whole_image_replaces_and_cut_off_one_keeps(tmp_path, image):
    data = image()
    people = setup(tmp_path, 'whole', 'cut')
    warnings = contributors.refresh(
        people, tmp_path, fetching({'whole': data, 'cut': data[: len(data) // 2]})
    )
    assert (tmp_path / 'whole.png').read_bytes() == data
    assert (tmp_path / 'cut.png').read_bytes() == OLD
    assert len(warnings) == 1 and warnings[0].startswith('cut:')
    assert sorted(path.name for path in tmp_path.iterdir()) == ['cut.png', 'whole.png']


@pytest.mark.parametrize(
    'data',
    [png(height=4), bytes.fromhex('FFD8FFC00002FFDA000200FFD9')],
    ids=['png-rows-missing', 'jpeg-empty-frame'],
)
def test_well_formed_but_undecodable_is_not_an_image(tmp_path, data):
    """Review 2's counterexamples: each chunk or segment in place, yet no whole image in them."""
    assert not contributors.is_image(data)
    people = setup(tmp_path, 'odd')
    warnings = contributors.refresh(people, tmp_path, fetching({'odd': data}))
    assert (tmp_path / 'odd.png').read_bytes() == OLD
    assert len(warnings) == 1


def test_signed_header_alone_is_not_an_image():
    assert not contributors.is_image(png()[:40])
    assert not contributors.is_image(b'\x89PNG\r\n\x1a\n' + b'\x00' * 200)
    assert not contributors.is_image(b'\xff\xd8\xff' + b'\x00' * 200)


@pytest.mark.parametrize(
    'failure',
    [
        urllib.error.HTTPError('https://github.com/x.png', 404, 'Not Found', None, None),
        TimeoutError('timed out'),
        b'<!DOCTYPE html><html>not an avatar</html>' * 4,
    ],
    ids=['http-error', 'timeout', 'not-an-image'],
)
def test_failed_download_keeps_the_avatar_and_refreshes_the_rest(tmp_path, failure):
    people = setup(tmp_path, 'broken', 'fine')
    warnings = contributors.refresh(people, tmp_path, fetching({'broken': failure, 'fine': png()}))
    assert (tmp_path / 'broken.png').read_bytes() == OLD
    assert (tmp_path / 'fine.png').read_bytes() == png()
    assert len(warnings) == 1 and warnings[0].startswith('broken:')


def test_failed_replace_keeps_the_avatar_whole(tmp_path, monkeypatch):
    people = setup(tmp_path, 'locked')

    def refuse(*_):
        raise PermissionError('read-only folder')

    monkeypatch.setattr(Path, 'replace', refuse)
    warnings = contributors.refresh(people, tmp_path, fetching({'locked': png()}))
    assert (tmp_path / 'locked.png').read_bytes() == OLD
    assert len(warnings) == 1 and 'could not be written' in warnings[0]
    assert [path.name for path in tmp_path.iterdir()] == ['locked.png']


def test_unchanged_avatar_is_not_written(tmp_path, monkeypatch):
    (tmp_path / 'same.png').write_bytes(png())
    written = []
    monkeypatch.setattr(contributors, 'replace_file', lambda target, _data: written.append(target))
    warnings = contributors.refresh(
        [{'name': 'same', 'github': 'same'}], tmp_path, fetching({'same': png()})
    )
    assert warnings == [] and written == []
