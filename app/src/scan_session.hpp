// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SCAN_SESSION_HPP
#define EDI_APP_SCAN_SESSION_HPP

#include <QObject>
#include <QString>
#include <atomic>
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
        QString error;
    };
    // The three result files a fresh run replaces, as they were (absent: none).
    struct Files {
        std::optional<std::string> results, provenance, run;
        std::string kept;  // where the taken files wait on disk until they are put back
    };

    explicit ScanSession(QObject* parent);
    ~ScanSession() override;

    // Lists the datasets and indexes the results; the refusal, if any (the index then holds no row).
    QString load(const edi::Project& project);
    // Indexes the results again (after a run or an undo); the refusal, if any.
    QString reindex(const edi::Project& project);
    const edi::ScanDatasets& datasets() const { return datasets_; }
    const edi::ScanResultIndex& index() const { return index_; }
    int place(const std::string& file) const;
    // A row a run just appended (the event's own cells): checked against the header, indexed at the file's end.
    // The dataset's place, or -1 with the refusal in `error`.
    int addRow(const edi::Project& project, const std::vector<std::string>& cells, const std::string& termination,
               QString& error);
    // The cells of a dataset's row, read at its offset and checked to name that dataset; empty without a row.
    std::vector<std::string> row(const edi::Project& project, int dataset) const;
    // How the run ended on a dataset: success, maxIterations, noStep, notConverged (no reason recorded), or ""
    // without a row.
    QString outcome(int dataset) const;
    // Calls `visit(dataset, value, uncertainty)` for every row's cells of one parameter column, reading the file once.
    void column(const edi::Project& project, const std::string& name,
                const std::function<void(int, double, double)>& visit) const;

    // The run provenance file.
    const Run& run() const { return run_; }
    QString writeRun(const edi::Project& project, const Run& run);
    // Results without a provenance file are taken as the template's they were opened with (kept in memory; a
    // save writes it).
    void assumeIdentity(std::string identity) { run_.identity = std::move(identity); }
    // A digest of what the template saves as (its structures, experiments and analysis): equal digests, equal
    // templates.
    static std::string templateIdentity(const edi::Project& project);

    // A fresh run's start or Reset fits: reads the three result files and sets them aside, all or none; the
    // in-memory provenance goes with them. The refusal, if any; a refusal that could not put everything back says
    // where the files were kept.
    QString takeFiles(const edi::Project& project, Files& taken);
    // Puts the three files back as they were, all or none, with the same refusal; the provenance is read again.
    QString putFiles(const edi::Project& project, const Files& files);
    // The provenance file alone, as it is now (a single fit's Undo restores it), and put back.
    std::optional<std::string> runFile(const edi::Project& project) const;
    QString putRunFile(const edi::Project& project, const std::optional<std::string>& bytes);

    // The extracted values of a dataset: its row's, or those read in the background; nullptr while unknown or
    // when the read failed (`metadataError` says why).
    const std::vector<std::string>* extracted(int dataset) const;
    QString metadataError(int dataset) const;
    // A dataset a view shows: its extracted values are read in the background if it has none yet, with the others
    // asked for in the same turn, one read per file; `metadataLoaded` reports them. Only what is shown is read.
    void want(int dataset);
    void stopMetadata();

   signals:
    void metadataLoaded(int first, int last);

   private:
    edi::ScanDatasets datasets_;
    edi::ScanPlaces places_;
    edi::ScanResultIndex index_;
    Run run_;
    std::vector<std::optional<std::vector<std::string>>> metadata_;
    std::unordered_map<int, QString> metadata_errors_;
    std::vector<bool> asked_;
    std::vector<int> wanted_;
    std::deque<int> loaded_;  // the datasets holding read values, oldest first (the cache is bounded)
    bool reading_ = false;    // one background read at a time
    std::shared_ptr<const edi::Project> source_;  // what the files' extract rules are read with
    std::shared_ptr<std::atomic<bool>> metadata_stop_;
    void readWanted();
    QString readRun(const edi::Project& project);
};

}  // namespace edi_app

#endif  // EDI_APP_SCAN_SESSION_HPP
