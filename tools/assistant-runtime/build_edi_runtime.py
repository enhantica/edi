#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Build the original pinned app-server target with Edi's explicit policy feature.

Offline inputs only. This tool never installs dependencies or modifies an
existing source/package tree. Invoke only after source review/build authority.
An output archive is a build artifact, not proof of enforcement qualification.
"""
import argparse
import copy
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tomllib

SOURCE_SHA256 = "79c8ea8547e1dd9969f63ef6b76a4fb0d1a024ef36c0c627fbcd2ffb658d9312"
SOURCE_LOCK_SHA256 = "49fe417bcafe3f69f1f6636e23274f90d37e75e388127a76888c39001a4f8117"
SOURCE_WORKSPACE_SHA256 = "c31fb138f0167e885a0dd349534b615a265f4190e7264a112070e7ea57188b05"
SOURCE_LOCAL_MANIFESTS_SHA256 = "8144897126a7bedbabd6435912f9462bde8ddf139df81f9ab3ec73aba472d794"
UPSTREAM_COMMIT = "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d"
PACKAGES = {
    "aarch64-apple-darwin": "28c0e2fbfb39a422dcfdd5bb87027a12242da7fa2dc997811bc0a6d2316c4f93",
    "x86_64-unknown-linux-musl": "8748f9f8b708b3bc5a52b3f0a1ccddb22e6985f0efb4f45dafa1677e324abe0e",
}

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def verified(path, expected):
    if path.is_symlink() or not path.is_file() or digest(path) != expected:
        raise ValueError("Pinned archive identity mismatch")

def extract(archive, target, source):
    # Pinned inputs contain one source-only license alias. Resolve that exact
    # entry using archive members, never a filesystem link or host path.
    alias = f"codex-{UPSTREAM_COMMIT}/codex-rs/vendor/bubblewrap/LICENSE"
    alias_target = str(PurePosixPath(alias).with_name("COPYING"))
    with tarfile.open(archive) as stream:
        members = {}
        for member in stream:
            path = PurePosixPath(member.name)
            if not member.name or path.is_absolute() or ".." in path.parts or path == PurePosixPath("."):
                raise ValueError("Archive member escapes its package")
            key = path.as_posix()
            if key in members:
                raise ValueError("Archive member identity is duplicated")
            if not (member.isdir() or member.isfile()):
                if not (source and member.issym() and member.name == alias and member.linkname == "COPYING"):
                    raise ValueError("Archive member is not a permitted regular file alias")
            members[key] = member
        if alias in members and members[alias].issym():
            original = members.get(alias_target)
            if original is None or not original.isfile() or original.size != 25383 or original.mode != 0o664:
                raise ValueError("Pinned license alias target is unavailable")
            with stream.extractfile(original) as incoming:
                if hashlib.file_digest(incoming, "sha256").hexdigest() != "b7993225104d90ddd8024fd838faf300bea5e83d91203eab98e29512acebd69c":
                    raise ValueError("Pinned license alias target identity mismatch")
        # Only a new owned root is populated, and no member creates a symlink.
        # Existing filesystem nodes cannot redirect later regular-file writes.
        target.mkdir(exist_ok=False)
        for member in members.values():
            name = member.name.partition("/")[2] if source else member.name
            path = PurePosixPath(name)
            if not name or (source and not name.startswith("codex-rs/")):
                continue
            if member.isdir():
                continue
            original = members[alias_target] if member.issym() else member
            destination = target.joinpath(*path.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with stream.extractfile(original) as incoming, destination.open("xb") as output:
                shutil.copyfileobj(incoming, output)
            destination.chmod(original.mode & 0o777)


def normalize_release_lock(workspace):
    # Upstream release tags bump the workspace version without rewriting the
    # lock. Reconcile only that known mismatch; never resolve dependencies here.
    lock = workspace / "Cargo.lock"
    backup = workspace / "Cargo.lock.original"
    if lock.is_symlink() or not lock.is_file() or backup.exists() or backup.is_symlink():
        raise ValueError("Release lock paths are not fresh regular inputs")
    original = lock.read_bytes()
    if hashlib.sha256(original).hexdigest() != SOURCE_LOCK_SHA256:
        raise ValueError("Pinned release lock identity mismatch")
    before = tomllib.loads(original.decode("utf-8"))
    manifest_path = workspace / "Cargo.toml"
    verified(manifest_path, SOURCE_WORKSPACE_SHA256)
    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))["workspace"]
    version = manifest["package"]["version"]
    if version != "0.162.1":
        raise ValueError("Pinned release workspace version mismatch")
    paths = set(manifest["members"])
    paths.update(value["path"] for value in manifest["dependencies"].values()
                 if isinstance(value, dict) and "path" in value)
    versions = {}
    manifest_identity = hashlib.sha256()
    for name in sorted(paths):
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or path == PurePosixPath("."):
            raise ValueError("Local release manifest escapes its workspace")
        local = workspace.joinpath(*path.parts) / "Cargo.toml"
        if local.is_symlink() or not local.is_file():
            raise ValueError("Local release manifest is not a regular file")
        raw = local.read_bytes()
        manifest_identity.update(name.encode("utf-8") + b"\0" + hashlib.sha256(raw).digest())
        package = tomllib.loads(raw.decode("utf-8"))["package"]
        if package["version"] != {"workspace": True} or package["name"] in versions:
            raise ValueError("Local release package version is ambiguous")
        versions[package["name"]] = version
    if manifest_identity.hexdigest() != SOURCE_LOCAL_MANIFESTS_SHA256:
        raise ValueError("Pinned local release manifest identity mismatch")
    packages = before["package"]
    local_names = [package["name"] for package in packages if "source" not in package]
    if len(local_names) != len(set(local_names)) or set(local_names) != set(versions):
        raise ValueError("Release lock local packages do not match their manifests")
    expected = copy.deepcopy(before)
    for package in expected["package"]:
        if "source" not in package:
            if package["version"] != "0.0.0" or "checksum" in package:
                raise ValueError("Local release lock has unexpected metadata")
            package["version"] = versions[package["name"]]
    blocks = original.split(b"[[package]]\n")
    if len(blocks) != len(packages) + 1:
        raise ValueError("Pinned release lock layout mismatch")
    for index, package in enumerate(packages, 1):
        if "source" not in package:
            blocks[index], count = re.subn(rb'^version = "0.0.0"$',
                b'version = "' + versions[package["name"]].encode("ascii") + b'"',
                blocks[index], flags=re.MULTILINE)
            if count != 1:
                raise ValueError("Local release version is not uniquely represented")
    normalized = b"[[package]]\n".join(blocks)
    # Includes every external version/revision/checksum/source, dependency edge
    # and root/package metadata. Any other parsed delta refuses before writes.
    if tomllib.loads(normalized.decode("utf-8")) != expected:
        raise ValueError("Release lock changed beyond local workspace versions")
    if lock.is_symlink() or lock.read_bytes() != original:
        raise ValueError("Release lock changed during normalization")
    with backup.open("xb") as output:
        output.write(original)
    lock.write_bytes(normalized)
    return {"original": {"sha256": hashlib.sha256(original).hexdigest(), "bytes": len(original)},
            "normalized": {"sha256": hashlib.sha256(normalized).hexdigest(), "bytes": len(normalized)},
            "workspaceVersion": version, "localPackages": sorted(versions)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--official-package", type=Path, required=True)
    parser.add_argument("--target", choices=PACKAGES, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    verified(args.source_archive, SOURCE_SHA256)
    verified(args.official_package, PACKAGES[args.target])
    patch = Path(__file__).with_name("edi-app-server.patch")
    patch_digest = digest(patch)
    if not args.work.is_absolute() or not args.output.is_absolute() or args.output.exists() or args.output.is_symlink():
        raise ValueError("Build paths must be new explicit absolute destinations")
    args.work.mkdir(exist_ok=False)
    source = args.work / "source"
    package = args.work / "package"
    extract(args.source_archive, source, True)
    extract(args.official_package, package, False)
    source_lock = normalize_release_lock(source / "codex-rs")
    subprocess.run(["git", "apply", "--check", str(patch)], cwd=source, check=True)
    subprocess.run(["git", "apply", str(patch)], cwd=source, check=True)
    environment = dict(os.environ, EDI_SOURCE_PATCH_SHA256=patch_digest)
    subprocess.run(["cargo", "build", "--frozen", "--release", "--package", "codex-app-server", "--features", "edi-runtime", "--target", args.target],
                   cwd=source / "codex-rs", env=environment, check=True)
    executable = source / "codex-rs" / "target" / args.target / "release" / "codex-app-server"
    shutil.copyfile(executable, package / "bin" / "codex-app-server")
    (package / "bin" / "codex-app-server").chmod(0o755)
    manifest = package / "codex-package.json"
    metadata = json.loads(manifest.read_text())
    if metadata.get("version") != "0.162.1" or metadata.get("target") != args.target or metadata.get("variant") != "codex-app-server":
        raise ValueError("Pinned package layout mismatch")
    metadata.update(ediPolicySchema="edi.runtime-policy/1", ediFlavour="edi-app-server/1", upstreamCommit=UPSTREAM_COMMIT, sourcePatchSha256=patch_digest)
    manifest.write_text(json.dumps(metadata, indent=2) + "\n")
    # Preserve original relative resources and package layout; only the original
    # app-server executable and explicit manifest extension have changed.
    with tarfile.open(args.output, "x:gz") as archive:
        for entry in sorted(package.iterdir()):
            archive.add(entry, arcname=entry.name, recursive=True)
    facts = {"sourcePatchSha256": patch_digest, "archiveSha256": digest(args.output), "executableSha256": digest(executable),
             "target": args.target, "flavour": "edi-app-server/1", "sourceLock": source_lock, "qualified": False}
    args.output.with_suffix(args.output.suffix + ".build.json").write_text(json.dumps(facts, indent=2) + "\n")

if __name__ == "__main__":
    main()
