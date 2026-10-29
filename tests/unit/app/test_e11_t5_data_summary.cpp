// SPDX-License-Identifier: BSD-3-Clause
// Literal arithmetic and original raw/native/public owners, never a second aggregator.
#include "assistant_data.hpp"
#include "assistant_data_summary.hpp"
#include "assistant_native_tools.hpp"
#include "assistant_outgoing.hpp"
#include "edi/io.hpp"
#include <QCoreApplication>
#include <QDebug>
#include <QDir>
#include <QFileInfo>
#include <QJsonDocument>
#include <QtQml/qqml.h>
#include <QtTest/qtestcase.h>
#include <algorithm>
#include <cmath>
#include <limits>
#include <memory>
#include <optional>
#include <span>
#include <vector>

namespace {
namespace s=edi_app::assistant_data::summary;
using Object=QJsonObject;using Array=QJsonArray;
struct Checks {
    int failures=0,checks=0;
    void require(bool ok,const QString& message) {
        ++checks;if(ok)return;++failures;QTest::qFail(message.toUtf8().constData(),__FILE__,__LINE__);
    }
    QVariantMap result() const {return {{"ok",failures==0},{"error",QStringLiteral("%1 individual data-summary failures; see QtTest incidents").arg(failures)},{"checks",checks}};}
};
void close(Checks& c,std::optional<double> actual,double expected,std::size_t terms,const QString& label) {
    c.require(actual && std::isfinite(*actual),label+": actual statistic is finite and available");
    if(!actual || !std::isfinite(*actual))return;
    // Independent forward-error allowance for at most8n+8 binary64 rounded
    // normalization/compensation/sqrt operations; not fitted to actual output.
    const double k=static_cast<double>(8*terms+8),eps=std::numeric_limits<double>::epsilon();
    const double gamma=k*eps/(1-k*eps);
    c.require(std::abs(*actual-expected)<=gamma*std::max(1.0,std::abs(expected)),label+": independently calculated moment retains binary64 numerical meaning");
}
s::ColumnInput input(s::ColumnKind kind,const char* name,std::span<const double> cells,bool available=true,bool current=true,const char* unit="counts") {
    return {{kind,name,std::string("original.")+name,unit,"original quantity",cells.size(),available,current},0,cells};
}
void coverage(Checks& c,const s::Coverage& v,std::size_t finite,std::size_t missing,std::size_t nan,std::size_t positive,std::size_t negative,const QString& label) {
    c.require(v.finite==finite && v.missing==missing && v.nan==nan && v.positive_infinity==positive && v.negative_infinity==negative,label+": five original cell classes have independent exact counts");
}
void witness(Checks& c,const std::optional<s::Witness>& v,double value,std::size_t row,std::optional<std::size_t> source,const QString& label) {
    c.require(v && v->value==value && v->row==row && v->source_row==source,label+": actual scalar, earliest native row and exact source mapping survive");
}
void moments(Checks& c,const std::optional<s::Moments>& m,s::Population population,std::size_t n,bool complete,double mean,double rms,const QString& label) {
    c.require(m && m->population==population && m->count==n && m->population_complete==complete && m->state==s::MomentState::Ok,label+": denominator, population and completeness remain distinct");
    if(!m)return;close(c,m->mean,mean,n,label+" mean");close(c,m->rms,rms,n,label+" RMS");
}
}

class DataSummaryProof final:public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    Q_INVOKABLE QVariantMap populationCoverageAndWitnesses() const {
        Checks c;
        try {
            const double nan=std::numeric_limits<double>::quiet_NaN(),inf=std::numeric_limits<double>::infinity();
            const std::vector<double> x{30,20,20,10,nan,5,4,inf,-0.0};
            const std::vector<double> measured{0,3,-4,nan,inf,-inf,12,12,6};
            const std::vector<double> sigma{1,0,-2,4,nan},residual{0,10,nan,-5,0,3,nan},background(9,0);
            const std::vector<s::Inclusion> mask{s::Inclusion::Included,s::Inclusion::Excluded,s::Inclusion::Included,
                s::Inclusion::Unknown,s::Inclusion::Included,s::Inclusion::Excluded,s::Inclusion::Unknown,s::Inclusion::Included,s::Inclusion::Included};
            const std::vector<s::ColumnInput> columns{input(s::ColumnKind::X,"x",x,true,true,"°"),
                input(s::ColumnKind::Measured,"measured",measured),input(s::ColumnKind::Sigma,"sigma",sigma),
                input(s::ColumnKind::Residual,"residual",residual),input(s::ColumnKind::Background,"background",background),
                input(s::ColumnKind::Calculated,"calculated",{},false,false)};
            s::Input q;q.total=9;q.start=1;q.count=7;q.partitions=3;q.columns=columns;
            q.mask={s::MaskSource::NativeCalcStatus,true,0,mask};q.axis_column=0;
            const auto result=s::summarize(q);const auto& r=result.overall;
            c.require(r.range.first==1 && r.range.end==8 && result.requested_partitions==3 && result.bins.size()==3,"Exact selected native extent and requested partitions remain separate");
            const std::vector<std::pair<std::size_t,std::size_t>> bins{{1,4},{4,6},{6,8}};
            for(std::size_t i=0;i<bins.size() && i<result.bins.size();++i)c.require(result.bins[i].range.first==bins[i].first && result.bins[i].range.end==bins[i].second,"Unequal literal contiguous bins partition the native rows without sorting");
            c.require(r.mask.applicable && r.mask.current && r.mask.source==s::MaskSource::NativeCalcStatus && r.mask.included==3 && r.mask.excluded==2 && r.mask.unknown==2,"Unknown mask rows never become inferred included/excluded from finite residual or sigma");
            c.require(r.axis_order==s::AxisOrder::Unknown,"Any actual nonfinite x makes this range's order unknown");
            c.require(r.columns.size()==columns.size(),"Every original declared column survives including unavailable computed data");
            const auto& m=r.columns.at(1);coverage(c,m.coverage,4,0,1,1,1,"measured");
            witness(c,m.minimum,-4,2,2,"minimum");witness(c,m.maximum,12,6,6,"equal maximum earliest native row");
            witness(c,m.first,3,1,1,"physical first endpoint");witness(c,m.last,12,7,7,"physical last endpoint");
            moments(c,m.all_finite,s::Population::AllFinite,4,true,23.0/4,std::sqrt(313.0/4),"measured all finite");
            moments(c,m.included_finite,s::Population::KnownIncludedFinite,2,false,4,std::sqrt(80.0),"measured included finite");
            const auto& su=r.columns.at(2);coverage(c,su.coverage,3,3,1,0,0,"short sigma");
            c.require(su.sigma_quality && su.sigma_quality->positive==1 && su.sigma_quality->zero==1 && su.sigma_quality->negative==1,"Finite zero/negative sigmas are described without invented weights or abs conversion");
            c.require(!su.last,"Missing physical endpoint is not replaced by last finite sample");
            moments(c,su.all_finite,s::Population::AllFinite,3,true,2.0/3,std::sqrt(20.0/3),"sigma independent denominator");
            moments(c,su.included_finite,s::Population::KnownIncludedFinite,1,false,-2,2,"sigma included denominator");
            const auto& residualSummary=r.columns.at(3);coverage(c,residualSummary.coverage,4,1,2,0,0,"native residual");
            moments(c,residualSummary.all_finite,s::Population::AllFinite,4,true,2,std::sqrt(134.0/4),"actual residual, not summary-mean difference");
            moments(c,residualSummary.included_finite,s::Population::KnownIncludedFinite,1,false,0,0,"included actual residual zero");
            moments(c,r.columns.at(4).all_finite,s::Population::AllFinite,7,true,0,0,"actual zero background");
            const auto& absent=r.columns.at(5);coverage(c,absent.coverage,0,7,0,0,0,"absent calculated");
            c.require(!absent.minimum && !absent.maximum && absent.all_finite && absent.all_finite->state==s::MomentState::UnavailableColumn && !absent.all_finite->mean && !absent.all_finite->rms,"Unavailable calculation has explicit absence, never valid zero moments");
            c.require(!r.columns.at(0).all_finite && !r.columns.at(0).included_finite,"Axes do not acquire physically invented intensity moments");
            for(std::size_t i=0;i<columns.size();++i) {
                const auto& a=columns[i].metadata;const auto& b=r.columns.at(i).metadata;
                c.require(a.name==b.name && a.item==b.item && a.unit==b.unit && a.quantity==b.quantity && a.length==b.length && a.available==b.available && a.current==b.current,"Original ordered dictionary/length/availability/currentness metadata stays exact");
            }
        }catch(const std::exception& error){c.require(false,QStringLiteral("population original entrance: ")+QString::fromUtf8(error.what()));}
        return c.result();
    }
    Q_INVOKABLE QVariantMap partitionsMasksAxesAndExtremes() const {
        Checks c;
        try {
            const auto edge=s::select_range(5,std::size_t{1000000007},9);
            c.require(edge.first==5 && edge.end==9,"A large independently admitted exact count clamps to the original native extent");
            c.require(s::select_range(9,0,9).count()==0 && s::partition_range({9,9},7).empty(),"Empty end range has no invented bins");
            bool refused=false;try{(void)s::select_range(10,0,9);}catch(const std::exception&){refused=true;}
            c.require(refused,"Beyond-native-extent data refuses rather than silently clamping");
            if constexpr(std::numeric_limits<std::size_t>::digits>53) {
                refused=false;try{(void)s::select_range(5,std::numeric_limits<std::size_t>::max(),9);}catch(const std::exception&){refused=true;}
                c.require(refused,"An out-of-domain count refuses even when the selected extent could have been clamped");
            }
            refused=false;try{(void)s::partition_range({0,7},0);}catch(const std::exception&){refused=true;}
            c.require(refused,"Zero partitions never becomes a guessed default");
            const auto singles=s::partition_range({2,7},1048577);
            c.require(singles.size()==5,"P>N gives exactly N one-row bins, no arbitrary work quota or empty bins");
            for(std::size_t i=0;i<singles.size();++i)c.require(singles[i].first==i+2 && singles[i].end==i+3,"Each selected native row occurs exactly once");
            const std::vector<std::pair<std::vector<double>,s::AxisOrder>> axes{
                {{1,2,3},s::AxisOrder::StrictlyIncreasing},{{3,2,1},s::AxisOrder::StrictlyDecreasing},
                {{1,1,2},s::AxisOrder::Nondecreasing},{{2,2,1},s::AxisOrder::Nonincreasing},
                {{2,2,2},s::AxisOrder::Constant},{{1,3,2},s::AxisOrder::Unordered},{{1},s::AxisOrder::Unknown},{{},s::AxisOrder::Unknown}};
            for(const auto& [values,order]:axes) {
                const std::vector<s::ColumnInput> cols{input(s::ColumnKind::X,"x",values)};
                s::Input q;q.total=values.size();q.count=values.size();q.columns=cols;q.axis_column=0;q.partitions=2;q.mask={s::MaskSource::NativeCalcStatus,false,0,{}};
                c.require(s::summarize(q).overall.axis_order==order,"Original adjacent native axis order is classified without sorting");
            }
            const std::vector<double> values{2,4,6};const std::vector<s::Inclusion> mask{s::Inclusion::Included,s::Inclusion::Excluded,s::Inclusion::Included};
            const std::vector<s::ColumnInput> cols{input(s::ColumnKind::Measured,"measured",values)};
            s::Input q;q.total=3;q.count=3;q.columns=cols;q.mask={s::MaskSource::NativeCalcStatus,false,0,mask};
            const auto stale=s::summarize(q).overall;
            c.require(!stale.mask.current && stale.mask.included==0 && stale.mask.excluded==0 && stale.mask.unknown==3,"Stale native status is unknown, never current inclusion");
            c.require(stale.columns[0].included_finite && !stale.columns[0].included_finite->population_complete && stale.columns[0].included_finite->count==0 && stale.columns[0].included_finite->state==s::MomentState::NoKnownIncludedFiniteValues && !stale.columns[0].included_finite->mean,"Unknown mask has no known finite population, not a fitted zero");
            const std::vector<s::ColumnInput> phaseCols{input(s::ColumnKind::X,"x",values)};
            q.row_space=s::RowSpace::BraggPhase;q.columns=phaseCols;q.axis_column=0;q.mask={};
            const std::vector<std::optional<std::size_t>> mapping{9,std::nullopt,9};q.mapping=s::ExplicitMapping{0,mapping};
            const auto bragg=s::summarize(q).overall;
            c.require(!bragg.mask.applicable && !bragg.mask.current && !bragg.mask.included && !bragg.mask.excluded && !bragg.mask.unknown && !bragg.columns[0].included_finite,"Phase ticks have not-applicable inclusion, never fitted count zero");
            witness(c,bragg.columns[0].first,2,0,9,"Bragg first source mapping");witness(c,bragg.columns[0].last,6,2,9,"Bragg separate source mapping");
            const std::vector<std::optional<double>> optional{std::nullopt,std::numeric_limits<double>::quiet_NaN(),-3,std::numeric_limits<double>::infinity()};
            s::ColumnInput sc{{s::ColumnKind::Measured,"measured","refln.intensity_meas","native unit","F_squared",4,true,true},0,std::span<const std::optional<double>>(optional)};
            const std::vector<s::ColumnInput> scCols{sc};q.row_space=s::RowSpace::SingleCrystal;q.total=4;q.count=4;q.columns=scCols;q.axis_column.reset();q.mapping=s::IdentityMapping{};
            q.mask={s::MaskSource::SingleCrystalFileFitUse,true,0,mask};
            const auto scResult=s::summarize(q).overall;coverage(c,scResult.columns[0].coverage,1,1,1,1,0,"SC absent cell vs present nonfinite");
            c.require(scResult.axis_order==s::AxisOrder::NotApplicable && !scResult.columns[0].first && !scResult.columns[0].last,"SC file order is not an angle/intensity axis and bad physical endpoints stay absent");
            moments(c,scResult.columns[0].included_finite,s::Population::KnownIncludedFinite,1,false,-3,3,"SC real signed measured F-squared");
            const std::vector<std::optional<double>> local{9,std::nullopt,std::numeric_limits<double>::quiet_NaN()};
            s::ColumnInput offset{{s::ColumnKind::Measured,"measured","refln.intensity_meas","unit","F_squared",5,true,true},2,std::span<const std::optional<double>>(local)};
            const std::vector<s::ColumnInput> offsetCols{offset};q.total=5;q.start=1;q.count=4;q.columns=offsetCols;
            const auto offsetResult=s::summarize(q).overall;coverage(c,offsetResult.columns[0].coverage,1,2,1,0,0,"SC captured span has original first-row offset");
            witness(c,offsetResult.columns[0].minimum,9,2,2,"SC offset witness keeps native row");
            for(const auto& sample:std::vector<std::vector<double>>{{std::numeric_limits<double>::max(),-std::numeric_limits<double>::max()},
                    {std::numeric_limits<double>::denorm_min(),std::numeric_limits<double>::denorm_min()},{1e16,1,-1e16}}) {
                const std::vector<s::ColumnInput> extremeCols{input(s::ColumnKind::Measured,"measured",sample)};
                s::Input extreme;extreme.total=sample.size();extreme.count=sample.size();extreme.columns=extremeCols;extreme.mask={s::MaskSource::NativeCalcStatus,false,0,{}};
                const auto m=s::summarize(extreme).overall.columns[0].all_finite;
                c.require(m && m->state==s::MomentState::Ok && m->count==sample.size(),"Original large/tiny/cancelling finite scalars retain representable statistics");
                if(!m)continue;
                if(sample[0]==std::numeric_limits<double>::max())c.require(m->mean==0 && m->rms==std::numeric_limits<double>::max(),"Opposite DBL_MAX gives exact zero mean and finite max RMS without square overflow");
                else if(sample[0]==std::numeric_limits<double>::denorm_min())c.require(m->mean==sample[0] && m->rms==sample[0],"Real subnormal observations are not silently zeroed");
                else {close(c,m->mean,1.0/3,3,"retained cancellation mean");close(c,m->rms,std::sqrt(2.0/3)*1e16,3,"cancellation RMS");}
            }
        }catch(const std::exception& error){c.require(false,QStringLiteral("partition/mask/extreme entrance: ")+QString::fromUtf8(error.what()));}
        return c.result();
    }
    Q_INVOKABLE QVariantMap rawCompatibilityAndStrictAdmission() const {
        Checks c;
        try {
            edi::PatternSource source;source.current=true;source.x_item="data.two_theta";
            source.x=std::make_shared<const std::vector<double>>(std::vector<double>{1,2,3,4});
            source.meas=std::make_shared<const std::vector<double>>(std::vector<double>{0,-2,std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity()});
            source.su=std::make_shared<const std::vector<double>>(std::vector<double>{1,0});
            const auto raw=edi_app::assistant_data::powder(source,0,4);const auto rows=raw["rows"].toArray();
            c.require(rows.size()==4 && !raw.contains("summary") && !raw.contains("view"),"Legacy raw shape/extent gains no summary fields");
            c.require(rows[0].toObject()["measured"]==0 && rows[1].toObject()["measured"]==-2 && rows[2].toObject()["measured"].isNull() && rows[3].toObject()["measured"].isNull(),"Original raw signed/zero/nonfinite-to-null values remain exact");
            c.require(rows[2].toObject()["sigma"].isNull() && rows[0].toObject()["calculated"].isNull(),"Short/absent raw cells remain null, not zero");
            c.require(edi_app::assistant_data::powder(source,1,2)["rows"].toArray()==Array{rows[1],rows[2]},"Original explicit raw slice equals exact full-native rows");
            edi::PatternSource::Phase a;a.structure_id="phase-A";a.label="A";a.position=source.x;a.rows={7,3,9,5};
            edi::PatternSource::Phase b;b.structure_id="phase-B";b.label="B";b.position=std::make_shared<const std::vector<double>>(std::vector<double>{8});
            source.phases={a,b};const auto phases=edi_app::assistant_data::bragg(source,2,99)["phases"].toArray();
            c.require(phases.size()==2 && phases[0].toObject()["count"]==2 && phases[1].toObject()["count"]==0 && phases[1].toObject()["requested_start"]==2,"Bragg keeps separate per-phase clamped extents, not measurement zipping");
            c.require(phases[0].toObject()["rows"].toArray()[0].toObject()["source_row"]==9,"Bragg native source-row mapping remains exact");
            const Object common{{"dataset_id","actual-dataset"},{"start",0},{"count",7}};
            auto admitted=[](const Object& args) {try{(void)edi_app::assistant_native_purpose(args,"inspect_data");edi_app::assistant_native_arguments("inspect_data",args);return true;}catch(const std::exception&){return false;}};
            c.require(admitted(common),"Legacy omitted view/purpose is admitted without new fields");
            auto rowsView=common;rowsView["view"]="rows";c.require(admitted(rowsView),"Explicit rows view needs no partitions");
            auto summary=common;summary["view"]="summary";summary["partitions"]=3;c.require(admitted(summary),"Same original inspect_data admits summary with positive explicit partitions");
            summary["partitions"]=1048577;c.require(admitted(summary),"Large valid partition request has no invented quota");
            std::vector<Object> bad;
            for(auto q:std::vector<Object>{common,rowsView}){q["partitions"]=2;bad.push_back(q);}
            auto missing=common;missing["view"]="summary";bad.push_back(missing);
            for(const auto value:Array{0,-1,1.5,true,"3",QJsonValue(QJsonValue::Null)}){auto q=summary;q["partitions"]=value;bad.push_back(q);}
            auto q=summary;q["view"]="unknown";bad.push_back(q);q=summary;q["source"]="sorted";bad.push_back(q);q=summary;q["unexpected"]="technical";bad.push_back(q);
            q=summary;q["partitions"]=9007199254740992.0;bad.push_back(q);q=summary;q["start"]=-1;bad.push_back(q);q=summary;q["purpose"]=Array{"not text"};bad.push_back(q);
            for(const auto& args:bad)c.require(!admitted(args),"Strict original schema/crossfields/types/native indices/purpose refuse before capture");
            int tools=0;for(const auto& value:edi_app::assistant_native_tool_specs())if(value.toObject()["name"]=="inspect_data") {
                ++tools;const auto schema=value.toObject()["inputSchema"].toObject();const auto properties=schema["properties"].toObject();
                c.require(schema["additionalProperties"]==false && properties["view"].toObject()["enum"].toArray().size()==2 && properties["view"].toObject()["enum"].toArray().contains("rows") && properties["view"].toObject()["enum"].toArray().contains("summary") && properties["partitions"].toObject()["type"]=="integer","Original offered schema advertises exact views/typed partitions without a shadow tool");
            }
            c.require(tools==1,"One original inspect_data registration owns the new view");
        }catch(const std::exception& error){c.require(false,QStringLiteral("raw/schema entrance: ")+QString::fromUtf8(error.what()));}
        return c.result();
    }
    Q_INVOKABLE QVariantMap closedOutgoingProjection() const {
        Checks c;
        try {
            const Object nullWitness{{"value",0},{"row",0},{"source_row",0}};
            const Object maximum{{"value",4},{"row",1},{"source_row",1}};
            const Object minimum{{"value",2},{"row",0},{"source_row",0}};
            const Object all{{"population","all_finite"},{"count",2},{"population_complete",true},{"state","ok"},{"mean",3},{"rms",std::sqrt(10.0)}};
            const Object included{{"population","known_included_finite"},{"count",1},{"population_complete",true},{"state","ok"},{"mean",2},{"rms",2}};
            const Object metadata{{"name","measured"},{"item","data.intensity_meas"},{"unit","counts"},{"quantity","original signal"},{"length",2},{"available",true},{"current",true}};
            auto column=metadata;column["finite"]=2;column["missing"]=0;column["nan"]=0;column["positive_infinity"]=0;column["negative_infinity"]=0;
            column["minimum"]=minimum;column["maximum"]=maximum;column["first"]=minimum;column["last"]=maximum;column["all_finite"]=all;column["included_finite"]=included;
            const Object mask{{"source","native_calc_status"},{"applicable",true},{"current",true},{"included",1},{"excluded",1},{"unknown",0}};
            const Object range{{"start",0},{"count",2},{"end",2},{"mask",mask},{"axis_order","unknown"},{"columns",Array{column}}};
            const Object summary{{"schema","edi.assistant.data-summary/1"},{"partitioning","contiguous_native_rows"},{"requested_partitions",1},{"partitions",1},
                {"physical_components",Object{{"available",false},{"reason","not_exposed_by_this_inspection"}}},{"overall",range},{"bins",Array{range}}};
            const Object data{{"dataset_id","literal-current-dataset"},{"sample_form","powder"},{"source","data"},{"captured_revision","17"},{"publication_generation","9"},
                {"row_space","native_data"},{"publication","native"},{"current",true},{"available",true},{"calculating",false},{"fitting",false},
                {"calculation_error",""},{"calculation_error_present",false},{"calculation_error_complete",true},{"axis_kind","data.two_theta"},{"axis_unit","°"},
                {"total",2},{"start",0},{"count",2},{"end",2},{"eof",true},{"columns",Array{metadata}},{"view","summary"},{"summary",summary}};
            Object source{{"status","inspected"},{"data",data}};
            auto polluted=source;auto extraData=data;auto extraSummary=summary;auto extraRange=range;auto extraColumn=column;
            extraColumn["opaque_native_debug"]=Object{{"command","never-copy-this"}};extraRange["columns"]=Array{extraColumn};
            extraRange["unknown_source_path"]="never-copy-path";extraSummary["overall"]=extraRange;extraSummary["bins"]=Array{extraRange};
            extraSummary["unverified_physics"]=Object{{"valid",true}};extraData["summary"]=extraSummary;extraData["opaque_array"]=Array{nullWitness};polluted["data"]=extraData;
            const auto admitted=edi_app::outgoing::size(polluted,edi_app::outgoing::Role::Result);
            const auto projected=edi_app::outgoing::project(polluted,edi_app::outgoing::Role::Result,admitted);
            c.require(projected["data"]==data,"Actual closed outgoing Result projection preserves every declared summary fact and drops unknown nested technical/physical assertions");
            c.require(source["data"]==data && polluted["data"].toObject().contains("opaque_array"),"Projection never overwrites original full backend objects or removes retained opaque evidence");
            auto malformed=source;auto badData=data;auto badSummary=summary;auto badRange=range;auto badColumn=column;auto badMoments=all;
            badMoments["count"]="two";badColumn["all_finite"]=badMoments;badRange["columns"]=Array{badColumn};badSummary["overall"]=badRange;badData["summary"]=badSummary;malformed["data"]=badData;
            bool refused=false;try{(void)edi_app::outgoing::size(malformed,edi_app::outgoing::Role::Result);}catch(const std::exception&){refused=true;}
            c.require(refused,"Known summary scalar roles reject invalid native types instead of recursively leaking malformed JSON");
        }catch(const std::exception& error){c.require(false,QStringLiteral("original outgoing projection entrance: ")+QString::fromUtf8(error.what()));}
        return c.result();
    }
    Q_INVOKABLE QVariantMap originalSingleCrystalOwner() const {
        Checks c;
        try {
            const auto root=QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()).absoluteFilePath("../../..");
            auto project=edi::load_project((root+"/docs/user/cli/sc-neut-cwl_tb2ti2o7-heidi_basic/project").toStdString());
            project.calculate();const auto& member=*project.experiments.at(0);
            edi_app::SingleCrystalReflectionModel model(member,project,nullptr);model.sync();
            const auto total=static_cast<std::size_t>(model.fileRowCount());c.require(total>2 && member.reflections && member.computed_current(),"Genuine original SC fixture/calculation/reflection owner is reached");
            const auto before=edi_app::assistant_data::reflections(member,model,0,total);
            model.sortBy("intensityMeas");const auto sorted=edi_app::assistant_data::reflections(member,model,0,total);
            c.require(before==sorted,"Original raw SC file order survives normal visual table sorting");
            c.require(before["row_space"]=="native_reflection" && before["axis_kind"]=="miller_indices" && before["current"]==true,"SC identity is original F-squared/reflection order, not powder-axis fiction");
            const auto rows=before["rows"].toArray();
            for(std::size_t i=0;i<total;++i) {
                const auto row=rows[static_cast<qsizetype>(i)].toObject();const auto& native=*member.reflections;
                c.require(row["row"]==static_cast<double>(i) && row["h"]==native.index_h[i] && row["k"]==native.index_k[i] && row["l"]==native.index_l[i] && row["measured"]==native.intensity_meas[i],"Actual signed HKL/F-squared/file-row identities remain exact");
                const auto used=model.fileValue(static_cast<qsizetype>(i),"fitUse");c.require(used.isValid() && row["used"]==QJsonValue(used.toDouble()!=0),"The original published file fit-use flag remains raw authority");
            }
            auto frame=std::make_shared<const std::vector<double>>(member.reflections->intensity_calc.values());model.showFrame(frame);
            const auto live=edi_app::assistant_data::reflections(member,model,0,total);
            c.require(live["publication"]=="fit_frame" && live["current"]==false && live["shape_valid"]==true,"Original public frame publication never certifies an adopted current calculation");
            model.sync();c.require(edi_app::assistant_data::reflections(member,model,0,total)==before,"Original sync restores native publication without inspection-side calculation or row sorting");
        }catch(const std::exception& error){c.require(false,QStringLiteral("original SC owner entrance: ")+QString::fromUtf8(error.what()));}
        return c.result();
    }
};
static void registerDataSummaryProof() {
    qmlRegisterSingletonType<DataSummaryProof>("DataSummaryAcceptance",1,0,"DataSummaryProof",[](QQmlEngine*,QJSEngine*)->QObject*{return new DataSummaryProof;});
}
Q_COREAPP_STARTUP_FUNCTION(registerDataSummaryProof)
#include "test_e11_t5_data_summary.moc"
