// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_DEMO_DRIVER_HPP
#define EDI_APP_DEMO_DRIVER_HPP

#include <QDir>
#include <QImage>
#include <QObject>
#include <QString>
#include <QStringList>
#include <QTemporaryDir>
#include <QTimer>
#include <functional>
#include <vector>

class QQuickItem;
class QQuickWindow;

namespace edi_app {

// The scripted demo mode: clicks through the app with real mouse events on controls found by
// objectName, waits for each state to settle, and saves one image per state into <dir>. The UI test
// compares those images with the committed expected set. A step whose control is missing, hidden or
// disabled stops the run with exit code 1, naming the step.
class DemoDriver : public QObject {
    Q_OBJECT

   public:
    // `only`: run just the steps whose image name starts with it (each opens what it needs), else all.
    DemoDriver(QQuickWindow& window, const QString& output_dir, const QString& only = QString(),
               QObject* parent = nullptr);
    void start();

   private:
    // One image and the actions that lead to it, in order. An action is an objectName to click, or:
    //   key:<name>               press a key (QKeySequence spelling, e.g. key:Escape)
    //   show:<view>:<row>        scroll a list view to a row, as a user would before clicking it
    //   choose:<text>            click the open popup's entry showing <text>
    //   load-experiments:<file>  load bundled .edi files through the view-model call the file
    //                            dialog's accept makes (the dialog itself is not driven)
    //   theme:<light|dark|system>   the Preferences theme (the base's Colors.theme)
    //   platform:<light|dark>       the platform appearance "system" follows (AppState's seam; a
    //                               headless runner has none)
    //   pin-time:<timestamp>        the open project's created / last-modified time, so its Text is
    //                               reproducible
    //   scroll-to:<view>:<text>     scroll the text view's Flickable so the first line holding <text> is
    //                               its top line, as a user scrolls to it
    //   wait-fit                    wait until the open project's fit has ended (at most kFitWaitMs)
    //   capture-now                 capture this step's image a fixed time after its actions, unsettled: a
    //                               running fit's moving bar never settles
    //   resize:<width>x<height>     the window's logical size
    //   type:<text>                 type the text into the focused field
    //   expand:<group>              unfold a group, whether or not it is folded
    //   save-as:<name>              save the open project into a directory of that name in the run's
    //                               scratch directory (or at an absolute path); open-project:<name> opens one
    struct Step {
        QString image;
        QStringList actions;
    };

    void run_step();
    void next_action();
    bool perform(const QString& action);
    QQuickItem* find(const QString& object_name, bool must_be_usable);
    bool on_screen(QQuickItem* item) const;  // any part of it shown: inside the window and every clip
    bool click_item(QQuickItem* item);
    void park_pointer();
    bool click(const QString& object_name);
    void settle_then(std::function<void()> next);
    void wait_fit_then(std::function<void()> next, int waited_ms = 0);
    void fail(const QString& message);

    QQuickWindow& window_;
    QDir output_dir_;
    std::vector<Step> steps_;
    std::size_t current_ = 0;
    qsizetype action_ = 0;
    QImage previous_frame_;
    int settle_attempts_ = 0;
    QTemporaryDir loaded_files_;
};

}  // namespace edi_app

#endif  // EDI_APP_DEMO_DRIVER_HPP
