"""Record the failed original Windows build; never manufacture a numerical reference."""

import json


def no_windows_predecessor(home):
    record = json.loads((home / 'windows-predecessor.json').read_text(encoding='utf-8'))
    assert record == {
        'kind': 'no-platform-predecessor',
        'platform': 'Windows',
        'source': '7a8eabf53084332a10b90991907d2040e5365b6a',
        'engine_source': 'b9f2267451adf1896463c706a87fea20790d28ac',
        'compiler': 'MSVC',
        'diagnostic': 'C2026',
        'translation_unit': 'embedded_data.cpp',
        'run': 43692035939,
        'evidence': 'https://github.com/enhantica/edi/actions/runs/43692035939',
    }, 'Windows predecessor absence retains the original source and actual C2026 build evidence'
    reference = home / 'tch-regression-Windows.json'
    assert not reference.exists() and not reference.is_symlink(), (
        'No Windows pre-change output exists; a fabricated reference cannot replace its absence'
    )
    return (
        'No Windows predecessor exists: original crysta b9f2267 fails MSVC C2026 in '
        'embedded_data.cpp; no Windows reference is required. Evidence: ' + record['evidence']
    )
