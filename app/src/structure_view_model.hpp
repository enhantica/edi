// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_STRUCTURE_VIEW_MODEL_HPP
#define EDI_APP_STRUCTURE_VIEW_MODEL_HPP

#include <QObject>
#include <QString>
#include <QStringList>
#include <QtQml/qqmlregistration.h>

#include <map>

#include "adp_preview.hpp"
#include "block_text.hpp"
#include "category_list_model.hpp"
#include "edi/model.hpp"
#include "edi/structure_scene.hpp"
#include "parameter_item.hpp"
#include "project_editor.hpp"
#include "row_table_model.hpp"

namespace edi_app {

class ParameterRegistry;
class ProjectEditor;

// A structure's space group: the setting is editable, the crystal system follows it through
// crysta.
class SpaceGroupViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a structure")
    Q_PROPERTY(QString nameHM READ nameHM WRITE setNameHM NOTIFY nameHMChanged)
    Q_PROPERTY(QString coordSystemCode READ coordSystemCode WRITE setCoordSystemCode NOTIFY coordSystemCodeChanged)
    Q_PROPERTY(int itNumber READ itNumber WRITE setItNumber NOTIFY itNumberChanged)
    Q_PROPERTY(bool hasItNumber READ hasItNumber NOTIFY hasItNumberChanged)
    Q_PROPERTY(QString crystalSystem READ crystalSystem NOTIFY crystalSystemChanged)
    // What the name and code pickers list (the owner, 2026-10-06): every name crysta's table resolves, by IT
    // number, and the codes of the shown space group's settings.
    Q_PROPERTY(QStringList names READ names CONSTANT)
    Q_PROPERTY(QStringList codes READ codes NOTIFY codesChanged)

   public:
    SpaceGroupViewModel(edi::Structure& structure, ProjectEditor& editor, QObject* parent);
    QString nameHM() const { return name_hm_; }
    void setNameHM(const QString& name);
    QString coordSystemCode() const { return code_; }
    void setCoordSystemCode(const QString& code);
    int itNumber() const { return it_number_; }
    // A new name or number chooses that space group's default setting, and a new code that setting's name, so
    // name, code and number always agree; a name or code crysta's table does not have is stored as typed, for the
    // calculation to say why it refuses it. A number of 0 or less clears the stored number.
    void setItNumber(int number);
    bool hasItNumber() const { return it_number_ > 0; }
    QString crystalSystem() const { return crystal_system_; }
    QStringList names() const;
    QStringList codes() const { return codes_; }
    void sync();

   signals:
    void codesChanged();
    void nameHMChanged();
    void coordSystemCodeChanged();
    void itNumberChanged();
    void hasItNumberChanged();
    void crystalSystemChanged();

   private:
    edi::Structure& structure_;
    ProjectEditor& editor_;
    QString name_hm_, code_, crystal_system_;
    QStringList codes_;
    int it_number_ = 0;
};

// The six cell parameters.
class CellViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a structure")
    Q_PROPERTY(edi_app::ParameterItem* lengthA READ lengthA NOTIFY lengthAChanged)
    Q_PROPERTY(edi_app::ParameterItem* lengthB READ lengthB NOTIFY lengthBChanged)
    Q_PROPERTY(edi_app::ParameterItem* lengthC READ lengthC NOTIFY lengthCChanged)
    Q_PROPERTY(edi_app::ParameterItem* angleAlpha READ angleAlpha NOTIFY angleAlphaChanged)
    Q_PROPERTY(edi_app::ParameterItem* angleBeta READ angleBeta NOTIFY angleBetaChanged)
    Q_PROPERTY(edi_app::ParameterItem* angleGamma READ angleGamma NOTIFY angleGammaChanged)

   public:
    CellViewModel(edi::Structure& structure, ParameterRegistry& registry, QObject* parent);
    ParameterItem* lengthA() const { return items_[0]; }
    ParameterItem* lengthB() const { return items_[1]; }
    ParameterItem* lengthC() const { return items_[2]; }
    ParameterItem* angleAlpha() const { return items_[3]; }
    ParameterItem* angleBeta() const { return items_[4]; }
    ParameterItem* angleGamma() const { return items_[5]; }
    void sync();

   signals:
    void lengthAChanged();
    void lengthBChanged();
    void lengthCChanged();
    void angleAlphaChanged();
    void angleBetaChanged();
    void angleGammaChanged();

   private:
    edi::Structure& structure_;
    ParameterRegistry& registry_;
    ParameterItem* items_[6] = {};
};

// The atom sites: label, type, Wyckoff letter and ADP type editable as text; coordinates, occupancy
// and Biso as ParameterItems; append, duplicate and remove as the library's AtomSites collection
// does.
class AtomSiteListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a structure")

   public:
    AtomSiteListModel(edi::Structure& structure, ProjectEditor& editor, ParameterRegistry& registry, QObject* parent);
    void sync();
    Q_INVOKABLE bool setText(int row, const QString& role, const QString& value);
    Q_INVOKABLE void append();
    Q_INVOKABLE void duplicate(int row);
    Q_INVOKABLE void remove(int row);

   protected:
    bool setRole(int row, const QString& role, const QVariant& value) override { return setText(row, role, value.toString()); }

   private:
    edi::Structure& structure_;
    ProjectEditor& editor_;
    ParameterRegistry& registry_;
};

// The Atomic displacement group (the owner, 2026-10-06): one row per atom site, in the sites' order — its label,
// ADP type, isotropic value and the six anisotropic components. Biso is the stored, calculated type; the others are
// the draft's previews (adp_preview.hpp), shown with `active` false. For an isotropic type `iso` is editable and the
// six are empty; for an anisotropic type the six are editable and `iso` is the equivalent value, read only.
class AtomSiteAdpListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a structure")
    // The types the group offers, in diffraction-lib's AdpTypeEnum order as the owner listed them.
    Q_PROPERTY(QStringList types READ types CONSTANT)
    // Some site has a type the calculation does not use yet.
    Q_PROPERTY(bool hasPreview READ hasPreview NOTIFY hasPreviewChanged)

   public:
    AtomSiteAdpListModel(edi::Structure& structure, ProjectEditor& editor, ParameterRegistry& registry,
                         std::map<const edi::AtomSite*, AdpPreview>& previews, QObject* parent);
    QStringList types() const;
    bool hasPreview() const { return has_preview_; }
    void sync();
    Q_INVOKABLE void setType(int row, const QString& type);
    // The isotropic value in the row's type (B for Biso, U for Uiso).
    Q_INVOKABLE void setIso(int row, double value);
    // One anisotropic component, 0 to 5 in the order 11, 22, 33, 12, 13, 23.
    Q_INVOKABLE void setComponent(int row, int component, double value);

   signals:
    void hasPreviewChanged();
    // A preview changed: the structure view redraws its ellipsoids.
    void previewsChanged();

   private:
    AdpCell cell() const;
    edi::Structure& structure_;
    ProjectEditor& editor_;
    ParameterRegistry& registry_;
    std::map<const edi::AtomSite*, AdpPreview>& previews_;
    bool has_preview_ = false;
};

// The structure's custom neutron scattering lengths.
class ScatteringLengthListModel : public RowTableModel {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a structure")

   public:
    ScatteringLengthListModel(edi::Structure& structure, ProjectEditor& editor, QObject* parent);
    void sync();
    Q_INVOKABLE bool setTypeSymbol(int row, const QString& symbol);
    Q_INVOKABLE bool setLengthFm(int row, double length);
    Q_INVOKABLE void append();
    Q_INVOKABLE void remove(int row);

   protected:
    bool setRole(int row, const QString& role, const QVariant& value) override {
        return role == QLatin1String("typeSymbol") ? setTypeSymbol(row, value.toString())
               : role == QLatin1String("lengthFm") ? setLengthFm(row, value.toDouble())
                                                   : false;
    }

   private:
    QString symbolAt(int row) const;
    edi::Structure& structure_;
    ProjectEditor& editor_;
};

// One structure of the project.
class StructureViewModel : public QObject {
    Q_OBJECT
    QML_ELEMENT
    QML_UNCREATABLE("Belongs to a project")
    Q_PROPERTY(QString name READ name WRITE setName NOTIFY nameChanged)
    Q_PROPERTY(edi_app::SpaceGroupViewModel* spaceGroup READ spaceGroup CONSTANT)
    Q_PROPERTY(edi_app::CellViewModel* cell READ cell CONSTANT)
    Q_PROPERTY(edi_app::AtomSiteListModel* atomSites READ atomSites CONSTANT)
    Q_PROPERTY(edi_app::AtomSiteAdpListModel* atomSiteAdps READ atomSiteAdps CONSTANT)
    Q_PROPERTY(edi_app::ScatteringLengthListModel* scatteringLengths READ scatteringLengths CONSTANT)
    Q_PROPERTY(edi_app::CategoryListModel* categories READ categories CONSTANT)
    Q_PROPERTY(edi_app::BlockText* text READ text CONSTANT)

   public:
    StructureViewModel(SavedFile saved, edi::Structure& structure, ProjectEditor& editor,
                       ParameterRegistry& registry, QObject* parent);
    QString name() const { return name_; }
    void setName(const QString& name);
    SpaceGroupViewModel* spaceGroup() const { return space_group_; }
    CellViewModel* cell() const { return cell_; }
    AtomSiteListModel* atomSites() const { return atom_sites_; }
    AtomSiteAdpListModel* atomSiteAdps() const { return atom_site_adps_; }
    // The draft's ADP previews by site (adp_preview.hpp); the structure view draws ellipsoids from them.
    const std::map<const edi::AtomSite*, AdpPreview>& adpPreviews() const { return adp_previews_; }
    ScatteringLengthListModel* scatteringLengths() const { return scattering_lengths_; }
    CategoryListModel* categories() const { return categories_; }
    BlockText* text() const { return text_; }
    const edi::Structure* structure() const { return &structure_; }
    void sync();
    // ADR-0022: the structure's immutable scene source, captured on this (the owner) thread when the
    // view-model is created and in the publication hook, and nowhere else. Between an admitted edit that
    // stales the geometry and its publication, the source is marked not current.
    const edi::SceneSource& sceneSource() const { return scene_source_; }
    void captureScene();
    // The draft's anisotropic previews into the captured source, for the ADP view's ellipsoids.
    void applyAdpPreviews();
    void markSceneStale();

   signals:
    void nameChanged();
    void sceneSourceChanged();
    void sceneWentStale();

   private:
    edi::Structure& structure_;
    edi::SceneSource scene_source_;
    ProjectEditor& editor_;
    QString name_;
    std::map<const edi::AtomSite*, AdpPreview> adp_previews_;
    SpaceGroupViewModel* space_group_;
    CellViewModel* cell_;
    AtomSiteListModel* atom_sites_;
    AtomSiteAdpListModel* atom_site_adps_;
    ScatteringLengthListModel* scattering_lengths_;
    CategoryListModel* categories_;
    BlockText* text_;
};

}  // namespace edi_app

#endif  // EDI_APP_STRUCTURE_VIEW_MODEL_HPP
