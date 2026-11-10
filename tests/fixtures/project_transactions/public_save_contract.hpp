// An arbitrary caller cannot reuse a pending operation through the legacy delegate.
extern "C" bool transaction_public_save_to(edi_app::ProjectViewModel*, const QString&, bool, bool,
                                           QString*);
namespace {
QJsonObject publicSaveBoundary(const QString& source, const QStringList& spec) {
    need(spec.size() == 3, "The unowned delegate declares its include choice and tree scope");
    SavePolicyInput input(source, "linked");
    auto& session = input.session;
    session.project()->setIncludeDataOnSave("ask");
    PolicyQuestions questions(session);
    session.saveProjectAs(QUrl::fromLocalFile(input.temp.filePath("owned-request")), false, false);
    need(questions.count() == 1,
         "The owned operation is really pending its independent data decision");
    const auto before = image(input.temp.path(), true);
    const auto writes = nativeSaveAttempts.load();
    QSignalSpy refused(session.project(), &ProjectViewModel::refused);
    QString error;
    const bool available =
        transaction_public_save_to(session.project(), input.temp.filePath("unowned-request"),
                                   spec[1] == "include", spec[2] == "whole", &error);
    return {{"available", available},
            {"refused", !error.isEmpty() || !refused.isEmpty() || !session.lastError().isEmpty()},
            {"writes", nativeSaveAttempts.load() - writes},
            {"unchanged", image(input.temp.path(), true) == before},
            {"questions", questions.count()}};
}
}  // namespace
