"""Native atomic publication and real browser serialization cannot escape observation."""

import pytest

from tests.fixtures.project_transactions import build


@pytest.mark.parametrize(
    ('platform', 'original', 'alias'),
    [
        ('linux', 'syscall', 'publication_syscall'),
        ('darwin', '_renameatx_np', '_publication_renameatx'),
    ],
)
@pytest.mark.parametrize('present', [False, True], ids=['missing', 'actual-import'])
def test_native_atomic_publication_requires_its_actual_platform_import(
    monkeypatch, tmp_path, platform, original, alias, present
):
    calls = []
    monkeypatch.setattr(build.sys, 'platform', platform)
    monkeypatch.setattr(build, 'run', lambda _: ' U ' + (original if present else 'unrelated'))
    monkeypatch.setattr(build.subprocess, 'run', lambda argv, **_kwargs: calls.append(argv))
    member = tmp_path / 'archive.o'
    if not present:
        with pytest.raises(RuntimeError, match='actual native atomic publication'):
            build.observe_native_publication(tmp_path, member)
        assert not calls, 'An unproven primitive cannot receive an observation certificate'
        return
    result = build.observe_native_publication(tmp_path, member)
    assert result == {original: alias}, (
        'The real platform publication import resolves to its typed observer'
    )
    assert calls == [
        [
            str(tmp_path / 'bin/llvm-objcopy'),
            f'--redefine-sym={original}={alias}',
            str(member),
        ]
    ], 'Only the privately extracted archive object redirects its native publication'


BROWSER = """void WebStorage::write(const QString& kind) {
#if defined(Q_OS_WASM)
    const int job = begin();
    if (kind == QStringLiteral("zip")) {
        edi_storage_stage(job, "", archive.data(), archive.size());
    } else {
        edi_storage_stage(job, path.data(), file.data(), file.size());
    }
    edi_storage_write(job);
    queueSerial(job);
#else
    native_refusal();
#endif
}
"""


@pytest.mark.parametrize('escape', ['none', 'no-method', 'no-stage', 'no-dispatch'])
def test_browser_observation_compiles_the_actual_serialization_statements(tmp_path, escape):
    source = BROWSER
    if escape == 'no-method':
        source = source.replace('WebStorage::write', 'Unrelated::write')
    elif escape == 'no-stage':
        source = source.replace('edi_storage_stage(', 'unobserved_stage(')
    elif escape == 'no-dispatch':
        source = source.replace('edi_storage_write(', 'unobserved_dispatch(')
    directory = tmp_path / 'app/src'
    directory.mkdir(parents=True)
    (directory / 'web_storage.cpp').write_text(source)
    if escape != 'none':
        with pytest.raises(RuntimeError, match='actual browser'):
            build.browser_staging_source(tmp_path)
        return
    generated = build.browser_staging_source(tmp_path)
    assert 'observed_browser_stage(job, "", archive.data(), archive.size());' in generated, (
        'Archive bytes come from the actual producer statements rather than a folder approximation'
    )
    assert 'observed_browser_stage(job, path.data(), file.data(), file.size());' in generated, (
        'Directory bytes use the exact selected paths and reads in the real serializer'
    )
    assert 'edi_storage_write(' not in generated and 'queueSerial(' not in generated, (
        'Only external staging and refusal delivery are injected at the native I/O seam'
    )
