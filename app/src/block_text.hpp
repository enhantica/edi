// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_BLOCK_TEXT_HPP
#define EDI_APP_BLOCK_TEXT_HPP

#include <QObject>
#include <QString>
#include <QtQml/qqmlregistration.h>
#include <functional>
#include <string>

namespace edi_app {

// A block's `.edi` text: what a save writes, from the core's block_edi_text. Computed on the first
// read, so a Text tab nobody opened costs nothing; a writer refusal is shown as `error`, never as
// an empty or stale text.
class BlockText : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("A BlockText belongs to a block")
    Q_PROPERTY(QString text READ text NOTIFY textChanged)
    Q_PROPERTY(QString error READ error NOTIFY errorChanged)

   public:
    using Source = std::function<std::string()>;  // throws the writer's refusal
    BlockText(Source source, QObject* parent);

    QString text() const;
    QString error() const;
    // The project changed. Nobody shows the text: the next read computes it. A Text tab shows it:
    // recompute now and signal only the value that changed, so an edit in another block leaves
    // this one's readers alone.
    void invalidate();

   signals:
    void textChanged();
    void errorChanged();

   private:
    void compute() const;

    Source source_;
    mutable bool valid_ = false;
    mutable QString text_;
    mutable QString error_;
};

}  // namespace edi_app

#endif  // EDI_APP_BLOCK_TEXT_HPP
