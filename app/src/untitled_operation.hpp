// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QPointer>
#include <QString>

#include <cstdint>
#include <functional>
#include <memory>
#include <optional>

namespace edi_app {

class ProjectViewModel;

// Naming and first saving of an untitled project, from the Create dialog to the written project (ADR-0100). One
// operation carries one request: who asked (`origin`), what waits for the result (`continuation`), what the dialog
// gave (`form`), where it goes (`destination`) and how far it got (`state`). Every callback holds the operation and
// its `id`, never a flag of the session, so an answer for an older request changes nothing.
class UntitledOperation {
   public:
    enum class Origin { ManualCreate, Save, GuardSave, AssistantCreate };
    enum class State { Asking, Replanning, Writing, Saved, Refused, Rejected, Superseded };

    struct Form {
        QString name, description, title, authors;
        QString location;  // empty: the browser
    };
    // Where the project goes once the dialog is accepted. In the browser a stage key of its own; on the desktop a
    // path, fresh or a Replace of the folder whose identity (device and inode of the folder and of its project.edi)
    // was read when the user confirmed it.
    struct FileIdentity {
        std::uint64_t device = 0, inode = 0;
        bool operator==(const FileIdentity&) const = default;
    };
    struct Destination {
        QString stage;  // browser
        QString path;   // desktop
        bool replace = false;
        bool zip = false;  // desktop: a .zip at `path` (a Save as of untitled work), never a Replace
        FileIdentity folder, file;
    };

    UntitledOperation(std::uint64_t id, ProjectViewModel* owner, std::uint64_t replacement, Origin origin,
                      std::function<void()> continuation = {});

    std::uint64_t id() const { return id_; }
    ProjectViewModel* owner() const { return owner_.data(); }
    std::uint64_t replacement() const { return replacement_; }
    Origin origin() const { return origin_; }
    State state() const { return state_; }
    bool settled() const { return state_ >= State::Saved; }
    // From `superseding` on the operation runs no continuation and writes no session state.
    bool superseding() const { return superseding_; }
    void markSuperseding() { superseding_ = true; }

    Form form;
    Destination destination;
    // What waits for a guard Save (Close, Quit, Replace, Open): a second request is this one only for the same action.
    QString action;
    // The browser's untitled place this operation's first save replaces.
    QString untitledKey;

    // Moves an open operation on; false when it is settled (nothing changes then).
    bool advance(State next);
    // Settles it once: true for the call that settled it, false when it was settled already.
    bool settle(State terminal);
    // The waiting action, taken once: empty after the first call.
    std::function<void()> takeContinuation();

    // A file's identity on the disk (device and inode, or volume and file index), which a rename keeps; read from the
    // entry itself, a link not followed. None when it cannot be read.
    static std::optional<FileIdentity> identity(const QString& path);

    static QString name(State state);
    static QString name(Origin origin);

   private:
    std::uint64_t id_;
    QPointer<ProjectViewModel> owner_;
    std::uint64_t replacement_;
    Origin origin_;
    State state_ = State::Asking;
    bool superseding_ = false;
    std::function<void()> continuation_;
};

}  // namespace edi_app
