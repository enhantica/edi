// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_USER_ACTION_LOG_HPP
#define EDI_APP_USER_ACTION_LOG_HPP

#include <QObject>
#include <QPointer>
#include <QString>

class QQuickItem;
class QQuickWindow;

namespace edi_app {

// Writes one Info line to the run log for each thing the user does with a control (edi ADR-0062): a button or tab
// clicked, a choice made in a combo box, a check box changed, a field's value committed. One application event
// filter does it for every control, the base's and the app's alike: when a control is pressed, or takes the keyboard
// focus, it waits for that control's own signal, so a press that does nothing writes nothing. A line names the
// control by its objectName, else by its type and page; a choice is written, and the number of a field made for a
// number; free text never is, whatever it reads.
class UserActionLog : public QObject {
    Q_OBJECT

   public:
    // Installs the one filter on the application, once.
    static void install();

    // The line's name for `control`: its objectName, else "<type>@<page>".
    static QString nameOf(const QQuickItem* control);

   protected:
    bool eventFilter(QObject* watched, QEvent* event) override;

   private:
    explicit UserActionLog(QObject* parent);
    void watchWindow(QQuickWindow* window);
    // Waits for `control`'s action and writes its line then.
    void await(QQuickItem* control);
    void focusChanged(QQuickWindow* window);

    QPointer<QObject> waiting_;
};

}  // namespace edi_app

#endif
