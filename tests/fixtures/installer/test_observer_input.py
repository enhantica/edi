# SPDX-License-Identifier: BSD-3-Clause
"""Exercise the production system-observer pipe adapter with real Qt and OS handles."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = r"""
#include "test_observer_input.hpp"
#include <QCoreApplication>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>
#include <QTimer>
#include <cstdio>
#include <cstdlib>
#include <memory>

int main(int argc, char** argv) {
    QCoreApplication app(argc, argv);
    auto owner = std::make_unique<QObject>();
    QByteArray received;
    int ended = 0;
    bool active_at_end = false;
    const bool installed = edi_app::observer_input::install(*owner,
        [&](const QByteArray& bytes) { received += bytes; }, [&] {
            ++ended;
#ifdef Q_OS_WIN
            for (const auto* input : owner->findChildren<QTimer*>())
                active_at_end |= input->isActive();
#else
            for (const auto* input : owner->findChildren<QSocketNotifier*>())
                active_at_end |= input->isEnabled();
#endif
            app.quit();
        });
    if (!installed) return 2;
#ifdef Q_OS_WIN
    if (argc > 1 && QByteArray(argv[1]) == "idle") {
        auto* input = owner->findChild<QTimer*>();
        const bool invoked = QMetaObject::invokeMethod(input, "timeout", Qt::DirectConnection);
        return invoked && received.isEmpty() && ended == 0 && input->isActive() ? 0 : 3;
    }
#endif
    bool retired = false;
    bool delivered = false;
    QPointer<QObject> input;
    if (argc > 1) {
        QTimer::singleShot(0, &app, [&] {
            input = owner->children().at(0);
            QMetaObject::invokeMethod(input, [&] { delivered = true; }, Qt::QueuedConnection);
            owner.reset();
            std::fputs("receiver destroyed\n", stderr);
            QMetaObject::invokeMethod(&app, [&] {
                retired = input.isNull() && !delivered;
                std::fputs("queued delivery checked\n", stderr);
                app.quit();
            }, Qt::QueuedConnection);
        });
    }
    app.exec();
    const auto report = QJsonDocument(QJsonObject{
        {"bytes", QString::fromLatin1(received.toHex())}, {"closed", ended},
        {"active_at_end", active_at_end}, {"retired", retired}}).toJson(QJsonDocument::Compact);
    std::fwrite(report.constData(), 1, static_cast<std::size_t>(report.size()), stdout);
    std::fflush(stdout);
    // The scan-cycle observer exits after emitting its final receipt.
    if (argc > 1) std::_Exit(0);
    return 0;
}

"""


@pytest.fixture(scope='module')
def binary(tmp_path_factory):
    source = tmp_path_factory.mktemp('observer-input')
    (source / 'probe.cpp').write_text(SOURCE, encoding='utf-8')
    (source / 'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.26)\nproject(input LANGUAGES CXX)\n'
        f'include("{(ROOT / "cmake/edi_build_options.cmake").as_posix()}")\n'
        'find_package(Qt6 REQUIRED COMPONENTS Core)\n'
        'add_executable(probe probe.cpp)\n'
        'target_compile_features(probe PRIVATE cxx_std_20)\n'
        f'target_include_directories(probe PRIVATE "{(ROOT / "app/src").as_posix()}")\n'
        'target_link_libraries(probe PRIVATE Qt6::Core)\n',
        encoding='utf-8',
    )
    build = source / 'build'
    subprocess.run(
        ['cmake', '-G', 'Ninja', '-S', str(source), '-B', str(build)], check=True, timeout=30
    )
    subprocess.run(['cmake', '--build', str(build), '--parallel', '4'], check=True, timeout=30)
    return build / ('probe.exe' if os.name == 'nt' else 'probe')


def test_pipe_preserves_every_byte_and_stops_at_eof(binary):
    payload = bytes(range(256)) * 257
    result = subprocess.run(
        [str(binary)], input=payload, capture_output=True, check=True, timeout=10
    )
    report = json.loads(result.stdout)
    assert report == {
        'bytes': payload.hex(),
        'closed': 1,
        'active_at_end': False,
        'retired': False,
    }


def test_retired_receiver_cannot_consume_input_or_eof(binary):
    with subprocess.Popen(
        [str(binary), 'retire'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        process.stdin.close()
        try:
            returncode = process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
            pytest.fail(
                f'Retirement probe timed out: {process.stderr.read()!r}; '
                f'report: {process.stdout.read()!r}'
            )
        stdout = process.stdout.read()
        assert returncode == 0, process.stderr.read()
    assert json.loads(stdout) == {
        'bytes': '',
        'closed': 0,
        'active_at_end': False,
        'retired': True,
    }


def test_nonpipe_input_is_refused(binary):
    result = subprocess.run(
        [str(binary)], stdin=subprocess.DEVNULL, capture_output=True, check=False, timeout=5
    )
    assert result.returncode == 2


@pytest.mark.skipif(os.name != 'nt', reason='Only Windows polls an empty open pipe')
def test_windows_idle_pipe_never_waits_for_input_or_eof(binary):
    with subprocess.Popen([str(binary), 'idle'], stdin=subprocess.PIPE) as process:
        try:
            assert process.wait(timeout=5) == 0
        finally:
            if process.poll() is None:
                process.kill()
