//  gate 3: crysta's public symmetry API is an independent oracle for edi's app.
// This test-only translation unit is globbed into edi_app_tests, never the product host.
// Parse the Qt-free reference headers before Qt defines its slots keyword macro.
#include <crysta/cell_symmetry.hpp>
#include <crysta/model.hpp>
#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QCryptographicHash>
#include <QObject>
#include <QVariantList>
#include <QtQml/qqml.h>
#include <array>
#include <set>

class SymmetryOracle final : public QObject {
    Q_OBJECT
public:
    using QObject::QObject;
    static QString root() {
        return QDir(QFileInfo(QString::fromUtf8(__FILE__)).absolutePath()).absoluteFilePath("../../..");
    }
    Q_INVOKABLE QString sourceHash(const QString &path) const {
        QFile file(QDir(root()).filePath(path));
        if (!file.open(QIODevice::ReadOnly)) return {};
        return QString::fromLatin1(QCryptographicHash::hash(file.readAll(), QCryptographicHash::Sha256).toHex());
    }
    Q_INVOKABLE QVariantList projects() const {
        QVariantList result;
        const QDir cli(QDir(root()).filePath("docs/user/cli"));
        for (const auto &id : cli.entryList(QDir::Dirs | QDir::NoDotAndDotDot, QDir::Name)) {
            const auto path = cli.filePath(id + "/project");
            if (QFileInfo::exists(path + "/project.edi")) {
                result.append(QVariantMap{{"tag", id}, {"id", id}, {"path", path}});
            }
        }
        return result;
    }
    Q_INVOKABLE QVariantList structure(const QString &directory) const {
        QVariantList result;
        const QDir structures(QDir(root()).absoluteFilePath(directory) + "/structures");
        const auto files = structures.entryList({"*.edi"}, QDir::Files, QDir::Name);
        if (files.size() != 1) {
            qCritical(" gate 3 oracle requires one independently loaded CLI structure");
            return {};
        }
        try {
            const auto reference = crysta::structure_from_edi_path(structures.filePath(files[0]).toStdString());
            const auto freedom = crysta::cell_freedom(reference.space_group.get());
            const std::array<const char *, 6> cellNames{
                "length_a", "length_b", "length_c", "angle_alpha", "angle_beta", "angle_gamma"};
            for (std::size_t axis = 0; axis < 6; ++axis) {
                const int leader = freedom.follows[axis];
                const double value = freedom.is_fixed(axis) ? freedom.fixed[axis]
                    : reference.cell.parameters[static_cast<std::size_t>(leader)].value();
                result.append(QVariantMap{{"category", "cell"}, {"row", ""}, {"name", cellNames[axis]},
                    {"independent", freedom.is_independent(axis)}, {"value", value}});
            }
            const auto constraints = reference.positional_constraints();
            const std::array<const char *, 3> names{"fract_x", "fract_y", "fract_z"};
            for (std::size_t site = 0; site < constraints.sites().size(); ++site) {
                const auto &[label, position] = constraints.sites()[site];
                const auto &atom = reference.atom_sites[site];
                const std::array<double, 3> coordinates{atom.fract[0].value(), atom.fract[1].value(), atom.fract[2].value()};
                std::vector<double> basics(position.n_basic());
                std::set<std::size_t> seen;
                std::array<bool, 3> independent{};
                for (std::size_t axis = 0; axis < 3; ++axis) {
                    if (position.axis_is_basic(axis)) {
                        const auto basic = position.axis_basic_index(axis);
                        independent[axis] = seen.insert(basic).second;
                        if (independent[axis]) basics[basic] = position.axis_basic(axis, coordinates[axis]);
                    }
                }
                const auto [x, y, z] = position.evaluate(basics);
                const std::array<double, 3> implied{x, y, z};
                for (std::size_t axis = 0; axis < 3; ++axis) {
                    result.append(QVariantMap{{"category", "atom_site"}, {"row", QString::fromStdString(label)},
                        {"name", names[axis]}, {"independent", independent[axis]}, {"value", implied[axis]}});
                }
            }
        } catch (const std::exception &error) {
            qCritical(" gate 3 crysta oracle refused: %s", error.what());
        }
        return result;
    }
};

static void registerSymmetryOracle() {
    qmlRegisterSingletonType<SymmetryOracle>("EdiSymmetryReference", 1, 0, "SymmetryOracle",
        [](QQmlEngine *, QJSEngine *) -> QObject * { return new SymmetryOracle; });
}
Q_COREAPP_STARTUP_FUNCTION(registerSymmetryOracle)
#include "test_e04_t5_oracle.moc"
