// A cancelled query cannot publish through an index/preparation continuation.
namespace {
QJsonObject queryOwner(const QString& source, const QStringList& spec) {
    Q_UNUSED(source);
    need(spec.size() == 5,
         "A query declares preparation/search, cancellation, completion order and old outcome");
    const auto entry = spec[1], retirement = spec[2], order = spec[3];
    const bool oldSuccess = spec[4] == "success";
    QTemporaryDir temp;
    Session session(nullptr);
    const auto originalSource = completeOwnerCollection(temp.filePath("original-source"));
    const auto id = configureOwnerCollection(session, originalSource);
    const auto freshSource = completeOwnerCollection(temp.filePath("fresh-source"));
    operationFetches.clear();
    holdOperationFetch = true;
    holdOperationIndex = true;
    struct ResetQueryTransport {
        ~ResetQueryTransport() {
            holdOperationFetch = false;
            holdOperationIndex = false;
            observingCanceledWrite = false;
        }
    } reset;
    session.onlineSources()->setUrl(id, QUrl::fromLocalFile(freshSource).toString());
    OnlineSearch search(session.onlineSources());
    search.setKind("data");
    search.setSourceId(id);
    std::vector<std::unique_ptr<QSignalSpy>> querySignals;
    const auto* meta = search.metaObject();
    for (int at = meta->methodOffset(); at < meta->methodCount(); ++at)
        if (meta->method(at).methodType() == QMetaMethod::Signal)
            querySignals.push_back(std::make_unique<QSignalSpy>(&search, meta->method(at)));
    const auto reports = [&] {
        int count = 0;
        for (const auto& signal : querySignals) count += signal->size();
        return count;
    };
    const auto state = [&] {
        return QJsonObject{{"rows", search.results()->rowCount()},
                           {"total", search.total()},
                           {"busy", search.busy()},
                           {"searched", search.searched()},
                           {"message", search.message()},
                           {"detail", search.detail()}};
    };
    if (entry == "prepare")
        search.prepare();
    else
        search.search();
    const auto older = operationFetches.size();
    need(older > 0, "The uncached real source reaches an actual held index transport");
    if (retirement == "cancel")
        need(cancelOwnedLoads(&search), "The actual query producer exposes its cancel entry");
    else if (retirement == "reset")
        search.reset();
    else {
        need(retirement == "newer", "The query retirement is an enumerated public operation");
        search.setField("name", "independent-impossible-current-name");
        search.search();
    }
    const auto afterRetirement = state();
    const int before = reports();
    operationWriteCalls = 0;
    observingCanceledWrite = true;
    const auto deliver = [&](std::size_t at, bool success) {
        if (!operationFetches[at].done) return;
        const bool exists = QFileInfo(operationFetches[at].url.toLocalFile()).isFile();
        finishOperationFetch(at, success && exists);
    };
    bool currentStayedStable = true, neverPublishedOlderRows = true;
    if (retirement == "newer" && order == "new-first" && operationFetches.size() > older) {
        for (std::size_t at = older; at < operationFetches.size(); ++at) deliver(at, true);
        const auto current = state();
        for (std::size_t at = 0; at < older; ++at) deliver(at, oldSuccess);
        currentStayedStable = state() == current;
    } else {
        for (std::size_t at = 0; at < older; ++at)
            deliver(at,
                    retirement == "newer" && operationFetches.size() == older ? true : oldSuccess);
        neverPublishedOlderRows = search.results()->rowCount() == 0;
        for (std::size_t at = older; at < operationFetches.size(); ++at) deliver(at, true);
    }
    observingCanceledWrite = false;
    return {{"reports", reports() - before},
            {"writes", operationWriteCalls.load()},
            {"stateUnchanged", state() == afterRetirement},
            {"currentStayedStable", currentStayedStable},
            {"neverPublishedOlderRows", neverPublishedOlderRows},
            {"rows", search.results()->rowCount()},
            {"searched", search.searched()},
            {"coalesced", operationFetches.size() == older}};
}
}  // namespace
