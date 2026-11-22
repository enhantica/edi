// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_LOAD_ATTEMPT_HPP
#define EDI_APP_LOAD_ATTEMPT_HPP

#include <QString>
#include <QTemporaryDir>
#include <memory>

class QObject;

namespace edi_app {

// What runs on this thread for one owner (a session, a project model): a load attempt, or a refusal being announced.
// The innermost of an owner's frames decides what its failure attaches (ADR-0063).
class LoadFrame {
    friend class LoadAttempt;
    friend class RefusalAnnouncement;

   protected:
    LoadFrame(const QObject* owner, bool announcing);
    ~LoadFrame();
    LoadFrame(const LoadFrame&) = delete;
    LoadFrame& operator=(const LoadFrame&) = delete;
    static LoadFrame* innermost(const QObject* owner);
    const QObject* owner_;
    LoadFrame* outer_;
    bool announcing_;
};

// One load attempt (an Open, an example's download, a Load data, …) and the file whose reading failed in it, for the
// error report to attach. The core's record of a failed read (edi::take_failed_file) is collected into the attempt
// it happened in: one that starts inside another collects the outer's first, and what an attempt leaves is dropped
// when it ends. A report asks only its own attempt, so it never attaches another attempt's file.
class LoadAttempt : private LoadFrame {
   public:
    explicit LoadAttempt(const QObject* owner);
    ~LoadAttempt();

    // The innermost live attempt `owner` started on this thread, or null; none while one of its refusals is being
    // announced and no load started since (what a listener does then is not that load).
    static LoadAttempt* current(const QObject* owner);

    // The user's file being read now, until it has been read.
    void reading(const QString& path) { reading_ = path; }
    void read() { reading_.clear(); }
    // The file this attempt failed on: the core's record of its innermost failed read, else the file being read;
    // empty when no file is to blame or it no longer exists.
    QString failed();
    // Copies the failed file now, so cleaning up the attempt's staging cannot remove it; failed() then names the copy.
    void keep();
    // The failed file and the copy that holds it, for the report; the attempt keeps neither.
    QString release(std::unique_ptr<QTemporaryDir>& copy);

   private:
    friend class RefusalAnnouncement;
    static void absorbBelow(const LoadFrame* frame);
    void collect();
    QString reading_;
    QString recorded_;
    std::unique_ptr<QTemporaryDir> copy_;
};

// A refusal being announced, with the file it attaches, fixed as it starts: the failed file of the owner's load
// making it, none when no load does. Asked while it is announced (takeRefusedFile), it answers for this refusal
// only: a refusal a listener's own operation makes is announced inside it with its own file, and what such an
// operation records is dropped when the announcement ends.
class RefusalAnnouncement : private LoadFrame {
   public:
    explicit RefusalAnnouncement(const QObject* owner);
    ~RefusalAnnouncement();
    // The file of the refusal `owner` is announcing now; empty when none is or it no longer exists.
    static QString file(const QObject* owner);

   private:
    QString file_;
};

}  // namespace edi_app

#endif
