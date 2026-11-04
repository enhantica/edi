// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QByteArray>
#include <QObject>
#include <QString>
#include <QUrl>

#include <functional>

class QNetworkAccessManager;

namespace edi_app {

/// A fetch's outcome: the bytes, else an error and whether the host or file could not be reached at all (as
/// opposed to answering with a refusal), which is what offers an alternative source (ADR-0068).
using FetchDone = std::function<void(const QByteArray& bytes, const QString& error, bool unreachable)>;

/// Read `url`: a local file or folder path on the next event-loop turn (so every source has one asynchronous
/// shape), or http(s) through `manager`, created on first use under `owner`. A missing local file counts as
/// unreachable, the offline stand-in for a host that does not answer.
void fetch_url(QObject* owner, QNetworkAccessManager*& manager, const QUrl& url, FetchDone done);

/// `base` joined with a relative `path`: a URL stays a URL, a bare folder becomes a file URL.
QUrl joined_url(const QString& base, const QString& path);

/// Why `bytes` is not the file the index describes: a size other than `expected_bytes` (when not negative) or a
/// SHA-256 other than `sha256` (when given). Empty when the content agrees or the index states neither.
QString content_problem(const QByteArray& bytes, long long expected_bytes, const QString& sha256, const QString& name);

}  // namespace edi_app
