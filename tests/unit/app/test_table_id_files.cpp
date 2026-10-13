// SPDX-License-Identifier: BSD-3-Clause
#include <QtQml/qqml.h>

#include <QCoreApplication>
#include <QObject>
#include <QTemporaryDir>
#include <QUrl>

class TableIdFiles : public QObject {
    Q_OBJECT
   public:
    using QObject::QObject;
    Q_INVOKABLE QUrl directory() const { return QUrl::fromLocalFile(directory_.path()); }

   private:
    QTemporaryDir directory_;
};
static void register_table_id_files() {
    qmlRegisterType<TableIdFiles>("TableIdTests", 1, 0, "TableIdFiles");
}
Q_COREAPP_STARTUP_FUNCTION(register_table_id_files)
#include "test_table_id_files.moc"
