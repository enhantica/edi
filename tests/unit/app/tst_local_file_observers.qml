import QtQuick
import QtTest
import edi.app
import ReportAcceptance 1.0

TestCase {
    name: "LocalFileObservers"
    when: windowShown
    function test_actual_owned_path_domains_and_ambient_refusal() {
        failOnWarning(/.*/);
        const owned = SettingsProof.emptyDirectory();
        const plain = SettingsProof.localPath(owned);
        verify(plain.length > 0, "The positive root is an actual owned absolute local directory");
        const adapted = Session.projectDirectoryUrl(plain);
        compare(String(adapted), String(owned), "The existing public adapter preserves actual local URL identity");
        const name = "owned # Ω.txt", expected = "independent-reader-control";
        verify(SettingsProof.write(owned, name, expected), "The positive witness is an actual owned file");
        compare(SettingsProof.text(owned, name), expected);
        compare(SettingsProof.text(adapted, name), expected, "A genuine native QString path is explicitly adapted before the typed observer");
        compare(SettingsProof.text(plain, name), "", "A plain absolute QString is not silently a typed file URL");
        compare(Object.keys(SettingsProof.fileFacts(plain, name)).length, 0, "Wrong-root refusal cannot be reinterpreted as supported-root absence");
        const facts = SettingsProof.fileFacts(adapted, name);
        verify(facts.exists && facts.regular && facts.readable && facts.bytes > 0 && facts.sha256.length === 64, "Positive bytes retain concrete file admission and hash fields");
        compare(String(SettingsProof.childUrl(owned, name)), String(Session.projectDirectoryUrl(plain + "/" + name)), "Reserved and Unicode filename bytes use the existing local-file encoder");
        const missing = SettingsProof.fileFacts(owned, "absent.txt");
        compare(Object.keys(missing).length, 3, "Supported-root absence is a precise receipt");
        compare(missing.exists, false);
        compare(missing.regular, false);
        compare(missing.readable, false);
        verify(SettingsProof.write(owned, "nested/control.txt", expected), "The non-file witness is an actual owned directory");
        const directory = SettingsProof.fileFacts(owned, "nested");
        verify(directory.exists === true && directory.regular === false && directory.readable === false, "An existing non-file is distinct from absence and is never opened as content");
        const wrong = Session.projectDirectoryUrl(plain + "/absent-directory");
        verify(SettingsProof.projectBytes(wrong).error !== undefined, "A genuinely absent directory is refused");
        compare(SettingsProof.text(wrong, name), "", "A missing directory never falls through to ambient CWD");
        compare(String(SettingsProof.copyProject(wrong)), "", "Copy refuses an absent source rather than manufacturing an empty project");
        const proof = SettingsProof.localRootBoundaryProof(owned);
        verify(proof.error === undefined && proof.cwdRestored, "The real ambient escape is scoped and restored on the existing helper owner");
        compare(proof.rows.length, 10, "Every independently authored URL/settings-domain control actually executes");
        for (const row of proof.rows)
            for (const key of Object.keys(row))
                if (key !== "name") compare(row[key], true, "Actual local observer refuses " + row.name + ":" + key);
    }
    function test_actual_archive_creator_failure_cannot_copy_into_ambient_directory() {
        failOnWarning(/.*/);
        const owned = SettingsProof.emptyDirectory();
        verify(String(owned).startsWith("file:"), "The failure contrast starts from an actual owned directory");
        try {
            verify(Session.openProject(Qt.resolvedUrl("../../fixtures/table_display")), "The source is a genuine independently declared project");
            const source = SettingsProof.childUrl(owned, "source.zip");
            verify(Session.saveProjectAs(source, true, false), "The ordinary app publishes a real source archive: " + Session.lastError);
            Session.closeProject();
            const sourceFacts = SettingsProof.fileFacts(owned, "source.zip");
            verify(sourceFacts.exists === true && sourceFacts.regular === true && sourceFacts.readable === true && sourceFacts.bytes > 0, "The explicit ZIP route publishes an actual nonempty regular readable archive");
            const original = SettingsProof.projectArchiveBytes(source);
            verify(original.length > 0, "The archive positive is actual saved bytes");
            const copied = SettingsProof.copyProjectArchive(source);
            verify(String(copied).startsWith("file:"), "The ordinary valid destination factory remains available");
            compare(SettingsProof.projectArchiveBytes(copied), original, "The valid local archive copy preserves every byte");
            const proof = SettingsProof.archiveCreationFailureProof(source, owned);
            verify(proof.error === undefined, "The actual creator-failure control is genuinely armed");
            for (const key of ["temporaryParentArmed", "creatorActuallyFailed", "archiveCopyRefused", "noAmbientArchive", "environmentRestored", "cwdRestored"])
                compare(proof[key], true, "Actual generated-root boundary: " + key);
            compare(SettingsProof.projectArchiveBytes(source), original, "The failed destination cannot mutate the source archive");
        } finally {
            Session.closeProject();
        }
    }

}
