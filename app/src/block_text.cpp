// SPDX-License-Identifier: BSD-3-Clause
#include "block_text.hpp"

#include <QMetaMethod>
#include <QPointer>

#include <exception>

#include "edi/display.hpp"

namespace edi_app {

BlockText::BlockText(Source source, QObject* parent, File file)
    : QObject(parent), source_(std::move(source)), file_(std::move(file)) {}

QString BlockText::file() const {
    const QPointer<const BlockText> receiver(this);
    const auto publication = notification_publication_;
    const QString value = file_ ? QString::fromStdString(file_()) : QString();
    if (receiver && notification_publication_ == publication && !observed_file_) observed_file_ = value;
    return value;
}

QString BlockText::inputText() const {
    const QPointer<const BlockText> receiver(this);
    const auto publication = notification_publication_;
    compute();
    const QString value = error_.isEmpty() ? QString::fromStdString(edi::input_categories_text(text_.toStdString())) : QString();
    if (receiver && notification_publication_ == publication && !observed_input_) observed_input_ = value;
    return value;
}

QString BlockText::withOutputs(const QString& edited) const {
    compute();
    return QString::fromStdString(edi::with_output_categories(edited.toStdString(), text_.toStdString()));
}

QString BlockText::text() const {
    compute();
    return text_;
}

QString BlockText::error() const {
    compute();
    return error_;
}

void BlockText::invalidate() {
    const QPointer<BlockText> receiver(this);
    quint64 publication = ++notification_publication_;
    const auto current = [&] { return receiver && receiver->notification_publication_ == publication; };
    const bool watchFile = isSignalConnected(QMetaMethod::fromSignal(&BlockText::fileChanged));
    const bool watchInput = isSignalConnected(QMetaMethod::fromSignal(&BlockText::inputTextChanged));
    valid_ = false;
    const bool watchText = isSignalConnected(QMetaMethod::fromSignal(&BlockText::textChanged));
    const bool watchError = isSignalConnected(QMetaMethod::fromSignal(&BlockText::errorChanged));
    if (!watchFile && !watchInput && !watchText && !watchError) return;
    const QString text = text_;
    const QString error = error_;
    if (watchText || watchError || watchInput) {
        compute();
        if (!receiver) return;
        // The original computation may itself reenter before committing its result.
        publication = ++notification_publication_;
    }
    if (text_ != text) emit textChanged();
    if (!current()) return;
    if (error_ != error) emit errorChanged();
    if (!current()) return;
    if (watchInput) {
        const auto previous = observed_input_;
        const QString next = inputText();
        if (!current()) return;
        if (!previous || *previous != next) {
            observed_input_ = next;
            emit inputTextChanged();
        }
    }
    if (!current()) return;
    if (watchFile) {
        const auto previous = observed_file_;
        const QString next = file();
        if (!current()) return;
        if (!previous || next != *previous) {
            observed_file_ = next;
            emit fileChanged();
        }
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
