// SPDX-License-Identifier: BSD-3-Clause
pragma Singleton
import QtQuick
import QtCore

import EasyApplication.Gui.Globals as EaGlobals

import edi.app

// The folder each kind of file or folder dialog last chose, kept across sessions in the app settings: a dialog opens
// there, or at its own default when the folder is gone.
QtObject {
    id: folders

    property Settings store: Settings {
        location: EaGlobals.Vars.settingsFile
        category: "DialogFolders"
    }
    // Where a dialog of `kind` opens: the folder it last chose, else `fallback` (empty: the dialog's own default).
    function folder(kind: string, fallback: url): url {
        return ApplicationInfo.rememberedFolder(String(folders.store.value(kind, "")), fallback);
    }
    // Remembers the folder holding `chosen` (a file, or a folder: its parent, where the user was looking).
    function remember(kind: string, chosen: url) {
        if (chosen.toString() !== "")
            folders.store.setValue(kind, ApplicationInfo.folderOf(chosen).toString());
    }
}
