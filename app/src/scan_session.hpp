// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SCAN_SESSION_HPP
#define EDI_APP_SCAN_SESSION_HPP

#include <QObject>
#include <QString>
#include <atomic>
#include <cstdint>
#include <deque>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <vector>

#include "edi/model.hpp"
#include "edi/scan.hpp"

namespace edi_app {

// A scan project's results, kept small whatever the scan's length (edi ADR-0026): the datasets (the file list), the
// checked index of `analysis/results.csv` with one small entry per dataset (rows are read at their offsets, never
// kept), the provenance of the last run (`analysis/scan-run.json`: which template produced the results, its time and
// outcome) and the extracted values of unfitted datasets, read in the background when a view shows them.
class ScanSession : public QObject {
    Q_OBJECT

   public:
    // The last run's provenance, as the app wrote it at the run's end; empty when no run of the app wrote one.
    struct Run {
        std::string identity;  // the template the latest rows came from (templateIdentity)
        double seconds = -1.0;     // the scan's total fitting time over its runs; negative: not known
        QString outcome;           // the run's outcome key (FitOutcomes)
        bool last_single = false;  // a single fit on a dataset came after the run
        bool mixed = false;        // the rows came from more than one template (a Continue after an edit)
        bool invalid = false;      // a provenance file was there but did not read as one (`error` says why)
        QString error{};
    };
    // The result files a fresh run replaces, as they were (absent: none): a series' bank rows and a Le Bail or Pawley
    // scan's intensities among them.
    struct Files {
        std::optional<std::string> results, provenance, run, skipped, experiments, intensities;
        std::string kept;  // where the taken files wait on disk until they are put back
    };

    explicit ScanSession(QObject* parent);
    ~ScanSession() override;

    // Lists the datasets and indexes the results; the refusal, if any (the index then holds no row).
    QString load(const edi::Project& project);
    // What `listing` loaded of the same project in another place, taken whole: the datasets, the index and the run.
    // Nothing is read, so a save takes the listing it read of its staged folder before it was published.
    void take(ScanSession& listing);
    /// Rebase an already loaded native staging snapshot before its tree moves.
    /// Only a data-directory path under from follows to; external paths remain.
    /// Retains snapshot as the immutable source. No read, calculation or row change.
    void relocate(std::shared_ptr<const edi::Project> snapshot, const QString& from, const QString& to);
    // Indexes the results again (after a run or an undo); the refusal, if any.
    QString reindex(const edi::Project& project, bool writing = false);
    const edi::ScanDatasets& datasets() const { return datasets_; }
    // The same listing, shared and read-only, for work off the GUI thread: a capture of it copies no file names.
    std::shared_ptr<const edi::ScanDatasets> sharedDatasets() const {
        if (!shared_datasets_ || shared_revision_ != datasets_revision_) {
            shared_datasets_ = std::make_shared<const edi::ScanDatasets>(datasets_);
            shared_revision_ = datasets_revision_;
        }
        return shared_datasets_;
    }
    const edi::ScanResultIndex& index() const { return *index_; }
    // The index as one unchanging copy, shared with readers on other threads: the session's next change to the index
    // makes its own copy first (writableIndex), so a reader never sees it change and the index is not copied per read.
    std::shared_ptr<const edi::ScanResultIndex> indexSnapshot() const { return index_; }
    int place(const std::string& file) const;
    const edi::ScanPlaces& places() const { return places_; }
    // A series' rule for its per-experiment rows, made from `project` the first time it is asked for in a load.
    const edi::SeriesBankRule& bankRule(const edi::Project& project) const;
    // What a reader of dataset `place`'s per-experiment rows checks them against (edi::series_point_check).
    edi::SeriesPointCheck pointCheck(const edi::Project& project, int place) const;
    // A row a run just appended (the event's own cells): checked against the header, indexed at the file's end.
    // The dataset's place, or -1 with the refusal in `error`; a refusal leaves the index refused (`index().error`),
    // never holding part of what was read.
    int addRow(const edi::Project& project, const std::vector<std::string>& cells, const std::string& termination,
               QString& error);
    // The cells of a dataset's row, read at its offset and checked to name that dataset; empty without a row.
    std::vector<std::string> row(const edi::Project& project, int dataset) const;
    // How the run ended on a dataset: success, maxIterations, noStep, notConverged (no reason recorded), or ""
    // without a row.
    QString outcome(int dataset) const;

    // The run provenance file.
    const Run& run() const { return run_; }
    QString writeRun(const edi::Project& project, const Run& run);
    // Results without a provenance file are taken as the template's they were opened with (kept in memory; a
    // save writes it).
    void assumeIdentity(std::string identity) { run_.identity = std::move(identity); }
    // A digest of what the template saves as (its structures, experiments and analysis): equal digests, equal
    // templates.
    static std::string templateIdentity(const edi::Project& project);
    // The same from the project's saved files (edi::project_edi_files of an uncalculated copy), made elsewhere.
    static std::string templateIdentity(const std::vector<std::pair<std::string, std::string>>& files);

    // A fresh run's start or Reset fits: reads the three result files and sets them aside, all or none; the
    // in-memory provenance goes with them. The refusal, if any; a refusal that could not put everything back says
    // where the files were kept.
    QString takeFiles(const edi::Project& project, Files& taken);
    // Prepared provenance and bounded rename ledgers precede file writes. committed
    // latches actual reversal; later cleanup cannot turn it into an unperformed Undo.
    QString putFiles(const edi::Project& project, const Files& files, bool* committed = nullptr);
    // The provenance file alone, as it is now (a single fit's Undo restores it), and put back.
    // The provenance file's bytes (absent: none) in `bytes`; false when it is there but cannot be read.
    bool runFile(const edi::Project& project, std::optional<std::string>& bytes) const;
    QString putRunFile(const edi::Project& project, const std::optional<std::string>& bytes);
    // The provenance file replaced by `bytes` (none: removed), the record it replaces first moved into its own
    // set-aside directory, `kept`, so it stays on disk. A refusal changes nothing (or says where the record was kept).
    // The swap is then committed (dropRunFile) or undone (restoreRunFile).
    QString swapRunFile(const edi::Project& project, const std::optional<std::string>& bytes, std::string& kept);
    static void dropRunFile(const std::string& kept);
    // The record a swap set aside put back in one step; a refusal leaves it in `kept` and says so.
    QString restoreRunFile(const edi::Project& project, const std::string& kept);

    // The extracted values of a dataset: its row's, or those read in the background; nullptr while unknown or
    // when the read failed (`metadataError` says why).
    const std::vector<std::string>* extracted(int dataset) const;
    // Only what this session's own reads extracted, under the rules it was listed with (source()), never a results row.
    const std::vector<std::string>* listExtracted(int dataset) const;
    const edi::Project* source() const { return source_.get(); }
    QString metadataError(int dataset) const;
    // A dataset a view shows: its extracted values are read in the background if it has none yet, with the others
    // asked for in the same turn, one read per file; `metadataLoaded` reports them. Only what is shown is read: a
    // list's rows only while a list shows them (setListShown), a pause that resumes when one shows again; the
    // template's values (`forTemplate`) whatever is shown, as a fit starts from them.
    void want(int dataset, bool forTemplate = false);
    void setListShown(bool shown);
    // Whether a list's row is in the current demand (a shown list watches it): asked again at each batch, so a row
    // scrolled away or left on a hidden list is dropped, not read (edi ADR-0102 rule 6).
    void setRowDemanded(std::function<bool(int)> demanded) { row_demanded_ = std::move(demanded); }
    void stopMetadata();

   signals:
    void metadataLoaded(int first, int last);

   private:
    // Replaces the index with a refused one saying why: no row, no count.
    void refuseIndex(const std::string& why);

    edi::ScanDatasets datasets_;
    // Raised at every change of datasets_, so sharedDatasets() copies it once per listing.
    std::uint64_t datasets_revision_ = 0;
    mutable std::shared_ptr<const edi::ScanDatasets> shared_datasets_;
    mutable std::uint64_t shared_revision_ = ~std::uint64_t{0};
    edi::ScanPlaces places_;
    // Every change goes through writableIndex.
    edi::ScanResultIndex& writableIndex();
    std::shared_ptr<edi::ScanResultIndex> index_ = std::make_shared<edi::ScanResultIndex>();
    // A series' rule for its results_experiments.csv rows (edi::SeriesBankRule), made once per load when first asked.
    mutable edi::SeriesBankRule bank_rule_;
    Run run_;
    std::vector<std::optional<std::vector<std::string>>> metadata_;
    std::unordered_map<int, QString> metadata_errors_;
    std::vector<bool> asked_;
    std::vector<bool> in_flight_;  // a row a batch is reading now: one operation per row, a want meanwhile waits for it
    std::vector<int> wanted_;           // a list's rows, read only while a list shows
    std::vector<int> template_wanted_;  // the template's, read whatever is shown
    bool list_shown_ = false;
    std::function<bool(int)> row_demanded_;
    std::deque<int> loaded_;  // the datasets holding read values, oldest first (the cache is bounded)
    bool reading_ = false;    // one background read at a time
    std::uint64_t metadata_generation_ = 0;  // bumped by every listing; a read delivers only to its own
    std::shared_ptr<const edi::Project> source_;  // what the files' extract rules are read with
    std::shared_ptr<std::atomic<bool>> metadata_stop_;
    void readWanted();
    QString readRun(const edi::Project& project);
    static QString decodeRun(const std::optional<std::string>& bytes, Run& run);
};

}  // namespace edi_app

#endif  // EDI_APP_SCAN_SESSION_HPP
