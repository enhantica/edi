// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_EXPERIMENT_MODELS_HPP
#define EDI_APP_EXPERIMENT_MODELS_HPP

#include <QStringList>
#include <QtQml/qqmlregistration.h>
#include <functional>

#include "edi/categories.hpp"
#include "edi/model.hpp"
#include "option_list_model.hpp"
#include "row_table_model.hpp"

namespace edi_app {

class ParameterRegistry;
class ProjectEditor;

// A category's shown parameter fields: the core's *_categories fields — never the model's storage
// walk. Roles `parameter` (ParameterItem), `name` (the `.edi` item name),
// `displayName`, `shortName` (the field's symbol), `displayUnits` and `usedByProfile` (false for a
// field outside the profile's set, shown because it is free). `usedCount` counts the fields the profile uses:
// the sidebar shows only those (edi ADR-0017 §5).
class ParameterListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a category")
    Q_PROPERTY(int usedCount READ usedCount NOTIFY usedCountChanged)

   public:
    using Fields = std::function<std::vector<edi::CategoryField>()>;
    ParameterListModel(Fields fields, ParameterRegistry& registry, QObject* parent);
    void sync();
    int usedCount() const { return used_count_; }

   signals:
    void usedCountChanged();

   private:
    Fields fields_;
    ParameterRegistry& registry_;
    int used_count_ = 0;
};

// The line-segment background points: `position` (text-editable) and `intensity` (ParameterItem).
class BackgroundListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to an experiment")

   public:
    BackgroundListModel(edi::ExperimentBase& experiment, ProjectEditor& editor, ParameterRegistry& registry,
                        QObject* parent);
    void sync();
    Q_INVOKABLE bool setPosition(int row, double position);
    Q_INVOKABLE void append();
    Q_INVOKABLE void remove(int row);

   protected:
    bool setRole(int row, const QString& role, const QVariant& value) override {
        return role == QLatin1String("position") && setPosition(row, value.toDouble());
    }

   private:
    edi::ExperimentBase& experiment_;
    ProjectEditor& editor_;
    ParameterRegistry& registry_;
};

// The reflections the loaded file carried (`_refln`), read-only: `hkl` ("h k l"),
// `dSpacing`, `position` (2θ or TOF) and `fSquaredCalc`, numbers as read; NaN where a cell is not one.
class ReflectionListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to an experiment")

   public:
    ReflectionListModel(const edi::ExperimentBase& experiment, QObject* parent);
    void sync();

   private:
    const edi::ExperimentBase& experiment_;
};

// The excluded regions: `start`, `end` pairs, editable, with append and remove.
class ExcludedRegionListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to an experiment")

   public:
    ExcludedRegionListModel(edi::ExperimentBase& experiment, ProjectEditor& editor, QObject* parent);
    void sync();
    Q_INVOKABLE bool setStart(int row, double start);
    Q_INVOKABLE bool setEnd(int row, double end);
    Q_INVOKABLE void append();
    Q_INVOKABLE void remove(int row);

   protected:
    bool setRole(int row, const QString& role, const QVariant& value) override {
        return role == QLatin1String("start") ? setStart(row, value.toDouble())
               : role == QLatin1String("end") ? setEnd(row, value.toDouble())
                                              : false;
    }

   private:
    edi::ExperimentBase& experiment_;
    ProjectEditor& editor_;
};

// The experiment's linked structures (phases): roles `structureId`, `scale` (ParameterItem), `enabled` and
// `colorIndex` (the structure's place in the project, its colour). `structureNames` lists the project's
// structures, the choices of a row's name. A row is added naming a structure not yet linked, removed while
// another remains, and disabled — kept and saved, but neither calculated nor fitted.
class LinkedStructureListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to an experiment")
    Q_PROPERTY(QStringList structureNames READ structureNames NOTIFY structureNamesChanged)
    Q_PROPERTY(bool canAppend READ canAppend NOTIFY canAppendChanged)
    Q_PROPERTY(bool canRemove READ canRemove NOTIFY canRemoveChanged)

   public:
    LinkedStructureListModel(edi::Project& project, edi::ExperimentBase& experiment, ProjectEditor& editor,
                             ParameterRegistry& registry, QObject* parent);
    void sync();
    QStringList structureNames() const { return structure_names_; }
    bool canAppend() const { return can_append_; }
    bool canRemove() const { return can_remove_; }
    Q_INVOKABLE bool setStructureId(int row, const QString& id);
    Q_INVOKABLE bool setEnabled(int row, bool enabled);
    Q_INVOKABLE void append();
    Q_INVOKABLE void remove(int row);

   protected:
    bool setRole(int row, const QString& role, const QVariant& value) override {
        return role == QLatin1String("structureId") ? setStructureId(row, value.toString())
               : role == QLatin1String("enabled")   ? setEnabled(row, value.toBool())
                                                    : false;
    }

   signals:
    void structureNamesChanged();
    void canAppendChanged();
    void canRemoveChanged();

   private:
    edi::Project& project_;
    edi::ExperimentBase& experiment_;
    ProjectEditor& editor_;
    ParameterRegistry& registry_;
    QStringList structure_names_;
    bool can_append_ = false;
    bool can_remove_ = false;
};

// The preferred-orientation rows: `structureId`, the texture axis `indexH/K/L` (the library's bounds,
// edits.hpp), and `marchR`, `marchRandomFract` (ParameterItems); one row per textured linked structure.
class PrefOrientListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to an experiment")
    Q_PROPERTY(bool canAppend READ canAppend NOTIFY canAppendChanged)

   public:
    PrefOrientListModel(edi::ExperimentBase& experiment, ProjectEditor& editor, ParameterRegistry& registry,
                        QObject* parent);
    void sync();
    bool canAppend() const { return can_append_; }
    Q_INVOKABLE bool setStructureId(int row, const QString& id);
    Q_INVOKABLE bool setIndex(int row, const QString& axis, int value);
    Q_INVOKABLE void append();
    Q_INVOKABLE void remove(int row);

   protected:
    bool setRole(int row, const QString& role, const QVariant& value) override {
        if (role == QLatin1String("structureId")) {
            return setStructureId(row, value.toString());
        }
        return role.startsWith(QLatin1String("index")) && setIndex(row, role.mid(5).toLower(), value.toInt());
    }

   signals:
    void canAppendChanged();

   private:
    edi::ExperimentBase& experiment_;
    ProjectEditor& editor_;
    ParameterRegistry& registry_;
    bool can_append_ = true;
};

// The scattering-source items of the experiment's probe: roles `name` (the
// `.edi` item name), `token` (the stored value, empty when absent), `effectiveToken` (what the engine
// uses), `isDeclared` and `options` (OptionListModel of the known values).
class ScatteringSourceViewModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to an experiment")

   public:
    ScatteringSourceViewModel(edi::ExperimentBase& experiment, ProjectEditor& editor, QObject* parent);
    void sync();
    // Select a known value for the named item (select_scattering_source); true on success.
    Q_INVOKABLE bool select(const QString& name, const QString& token);
    Q_INVOKABLE edi_app::OptionListModel* optionsFor(const QString& name) const;

   protected:
    bool setRole(int row, const QString& role, const QVariant& value) override {
        return role == QLatin1String("token") && select(get(row, QStringLiteral("name")).toString(), value.toString());
    }

   private:
    edi::ExperimentBase& experiment_;
    ProjectEditor& editor_;
    QHash<QString, OptionListModel*> options_;
};

}  // namespace edi_app

#endif  // EDI_APP_EXPERIMENT_MODELS_HPP
