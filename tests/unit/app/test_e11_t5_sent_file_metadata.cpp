// SPDX-License-Identifier: BSD-3-Clause
#include <QCoreApplication>
#include <QJSValue>
#include <QJsonArray>
#include <QJsonDocument>
#include <QLocale>
#include <QQmlComponent>
#include <QQmlContext>
#include <QQmlEngine>
#include <QQmlExpression>
#include <QQuickItem>
#include <QSignalSpy>
#include <QVariantMap>
#include <QtQml/qqml.h>
#include <QtTest/qtestcase.h>
#include <memory>
#include <stdexcept>
#include <vector>

namespace {
struct FileChecks {
    int count=0,failures=0;
    void require(bool ok,const QString& message) {
        ++count;
        if(!ok) {++failures;QTest::qFail(message.toUtf8().constData(),__FILE__,__LINE__);}
    }
    QVariantMap result() const {
        return {{"ok",failures==0},{"checks",count},{"error",QStringLiteral("%1 sent-file failures").arg(failures)}};
    }
};
QVariant observed(QObject* object,const QString& source) {
    QQmlExpression expression(QQmlEngine::contextForObject(object),object,source);
    const auto value=expression.evaluate();
    if(expression.hasError())throw std::runtime_error(expression.error().toString().toStdString());
    return value;
}
QString quote(const QString& value) {
    return QString::fromUtf8(QJsonDocument(QJsonArray{value}).toJson(QJsonDocument::Compact).mid(1).chopped(1));
}
const QString ordinary=QStringLiteral("({id:'first',name:'reference.cif',bytes:10000,textReadable:true,format:'cif'})");
QString envelope(const QString& files) {return "({type:'ediInput',files:"+files+"})";}
struct OriginalFileRow {
    QQmlContext context;
    QQmlComponent component;
    QJSValue trace;
    QSignalSpy warnings;
    std::unique_ptr<QObject> row;
    explicit OriginalFileRow(QQmlEngine* engine)
        :context(engine->rootContext()),component(engine),trace(engine->newObject()),
         warnings(engine,&QQmlEngine::warnings) {
        trace.setProperty("reads",engine->newArray());
        context.setContextProperty("inputFilesTrace",QVariant::fromValue(trace));
        component.setData("import QtQuick\nimport edi.app\nAssistantMessage { assistant: Session.assistant }\n",
                          QUrl("qrc:/tests/OriginalSentFileMetadata.qml"));
        if(component.isError())throw std::runtime_error(component.errorString().toStdString());
        row.reset(component.createWithInitialProperties({{"kind",QStringLiteral("user")},
            {"text",QString()},{"status",QStringLiteral("completed")},{"payload",QVariantMap{}},
            {"rowId",QStringLiteral("absent-test-presentation-row")},{"width",900}},&context));
        if(!row)throw std::runtime_error(component.errorString().toStdString());
    }
    void assign(const QString& source,bool captureJSON=false) {
        const auto value=observed(row.get(),"(function(){const p="+source+
            ";inputFilesTrace.payload=p;"+(captureJSON?"inputFilesTrace.before=JSON.stringify(p);":"")+
            "payload=p;return true;})()");
        if(value.metaType()!=QMetaType::fromType<bool>() || !value.toBool())
            throw std::runtime_error("Original public payload assignment did not return true");
    }
    QStringList reads() const {
        const auto values=trace.property("reads");QStringList result;
        if(!values.isArray())throw std::runtime_error("The independent metadata-access trace is not an array");
        for(quint32 i=0;i<values.property("length").toUInt();++i)result.append(values.property(i).toString());
        return result;
    }
    QList<QQuickItem*> lines(const QString& identity=QString()) const {
        auto* root=qobject_cast<QQuickItem*>(row.get());
        if(!root)throw std::runtime_error("The original sent-file observer requires its actual QuickItem root");
        QList<QQuickItem*> result,pending{root};
        while(!pending.isEmpty()) {
            auto* item=pending.takeLast();
            for(auto* child:item->childItems())pending.append(child);
            if(item!=root && item->objectName().startsWith("assistant.sentFile.") &&
                (identity.isEmpty() || item->objectName()=="assistant.sentFile."+identity))result.append(item);
        }
        return result;
    }
    void cold(FileChecks& check,const QString& prefix) const {
        check.require(observed(row.get(),"payload === inputFilesTrace.payload").toBool(),
                      prefix+"the original public payload identity remains unchanged");
        check.require(observed(row.get(),"humanDetailsSnapshot === null").toBool() &&
                      !row->property("technicalCopied").toBool(),
                      prefix+"metadata presentation neither retains human details nor reports a copy");
        const auto details=row->findChildren<QObject*>(QStringLiteral("assistant.activity.details"));
        check.require(details.size()==1 && details.front()->property("text").toString().isEmpty() &&
                      !details.front()->property("visible").toBool(),
                      prefix+"the actual collapsed full-detail field stays empty and hidden");
        const auto headers=row->findChildren<QObject*>(QStringLiteral("assistant.activity.toggle"));
        check.require(headers.size()==1 && !headers.front()->property("checked").toBool(),
                      prefix+"metadata admission does not open an activity disclosure");
    }
    void admission(FileChecks& check,const QString& name,const QString& source,int expected,bool captureJSON=false) {
        assign(source,captureJSON);const auto prefix=name+": ";
        check.require(observed(row.get(),"inputFiles.length").toInt()==expected,
                      prefix+"the original metadata admission has the literal all-or-empty count");
        if(expected>0)check.require(observed(row.get(),
            "inputFiles.every((file,index)=>file === payload.files[index])").toBool(),
            prefix+"admitted metadata retains exact member references and original order");
        if(captureJSON)check.require(observed(row.get(),"JSON.stringify(payload) === inputFilesTrace.before").toBool(),
            prefix+"original data-only metadata bytes/types are not rewritten by admission or presentation");
        cold(check,prefix);
    }
};
struct LocaleScope {
    QLocale previous;
    LocaleScope() {QLocale::setDefault(QLocale::c());}
    ~LocaleScope() {QLocale::setDefault(previous);}
};
}

class SentFileMetadataProof final : public QObject {
    Q_OBJECT
    QQmlEngine* engine_;
    static void line(FileChecks& check,OriginalFileRow& fixture,const QString& id,
                     const QString& expected,const QString& accessible,bool visible) {
        const auto matches=fixture.lines(id);
        check.require(matches.size()==1,"Each admitted original metadata record owns one exact sent-file line");
        if(matches.size()!=1)return;
        auto* item=qobject_cast<QQuickItem*>(matches.front());
        check.require(item && item->isVisible()==visible,
                      "The actual original sent-file line follows user/completed visibility");
        if(!item)return;
        QList<QQuickItem*> labels;
        for(auto* child:item->childItems())
            if(child->metaObject()->indexOfProperty("text")>=0)labels.append(child);
        check.require(labels.size()==1,"The original individual file line has one direct rendered text label");
        if(labels.size()!=1)return;
        auto* label=labels.front();
        check.require(label->property("text").toString()==expected,
                      "The visible original file label preserves literal name, decimal KB and export suffix");
        check.require(observed(label,"Accessible.name").toString()==accessible,
                      "Original sent-file accessibility names the snapshot and the same independently expected size");
        check.require(label->property("textFormat").toInt()==int(Qt::PlainText) &&
                      label->property("elide").toInt()==int(Qt::ElideMiddle),
                      "Original metadata remains plain text with middle elision rather than markup interpretation");
    }
public:
    explicit SentFileMetadataProof(QQmlEngine* engine):engine_(engine){}
    Q_INVOKABLE QVariantMap metadataAdmission() const {
        FileChecks check;
        try {
            LocaleScope locale;OriginalFileRow f(engine_);
            struct Case {QString name,payload;int count;};
            std::vector<Case> cases{
                {"empty-list",envelope("[]"),0},
                {"null-payload","null",0},{"undefined-payload","undefined",0},
                {"false-payload","false",0},{"zero-payload","0",0},{"empty-payload-string","''",0},
                {"truthy-primitive-payload","17",0},{"truthy-string-payload","'text'",0},
                {"boolean-payload","true",0},{"array-payload","[]",0},
                {"missing-type","({files:["+ordinary+"]})",0},
                {"wrong-case-type","({type:'ediinput',files:["+ordinary+"]})",0},
                {"boxed-type","({type:new String('ediInput'),files:["+ordinary+"]})",0},
                {"missing-files","({type:'ediInput'})",0},
                {"null-files",envelope("null"),0},{"false-files",envelope("false"),0},
                {"zero-files",envelope("0"),0},{"empty-files-string",envelope("''"),0},
                {"truthy-primitive-files",envelope("17"),0},
                {"nonempty-files-string",envelope("'abc'"),0},
                {"array-like-files",envelope("({0:"+ordinary+",length:1})"),1},
                {"inherited-array-like-files",envelope("Object.create({0:"+ordinary+",length:1})"),1},
                {"function-array-like-files",envelope("Object.assign(function(a){},{0:"+ordinary+"})"),1},
                {"array-payload-with-metadata","Object.assign([],"+envelope("["+ordinary+"]")+")",1},
                {"function-payload-with-metadata","Object.assign(function(){},"+envelope("["+ordinary+"]")+")",1},
                {"inherited-payload-fields","Object.create("+envelope("["+ordinary+"]")+")",1},
                {"missing-record-fields",envelope("[{}]"),0},
                {"inherited-record-fields",envelope("[Object.create("+ordinary+")]"),1},
                {"array-record-with-fields",envelope("[Object.assign([],"+ordinary+")]"),1},
                {"function-record-with-fields",envelope("[(function(){const f=function(){};Object.defineProperty(f,'name',{value:'reference.cif',writable:true,configurable:true});return Object.assign(f,"+ordinary+");})()]"),1},
                {"sparse-first-entry",envelope("[,"+ordinary+"]"),0},
                {"sparse-middle-entry",envelope("["+ordinary+",,"+ordinary+"]"),0},
                {"invalid-after-valid-is-not-partial",envelope("["+ordinary+",{id:''},"+ordinary+"]"),0},
                {"duplicates-are-not-deduplicated",envelope("["+ordinary+","+ordinary+"]"),2}
            };
            for(const auto& value:QStringList{"undefined","null","false","true","1","[]","{}"})
                cases.push_back({"wrong-payload-type-"+value,"({type:"+value+",files:["+ordinary+"]})",0});
            for(const int count:{1,6,7,31,32,33})cases.push_back({"declared-file-count-"+QString::number(count),
                envelope("Array.from({length:"+QString::number(count)+"},()=>"+ordinary+")"),count<=32?count:0});
            for(const auto& value:QStringList{"undefined","null","true","'1'","1.5","-1","NaN","Infinity","new Number(1)"})
                cases.push_back({"invalid-array-length-"+value,envelope("({0:"+ordinary+",length:"+value+"})"),0});
            cases.push_back({"negative-zero-array-length",envelope("({length:-0})"),0});
            for(const auto& value:QStringList{"null","undefined","false","true","0","''","1","'text'"})
                cases.push_back({"invalid-record-"+value,envelope("["+value+"]"),0});
            const auto field=[&](const QString& key,const QString& value) {
                return envelope("[Object.assign({},"+ordinary+",{"+key+":"+value+"})]");
            };
            for(const auto& key:QStringList{"id","name","format"}) {
                for(const auto& value:QStringList{"undefined","null","false","true","0","[]","{}","new String('text')","function(){}"})
                    cases.push_back({key+"-strict-string-"+value,field(key,value),0});
            }
            for(const auto& value:QStringList{"undefined","null","false","true","'0'","[]","{}","new Number(1)","function(){}","NaN","Infinity","-Infinity","-1","-0.25","-Number.MIN_VALUE"})
                cases.push_back({"bytes-number-finite-nonnegative-"+value,field("bytes",value),0});
            for(const auto& value:QStringList{"0","-0","0.25","1536","Number.MIN_VALUE","Number.MAX_SAFE_INTEGER","Number.MAX_VALUE"})
                cases.push_back({"admitted-numeric-bytes-"+value,field("bytes",value),1});
            for(const auto& value:QStringList{"undefined","null","0","1","''","'true'","[]","{}","new Boolean(true)","function(){}"})
                cases.push_back({"text-readable-strict-boolean-"+value,field("textReadable",value),0});
            cases.push_back({"false-text-readable-is-valid",field("textReadable","false"),1});
            for(const int length:{0,1,255,256,257})cases.push_back({"id-code-units-"+QString::number(length),
                field("id","'i'.repeat("+QString::number(length)+")"),length>0&&length<=256?1:0});
            for(const int length:{0,1,511,512,513})cases.push_back({"name-code-units-"+QString::number(length),
                field("name","'n'.repeat("+QString::number(length)+")"),length<=512?1:0});
            cases.push_back({"id-utf8-byte-count-is-not-the-limit",field("id","'é'.repeat(256)"),1});
            cases.push_back({"id-supplementary-at-limit",field("id","'🔬'.repeat(128)"),1});
            cases.push_back({"id-supplementary-over-limit",field("id","'🔬'.repeat(129)"),0});
            cases.push_back({"name-supplementary-at-limit",field("name","'🔬'.repeat(256)"),1});
            cases.push_back({"name-supplementary-over-limit",field("name","'🔬'.repeat(257)"),0});
            cases.push_back({"whitespace-id-is-not-trimmed",field("id","' '"),1});
            cases.push_back({"nul-id-is-a-string",field("id","'a\\u0000b'"),1});
            cases.push_back({"empty-format-is-valid",field("format","''"),1});
            cases.push_back({"format-has-no-declared-length-limit",field("format","'F'.repeat(4096)"),1});
            for(const auto& item:cases)f.admission(check,item.name,item.payload,item.count,true);
        }catch(const std::exception& error) {check.require(false,"Original metadata admission prerequisite: "+QString::fromUtf8(error.what()));}
        return check.result();
    }
    Q_INVOKABLE QVariantMap orderedAccessAndColdPrivacy() const {
        FileChecks check;
        const auto run=[&](const QString& name,const QString& payload,int count,const QStringList& required,
                           const QStringList& forbidden,const QString& kind=QStringLiteral("user")) {
            OriginalFileRow f(engine_);
            check.require(f.row->setProperty("kind",kind),name+": the original public row kind is established before metadata assignment");
            f.admission(check,name,payload,count);const auto reads=f.reads();
            for(const auto& field:required)check.require(reads.contains(field),name+": required original metadata field is actually read: "+field);
            for(const auto& field:forbidden)check.require(!reads.contains(field),name+": original admission never reaches the short-circuited field: "+field);
            check.require(f.warnings.isValid() && f.warnings.isEmpty(),
                          name+": untouched throwing metadata fields cause no original binding error");
        };
        try {
            const QString coldFiles="get files(){inputFilesTrace.reads.push('files');throw Error('FILES_MUST_STAY_COLD');}";
            for(const auto& kind:QStringList{"assistant","activity","plan","error","question","tool","trial","User",""})
                run("non-user-skips-files-"+kind,"({type:'ediInput',"+coldFiles+"})",0,{}, {"files"},kind);
            run("wrong-type-skips-files","({type:'other',"+coldFiles+"})",0,{}, {"files"});
            for(const auto& length:QStringList{"0","-0","33","-1","1.5","NaN","undefined","'1'","new Number(1)"})
                run("invalid-or-empty-length-skips-index-"+length,envelope("({get length(){inputFilesTrace.reads.push('length');return "+length+";},"
                    "get 0(){inputFilesTrace.reads.push('index0');throw Error('INDEX_MUST_STAY_COLD');}})"),0,{"length"},{"index0"});
            struct ShortCase {QString name,record;QStringList later;};
            const std::vector<ShortCase> shorts{
                {"invalid-id","({id:0})",{"name","bytes","textReadable","format"}},
                {"empty-id","({id:''})",{"name","bytes","textReadable","format"}},
                {"invalid-name","({id:'guarded',name:0})",{"bytes","textReadable","format"}},
                {"wrong-byte-type","({id:'guarded',name:'x',bytes:'1'})",{"textReadable","format"}},
                {"nonfinite-bytes","({id:'guarded',name:'x',bytes:NaN})",{"textReadable","format"}},
                {"negative-bytes","({id:'guarded',name:'x',bytes:-1})",{"textReadable","format"}},
                {"wrong-readable-type","({id:'guarded',name:'x',bytes:1,textReadable:0})",{"format"}}
            };
            for(const auto& item:shorts)for(const auto& later:item.later) {
                const auto payload="(function(){const f="+item.record+";Object.defineProperty(f,"+quote(later)+
                    ",{get:function(){inputFilesTrace.reads.push("+quote(later)+");throw Error('LATER_FIELD_MUST_STAY_COLD');}});"
                    "return {type:'ediInput',files:[f]};})()";
                run(item.name+"-skips-"+later,payload,0,{}, {later});
            }
            for(const int invalid:{0,1,2}) {
                const auto payload="(function(){const a=Array.from({length:"+QString::number(invalid)+"},()=>"+ordinary+");"
                    "Object.defineProperty(a,"+QString::number(invalid)+",{get:function(){inputFilesTrace.reads.push('invalid');return {id:''};}});"
                    "Object.defineProperty(a,"+QString::number(invalid+1)+",{get:function(){inputFilesTrace.reads.push('later-index');throw Error('LATER_INDEX_MUST_STAY_COLD');}});"
                    "return {type:'ediInput',files:a};})()";
                run("first-invalid-stops-array-at-"+QString::number(invalid),payload,0,{"invalid"},{"later-index"});
            }
            for(const auto& extra:QStringList{"sourceText","path","contents","hash","privatePayload"}) {
                const auto payload="(function(){const f="+ordinary+";Object.defineProperty(f,"+quote(extra)+
                    ",{get:function(){inputFilesTrace.reads.push('extra');throw Error('EXTRA_DATA_MUST_STAY_COLD');}});"
                    "return {type:'ediInput',files:[f]};})()";
                run("extra-record-data-remains-cold-"+extra,payload,1,{}, {"extra"});
            }
            for(const auto& field:QStringList{"id","name","bytes","textReadable","format"}) {
                const auto payload=envelope("[Object.assign({},"+ordinary+",{"+field+":{"
                    "toString:function(){inputFilesTrace.reads.push('coercion');throw Error('NO_METADATA_COERCION');},"
                    "valueOf:function(){inputFilesTrace.reads.push('coercion');throw Error('NO_METADATA_COERCION');}}})]");
                run("wrong-field-never-coerces-"+field,payload,0,{}, {"coercion"});
            }
            const auto payload="({type:'ediInput',files:[{"
                "get id(){inputFilesTrace.reads.push('id');return 'accessor';},"
                "get name(){inputFilesTrace.reads.push('name');return 'accessor.cif';},"
                "get bytes(){inputFilesTrace.reads.push('bytes');return 10000;},"
                "get textReadable(){inputFilesTrace.reads.push('textReadable');return true;},"
                "get format(){inputFilesTrace.reads.push('format');return 'cif';}}]})";
            run("all-required-fields-actually-consumed",payload,1,{"id","name","bytes","textReadable","format"},{});
        }catch(const std::exception& error) {check.require(false,"Original cold admission prerequisite: "+QString::fromUtf8(error.what()));}
        return check.result();
    }
    Q_INVOKABLE QVariantMap visibleFileLines() const {
        FileChecks check;
        try {
            LocaleScope locale;OriginalFileRow f(engine_);
            const QString name=QString::fromUtf8("<b>ά 🔬</b>.cif");
            f.admission(check,"visible-original-lines",envelope("[{id:'visible-a',name:"+quote(name)+
                ",bytes:10000,textReadable:true,format:'SECRET_FORMAT_ONLY'},"
                "{id:'visible-b',name:'binary.dat',bytes:1536,textReadable:false,format:'raw'},"
                "{id:'visible-c',name:'',bytes:0,textReadable:true,format:''}]"),3);
            check.require(f.lines().size()==3,"All admitted original file snapshots have individual rendered lines");
            line(check,f,"visible-a",name+" (10.0 KB)","Sent file snapshot: "+name+", 10.0 KB",true);
            line(check,f,"visible-b","binary.dat (1.5 KB) · text export required","Sent file snapshot: binary.dat, 1.5 KB",true);
            line(check,f,"visible-c"," (0.0 KB)","Sent file snapshot: , 0.0 KB",true);
            check.require(f.warnings.isValid() && f.warnings.isEmpty(),"Original safe visible metadata emits no QML binding errors");
        }catch(const std::exception& error) {check.require(false,"Original visible metadata prerequisite: "+QString::fromUtf8(error.what()));}
        return check.result();
    }
    Q_INVOKABLE QVariantMap liveUpdates() const {
        FileChecks check;
        try {
            LocaleScope locale;OriginalFileRow f(engine_);
            f.admission(check,"live-first",envelope("["+ordinary+"]"),1);
            line(check,f,"first","reference.cif (10.0 KB)","Sent file snapshot: reference.cif, 10.0 KB",true);
            for(const auto& status:QStringList{"in_progress","failed","interrupted","refused","","Completed"}) {
                check.require(f.row->setProperty("status",status),"Live status uses the original public row property");
                check.require(observed(f.row.get(),"inputFiles.length").toInt()==1,"Noncompleted user status retains admitted metadata independently of line visibility");
                line(check,f,"first","reference.cif (10.0 KB)","Sent file snapshot: reference.cif, 10.0 KB",false);
            }
            check.require(f.row->setProperty("status",QStringLiteral("completed")),"Completed status restores the original public visibility");
            line(check,f,"first","reference.cif (10.0 KB)","Sent file snapshot: reference.cif, 10.0 KB",true);
            check.require(f.row->setProperty("kind",QStringLiteral("assistant")),"Kind updates use the original public row property");
            check.require(observed(f.row.get(),"inputFiles.length").toInt()==0 && f.lines().isEmpty(),"A non-user row admits no sent-file metadata or delegates");
            f.cold(check,"live-non-user: ");
            check.require(f.row->setProperty("kind",QStringLiteral("user")),"Returning to user kind restores ordinary metadata admission");
            line(check,f,"first","reference.cif (10.0 KB)","Sent file snapshot: reference.cif, 10.0 KB",true);
            f.admission(check,"live-invalid-replaces-old",envelope("["+ordinary+",{id:''}]"),0);
            check.require(f.lines().isEmpty(),"An invalid replacement removes all old file delegates rather than retaining stale or partial lines");
            f.admission(check,"live-new-snapshot",envelope("[{id:'new',name:'new.xye',bytes:10000,textReadable:false,format:'xye'}]"),1);
            check.require(f.lines().size()==1 && f.lines(QStringLiteral("first")).isEmpty(),"A valid replacement owns only the new immutable file-line identity");
            line(check,f,"new","new.xye (10.0 KB) · text export required","Sent file snapshot: new.xye, 10.0 KB",true);
            f.admission(check,"live-wrong-payload-type","({type:'other',files:["+ordinary+"]})",0);
            check.require(f.lines().isEmpty(),"A changed payload type cannot retain the old sent-file lines");
            check.require(f.warnings.isValid() && f.warnings.isEmpty(),"Original live metadata updates emit no QML binding errors");
        }catch(const std::exception& error) {check.require(false,"Original live metadata prerequisite: "+QString::fromUtf8(error.what()));}
        return check.result();
    }
};
static void registerSentFileMetadataProof() {
    qmlRegisterSingletonType<SentFileMetadataProof>("SentFileMetadataAcceptance",1,0,"SentFileMetadataProof",
        [](QQmlEngine* engine,QJSEngine*)->QObject* {return new SentFileMetadataProof(engine);});
}
Q_COREAPP_STARTUP_FUNCTION(registerSentFileMetadataProof)
#include "test_e11_t5_sent_file_metadata.moc"
