// SPDX-License-Identifier: BSD-3-Clause
#include "assistant_skill_import.hpp"
#ifndef __EMSCRIPTEN__
#include "connection_services.hpp"
#include "edi/assistant_limits.hpp"
#include <QCryptographicHash>
#include <QDir>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QPointer>
#include <QSaveFile>
#include <QSet>
#include <QStandardPaths>
#include <QTimer>
#include <algorithm>
#include <stdexcept>

using namespace edi::assistant::native;
struct AssistantSkillWebImport::State {
    struct File {QString source,target,sha;};
    QPointer<QObject> receiver;
    Completion completion;
    ProductionServices services=production_services();
    std::unique_ptr<HttpOperation> operation;
    std::unique_ptr<QTemporaryDir> directory;
    std::weak_ptr<AssistantSkillWebImport> owner;
    QString repository,ref,subdirectory,commit,origin;
    QList<File> files;
    qsizetype next=0;
    QByteArray body;
    quint64 total=0;
    int status=0;
    bool cancelled=false,done=false;
    static bool component(QStringView text) {
        return !text.isEmpty() && text!=u"." && text!=u".." && std::all_of(text.begin(),text.end(),[](QChar c){
            const auto u=c.unicode();return (u>='a'&&u<='z') || (u>='A'&&u<='Z') || (u>='0'&&u<='9') || c=='-' || c=='_' || c=='.';});
    }
    static bool sha(QStringView text) {
        return text.size()==40 && std::all_of(text.begin(),text.end(),[](QChar c){return (c>='0'&&c<='9') || (c>='a'&&c<='f');});
    }
    static bool inside(QStringView path) {
        if(path.isEmpty() || path.startsWith('/') || path.contains('\\') || path.contains(':') || path.contains(QChar(0)))return false;
        for(const auto& part:path.toString().split('/'))if(part.isEmpty() || part=="." || part=="..")return false;
        return true;
    }
    static QByteArray encodedPath(const QString& path) {
        QByteArray result;
        for(const auto& part:path.split('/')){if(!result.isEmpty())result+='/';result+=QUrl::toPercentEncoding(part);}
        return result;
    }
    void parse(const QUrl& url) {
        if(!url.isValid() || url.scheme()!="https" || url.host()!="github.com" || !url.userInfo().isEmpty() || url.port()!=-1 || url.hasQuery() || url.hasFragment() ||
            url.path(QUrl::FullyEncoded).contains("%2f",Qt::CaseInsensitive))
            throw std::runtime_error("Use a public https://github.com/owner/repository URL, optionally /tree/ref/folder or /blob/ref/folder/SKILL.md; private credentials and slash-containing refs are not supported.");
        auto parts=url.path().split('/',Qt::SkipEmptyParts);
        if(parts.size()<2 || !component(parts[0]) || !component(parts[1]))throw std::runtime_error("The GitHub repository URL is incomplete.");
        if(parts[1].endsWith(".git"))parts[1].chop(4);
        if(!component(parts[1]))throw std::runtime_error("The GitHub repository name is invalid.");
        repository=parts[0]+'/'+parts[1];origin=url.toString();
        if(parts.size()>2) {
            if(parts.size()<4 || (parts[2]!="tree" && parts[2]!="blob") || !component(parts[3]))throw std::runtime_error("Use a repository URL or a GitHub tree/blob URL with a single-component ref.");
            ref=parts[3];subdirectory=parts.mid(4).join('/');
            if(parts[2]=="blob") {
                if(!subdirectory.endsWith("/SKILL.md") && subdirectory!="SKILL.md")throw std::runtime_error("A GitHub file URL must name SKILL.md.");
                subdirectory=subdirectory=="SKILL.md"?QString():subdirectory.chopped(9);
            }
            if(!subdirectory.isEmpty() && !inside(subdirectory))throw std::runtime_error("The requested skill folder path is invalid.");
        }
    }
    bool current() const {return !cancelled && !done && receiver;}
    void finish(QString error={}) {
        if(!current())return;
        done=true;operation.reset();auto callback=std::move(completion);
        auto folder=error.isEmpty()?std::move(directory):std::unique_ptr<QTemporaryDir>{};
        if(receiver && callback)callback(std::move(folder),origin+" @ "+commit.left(12),std::move(error));
    }
    void request(const QUrl& url,std::function<void()> complete) {
        if(!current())return;
        body.clear();status=0;const auto weak=owner;
        HttpCallbacks callbacks;
        callbacks.headers=[weak](int code,HttpHeaders){if(auto task=weak.lock();task && task->state_->current())task->state_->status=code;};
        callbacks.data=[weak](QByteArray bytes) {
            if(auto task=weak.lock();task && task->state_->current())try {
                auto& s=*task->state_;
                if(static_cast<quint64>(bytes.size())>edi::assistant::Limits::context_bytes-static_cast<quint64>(s.body.size()))
                    throw std::runtime_error("The web response exceeds the existing skill-source input capacity.");
                s.body+=bytes;
            }catch(const std::exception& error){task->state_->finish(QString::fromUtf8(error.what()));}
        };
        callbacks.finished=[weak,complete=std::move(complete)](HttpFailure failure) {
            if(auto task=weak.lock();task && task->state_->current())try {
                auto& s=*task->state_;s.operation.reset();
                if(failure!=HttpFailure::none)throw std::runtime_error("The public GitHub source could not be fetched. Check the connection and URL; no private credentials were used.");
                if(s.status!=200)throw std::runtime_error("The public GitHub source returned a refusal or redirect. Use its canonical public URL; no private credentials were used.");
                complete();
            }catch(const std::exception& error){task->state_->finish(QString::fromUtf8(error.what()));}
            catch(...){task->state_->finish(QStringLiteral("The web skill source could not be captured."));}
        };
        operation=services.dependencies.request(HttpRequest{HttpMethod::get,url,{{"Accept","application/vnd.github+json"},{"User-Agent","EasyDiffraction"}}, {},edi::assistant::Limits::context_bytes,edi::assistant::Limits::http_json_ms},std::move(callbacks));
        if(!operation)throw std::runtime_error("The native web request could not start.");
    }
    QJsonObject json() const {
        QJsonParseError error;const auto document=QJsonDocument::fromJson(body,&error);
        if(error.error!=QJsonParseError::NoError || !document.isObject())throw std::runtime_error("The public GitHub metadata is invalid.");
        return document.object();
    }
    void resolve() {
        if(ref.isEmpty())request(QUrl("https://api.github.com/repos/"+repository),[this]{
            const auto value=json().value("default_branch");if(!value.isString() || value.toString().isEmpty())throw std::runtime_error("The repository has no readable default branch.");
            ref=value.toString();resolveCommit();
        });else resolveCommit();
    }
    void resolveCommit() {
        request(QUrl::fromEncoded("https://api.github.com/repos/"+repository.toUtf8()+"/commits/"+QUrl::toPercentEncoding(ref)),[this]{
            const auto metadata=json();commit=metadata.value("sha").toString();const auto tree=metadata.value("commit").toObject().value("tree").toObject().value("sha").toString();
            if(!sha(commit) || !sha(tree))throw std::runtime_error("The GitHub commit identity is invalid.");
            request(QUrl("https://api.github.com/repos/"+repository+"/git/trees/"+tree+"?recursive=1"),[this]{selectFiles();});
        });
    }
    void selectFiles() {
        const auto metadata=json();if(metadata.value("truncated")!=false || !metadata.value("tree").isArray())throw std::runtime_error("The complete GitHub file inventory is unavailable. Choose a smaller supported skill source.");
        const auto entries=metadata.value("tree").toArray();QSet<QString> paths,roots,names;
        for(const auto& value:entries) {
            const auto row=value.toObject();const auto path=row.value("path").toString();
            if(!inside(path) || paths.contains(path))throw std::runtime_error("The GitHub file inventory contains an invalid or duplicate path.");paths.insert(path);
            if(!subdirectory.isEmpty() && path!=subdirectory && !path.startsWith(subdirectory+'/'))continue;
            if(path=="SKILL.md" || path.endsWith("/SKILL.md")) {
                const auto root=path=="SKILL.md"?QString():path.chopped(9);const auto name=root.isEmpty()?repository.section('/',1):root.section('/',-1);
                if(!component(name) || names.contains(name))throw std::runtime_error("The selected source contains ambiguous skill folder names.");
                roots.insert(root);names.insert(name);
            }
        }
        if(roots.isEmpty())throw std::runtime_error("The public repository selection contains no SKILL.md packages.");
        for(const auto& value:entries) {
            const auto row=value.toObject();const auto path=row.value("path").toString();
            if(row.value("type")=="tree")continue;
            for(const auto& root:roots)if(root.isEmpty() || path.startsWith(root+'/')) {
                if(row.value("type")!="blob" || (row.value("mode")!="100644" && row.value("mode")!="100755") || !sha(row.value("sha").toString()))
                    throw std::runtime_error("Skill sources support original regular files only, without links or submodules.");
                const auto name=root.isEmpty()?repository.section('/',1):root.section('/',-1);
                const auto target=name+'/'+(root.isEmpty()?path:path.mid(root.size()+1));
                if(std::any_of(files.begin(),files.end(),[&](const auto& held){return held.target==target;}))throw std::runtime_error("The skill snapshot contains duplicate destinations.");
                files.append({path,target,row.value("sha").toString()});break;
            }
        }
        const auto parent=QStandardPaths::writableLocation(QStandardPaths::AppLocalDataLocation)+"/assistant/skill-sources";
        if(!QDir().mkpath(parent))throw std::runtime_error("The local skill-source cache is unavailable.");
        directory=std::make_unique<QTemporaryDir>(parent+"/import-XXXXXX");if(!directory->isValid())throw std::runtime_error("The local skill snapshot could not be staged.");
        download();
    }
    void download() {
        if(next>=files.size()) {
            QSaveFile provenance(directory->path()+"/SOURCE.json");const auto bytes=QJsonDocument(QJsonObject{{"url",origin},{"commit",commit}}).toJson();
            if(!provenance.open(QIODevice::WriteOnly) || provenance.write(bytes)!=bytes.size() || !provenance.commit())throw std::runtime_error("The skill provenance could not be retained.");
            finish();return;
        }
        const auto file=files[next];
        request(QUrl::fromEncoded("https://raw.githubusercontent.com/"+repository.toUtf8()+'/'+commit.toUtf8()+'/'+encodedPath(file.source)),[this,file]{
            if(static_cast<quint64>(body.size())>edi::assistant::Limits::context_bytes-total)throw std::runtime_error("The source exceeds the existing skill inventory capacity.");
            QCryptographicHash digest(QCryptographicHash::Sha1);digest.addData("blob "+QByteArray::number(body.size())+QByteArray(1,'\0'));digest.addData(body);
            if(QString::fromLatin1(digest.result().toHex())!=file.sha)throw std::runtime_error("The downloaded skill file differs from the original commit.");
            const auto path=directory->path()+'/'+file.target;if(!QDir().mkpath(QFileInfo(path).path()))throw std::runtime_error("The skill folder could not be staged.");
            QSaveFile output(path);if(!output.open(QIODevice::WriteOnly) || output.write(body)!=body.size() || !output.commit())throw std::runtime_error("The skill file could not be retained.");
            total+=static_cast<quint64>(body.size());++next;download();
        });
    }
};
AssistantSkillWebImport::AssistantSkillWebImport(std::unique_ptr<State> state):state_(std::move(state)){}
AssistantSkillWebImport::~AssistantSkillWebImport(){cancel();}
void AssistantSkillWebImport::cancel() noexcept {state_->cancelled=true;state_->completion={};state_->operation.reset();}
std::shared_ptr<AssistantSkillWebImport> AssistantSkillWebImport::start(QObject* receiver,const QUrl& url,Completion completion) {
    auto state=std::make_unique<State>();state->receiver=receiver;state->completion=std::move(completion);state->parse(url);
    auto task=std::shared_ptr<AssistantSkillWebImport>(new AssistantSkillWebImport(std::move(state)));task->state_->owner=task;
    QTimer::singleShot(0,receiver,[weak=std::weak_ptr(task)]{if(auto task=weak.lock();task && task->state_->current())try{task->state_->resolve();}
        catch(const std::exception& error){task->state_->finish(QString::fromUtf8(error.what()));}catch(...){task->state_->finish(QStringLiteral("The web skill source could not start."));}});
    return task;
}
#endif
