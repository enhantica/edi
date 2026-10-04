// SPDX-License-Identifier: BSD-3-Clause
#include "block_text.hpp"

#include <QMetaMethod>

#include <exception>

namespace edi_app {

BlockText::BlockText(Source source, QObject* parent) : QObject(parent), source_(std::move(source)) {}

QString BlockText::text() const {
    compute();
    return text_;
}

QString BlockText::error() const {
    compute();
    return error_;
}

void BlockText::invalidate() {
    valid_ = false;
    if (!isSignalConnected(QMetaMethod::fromSignal(&BlockText::textChanged)) &&
        !isSignalConnected(QMetaMethod::fromSignal(&BlockText::errorChanged))) {
        return;
    }
    const QString text = text_;
    const QString error = error_;
    compute();
    if (text_ != text) {
        emit textChanged();
    }
    if (error_ != error) {
        emit errorChanged();
    }
}

void BlockText::compute() const {
    if (valid_) {
        return;
    }
    valid_ = true;
    try {
        text_ = QString::fromStdString(source_());
        error_.clear();
    } catch (const std::exception& refusal) {
        text_.clear();
        error_ = QString::fromUtf8(refusal.what());
    }
}

}  // namespace edi_app
