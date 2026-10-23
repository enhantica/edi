"""Read display labels directly from YAML, independently of the production tables."""

import argparse
import json
from pathlib import Path

import yaml


def quote(value):
    return json.dumps(str(value), ensure_ascii=False)


def make_header(source):
    document = yaml.safe_load(source.read_text())
    items = document['parameters'] + document.get('items', [])
    groups = document.get('categories', [])
    text = (
        '// Generated from the dictionary YAML by generate_metadata.py.\n#pragma once\n'
        'struct MetadataCase { const char* uid; const char* label; '
        'const char* units; const char* tag; };\n'
        'inline constexpr MetadataCase kMetadataCases[] = {\n'
    )
    for row in items:
        tag = row['edi_names'][0] if row.get('edi_names') else row['cif_tag']
        values = [row['uid'], row['display_name'], row.get('display_units', ''), tag]
        text += '    {' + ', '.join(map(quote, values)) + '},\n'
    text += (
        '};\nstruct CategoryCase { const char* id; const char* title; '
        'const char* loop_title; const char* icon; bool loop; };\n'
    )
    text += 'inline constexpr CategoryCase kCategoryCases[] = {\n'
    for row in groups:
        values = [row['id'], row['title'], row.get('loop_title', ''), row['icon']]
        text += (
            '    {'
            + ', '.join(map(quote, values))
            + ', '
            + str(bool(row.get('loop'))).lower()
            + '},\n'
        )
    text += '};\nstruct OptionCase { const char* uid; const char* token; const char* label; };\n'
    text += 'inline constexpr OptionCase kOptionCases[] = {\n'
    for row in items:
        for option in row.get('options', []):
            text += (
                '    {'
                + ', '.join(map(quote, [row['uid'], option['token'], option['display_name']]))
                + '},\n'
            )
    return text + '};\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    Path(__file__).with_name('metadata_reference.hpp').write_text(make_header(args.source))


if __name__ == '__main__':
    main()
