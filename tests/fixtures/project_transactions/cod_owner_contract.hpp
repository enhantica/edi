// COD count, row, identity-list and paging continuations keep the query owner.
namespace {
QByteArray independentCodRows(int first, int count) {
    QJsonArray rows;
    for (int at = first; at < first + count; ++at)
        rows.append(QJsonObject{{"file", QString::number(9100000 + at)},
                                {"commonname", "independent older row"},
                                {"formula", "- La O -"},
                                {"sg", "P 1"},
                                {"a", "5.13"},
                                {"b", "7.26"},
                                {"c", "8.92"},
                                {"alpha", "90"},
                                {"beta", "109.3"},
                                {"gamma", "90"}});
    return QJsonDocument(rows).toJson();
}
QJsonObject codOwner(const QStringList& spec) {
    need(spec.size() == 5,
         "A COD request declares its stage, retirement, outcome and reply order");
    const auto stage = spec[1], retirement = spec[2], ending = spec[3], order = spec[4];
    Session session(nullptr);
    auto* sources = session.onlineSources();
    // Configure only the injected transport's endpoint, retaining the actual
    // built-in COD identity, eligibility and query protocol.
    auto& configured = const_cast<QList<OnlineSourcesModel::Source>&>(sources->sources());
    for (auto& item : configured)
        if (item.id == "cod") item.override = item.url;
    operationFetches.clear();
    holdOperationFetch = true;
    holdOperationIndex = true;
    struct ResetCod {
        ~ResetCod() { holdOperationFetch = holdOperationIndex = false; }
    } reset;
    OnlineSearch search(sources);
    search.setKind("structure");
    search.setSourceId("cod");
    std::vector<std::unique_ptr<QSignalSpy>> querySignals;
    const auto* meta = search.metaObject();
    for (int at = meta->methodOffset(); at < meta->methodCount(); ++at)
        if (meta->method(at).methodType() == QMetaMethod::Signal)
            querySignals.push_back(std::make_unique<QSignalSpy>(&search, meta->method(at)));
    const auto reports = [&] {
        int n = 0;
        for (const auto& spy : querySignals) n += spy->size();
        return n;
    };
    const auto ids = [&] {
        QJsonArray out;
        for (int row = 0; row < search.results()->rowCount(); ++row)
            out.append(search.results()
                           ->data(search.results()->index(row, 0), OnlineResultsModel::IdRole)
                           .toString());
        return out;
    };
    const auto state = [&] {
        return QJsonObject{{"ids", ids()},
                           {"total", search.total()},
                           {"busy", search.busy()},
                           {"searched", search.searched()},
                           {"message", search.message()},
                           {"detail", search.detail()},
                           {"more", search.moreAvailable()},
                           {"chunkError", search.chunkError()}};
    };
    const auto pending = [&] {
        for (std::size_t at = 0; at < operationFetches.size(); ++at)
            if (operationFetches[at].done && operationFetches[at].url.scheme().startsWith("http"))
                return at;
        throw std::runtime_error("The actual COD stage must reach its held transport");
    };
    const auto deliver = [&](std::size_t at, const QByteArray& bytes, bool success = true) {
        auto done = std::move(operationFetches.at(at).done);
        need(bool(done), "Each actual COD transport is delivered once");
        done(success ? bytes : QByteArray(), success ? QString() : "Independent old COD refusal",
             false);
        turn();
    };
    QByteArray identities;
    for (int at = 0; at < 201; ++at) identities += QByteArray::number(9100000 + at) + '\n';
    const bool paged = stage == "list" || stage == "first-chunk" || stage == "more";
    search.setField("name", "independent old query");
    search.search();
    if (stage != "count") deliver(pending(), paged ? "201" : "2");
    if (stage == "first-chunk" || stage == "more") deliver(pending(), identities);
    if (stage == "more") {
        deliver(pending(), independentCodRows(0, 100));
        need(search.results()->rowCount() == 100,
             "The next-page witness retains its independently authored first "
             "hundred rows");
        search.loadMore();
    }
    const auto older = pending();
    const auto oldUrl = operationFetches[older].url;
    QByteArray payload = stage == "count" ? (paged ? QByteArray("201") : QByteArray("2"))
                         : stage == "list"
                             ? identities
                             : independentCodRows(stage == "more" ? 100 : 0, paged ? 100 : 2);
    if (retirement == "cancel")
        need(cancelOwnedLoads(&search), "The COD query exposes its actual cancellation entry");
    else if (retirement == "reset")
        search.reset();
    else if (retirement == "kind")
        search.setKind("data");
    else if (retirement == "source")
        search.setSourceId("easydiffraction");
    else if (retirement == "disabled")
        sources->setEnabled("cod", false);
    else if (retirement == "newer") {
        search.setField("name", "independent empty current query");
        search.search();
    } else
        need(retirement == "none", "The COD retirement is explicitly enumerated");
    const auto afterRetirement = state();
    const int beforeReports = reports();
    const auto codFetches = [&] {
        int count = 0;
        for (const auto& fetch : operationFetches)
            if (fetch.url.host() == oldUrl.host() && fetch.url.scheme().startsWith("http"))
                ++count;
        return count;
    };
    const auto beforeFetches = codFetches();
    const auto finishCurrent = [&] {
        const auto count = pending();
        need(count != older, "The newer count has its own transport continuation");
        deliver(count, "0");
        deliver(pending(), "[]");
    };
    bool currentStable = true, neverOld = true;
    if (retirement == "newer" && order == "new-first") {
        // Select the new count explicitly while the older transport stays held.
        std::size_t current = operationFetches.size();
        for (std::size_t at = older + 1; at < operationFetches.size(); ++at)
            if (operationFetches[at].done && operationFetches[at].url.scheme().startsWith("http"))
                current = at;
        need(current < operationFetches.size(),
             "The replacement query reaches its independent count request");
        deliver(current, "0");
        std::size_t rows = operationFetches.size();
        for (std::size_t at = current + 1; at < operationFetches.size(); ++at)
            if (operationFetches[at].done && operationFetches[at].url.scheme().startsWith("http"))
                rows = at;
        need(rows < operationFetches.size(),
             "The current zero-count query reaches its actual empty detail request");
        deliver(rows, "[]");
        const auto completed = state();
        deliver(older, payload, ending == "success");
        currentStable = state() == completed;
    } else {
        deliver(older, payload, ending == "success");
        neverOld = search.results()->rowCount() == 0;
        if (retirement == "newer")
            finishCurrent();
        else if (retirement == "none" && ending == "success") {
            if (stage == "count")
                deliver(pending(), independentCodRows(0, 2));
            else if (stage == "list")
                deliver(pending(), independentCodRows(0, 100));
        }
    }
    Q_UNUSED(oldUrl);
    return {{"reports", reports() - beforeReports},
            {"stateUnchanged", state() == afterRetirement},
            {"newFetches", codFetches() - beforeFetches},
            {"currentStable", currentStable},
            {"neverOld", neverOld},
            {"ids", ids()},
            {"searched", search.searched()},
            {"error", search.message()},
            {"stage", stage}};
}
}  // namespace
