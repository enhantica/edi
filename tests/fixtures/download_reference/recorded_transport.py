# SPDX-License-Identifier: BSD-3-Clause
"""Recorded collection replies; a caller can never escape to a real socket."""

import io
import json
import os
import socket
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse


class Response(io.BytesIO):
    status = 200

    def __init__(self, content, url):
        super().__init__(content)
        self.url = url
        self.headers = {}

    def getcode(self):
        return self.status


class Transport:
    def __init__(self, root, trace, *, dead_primary=False):
        self.root = Path(root).resolve()
        self.trace = Path(trace)
        self.dead_primary = dead_primary

    def __call__(self, request, *_args, **_kwargs):
        address = request.full_url if hasattr(request, 'full_url') else str(request)
        url = urlparse(address)
        primary = url.hostname == 'raw.githubusercontent.com'
        if primary and url.path.startswith('/enhantica/edi-data/main/'):
            relative = url.path.removeprefix('/enhantica/edi-data/main/')
            location = 'primary'
        elif url.hostname == 'data.easydiffraction.org':
            relative, location = url.path.lstrip('/'), 'mirror'
        elif url.hostname == 'enhantica.github.io' and url.path.startswith('/edi/tutorials/'):
            relative = 'tutorials/' + url.path.removeprefix('/edi/tutorials/')
            location = 'tutorials'
        else:
            raise AssertionError('A recorded download must never request an unrecorded location')
        with self.trace.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'location': location, 'path': relative}) + '\n')
        if primary and self.dead_primary:
            raise urllib.error.URLError('recorded primary outage')
        path = (self.root / unquote(relative)).resolve()
        if not path.is_relative_to(self.root) or not path.is_file():
            raise urllib.error.HTTPError(address, 404, 'recorded missing file', {}, None)
        return Response(path.read_bytes(), address)


def refuse_socket(*_args, **_kwargs):
    raise AssertionError('Recorded download witnesses must never open a real socket')


def install_from_environment():
    root = os.environ.get('EDI_REFERENCE_TRANSPORT_ROOT')
    if root:
        socket.socket.connect = refuse_socket
        socket.socket.connect_ex = refuse_socket
        urllib.request.urlopen = Transport(
            root,
            os.environ['EDI_REFERENCE_TRANSPORT_TRACE'],
            dead_primary=os.environ.get('EDI_REFERENCE_PRIMARY_OUTAGE') == '1',
        )
