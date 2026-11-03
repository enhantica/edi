// SPDX-License-Identifier: BSD-3-Clause
// Independent literal-index characterization of the normal internal lookup.
// No State access, canonical setter, native authority or timing claim.
#include <QCoreApplication>
#include <QJsonArray>
#include <QJsonObject>
#include <QJsonValue>
#include <QObject>
#include <QVariantMap>
#include <QtQml/qqml.h>
#include <exception>
#include <type_traits>
#include <vector>
#include "assistant_history_lookup.hpp"

using Lookup = edi_app::detail::FirstHistoryRowLookup;
static_assert(std::is_final_v<Lookup>);
static_assert(!std::is_copy_constructible_v<Lookup>);
static_assert(!std::is_copy_assignable_v<Lookup>);
static_assert(!std::is_move_constructible_v<Lookup>);
static_assert(!std::is_move_assignable_v<Lookup>);
// A borrowing lookup must never accept an array temporary, with either
// constructor spelling. Both const and mutable lvalues remain normal inputs.
static_assert(!std::is_constructible_v<Lookup,QJsonArray&&>);
static_assert(!std::is_constructible_v<Lookup,const QJsonArray&&>);
static_assert(!std::is_constructible_v<Lookup,QJsonArray&&,bool>);
static_assert(!std::is_constructible_v<Lookup,const QJsonArray&&,bool>);
static_assert(std::is_constructible_v<Lookup,const QJsonArray&>);
static_assert(std::is_constructible_v<Lookup,const QJsonArray&,bool>);
static_assert(std::is_constructible_v<Lookup,QJsonArray&>);
static_assert(std::is_constructible_v<Lookup,QJsonArray&,bool>);

class FirstHistoryLookupProof final : public QObject {
    Q_OBJECT
    struct Query { const char* name; QJsonValue id; qsizetype expected; };
    static QVariantMap failure(const QString& message, int checks) {
        return {{"ok",false},{"error",message},{"checks",checks}};
    }
    static QVariantMap check(const QJsonArray& original, const std::vector<Query>& queries) {
        const auto unchanged=original;
        int checks=0;
        try {
            const Lookup indexed(original,true), unindexed(original,false), ordinary(original);
            for(const auto& query:queries) {
                const qsizetype actuals[]{indexed.first(query.id),unindexed.first(query.id),ordinary.first(query.id)};
                for(int mode=0;mode<3;++mode) {
                    ++checks;
                    if(actuals[mode]!=query.expected)
                        return failure(QStringLiteral("%1 mode %2: expected literal first index %3, observed %4")
                            .arg(QString::fromLatin1(query.name)).arg(mode).arg(query.expected).arg(actuals[mode]),checks);
                }
            }
            if(original!=unchanged)return failure(QStringLiteral("Lookup changed its borrowed original array"),checks);
            return {{"ok",true},{"checks",checks},{"original_unchanged",true}};
        }catch(const std::exception& error) {
            return failure(QStringLiteral("Lookup did not complete its ordinary literal query: ")+QString::fromUtf8(error.what()),checks);
        }catch(...) {return failure(QStringLiteral("Lookup failed without a standard diagnostic"),checks);}
    }
public:
    using QObject::QObject;
    Q_INVOKABLE QVariantMap literalIndices() const {
        const QString unicode=QString::fromUtf8("\xCE\xB1\xF0\x9F\x98\x80");
        const QString composed=QString::fromUtf8("\xC3\xA9");
        const QString decomposed=QStringLiteral("e\u0301");
        const QString nul=QString::fromLatin1("a\0b",3);
        // Positions are authored literally. In particular, non-object row 0
        // has an absent ID after the ORIGINAL row-to-object conversion.
        const QJsonArray rows{
            QJsonValue(7),                                      // 0 absent ID
            QJsonObject{},                                     // 1 absent again
            QJsonObject{{"id",QJsonValue(QJsonValue::Null)}},    // 2 null
            QJsonObject{{"id",false}},                          // 3 bool
            QJsonObject{{"id",true}},                           // 4 bool
            QJsonObject{{"id",0}},                              // 5 number zero
            QJsonObject{{"id",-0.0}},                           // 6 equal numeric zero
            QJsonObject{{"id",1}},                              // 7 number one
            QJsonObject{{"id",1.0}},                            // 8 equal numeric one
            QJsonObject{{"id",""}},                             // 9 empty string
            QJsonObject{{"id",""},{"purpose","later"}},         // 10 later empty duplicate
            QJsonObject{{"id","1"}},                            // 11 string, not number
            QJsonObject{{"id","0"}},                            // 12 string, not number
            QJsonObject{{"id",unicode}},                        // 13 exact supplementary spelling
            QJsonObject{{"id",unicode},{"nativeOutcome",true}},  // 14 later string duplicate
            QJsonObject{{"id",QJsonArray{"x",1}}},               // 15 array ID
            QJsonObject{{"id",QJsonObject{{"a",1},{"b",true}}}},  // 16 object ID
            QJsonObject{{"id",QJsonArray{"x",1}}},               // 17 later equal array
            QJsonObject{{"id",QJsonArray{1,true}}},              // 18 nested typed array
            QJsonObject{{"id",QJsonArray{1,1}}},                 // 19 distinct from bool element
            QJsonObject{{"id",QJsonArray{}}},                    // 20 empty array
            QJsonObject{{"id",QJsonObject{}}},                   // 21 empty object
            QJsonObject{{"id",composed}},                       // 22 normalization is not identity
            QJsonObject{{"id",decomposed}},                     // 23 distinct exact spelling
            QJsonObject{{"id",nul}},                            // 24 internal QString with NUL
            QJsonObject{{"id","a"}},                            // 25 not a truncation match
            QJsonValue(QJsonValue::Null),                       // 26 another non-object/absent ID
            QJsonArray{"not","a","row"},                        // 27 another non-object/absent ID
            QJsonObject{{"id",QJsonObject{{"b",true},{"a",1}}}}   // 28 later equal object
        };
        return check(rows,{
            {"missing is not null",QJsonValue(QJsonValue::Undefined),0},
            {"explicit null",QJsonValue(QJsonValue::Null),2},
            {"false is not zero",false,3},{"true is not one",true,4},
            {"numeric zero",0,5},{"negative zero",-0.0,5},
            {"numeric one",1,7},{"same JSON number",1.0,7},
            {"empty string first duplicate",QString(),9},
            {"string one",QStringLiteral("1"),11},{"string zero",QStringLiteral("0"),12},
            {"Unicode first duplicate",unicode,13},{"array first duplicate",QJsonArray{"x",1},15},
            {"object first duplicate",QJsonObject{{"b",true},{"a",1}},16},
            {"array bool element",QJsonArray{1,true},18},{"array numeric element",QJsonArray{1,1},19},
            {"empty array",QJsonArray{},20},{"empty object",QJsonObject{},21},
            {"composed exact string",composed,22},{"decomposed exact string",decomposed,23},
            {"embedded NUL exact",nul,24},{"short string distinct",QStringLiteral("a"),25},
            {"missing string",QStringLiteral("absent"),-1},{"missing number",2,-1},
            {"different array order",QJsonArray{1,"x"},-1},
            {"different object value",QJsonObject{{"a",1},{"b",false}},-1}
        });
    }
    Q_INVOKABLE QVariantMap emptyAndPublicationIsolation() const {
        auto empty=check({},{{"empty missing",QJsonValue(QJsonValue::Undefined),-1},
            {"empty null",QJsonValue(QJsonValue::Null),-1},{"empty string",QString(),-1},
            {"empty array",QJsonArray{},-1},{"empty object",QJsonObject{},-1}});
        if(!empty.value("ok").toBool())return empty;
        // Independent original arrays remain alive together. No publication may
        // borrow another publication's position or retain process-global authority.
        const QJsonArray first{QJsonObject{{"id","shared"},{"marker","first"}},QJsonObject{{"id","shared"},{"marker","later"}}};
        const QJsonArray second{QJsonObject{{"id","other"}},QJsonObject{{"id","shared"}}};
        const QJsonArray third{QJsonObject{{"id","other"}}};
        try {
            const Lookup a(first), b(second), c(third), plain(second,false);
            if(a.first(QStringLiteral("shared"))!=0 || b.first(QStringLiteral("shared"))!=1 ||
                c.first(QStringLiteral("shared"))!=-1 || plain.first(QStringLiteral("shared"))!=1 ||
                a.first(QStringLiteral("shared"))!=0)
                return failure(QStringLiteral("A lookup retained another live publication's ID position"),5);
            return {{"ok",true},{"empty",empty},{"publication_isolation",true}};
        }catch(...) {return failure(QStringLiteral("Ordinary separate publication lookup failed"),0);}
    }
    Q_INVOKABLE QVariantMap longPrefix() const {
        // Authored input scale only, never a CPU threshold or measured latency.
        QJsonArray rows;
        for(int i=0;i<128;++i)rows.append(QJsonObject{{"id",QStringLiteral("prefix-%1").arg(i)},
            {"payload",QJsonObject{{"opaque",QString(1024,QChar('R'))}}}});
        rows.append(QJsonObject{{"id","tail"}});                    // 128 FIRST
        rows.append(QJsonObject{{"id","tail"},{"marker","later"}}); // 129
        rows.append(QJsonObject{{"id",QJsonArray{"tail",false}}});   // 130
        rows.append(QJsonObject{{"id",QJsonArray{"tail",false}}});   // 131
        return check(rows,{{"first prefix",QStringLiteral("prefix-0"),0},
            {"last prefix",QStringLiteral("prefix-127"),127},
            {"first tail",QStringLiteral("tail"),128},
            {"typed fallback tail",QJsonArray{"tail",false},130},
            {"absent tail",QStringLiteral("prefix-128"),-1},
            {"absent undefined",QJsonValue(QJsonValue::Undefined),-1}});
    }
};
static void registerFirstHistoryLookupProof() {
    qmlRegisterSingletonType<FirstHistoryLookupProof>("HistoryLookupAcceptance",1,0,"HistoryLookupProof",
        [](QQmlEngine*,QJSEngine*) -> QObject* {return new FirstHistoryLookupProof;});
}
Q_COREAPP_STARTUP_FUNCTION(registerFirstHistoryLookupProof)
#include "test_e11_t5_first_history_row_lookup.moc"
