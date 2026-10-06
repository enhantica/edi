//  test-only introspection and CLI fixture loading. Never linked into the app host.
#include <crysta/analysis.hpp>
#include <crysta/cell_symmetry.hpp>
#include <map>
#include <set>
#include <crysta/computed.hpp>
#include <crysta/model.hpp>
#include "edi/calculation.hpp"
#include "edi/io.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/presentation.hpp"
#include "project_view_model.hpp"
#include "pattern_chart_controller.hpp"
#include <algorithm>
#include <QCryptographicHash>
#include <QDirIterator>
#include <QtGraphs/QXYSeries>
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QMetaMethod>
#include <QThread>
#include <QElapsedTimer>
#include <QEvent>
#include <QPointer>
#include <QSysInfo>
#include <QTemporaryDir>
#include <QRegularExpression>
#include <memory>
#include <QVariantList>
#include <QtQml/qqml.h>
#include <chrono>
#include <cmath>

class FitOracle final : public QObject {
    Q_OBJECT
    QList<QMetaObject::Connection> connections_;
    QVariantList progress_;
    std::vector<std::unique_ptr<QTemporaryDir>> directories_;
    bool owner_=true;
    QPointer<QObject> observed_;
    std::vector<double> delivery_ms_;
    bool forwarding_=false;
    bool presentation_=false;
    QPointer<QObject> presentationController_;
    static QString root() {return QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()).absoluteFilePath("../../..");}
    static QJsonObject manifest() {
        QFile file(QDir(root()).filePath("tests/fixtures/e05_t1/cli.json"));
        if(!file.open(QIODevice::ReadOnly)) return {};
        return QJsonDocument::fromJson(file.readAll()).object();
    }
    static QJsonObject entry(const QString& path) {
        for(const auto& row : manifest()["cases"].toArray()) if(row.toObject()["path"].toString()==path) return row.toObject();
        QFile file(QDir(root()).filePath("tests/fixtures/e05_t1/stops.json"));
        if(file.open(QIODevice::ReadOnly)) for(const auto& row:QJsonDocument::fromJson(file.readAll()).object()["cases"].toArray())
            if(row.toObject()["path"].toString()==path) return row.toObject();
        return {};
    }
    static bool near(double a,double b) {return std::abs(a-b)<=std::max(5e-10,5e-9*std::abs(b));}
   public:
    using QObject::QObject;
    Q_INVOKABLE QVariantList cases() const {
        QVariantList output;
        for(const auto& v : manifest()["cases"].toArray()) {
            const auto row=v.toObject();
            output.append(QVariantMap{{"tag",row["id"].toString()},{"path",row["path"].toString()},{"mode",row["mode"].toString()}});
        }
        return output;
    }
    Q_INVOKABLE QVariantMap refusalCase() const {
        QFile file(QDir(root()).filePath("tests/fixtures/e05_t1/refusal.json"));
        if(!file.open(QIODevice::ReadOnly)) return {};
        return QJsonDocument::fromJson(file.readAll()).object().toVariantMap();
    }
    Q_INVOKABLE QVariantList stopCases() const {
        QFile file(QDir(root()).filePath("tests/fixtures/e05_t1/stops.json"));
        if(!file.open(QIODevice::ReadOnly)) return {};
        QVariantList output;
        for(const auto& v:QJsonDocument::fromJson(file.readAll()).object()["cases"].toArray()) {
            const auto row=v.toObject();
            output.append(QVariantMap{{"tag",row["id"].toString()},{"path",row["path"].toString()}});
        }
        return output;
    }
    Q_INVOKABLE QVariantMap expected(const QString& path) const {
        auto result=entry(path)["record"].toObject().toVariantMap();
        result["minimizer"]=entry(path)["minimizer"].toString(); return result;
    }
    Q_INVOKABLE QObject* controller(QObject* chart) const {
        return chart ? chart->findChild<edi_app::PatternChartController*>() : nullptr;
    }
    Q_INVOKABLE bool inputsMatchCli(const QString& path) const {
        const auto hashes=entry(path)["inputs_sha256"].toObject(); if(hashes.empty()) return false;
        const QDir directory(QDir(root()).filePath(path)); int count=0;
        QDirIterator files(directory.path(),QDir::Files,QDirIterator::Subdirectories);
        while(files.hasNext()) {
            QFile file(files.next());const auto name=directory.relativeFilePath(file.fileName());
            if(!hashes.contains(name) || !file.open(QIODevice::ReadOnly)) return false;
            const auto hash=QString::fromLatin1(QCryptographicHash::hash(file.readAll(),QCryptographicHash::Sha256).toHex());
            if(hash!=hashes[name].toString()) return false;
            ++count;
        }
        return count==hashes.size();
    }
    Q_INVOKABLE bool chartFresh(QObject* chart,QObject* project) const {
        auto* vm=qobject_cast<edi_app::ProjectViewModel*>(project);
        auto* controller=chart ? chart->findChild<edi_app::PatternChartController*>() : nullptr;
        if(!vm || !controller) return false;
        auto* series=controller->property("calculatedSeries").value<QXYSeries*>();
        if(!series || series->count()==0) return false;
        auto copy=edi::snapshot_for_work(vm->project()).project;copy.calculate();
        const auto reference=edi::capture_pattern(copy,static_cast<std::size_t>(vm->currentExperimentIndex()));
        if(!reference.x || !reference.calc) return false;
        for(const auto& point:series->points()) {
            if(std::isnan(point.x()) && std::isnan(point.y())) continue;
            const auto at=std::find(reference.x->begin(),reference.x->end(),point.x());
            if(at==reference.x->end() || !near(point.y(),(*reference.calc)[static_cast<std::size_t>(at-reference.x->begin())])) return false;
        }
        return true;
    }
    Q_INVOKABLE bool pointsEqualInstant(QObject* chart,QObject* project,double left,double right) const {
        auto* vm=qobject_cast<edi_app::ProjectViewModel*>(project);
        auto* controller=chart ? chart->findChild<edi_app::PatternChartController*>() : nullptr;
        if(!vm || !controller) return false;
        const auto source=edi::capture_pattern(vm->project(),static_cast<std::size_t>(vm->currentExperimentIndex()));
        edi::PatternView view;view.x_min=left;view.x_max=right;
        view.columns=edi::pixel_columns(controller->property("plotWidth").toDouble(),controller->property("devicePixelRatio").toDouble());
        // Regression comparison to the prior instant path, not a fit correctness oracle.
        const auto instant=edi::present_pattern(source,view);
        QList<QPointF> ticks[3];
        for(const auto& reference:instant.series) {
            if(reference.kind==edi::SeriesKind::BraggTicks) {
                const auto slot=reference.style.empty()?0:(reference.style.back()-'0')%3;
                for(const auto& p:reference.points) ticks[slot].append(QPointF(p.x,p.y));
                continue;
            }
            auto* object=chart->findChild<QObject*>("chart.series."+QString::fromStdString(reference.id));
            auto* actual=qobject_cast<QXYSeries*>(object);if(!actual || actual->count()!=static_cast<int>(reference.points.size())) return false;
            for(std::size_t i=0;i<reference.points.size();++i) {
                const auto at=actual->at(static_cast<int>(i));const auto& expected=reference.points[i];
                if(std::isnan(at.x()) && std::isnan(expected.x) && std::isnan(at.y()) && std::isnan(expected.y)) continue;
                if(at.x()!=expected.x || at.y()!=expected.y) return false;
            }
        }
        for(int slot=0;slot<3;++slot) {
            auto* actual=qobject_cast<QXYSeries*>(chart->findChild<QObject*>("chart.series.bragg."+QString::number(slot)));
            if(!actual || actual->count()!=ticks[slot].size()) return false;
            for(int i=0;i<actual->count();++i) {
                const auto a=actual->at(i),b=ticks[slot][i];
                if(std::isnan(a.x()) && std::isnan(b.x()) && std::isnan(a.y()) && std::isnan(b.y())) continue;
                if(a!=b) return false;
            }
        }
        return true;
    }
    Q_INVOKABLE QVariantMap instantFittedY(QObject* object,double left,double right) const {
        auto* vm=qobject_cast<edi_app::ProjectViewModel*>(object);if(!vm) return {};
        edi::PatternView view;view.x_min=left;view.x_max=right;
        const auto source=edi::capture_pattern(vm->project(),static_cast<std::size_t>(vm->currentExperimentIndex()));
        const auto instant=edi::present_pattern(source,view);
        double low=instant.y_main.min,high=instant.y_main.max;
        if(!(high>low)) high=low+1.0;
        // Regression pin: prior instant chart's ADR-0017 auto-range adds one tenth at each end.
        const double padding=.1*(high-low);
        return {{"min",low-padding},{"max",high+padding}};
    }
    Q_INVOKABLE bool tableEqualsCli(QObject* object,const QString& path) const {
        auto* vm=qobject_cast<edi_app::ProjectViewModel*>(object); if(!vm) return false;
        auto copy=edi::snapshot_for_work(vm->project()).project;
        const auto ordered=copy.parameters();
        const auto expected=entry(path)["parameters"].toArray();
        if(expected.empty() || static_cast<std::size_t>(expected.size())!=ordered.size()) return false;
        const auto fields=edi::parameter_entries(copy);
        auto* table=vm->parameters();
        int checked=0;
        for(int row=0;row<table->rowCount();++row) {
            const auto key=table->get(row,"path").toString().toStdString();
            const auto field=std::find_if(fields.begin(),fields.end(),[&](const auto& f){return f.path==key;});
            if(field==fields.end()) return false;
            const auto at=std::find(ordered.begin(),ordered.end(),field->parameter);
            if(at==ordered.end()) return false;
            const auto value=expected[static_cast<int>(at-ordered.begin())].toObject();
            if(!near(table->get(row,"value").toDouble(),value["value"].toDouble())) return false;
            const bool has=!value["uncertainty"].isNull();
            if(table->get(row,"hasUncertainty").toBool()!=has) return false;
            if(has && !near(table->get(row,"uncertainty").toDouble(),value["uncertainty"].toDouble())) return false;
            if(table->get(row,"free").toBool()!=value["free"].toBool()) return false;
            ++checked;
        }
        return checked>0;
    }
    Q_INVOKABLE QVariantList fittedRangeRows(const QString& path) const {
        auto input=edi::load_project(QDir(root()).filePath(path).toStdString());
        const auto ordered=input.parameters();
        const auto fields=edi::parameter_entries(input);
        const auto expected=entry(path)["parameters"].toArray();
        if(expected.size()!=static_cast<int>(ordered.size())) return {};
        // ADR-0019: the table contains independent symmetry parameters. The reference
        // comes directly from crysta's public maps, outside edi's marks/table model.
        const auto external=crysta::load_project(QDir(root()).filePath(path).toStdString());
        std::map<std::pair<std::string,std::string>,bool> independent;
        for(const auto& structure:external.structures) {
            const auto freedom=crysta::cell_freedom(structure.space_group);
            const char* cell_names[]={"length_a","length_b","length_c","angle_alpha","angle_beta","angle_gamma"};
            for(std::size_t axis=0;axis<6;++axis)
                independent[{structure.name.value(),cell_names[axis]}]=freedom.is_independent(axis);
            const auto constraints=structure.positional_constraints();
            for(const auto& [site,position]:constraints.sites()) {
                std::set<std::size_t> seen;
                const char* axis_names[]={"fract_x","fract_y","fract_z"};
                for(std::size_t axis=0;axis<3;++axis)
                    independent[{structure.name.value(),site+"."+axis_names[axis]}]=
                        position.axis_is_basic(axis) && seen.insert(position.axis_basic_index(axis)).second;
            }
        }
        QVariantList rows;
        for(const auto& field:fields) {
            const auto at=std::find(ordered.begin(),ordered.end(),field.parameter);
            if(at==ordered.end() || !field.parameter->spec) return {};
            const auto fixture=expected[static_cast<int>(at-ordered.begin())].toObject();
            if(!fixture["free"].toBool()) continue;
            const double value=fixture["value"].toDouble();
            const auto range=field.parameter->spec->range;
            const auto key=std::make_pair(field.block_name,
                field.row_label.empty()?field.name:field.row_label+"."+field.name);
            const auto found=independent.find(key);
            rows.append(QVariantMap{{"path",QString::fromStdString(field.path)},
                {"value",value},{"outside",value<range.min || value>range.max},
                {"independent",found==independent.end() || found->second}});
        }
        return rows;
    }
    Q_INVOKABLE QVariantMap rawParameter(QObject* object,const QString& path) const {
        auto* vm=qobject_cast<edi_app::ProjectViewModel*>(object);if(!vm) return {};
        auto copy=edi::snapshot_for_work(vm->project()).project;
        for(const auto& field:edi::parameter_entries(copy))
            if(QString::fromStdString(field.path)==path)
                return {{"value",field.parameter->value.get()},{"independent",field.refinable}};
        return {};
    }
    Q_INVOKABLE QString bytes(QObject* object) const {
        auto* vm=qobject_cast<edi_app::ProjectViewModel*>(object); if(!vm) return {};
        QString output;
        for(const auto& [path,value] : edi::project_edi_files(vm->project())) output+=QString::fromStdString(path)+"\n"+QString::fromStdString(value)+"\n";
        return output;
    }
    Q_INVOKABLE QVariantList modelValues(QObject* object) const {
        auto* vm=qobject_cast<edi_app::ProjectViewModel*>(object);if(!vm) return {};
        auto copy=edi::snapshot_for_work(vm->project()).project;QVariantList values;
        for(const auto* parameter:copy.parameters()) values.append(QVariantMap{{"value",static_cast<double>(parameter->value)},{"free",static_cast<bool>(parameter->free)},{"uncertainty",parameter->uncertainty.get().value_or(-1)}});
        return values;
    }
    Q_INVOKABLE bool freshCalculated(QObject* object) const {
        auto* vm=qobject_cast<edi_app::ProjectViewModel*>(object); if(!vm) return false;
        auto copy=edi::snapshot_for_work(vm->project()).project; copy.calculate();
        for(std::size_t bank=0;bank<copy.experiments.size();++bank) {
            const auto live=edi::capture_pattern(vm->project(),bank),fresh=edi::capture_pattern(copy,bank);
            if(!live.current || !live.calc || !fresh.calc || live.calc->size()!=fresh.calc->size()) return false;
            for(std::size_t i=0;i<live.calc->size();++i) if(!near((*live.calc)[i],(*fresh.calc)[i]) && !(std::isnan((*live.calc)[i]) && std::isnan((*fresh.calc)[i]))) return false;
        }
        return true;
    }
    Q_INVOKABLE QUrl directory() {
        auto dir=std::make_unique<QTemporaryDir>();
        if(!dir->isValid()) return {};
        auto url=QUrl::fromLocalFile(dir->path()+"/saved");directories_.push_back(std::move(dir));return url;
    }
    Q_INVOKABLE QVariantMap savedResult(const QUrl& directory) const {
        QFile file(QDir(directory.toLocalFile()).filePath("analysis/analysis.edi"));
        if(!file.open(QIODevice::ReadOnly)) return {};
        const auto text=QString::fromUtf8(file.readAll());QVariantMap result;
        const QRegularExpression tags(QStringLiteral("(?m)^_fit_result\\.([a-z_]+)[ \t]+([^\n]+)"));
        auto at=tags.globalMatch(text);
        while(at.hasNext()) {auto row=at.next();auto value=row.captured(2).trimmed();
            if(value.size()>1 && (value.startsWith('\"') || value.startsWith('\''))) value=value.mid(1,value.size()-2);
            result[row.captured(1)]=value;
        }
        return result;
    }
    Q_INVOKABLE bool observe(QObject* object) {
        disarm();
        if(!object) return false;
        const int signal=object->metaObject()->indexOfSignal("iterationsChanged()");
        const int slot=metaObject()->indexOfSlot("iteration()");
        if(signal<0 || slot<0) return false;
        observed_=object->parent();
        if(observed_) observed_->installEventFilter(this);
        connections_.append(connect(object,object->metaObject()->method(signal),this,metaObject()->method(slot),Qt::DirectConnection));
        return true;
    }
    Q_INVOKABLE QVariantList progress() const {return progress_;}
    Q_INVOKABLE bool ownerThread() const {return owner_;}
    Q_INVOKABLE bool observePresentation(QObject* controller) {
        disarm();presentationController_=controller;presentation_=true;QCoreApplication::instance()->installEventFilter(this);return true;
    }
    Q_INVOKABLE void disarm() {
        QCoreApplication::instance()->removeEventFilter(this);presentation_=false;presentationController_.clear();
        if(observed_) observed_->removeEventFilter(this);observed_.clear();
        for(const auto& c:connections_) disconnect(c);connections_.clear();progress_.clear();delivery_ms_.clear();owner_=true;
    }
    Q_INVOKABLE QString bankDeliveryWork(const QString& path,const QString& scenario) const {
        if(delivery_ms_.empty()) return {};
        auto values=delivery_ms_;std::sort(values.begin(),values.end());
        QJsonArray raw;for(double value:delivery_ms_) raw.append(value);
        QJsonObject stats{{"median_ms",values[(values.size()-1)/2]},
                          {"p95_ms",values[static_cast<std::size_t>(std::ceil(.95*values.size()))-1]}};
        const auto runner=qEnvironmentVariable("RUNNER_NAME");
        const auto machine=runner.isEmpty()?"hand:"+QSysInfo::machineHostName():runner;
        const auto id=entry(path)["id"].toString();
        QJsonObject table{{"schema",1},{"machine",machine},{"commit",qEnvironmentVariable("EDI_TEST_COMMIT",qEnvironmentVariable("GITHUB_SHA"))},
                          {"delivery_samples_ms",raw},
                          {"rows",QJsonArray{QJsonObject{{"dataset",scenario+":"+id},{"scenario","S3"},{"presentation",stats}}}}};
        const auto folder=QDir(root()).filePath("build/delivery-latency");QDir().mkpath(folder);
        const auto output=folder+"/"+scenario+"-"+id+".json";QFile file(output);
        if(!file.open(QIODevice::WriteOnly)) return {};
        file.write(QJsonDocument(table).toJson());return output;
    }
   protected:
    bool eventFilter(QObject* receiver,QEvent* event) override {
        if((!presentation_ && receiver!=observed_) || forwarding_ ||
           (event->type()!=QEvent::MetaCall && !(presentation_ && event->type()==QEvent::Timer))) return false;
        QVariantList before;
        if(presentationController_) for(const char* name:{"revision","xMin","xMax","yMin","yMax"}) before.append(presentationController_->property(name));
        forwarding_=true;QElapsedTimer timer;timer.start();
        QCoreApplication::sendEvent(receiver,event);
        const double elapsed=static_cast<double>(timer.nsecsElapsed())/1e6;
        bool changed=!presentation_;
        if(presentationController_) {
            int i=0;
            for(const char* name:{"revision","xMin","xMax","yMin","yMax"})
                changed=changed || before[i++]!=presentationController_->property(name);
        }
        if(changed) delivery_ms_.push_back(elapsed);
        forwarding_=false;return true;
    }
   public:
    Q_INVOKABLE QVariantMap hoverReference(QObject* object,QObject* project,int pane) const {
        auto* controller=qobject_cast<edi_app::PatternChartController*>(object);
        if(!controller || !controller->experiment()) return {};
        auto* vm=qobject_cast<edi_app::ProjectViewModel*>(project); if(!vm) return {};
        auto reference=crysta::load_project(vm->project().path);
        crysta::calculate_project(reference);
        const auto& experiment=reference.experiment();
        const auto& categories=crysta::current(reference,experiment);
        if(pane==1) {
            const auto& ticks=categories.refln(); if(ticks.size()==0) return {};
            return {{"x",ticks.position[0]},{"name",QString::fromStdString(ticks.structure_id[0])},
                    {"hkl",QString("Miller indices: (%1 %2 %3)").arg(ticks.index_h[0]).arg(ticks.index_k[0]).arg(ticks.index_l[0])},
                    {"y",.5}};
        }
        const auto residual=crysta::residual(experiment);
        for(std::size_t i=0;i<experiment.data->grid.size();++i) if(std::isfinite(categories.data().intensity_calc[i]) && residual[i]!=0)
            return {{"x",experiment.data->grid[i]},{"meas",experiment.data->intensity[i]},
                    {"calc",categories.data().intensity_calc[i]},{"bkg",categories.data().intensity_bkg[i]},
                    {"resid",residual[i]},{"y",experiment.data->intensity[i]}};
        return {};
    }
   private slots:
    void iteration() {
        auto* project=sender();
        owner_=owner_ && QThread::currentThread()==QCoreApplication::instance()->thread();
        progress_.append(project->property("iterations").toInt());
    }
};
static void registerFitOracle() {
    qmlRegisterSingletonType<FitOracle>("EdiFitReference",1,0,"FitOracle",[](QQmlEngine*,QJSEngine*)->QObject*{return new FitOracle;});
}
Q_COREAPP_STARTUP_FUNCTION(registerFitOracle)
#include "test_e05_t1_oracle.moc"
