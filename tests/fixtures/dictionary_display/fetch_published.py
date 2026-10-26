"""Fetch pinned published CIFs while keeping their public source URLs."""

import argparse
import hashlib
import http.client
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((HERE / 'published_sources.json').read_text())
    for code, source in manifest.items():
        target = HERE / ('published_cod_' + code + '.cif')
        if not args.check:
            connection = http.client.HTTPSConnection('www.crystallography.net', timeout=20)
            try:
                connection.request('GET', '/cod/' + code + '.cif')
                response = connection.getresponse()
                if response.status != 200:
                    message = 'The published CIF source did not return HTTP 200'
                    raise RuntimeError(message)
                raw = response.read()
            finally:
                connection.close()
            if hashlib.sha256(raw).hexdigest() != source['raw_sha256']:
                message = (
                    'The published source changed; review its provenance before updating the pin'
                )
                raise RuntimeError(message)
            text = raw.decode()
            text = ''.join(
                '#$URL: ' + source['url'] + ' $\n' if line.startswith('#$URL:') else line
                for line in text.splitlines(keepends=True)
            )
            target.write_text(text)
        if hashlib.sha256(target.read_bytes()).hexdigest() != source['fixture_sha256']:
            message = 'The pinned published fixture changed'
            raise RuntimeError(message)


if __name__ == '__main__':
    main()
