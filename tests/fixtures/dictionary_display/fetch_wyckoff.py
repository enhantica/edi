"""Fetch independent published Wyckoff witnesses with pinned content and public provenance."""

import argparse
import hashlib
import http.client
import json
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for row in json.loads((HERE / 'wyckoff_sources.json').read_text()).values():
        if 'url' not in row:
            continue
        path = HERE / row['file']
        if not args.check:
            url = urlsplit(row['url'])
            if url.scheme != 'https' or url.hostname not in {
                'raw.githubusercontent.com',
                'www.crystallography.net',
            }:
                message = 'The published fixture URL must name an admitted HTTPS source'
                raise RuntimeError(message)
            connection = http.client.HTTPSConnection(url.hostname, timeout=20)
            try:
                connection.request('GET', url.path)
                response = connection.getresponse()
                if response.status != 200:
                    message = 'The published fixture URL did not return HTTP 200'
                    raise RuntimeError(message)
                raw = response.read()
            finally:
                connection.close()
            if hashlib.sha256(raw).hexdigest() != row['sha256']:
                message = 'Published source changed; review before updating the source pin'
                raise RuntimeError(message)
            text = ''.join(
                '#$URL: ' + row['url'] + ' $\n' if line.startswith('#$URL:') else line
                for line in raw.decode().splitlines(keepends=True)
            )
            path.write_text(text)
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['fixture_sha256']:
            message = 'The pinned published Wyckoff fixture changed'
            raise RuntimeError(message)


if __name__ == '__main__':
    main()
