// SPDX-License-Identifier: BSD-3-Clause
// Actual owner/getter observations; no replacement property model or production algorithm.
#include <QtQml/qqml.h>

#include <QAbstractTextDocumentLayout>
#include <QColor>
#include <QCoreApplication>
#include <QFont>
#include <QMetaMethod>
#include <QMetaProperty>
#include <QMetaType>
#include <QPointer>
#include <QQmlComponent>
#include <QQmlEngine>
#include <QQuickItem>
#include <QQuickTextDocument>
#include <QStringList>
#include <QTextDocument>
#include <QUrl>
#include <QVariantMap>
#include <functional>
#include <memory>
#include <stdexcept>
#include <utility>
#include <vector>

#include "assistant_markdown.hpp"
#include "assistant_view_model.hpp"
#include "block_text.hpp"
#include "experiment_view_model.hpp"
#include "generated_category.hpp"
#include "project_view_model.hpp"
#include "session.hpp"

namespace {
struct Observations {
    QStringList errors;
    QVariantList facts;
    void require(bool yes, const QString& why) {
        if (!yes) errors.append(why);
    }
    QVariantMap result() const {
        return {{"ok", errors.isEmpty()}, {"errors", errors}, {"facts", facts}};
    }
};

// Each instance listens to one REAL QMetaProperty's advertised notifier and reads its
// current getter before invoking a nested public setter. Its baseline is an observation,
// never supplied back to the owner. Legacy broad signals are deliberately separate.
class Notice final : public QObject {
    Q_OBJECT
    QPointer<QObject> owner_;
    QMetaProperty property_;
    QVariant last_;
    Observations& check_;
    QString label_;

   public:
    QVariantList values;
    std::function<void()> after;
    Notice(QObject* owner, const char* name, Observations& check, QString label)
        : owner_(owner), check_(check), label_(std::move(label)) {
        const int index = owner->metaObject()->indexOfProperty(name);
        check_.require(index >= 0, label_ + ": actual property exists");
        if (index < 0) return;
        property_ = owner->metaObject()->property(index);
        check_.require(property_.hasNotifySignal(), label_ + ": own NOTIFY exists");
        if (!property_.hasNotifySignal()) return;
        last_ = property_.read(owner);
        const auto slot = metaObject()->method(metaObject()->indexOfSlot("announced()"));
        check_.require(bool(QObject::connect(owner, property_.notifySignal(), this, slot,
                                             Qt::DirectConnection)),
                       label_ + ": connect the real notifier");
    }
    void finish() {
        if (owner_ && property_.isValid())
            check_.require(last_ == property_.read(owner_),
                           label_ + ": final changed getter was announced");
        check_.facts.append(QVariantMap{
            {"property", label_}, {"values", values}, {"ownerAlive", !owner_.isNull()}});
    }

   private slots:
    void announced() {
        if (!owner_) {
            check_.require(false, label_ + ": callback still has its owner");
            return;
        }
        const QVariant now = property_.read(owner_);
        check_.require(values.isEmpty() || now != last_,
                       label_ + ": no duplicate consecutive announcement after reentry");
        last_ = now;
        if (now.metaType().flags().testFlag(QMetaType::PointerToQObject))
            values.append(QStringLiteral("QObject@%1")
                              .arg(reinterpret_cast<quintptr>(now.value<QObject*>()), 0, 16));
        else
            values.append(now);
        if (after) after();
    }
};

class Notices {
    std::vector<std::unique_ptr<Notice>> entries_;

   public:
    Notice* add(QObject* owner, const char* property, Observations& check, const QString& label) {
        auto notice = std::make_unique<Notice>(owner, property, check, label + '.' + property);
        auto* result = notice.get();
        entries_.push_back(std::move(notice));
        return result;
    }
    qsizetype count() const {
        qsizetype total = 0;
        for (const auto& notice : entries_) total += notice->values.size();
        return total;
    }
    void finish() {
        for (const auto& notice : entries_) notice->finish();
    }
};

void dedicated(const QMetaObject& meta, const QStringList& names, Observations& check) {
    QList<int> notifySignals;
    for (const auto& name : names) {
        const int index = meta.indexOfProperty(name.toUtf8().constData());
        check.require(index >= 0, QString::fromUtf8(meta.className()) + '.' + name + ": property");
        if (index < 0) continue;
        const auto property = meta.property(index);
        check.require(property.hasNotifySignal(),
                      name + ": notifier is required, including baseline");
        if (!property.hasNotifySignal()) continue;
        check.require(property.notifySignal().name() == name.toUtf8() + "Changed",
                      name + ": declared dedicated notifier name");
        const int signal = property.notifySignalIndex();
        check.require(!notifySignals.contains(signal),
                      name + ": unrelated properties have distinct signals");
        notifySignals.append(signal);
    }
}

QString categoryText(const QString& value) {
    return "data_notice\n_metadata.title " + value + "\n_metadata.description " + value +
           "\n_first.value A\n_middle.value B\n_last.value C\n";
}
}  // namespace

class PropertyNotificationProof : public QObject {
    Q_OBJECT
    QPointer<edi_app::ExperimentViewModel> retiredExperiment_;
    QPointer<edi_app::ProjectViewModel> retiredProject_;

   public:
    using QObject::QObject;
    Q_INVOKABLE QVariantMap metadata() const {
        Observations check;
        dedicated(edi_app::GeneratedCategory::staticMetaObject,
                  {"source", "categoryId", "loop", "output", "names", "labels", "units",
                   "setByProgram", "rows"},
                  check);
        dedicated(edi_app::ExperimentViewModel::staticMetaObject,
                  {"facilityToken", "instrumentToken", "descriptionEditable"}, check);
        dedicated(
            edi_app::AssistantMarkdown::staticMetaObject,
            {"document", "editor", "source", "markdown", "textColor", "accentColor", "bodyFont",
             "monoFontFamily", "tableBorderColor", "tableShadeColor", "tableBaseColor"},
            check);
        dedicated(edi_app::BlockText::staticMetaObject, {"text", "error", "inputText", "file"},
                  check);
        dedicated(edi_app::AssistantViewModel::staticMetaObject,
                  {"sessionDraft", "contextPreview", "contextConsentIdentity",
                   "contextConsentRequired", "contextApprovalBlocked"},
                  check);
        return check.result();
    }

    Q_INVOKABLE QVariantMap category(const QString& boundary) const {
        Observations check;
        edi_app::BlockText a([] { return categoryText("A").toStdString(); }, nullptr);
        edi_app::BlockText b([] { return categoryText("B").toStdString(); }, nullptr);
        edi_app::BlockText c([] { return categoryText("C").toStdString(); }, nullptr);
        edi_app::GeneratedCategory owner;
        const bool categoryId = boundary.startsWith("id-");
        owner.setCategoryId(categoryId ? "first" : "metadata");
        owner.setSource(&a);
        check.require(
            !owner.rows().isEmpty() && owner.names().contains(categoryId ? "value" : "title"),
            "Actual initial text category has its authored column");
        Notices notices;
        for (const auto* name : {"source", "categoryId", "loop", "output", "names", "labels",
                                 "units", "setByProgram"})
            notices.add(&owner, name, check, "category");
        auto* rows = notices.add(&owner, "rows", check, "category");
        bool entered = false;
        const auto nested = [&] {
            if (entered) return;
            entered = true;
            if (categoryId)
                owner.setCategoryId("last");
            else
                owner.setSource(&c);
        };
        QObject legacyContext;
        if (boundary.endsWith("dedicated"))
            rows->after = nested;
        else
            QObject::connect(&owner, &edi_app::GeneratedCategory::changed, &legacyContext, nested);
        if (categoryId)
            owner.setCategoryId("middle");
        else
            owner.setSource(&b);
        check.require(entered, "Actual legacy/dedicated callback enters same owner C");
        const int title = owner.names().indexOf(categoryId ? "value" : "title");
        const auto row =
            owner.rows().isEmpty() ? QStringList{} : owner.rows().first().toStringList();
        check.require((categoryId ? owner.categoryId() == "last" : owner.source() == &c) &&
                          title >= 0 && title < row.size() && row[title] == "C",
                      "The real final category reads C, not an observer-supplied value");
        notices.finish();
        const auto before = notices.count();
        if (categoryId)
            owner.setCategoryId("last");
        else
            owner.setSource(&c);
        check.require(notices.count() == before, "Identical category source/id is quiet");
        return check.result();
    }

    Q_INVOKABLE QVariantMap block(bool throughError) const {
        Observations check;
        QString value = categoryText("A");
        QString file = "A.edi";
        int sourceReads = 0, fileReads = 0;
        bool refusal = false;
        edi_app::BlockText owner(
            [&] {
                ++sourceReads;
                if (refusal) throw std::runtime_error("owned writer refusal");
                return value.toStdString();
            },
            nullptr,
            [&] {
                ++fileReads;
                return file.toStdString();
            });
        check.require(owner.text() == value, "Prime the actual lazy text A");
        Notices notices;
        auto* text = notices.add(&owner, "text", check, "block");
        auto* error = notices.add(&owner, "error", check, "block");
        notices.add(&owner, "inputText", check, "block");
        notices.add(&owner, "file", check, "block");
        bool entered = false;
        (throughError ? error : text)->after = [&] {
            if (entered) return;
            entered = true;
            value = categoryText("C");
            file = "C.edi";
            refusal = false;
            owner.invalidate();
        };
        value = categoryText("B");
        file = "B.edi";
        refusal = throughError;
        owner.invalidate();
        check.require(entered && owner.text() == categoryText("C") && owner.file() == "C.edi",
                      "Nested real text/error invalidation ends at source C");
        notices.finish();
        const auto published = notices.count();
        owner.invalidate();
        check.require(notices.count() == published, "Unchanged text/input/file/error is quiet");
        int coldReads = 0;
        edi_app::BlockText cold(
            [&] {
                ++coldReads;
                return categoryText("cold").toStdString();
            },
            nullptr,
            [&] {
                ++fileReads;
                return file.toStdString();
            });
        const int beforeColdFileReads = fileReads;
        cold.invalidate();
        cold.invalidate();
        check.require(fileReads == beforeColdFileReads,
                      "Unobserved invalidation keeps the file source cold");
        check.require(coldReads == 0, "Unobserved invalidation never computes text");
        const int priorFileReads = fileReads;
        file = "D.edi";
        check.require(cold.file() == "D.edi" && fileReads == priorFileReads + 1,
                      "File getter reads the live source exactly once without caching");
        check.require(coldReads == 0 && sourceReads > 0, "File-only observation keeps text cold");
        return check.result();
    }

    Q_INVOKABLE QVariantMap markdown(QQuickItem* host, const QString& boundary) const {
        Observations check;
        auto* engine = qmlEngine(this);
        check.require(engine && host && host->window(), "Actual Qt Quick host and engine");
        if (!engine || !host || !host->window()) return check.result();
        QQmlComponent component(engine);
        component.setData(
            "import QtQuick\nTextEdit { width: 420; height: 220; wrapMode: TextEdit.Wrap }",
            QUrl("qrc:/tests/NotificationEditor.qml"));
        std::unique_ptr<QObject> editorObject(component.create());
        auto* editor = qobject_cast<QQuickItem*>(editorObject.get());
        check.require(editor != nullptr, component.errorString());
        if (!editor) return check.result();
        editor->setParentItem(host);
        auto* target = editor->property("textDocument").value<QQuickTextDocument*>();
        check.require(target && target->textDocument(), "Actual TextEdit owns its document");
        if (!target || !target->textDocument()) return check.result();
        edi_app::AssistantMarkdown owner(host);
        owner.setEditor(editor);
        owner.setDocument(target);
        owner.setMarkdown(true);
        owner.setSource("A first paragraph\n\nsecond paragraph");
        check.require(target->textDocument()->toPlainText().contains("A first"),
                      "Actual renderer populated the real document before observers attach");
        Notices notices;
        auto* source = notices.add(&owner, "source", check, "markdown");
        auto* font = notices.add(&owner, "bodyFont", check, "markdown");
        auto* accent = notices.add(&owner, "accentColor", check, "markdown");
        auto* doc = notices.add(&owner, "document", check, "markdown");
        auto* edit = notices.add(&owner, "editor", check, "markdown");
        for (const auto* name : {"markdown", "textColor", "monoFontFamily", "tableBorderColor",
                                 "tableShadeColor", "tableBaseColor"})
            notices.add(&owner, name, check, "markdown");
        bool entered = false;
        QObject callbackContext;
        if (boundary == "document-source" || boundary == "document-unrelated" ||
            boundary == "layout-source" || boundary == "document-font" ||
            boundary == "document-color") {
            QFont b = owner.bodyFont();
            b.setPixelSize(19);
            QFont c = b;
            c.setPixelSize(23);
            const auto nested = [&] {
                if (entered) return;
                entered = true;
                if (boundary == "document-unrelated")
                    owner.setAccentColor(QColor("#123456"));
                else if (boundary == "document-font")
                    owner.setBodyFont(c);
                else if (boundary == "document-color")
                    owner.setTextColor(QColor("#234567"));
                else
                    owner.setSource("C nested source");
            };
            if (boundary == "layout-source")
                QObject::connect(target->textDocument()->documentLayout(),
                                 &QAbstractTextDocumentLayout::documentSizeChanged,
                                 &callbackContext, nested);
            else
                QObject::connect(target->textDocument(), &QTextDocument::contentsChanged,
                                 &callbackContext, nested);
            if (boundary == "document-font")
                owner.setBodyFont(b);
            else if (boundary == "document-color")
                owner.setTextColor(QColor("#345678"));
            else
                owner.setSource("B outer source");
            check.require(entered, "Real QTextDocument/layout callback was exercised");
            if (boundary == "document-font")
                check.require(owner.bodyFont() == c, "Nested current font C wins");
            else if (boundary == "document-color")
                check.require(owner.textColor() == QColor("#234567"),
                              "Nested current text color C wins");
            else
                check.require(
                    owner.source() ==
                        (boundary == "document-unrelated" ? "B outer source" : "C nested source"),
                    "Source follows the actual nested public setter");
            if (boundary == "document-unrelated") {
                check.require(!source->values.isEmpty(),
                              "Unrelated accent reentry cannot suppress source notice");
                check.require(
                    owner.accentColor() == QColor("#123456") && !accent->values.isEmpty(),
                    "Unrelated accent property is also announced");
            }
        } else if (boundary == "dedicated-source") {
            source->after = [&] {
                if (entered) return;
                entered = true;
                owner.setSource("C nested source");
            };
            owner.setSource("B outer source");
            check.require(entered && owner.source() == "C nested source",
                          "Dedicated source callback reenters C");
        } else if (boundary == "dedicated-font") {
            QFont b = owner.bodyFont();
            b.setPixelSize(19);
            QFont c = b;
            c.setPixelSize(23);
            font->after = [&] {
                if (entered) return;
                entered = true;
                owner.setBodyFont(c);
            };
            owner.setBodyFont(b);
            check.require(entered && owner.bodyFont() == c, "Dedicated font callback reenters C");
        } else if (boundary == "pointer-roundtrip") {
            std::unique_ptr<QObject> secondEditorObject(component.create());
            auto* secondEditor = qobject_cast<QQuickItem*>(secondEditorObject.get());
            check.require(secondEditor != nullptr,
                          "Second actual TextEdit for pointer round trip");
            if (!secondEditor) return check.result();
            secondEditor->setParentItem(host);
            auto* secondTarget =
                secondEditor->property("textDocument").value<QQuickTextDocument*>();
            check.require(secondTarget && secondTarget->textDocument(),
                          "Second real owned document");
            if (!secondTarget || !secondTarget->textDocument()) return check.result();
            const auto roundtripConnection =
                QObject::connect(secondTarget->textDocument(), &QTextDocument::contentsChanged,
                                 &callbackContext, [&] {
                                     if (entered) return;
                                     entered = true;
                                     owner.setDocument(target);
                                     owner.setDocument(secondTarget);
                                 });
            owner.setDocument(secondTarget);
            QObject::disconnect(roundtripConnection);
            check.require(entered && owner.document() == secondTarget,
                          "Qt document callback returns to the SAME outer-requested pointer");
            entered = false;
            edit->after = [&] {
                if (entered) return;
                entered = true;
                owner.setEditor(editor);
                owner.setEditor(secondEditor);
            };
            owner.setEditor(secondEditor);
            check.require(entered && owner.editor() == secondEditor,
                          "Dedicated editor callback returns to the requested actual editor");
            edit->after = {};
            const auto docCount = doc->values.size(), editCount = edit->values.size();
            secondEditorObject.reset();
            check.require(owner.document() == nullptr && owner.editor() == nullptr,
                          "Actual document/editor destruction clears both retained properties");
            check.require(
                doc->values.size() == docCount + 1 && edit->values.size() == editCount + 1,
                "Each actual pointer lifetime transition to null is announced once");
        } else {
            check.require(false, "Closed Markdown boundary selector");
        }
        notices.finish();
        const auto before = notices.count();
        owner.setSource(owner.source());
        owner.setMarkdown(owner.markdown());
        owner.setDocument(owner.document());
        owner.setEditor(owner.editor());
        owner.setBodyFont(owner.bodyFont());
        owner.setTextColor(owner.textColor());
        owner.setAccentColor(owner.accentColor());
        owner.setMonoFontFamily(owner.monoFontFamily());
        owner.setTableBorderColor(owner.tableBorderColor());
        owner.setTableShadeColor(owner.tableShadeColor());
        owner.setTableBaseColor(owner.tableBaseColor());
        check.require(notices.count() == before,
                      "Same current scalar/font/pointer values are quiet");
        return check.result();
    }

    Q_INVOKABLE QVariantMap deletedOwner(const QString& kind, QQuickItem* host) const {
        Observations check;
        QObject callbackContext;
        if (kind == "category") {
            edi_app::BlockText a([] { return categoryText("A").toStdString(); }, nullptr);
            edi_app::BlockText b([] { return categoryText("B").toStdString(); }, nullptr);
            QPointer<edi_app::GeneratedCategory> owner = new edi_app::GeneratedCategory;
            owner->setCategoryId("metadata");
            owner->setSource(&a);
            QObject::connect(owner.data(), &edi_app::GeneratedCategory::changed, &callbackContext,
                             [&] { delete owner.data(); });
            owner->setSource(&b);
            check.require(owner.isNull(), "Actual category owner deleted at legacy boundary");
            delete owner.data();
        } else if (kind == "block") {
            QString value = categoryText("A");
            QPointer<edi_app::BlockText> owner =
                new edi_app::BlockText([&] { return value.toStdString(); }, nullptr);
            check.require(owner->text() == value, "Prime actual observed text before deletion");
            QObject::connect(owner.data(), &edi_app::BlockText::textChanged, &callbackContext,
                             [&] { delete owner.data(); });
            value = categoryText("B");
            owner->invalidate();
            check.require(owner.isNull(), "Actual BlockText owner deleted at text boundary");
            delete owner.data();
        } else if (kind == "markdown") {
            auto* engine = qmlEngine(this);
            check.require(engine && host && host->window(), "Real host for Markdown deletion");
            if (!engine || !host || !host->window()) return check.result();
            QQmlComponent component(engine);
            component.setData("import QtQuick\nTextEdit { width: 420; height: 220 }",
                              QUrl("qrc:/tests/NoticeDelete.qml"));
            std::unique_ptr<QObject> editorObject(component.create());
            auto* editor = qobject_cast<QQuickItem*>(editorObject.get());
            check.require(editor != nullptr, component.errorString());
            if (!editor) return check.result();
            editor->setParentItem(host);
            auto* target = editor->property("textDocument").value<QQuickTextDocument*>();
            check.require(target && target->textDocument(), "Real document for Markdown deletion");
            if (!target || !target->textDocument()) return check.result();
            QPointer<edi_app::AssistantMarkdown> owner = new edi_app::AssistantMarkdown(host);
            owner->setEditor(editor);
            owner->setDocument(target);
            owner->setSource("A");
            QObject::connect(target->textDocument(), &QTextDocument::contentsChanged,
                             &callbackContext, [&] { delete owner.data(); });
            owner->setSource("B");
            check.require(owner.isNull(),
                          "Actual Markdown owner deleted inside the Qt document callback");
            delete owner.data();
        } else
            check.require(false, "Closed owner deletion selector");
        return check.result();
    }

    Q_INVOKABLE bool retiredOwnerAlive() const {
        return !retiredExperiment_.isNull() || !retiredProject_.isNull();
    }

    Q_INVOKABLE QVariantMap experiment(QObject* object, QObject* sessionObject,
                                       const QString& boundary) {
        Observations check;
        auto* owner = qobject_cast<edi_app::ExperimentViewModel*>(object);
        auto* session = qobject_cast<edi_app::Session*>(sessionObject);
        check.require(owner && session && owner->descriptionEditable(),
                      "Real plain-data editable experiment");
        if (!owner || !session || !owner->descriptionEditable()) return check.result();
        QStringList facilities;
        for (int row = 0; row < owner->facilityOptions()->count(); ++row) {
            const auto token = owner->facilityOptions()->tokenAt(row);
            if (!token.isEmpty()) facilities.append(token);
        }
        check.require(facilities.size() >= 2,
                      "Two distinct declared facility choices are available");
        if (facilities.size() < 2) return check.result();
        const bool instrument = boundary.startsWith("instrument-");
        QStringList choices;
        if (instrument) {
            for (const auto& facility : facilities) {
                owner->setFacility(facility);
                choices.clear();
                for (int row = 0; row < owner->instrumentOptions()->count(); ++row) {
                    const auto token = owner->instrumentOptions()->tokenAt(row);
                    if (!token.isEmpty() && token != owner->instrumentToken())
                        choices.append(token);
                }
                if (choices.size() >= 2) break;
            }
        } else {
            owner->setFacility(QString());
            choices = facilities;
        }
        check.require(choices.size() >= 2,
                      "Two distinct declared setter choices, no invented tokens");
        if (choices.size() < 2) return check.result();
        Notices notices;
        auto* facility = notices.add(owner, "facilityToken", check, "experiment");
        auto* selectedInstrument = notices.add(owner, "instrumentToken", check, "experiment");
        notices.add(owner, "descriptionEditable", check, "experiment");
        QPointer<edi_app::ExperimentViewModel> guarded(owner);
        bool entered = false;
        QString immediateRefusal;
        QString facilityBefore, instrumentBefore, facilityAfter, instrumentAfter;
        bool detachedInside = false, stillAliveInside = false;
        const auto nested = [&] {
            if (entered) return;
            entered = true;
            if (boundary == "delete") {
                retiredExperiment_ = owner;
                retiredProject_ = session->project();
                session->closeProject();
                detachedInside = session->project() == nullptr;
                stillAliveInside = !retiredExperiment_.isNull() && !retiredProject_.isNull();
            } else {
                facilityBefore = owner->facilityToken();
                instrumentBefore = owner->instrumentToken();
                if (instrument)
                    owner->setInstrument(choices[1]);
                else
                    owner->setFacility(choices[1]);
                immediateRefusal = owner->lastError();
                facilityAfter = owner->facilityToken();
                instrumentAfter = owner->instrumentToken();
            }
        };
        QObject legacyContext;
        if (boundary.endsWith("dedicated"))
            (instrument ? selectedInstrument : facility)->after = nested;
        else if (boundary == "options")
            QObject::connect(owner->instrumentOptions(), &edi_app::OptionListModel::countChanged,
                             &legacyContext, nested);
        else
            QObject::connect(owner, &edi_app::ExperimentViewModel::descriptionChanged,
                             &legacyContext, nested);
        if (instrument)
            owner->setInstrument(choices[0]);
        else
            owner->setFacility(choices[0]);
        check.require(entered,
                      "The selected actual legacy/dedicated/options boundary was exercised");
        if (boundary == "delete") {
            check.require(
                detachedInside && stillAliveInside && guarded,
                "Session detaches and retires the protected live owner before deferred deletion");
            notices.finish();
            check.facts.append(QVariantMap{{"detachedInside", detachedInside},
                                           {"aliveInside", stillAliveInside},
                                           {"aliveAfterSetter", !guarded.isNull()}});
            // The live child still announces committed fields truthfully. The QML
            // caller observes its genuine deferred destruction after this stack unwinds.
        } else {
            check.require(!immediateRefusal.isEmpty(),
                          "The real editor refuses the attempted synchronous nested edit");
            check.require(facilityBefore == facilityAfter && instrumentBefore == instrumentAfter,
                          "A refused nested edit cannot mutate either actual selector getter");
            check.facts.append(QVariantMap{{"immediateRefusal", immediateRefusal},
                                           {"facilityBefore", facilityBefore},
                                           {"facilityAfter", facilityAfter},
                                           {"instrumentBefore", instrumentBefore},
                                           {"instrumentAfter", instrumentAfter}});
            check.require(guarded && (instrument ? owner->instrumentToken()
                                                 : owner->facilityToken()) == choices[0],
                          "The admitted outer B selection remains truthful after refusal");
            notices.finish();
            if (guarded) {
                // The publication/edit fence has now unwound: this separate ordinary
                // public call must admit C and announce its current value.
                if (instrument)
                    owner->setInstrument(choices[1]);
                else
                    owner->setFacility(choices[1]);
                check.require(owner->lastError().isEmpty(),
                              "Ordinary C selection succeeds after publication unwinds");
                check.require(
                    (instrument ? owner->instrumentToken() : owner->facilityToken()) == choices[1],
                    "The separate admitted C selection is the actual current getter");
                notices.finish();
                const auto count = notices.count();
                if (instrument)
                    owner->setInstrument(choices[1]);
                else
                    owner->setFacility(choices[1]);
                check.require(notices.count() == count, "Same current C value emits no duplicate");
            }
        }
        return check.result();
    }
};

static void registerPropertyNotificationProof() {
    qmlRegisterType<PropertyNotificationProof>("PropertyNotificationAcceptance", 1, 0,
                                               "PropertyNotificationProof");
}
Q_COREAPP_STARTUP_FUNCTION(registerPropertyNotificationProof)
#include "test_e11_t5_property_notifications.moc"
