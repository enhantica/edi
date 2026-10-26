// SPDX-License-Identifier: BSD-3-Clause
// Test only the actual production synchronization methods, with an observable sink.
#include <QGuiApplication>
#include <QQuickWindow>
#include <QCoreApplication>
#include <QEvent>
#include <QTimer>
#include <QElapsedTimer>
#include <atomic>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

struct ExperimentViewModel {
    std::uint64_t generation = 19;
    std::uint64_t patternGeneration() const { return generation; }
    std::uint64_t presentedGeneration() const { return generation; }
    bool patternShown() const { return true; }
};
struct FitViewModel {
    struct Receipt { std::uint64_t token; std::string file; bool drawn; };
    std::vector<Receipt> released;
    std::vector<Receipt> presented;
    void followRendered(std::uint64_t token, const std::string& file, bool drawn) {
        released.push_back({token, file, drawn});
    }
    void followPresented(std::uint64_t token, const std::string& file) {
        presented.push_back({token, file, true});
    }
};
QQuickWindow* test_window = nullptr;
QQuickWindow* chart_window() { return test_window; }
constexpr int kRenderWaitMs = 60000;
class ProjectViewModel : public QObject {
public:
    ExperimentViewModel experiment;
    FitViewModel* fit_ = nullptr;
    int current_dataset_ = 3, projected_dataset_ = 3;
    bool scan_visible = true;
    const ExperimentViewModel* currentExperiment() const { return &experiment; }
    bool scanViewShown() const { return scan_visible; }
    int follow_index_ = -1;
    std::string follow_file_;
    std::uint64_t follow_token_ = 0, follow_before_ = 0, follow_generation_ = 0;
    bool follow_selection_ = false;
    int render_swaps_ = -1;
    std::atomic<bool> render_armed_{false}, render_synced_{false};
    // Extra handover identity fields, when declared by the production header.
    // @IDENTITY_MEMBERS@
    QTimer render_wait_;
    QMetaObject::Connection render_connection_, render_sync_connection_;
    void handFollowed(int, const std::string&, std::uint64_t);
    bool presentedFollowed() const;
    void awaitRender();
    void followRendered(bool);
};
// @PRODUCTION_METHODS@

static void require(bool condition, const char* message) {
    if (!condition) { std::cerr << "FAIL: " << message << '\n'; std::exit(1); }
}
static void frame_start(QQuickWindow& window) { window.afterAnimating(); }
static void frame_sync(QQuickWindow& window) { window.afterSynchronizing(); }
static void callbacks(ProjectViewModel& project) {
    QCoreApplication::sendPostedEvents(&project, QEvent::MetaCall);
}
int main(int argc, char** argv) {
    QGuiApplication application(argc, argv);
    QQuickWindow window;
    test_window = &window;
    ProjectViewModel project;
    FitViewModel fit;
    project.fit_ = &fit;
    const bool selection = argc > 1 && std::string(argv[1]) == "selection";
    const bool same_file = argc > 2 && std::string(argv[2]) == "same-file";
    auto hand = [&](std::uint64_t token, const std::string& file) {
        project.handFollowed(3, file, token);
        ++project.experiment.generation;
        project.follow_selection_ = selection;
        project.awaitRender();
    };
    hand(41, "frame-A");
    frame_start(window);
    frame_sync(window); // Real production connection queues A; do not deliver it yet.
    require(fit.released.empty(), "Synchronization posts, but does not synchronously release, the handover");
    require(fit.presented.size() == 1 && fit.presented[0].token == 41,
            "The frame start names exactly the first handover");
    hand(57, same_file ? "frame-A" : "frame-B");
    require(fit.released.size() == 1 && !fit.released[0].drawn && fit.released[0].token == 41,
            "Replacement retires only the old handover, without drawing it");
    callbacks(project); // Deliberately late A after replacement B, before B has a frame.
    require(fit.released.size() == 1, "A stale synchronized callback releases no replacement or successor");
    require(fit.presented.size() == 1, "A stale callback cannot count or present the replacement");
    require(project.follow_token_ == 57 && project.follow_file_ == (same_file ? "frame-A" : "frame-B"),
            "A stale callback cannot clear the replacement's identity");
    require(project.render_swaps_ > 0 && project.render_armed_.load() && project.render_wait_.isActive(),
            "The replacement keeps its frame arm and deadline after the stale callback");
    frame_start(window);
    frame_sync(window);
    callbacks(project);
    require(fit.presented.size() == 2 && fit.presented.back().token == 57,
            "The replacement is presented only at its own frame start");
    require(fit.released.size() == 2 && fit.released.back().token == 57 && fit.released.back().drawn,
            "Only the replacement's own synchronized frame releases it");
    require(project.follow_file_.empty() && !project.render_wait_.isActive(),
            "The actual completed replacement clears its handover and deadline");
    callbacks(project);
    require(fit.released.size() == 2, "Duplicate callback delivery cannot release a completed handover twice");
    std::cout << "HANDOVER_OK " << (selection ? "selection" : "pattern") << ' '
              << (same_file ? "same-file" : "different-file") << '\n';
}
