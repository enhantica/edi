// Test-owned clocks/read-back. Not compiled into edi_app.
#include <crysta/model.hpp>
#include <crysta/structure_geometry.hpp>
#include "../../fixtures/e04_t10/generated.hpp"
#include "edi/io.hpp"
#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QMetaMethod>
#include <QObject>
#include <QQuickItem>
#include <QQuickWindow>
#include <QSGRendererInterface>
#include <QTemporaryDir>
#include <QThread>
#include <QVariantList>
#include <QtQml/qqml.h>
#include <QtTest/qtestkeyboard.h>
#include <QOpenGLContext>
#include <QOpenGLFunctions>
#include <algorithm>
#include <atomic>
#include <chrono>
#include <deque>
#include <mutex>
#include <set>
#if __has_include(<QtQuick3D/qquick3dinstancing.h>)
#include <QtQuick3D/qquick3dinstancing.h>
#define E04_T10_QUICK3D 1
#else
#define E04_T10_QUICK3D 0
#endif

class StructureOracle final:public QObject {
    Q_OBJECT
    struct Frame { qint64 at;bool requested;bool superseded; };
    std::mutex mutex_;
    std::deque<Frame> pending_;
    QList<QMetaObject::Connection> connections_;
    QVector3D expected_;
    qint64 start_=0,stop_=0,last_swap_=0;
    qulonglong baseline_revision_=0;
    std::vector<double> frames_;
    QString renderer_;
    bool superseded_=false;
    std::atomic<bool> gui_publication_{true};
    std::atomic<int> changes_{0};
    QTemporaryDir generated_dir_,pick_dir_;
    static qint64 now() {return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();}
    static QString root() {return QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()).absoluteFilePath("../../..");}
public:
    using QObject::QObject;
    // Qt Quick Test's keyClick chooses the OS-active window when multiple
    // windows exist. Cocoa CI cannot guarantee that activation. Qt Test's
    // explicit-window overload still dispatches real press/release events
    // through QQuickWindow and the field's production accepted handler.
    Q_INVOKABLE bool returnKey(QQuickWindow* window,QQuickItem* field) {
        if(!window || !field || field->window()!=window || !window->isVisible() || !window->isExposed()
           || !field->isVisible() || !field->isEnabled() || window->activeFocusItem()!=field)return false;
        QTest::keyClick(window,Qt::Key_Return,Qt::NoModifier,0);
        return true;
    }
    Q_INVOKABLE QVariantList datasets() {
        auto generated=e04_t10_fixture::generated();generated.structure().current_geometry();
        e04_t10_fixture::write_calculation_project(generated,generated_dir_.path().toStdString());
        return {QVariantMap{{"tag","T1"},{"path",QDir(root()).filePath(QString::fromUtf8(e04_t10_fixture::t1))}},
                QVariantMap{{"tag","G1"},{"path",generated_dir_.path()}}};
    }
    Q_INVOKABLE QString pickFixture(double near) {
        edi::Project project;project.experiments.clear();project.structures.clear();edi::Structure s;
        s.name="hit-identity";s.space_group.name_h_m="P 1";
        s.cell.length_a.value=10;s.cell.length_b.value=10;s.cell.length_c.value=10;
        for(const std::string symbol:{"La","Ba","H","He"}) {
            auto site=std::make_shared<edi::AtomSite>();site->id=symbol;site->type_symbol=symbol;
            site->fract_x.value=.5;site->fract_y.value=.5;site->fract_z.value=(symbol=="H" || symbol=="He")?.5+near/10:.5;
            site->wyckoff_letter="a"; // P 1 general position.
            site->occupancy.value=.5;site->adp_type="Biso";site->adp_iso.value=.5;s.atom_sites.push_back(site);
        }
        s.current_geometry();project.structures.push_back(s);
        e04_t10_fixture::write_calculation_project(project,pick_dir_.path().toStdString());return pick_dir_.path();
    }
    Q_INVOKABLE QVariantList reference(const QString& path,double x=-1) const {
        const auto input=QDir(root()).filePath(path);
        const auto read=[x](crysta::Structure& structure) {
            if(x>=0)structure.atom_sites[0].fract[0].set_value(x);
            const auto& g=crysta::current(structure).expanded_atom_sites;
            std::set<std::int32_t> seen;QVariantList out;
            for(std::size_t r=0;r<g.size();++r)if(seen.insert(g.cluster_id[r]).second)
                out.append(QVariantMap{{"x",g.cartn_x[r]},{"y",g.cartn_y[r]},{"z",g.cartn_z[r]},{"site",QString::fromStdString(g.atom_site_id[r])}});
            return out;
        };
        if(QFileInfo(input).isDir()) {
            auto project=crysta::load_project(input.toStdString());return read(project.structure);
        }
        auto structure=crysta::structure_from_edi_path(input.toStdString());return read(structure);
    }

    Q_INVOKABLE QVariantList instances(QObject* object) const {
        QVariantList out;
#if E04_T10_QUICK3D
        auto* table=qobject_cast<QQuick3DInstancing*>(object);if(!table)return out;
        int count=0;table->instanceBuffer(&count);
        for(int i=0;i<count;++i) {const auto p=table->instancePosition(i);const auto c=table->instanceColor(i);out.append(QVariantMap{{"x",p.x()},{"y",p.y()},{"z",p.z()},{"color",c.name()}});}
#else
        Q_UNUSED(object)
#endif
        return out;
    }
    Q_INVOKABLE bool watch(QObject* table) {
        changes_=0;if(!table)return false;
        const int signal=table->metaObject()->indexOfSignal("instanceTableChanged()");
        const int slot=metaObject()->indexOfSlot("changed()");
        if(signal<0)return false;
        connections_.append(QObject::connect(table,table->metaObject()->method(signal),this,metaObject()->method(slot),Qt::DirectConnection));return true;
    }
    Q_INVOKABLE int changes() const {return changes_;}
    Q_INVOKABLE bool watchPublication(QObject* project) {
        if(!project)return false;
        const int signal=project->metaObject()->indexOfSignal("recalculated()");
        const int slot=metaObject()->indexOfSlot("published()");if(signal<0)return false;
        connections_.append(QObject::connect(project,project->metaObject()->method(signal),this,metaObject()->method(slot),Qt::DirectConnection));return true;
    }
    Q_INVOKABLE bool guiPublication() const {return gui_publication_;}
    Q_INVOKABLE bool arm(QQuickWindow* window,QObject* view,const QVariantMap& expected) {
#if E04_T10_QUICK3D
        auto* table=qobject_cast<QQuick3DInstancing*>(view?view->findChild<QObject*>("structure.view.spheres"):nullptr);
        if(!table || !window)return false;
        disarm();expected_={expected.value("x").toFloat(),expected.value("y").toFloat(),expected.value("z").toFloat()};
        baseline_revision_=view->property("revision").toULongLong();
        connections_.append(connect(window,&QQuickWindow::afterSynchronizing,this,[=,this] {
            const auto position=table->instancePosition(0);
            const bool new_revision=view->property("revision").toULongLong()>baseline_revision_;
            const bool current=view->property("current").toBool();
            const bool matches=position==expected_;
            std::lock_guard lock(mutex_);
            if(auto* context=QOpenGLContext::currentContext())renderer_=QString::fromLatin1(reinterpret_cast<const char*>(context->functions()->glGetString(GL_RENDERER)));
            else renderer_=window->rendererInterface()->graphicsApi()==QSGRendererInterface::Metal?"Metal":"graphics API unreported";
            pending_.push_back({now(),new_revision && current && matches,new_revision && current && !matches});
        },Qt::DirectConnection));
        connections_.append(connect(window,&QQuickWindow::frameSwapped,this,[this] {
            const auto at=now();
            QMetaObject::invokeMethod(this,[this] {emit nextFrame();},Qt::QueuedConnection);
            std::lock_guard lock(mutex_);
            if(last_swap_)frames_.push_back((at-last_swap_)/1e6);last_swap_=at;
            if(pending_.empty())return;const auto sync=pending_.front();pending_.pop_front();
            if(!start_ || sync.at<start_)return;
            superseded_=superseded_ || sync.superseded;
            if(!stop_ && sync.requested)stop_=at;
        },Qt::DirectConnection));return true;
#else
        Q_UNUSED(window) Q_UNUSED(view) Q_UNUSED(expected)
        return false;
#endif
    }
    Q_INVOKABLE void start() {std::lock_guard lock(mutex_);start_=now();stop_=0;superseded_=false;}
    Q_INVOKABLE QVariantMap result() {
        std::lock_guard lock(mutex_);QVariantList frames;for(auto v:frames_)frames.append(v);
        return {{"complete",stop_>start_ && start_>0},{"update_ms",(stop_-start_)/1e6},{"superseded",superseded_},{"frames_ms",frames},{"renderer",renderer_},
                {"performanceReference",renderer_=="Metal" || (!renderer_.contains("llvmpipe",Qt::CaseInsensitive) && !renderer_.contains("soft",Qt::CaseInsensitive) && renderer_!="graphics API unreported" && !renderer_.isEmpty())}};
    }
    Q_INVOKABLE void disarm() {
        for(const auto& c:connections_)disconnect(c);connections_.clear();std::lock_guard lock(mutex_);
        pending_.clear();frames_.clear();start_=stop_=last_swap_=0;renderer_.clear();superseded_=false;
    }
signals:
    void nextFrame();
private slots:
    void changed() {++changes_;}
    void published() {if(QThread::currentThread()!=QCoreApplication::instance()->thread())gui_publication_=false;}
};
static void registerStructureOracle() {
    qmlRegisterSingletonType<StructureOracle>("EdiStructureReference",1,0,"StructureOracle",[](QQmlEngine*,QJSEngine*)->QObject* {return new StructureOracle;});
}
Q_COREAPP_STARTUP_FUNCTION(registerStructureOracle)
#include "test_e04_t10_observer.moc"
