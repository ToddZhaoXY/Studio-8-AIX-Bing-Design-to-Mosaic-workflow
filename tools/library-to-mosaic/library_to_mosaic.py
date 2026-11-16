#!/usr/bin/env python3
"""Traceable, local-only preparation for Library → Mosaic conversions (stdlib)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import stat
import sys
import unicodedata
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

VERSION = "0.2.0"
MANIFEST = "BUILD-MANIFEST.json"
MAX_FILES = 10_000
MAX_MEMBER_BYTES = 128 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024


class PackageError(ValueError):
    """The input cannot be accepted without guessing or unsafe extraction."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PackageError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def safe_member_name(name: str, *, directory: bool = False) -> str:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise PackageError(f"Unsafe ZIP path: {name!r}")
    if any(ord(char) < 32 for char in name):
        raise PackageError(f"Control character in ZIP path: {name!r}")
    trimmed = name[:-1] if directory and name.endswith("/") else name
    parts = trimmed.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise PackageError(f"Unsafe ZIP path: {name!r}")
    if PurePosixPath(trimmed).is_absolute():
        raise PackageError(f"Absolute ZIP path: {name!r}")
    return trimmed


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def write_new_json(path: Path, value) -> None:
    """Never overwrite user-maintained specifications or prior evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json_text(value))


class LibraryPackage:
    """An adapter boundary: verified release bytes + versioned source metadata.

    Selection-specific extractors should consume `manifest`, `provenance`, and
    `read_verified(name)`, then emit a design-spec. They must not infer runtime
    Mosaic support from the library's own export/schema validation.
    """

    def __init__(self, path: Path):
        self.path = path.resolve(strict=True)
        self.archive = zipfile.ZipFile(self.path)
        try:
            self.members = self._check_members()
            self.manifest_bytes = self.archive.read(MANIFEST)
            self.manifest = json.loads(
                self.manifest_bytes.decode("utf-8"), object_pairs_hook=unique_object
            )
            self._check_manifest()
            for name in self.manifest["files"]:
                self.read_verified(name)
            self.provenance = self._provenance()
        except BaseException:
            self.archive.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.archive.close()

    def _check_members(self) -> dict[str, zipfile.ZipInfo]:
        infos = self.archive.infolist()
        if len(infos) > MAX_FILES:
            raise PackageError(f"ZIP exceeds {MAX_FILES} members")
        if sum(info.file_size for info in infos) > MAX_TOTAL_BYTES:
            raise PackageError("ZIP exceeds total uncompressed size limit")
        members, seen, kinds = {}, {}, {}
        for info in infos:
            # orig_filename retains embedded NUL that ZipInfo.filename truncates.
            name = safe_member_name(info.orig_filename, directory=info.is_dir())
            folded = unicodedata.normalize("NFC", name).casefold()
            if folded in seen:
                raise PackageError(f"Duplicate/colliding ZIP paths: {seen[folded]!r}, {name!r}")
            seen[folded] = name
            kind = stat.S_IFMT(info.external_attr >> 16)
            allowed = (0, stat.S_IFDIR) if info.is_dir() else (0, stat.S_IFREG)
            if kind not in allowed:
                raise PackageError(f"Symlink or special ZIP member: {name}")
            if info.flag_bits & 1:
                raise PackageError(f"Encrypted ZIP member: {name}")
            if info.file_size > MAX_MEMBER_BYTES:
                raise PackageError(f"ZIP member exceeds size limit: {name}")
            kinds[folded] = info.is_dir()
            if not info.is_dir():
                members[name] = info
        for name in seen:
            for parent in PurePosixPath(name).parents:
                if str(parent) != "." and kinds.get(str(parent)) is False:
                    raise PackageError(f"File/directory collision: {seen[name]}")
        if MANIFEST not in members:
            raise PackageError(f"Missing root {MANIFEST}")
        return members

    def _check_manifest(self):
        manifest = self.manifest
        if not isinstance(manifest, dict) or manifest.get("format") != 3:
            raise PackageError("Only BUILD-MANIFEST format 3 is supported")
        files = manifest.get("files")
        if not isinstance(files, dict) or not files:
            raise PackageError("Manifest.files must be a nonempty path → SHA-256 object")
        for name, checksum in files.items():
            safe_member_name(name)
            if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
                raise PackageError(f"Invalid SHA-256 for {name}")
        actual = set(self.members) - {MANIFEST}
        if set(files) != actual:
            raise PackageError(
                f"Manifest membership mismatch; missing={sorted(set(files) - actual)}, "
                f"unlisted={sorted(actual - set(files))}"
            )
        entries = manifest.get("entries", {})
        assets = manifest.get("assets", {})
        if not isinstance(entries, dict) or not isinstance(assets, dict):
            raise PackageError("Manifest.entries and assets must be objects")
        references = list(assets.values())
        for entry in entries.values():
            if not isinstance(entry, dict):
                raise PackageError("Every manifest entry must be an object")
            references.extend(entry.values())
        for name in references:
            if not isinstance(name, str) or name not in files:
                raise PackageError(f"Manifest references an unverified member: {name!r}")

    def read_verified(self, name: str) -> bytes:
        if not isinstance(name, str) or name not in self.manifest["files"]:
            raise PackageError(f"Not a manifest-verified member: {name}")
        data = self.archive.read(self.members[name])
        if sha256_bytes(data) != self.manifest["files"][name]:
            raise PackageError(f"SHA-256 mismatch: {name}")
        return data

    def _provenance(self) -> dict:
        return {
            "formatVersion": 1,
            "tool": {"name": "library-to-mosaic", "version": VERSION},
            "checkedAt": datetime.now(timezone.utc).isoformat(),
            "package": {
                "path": str(self.path),
                "sha256": sha256_file(self.path),
                "bytes": self.path.stat().st_size,
                "manifestPath": MANIFEST,
                "manifestSha256": sha256_bytes(self.manifest_bytes),
                "builtAt": self.manifest.get("builtAt"),
                "manifestFormat": self.manifest["format"],
                "packaging": self.manifest.get("packaging"),
                "navigation": self.manifest.get("navigation"),
                "verifiedFileCount": len(self.manifest["files"]),
                "uncompressedBytes": sum(info.file_size for info in self.members.values()),
            },
            "entries": self.manifest.get("entries", {}),
            "assetMap": self.manifest.get("assets", {}),
            "files": self.manifest["files"],
            "verification": {
                "archivePaths": "pass",
                "manifestMembership": "pass",
                "manifestHashes": "pass",
                "sourceAuthenticity": "not-established-by-self-contained-hashes",
                "libraryRendering": "not-tested",
                "mosaicValidation": "not-tested",
                "mosaicRendering": "not-tested",
                "userAcceptance": "pending",
            },
        }

    def extract(self, output: Path) -> dict:
        """Extract only after full verification, into a fresh owned directory."""
        output = output.absolute()
        output.mkdir(parents=True, exist_ok=False)
        try:
            library = output / "library"
            library.mkdir()
            for name in self.members:
                target = library.joinpath(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                data = self.manifest_bytes if name == MANIFEST else self.read_verified(name)
                with target.open("xb") as stream:
                    stream.write(data)
            record = dict(self.provenance)
            record["extraction"] = {"libraryRoot": str(library), "status": "pass"}
            write_new_json(output / "provenance.json", record)
        except BaseException:
            shutil.rmtree(output)
            raise
        return record


def check_spec(spec_path: Path, package: LibraryPackage) -> dict:
    """Bind a human/AI extracted design-spec to exact, verified source bytes.

    This verifies provenance, not the correctness of interpreted design intent.
    Conversion adapters receive this checked specification as their input.
    """
    spec_bytes = spec_path.read_bytes()
    spec = json.loads(spec_bytes.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(spec, dict) or spec.get("specVersion") != "0.1.0":
        raise PackageError("Only design-spec specVersion 0.1.0 is supported")
    if not isinstance(spec.get("id"), str) or not spec["id"]:
        raise PackageError("design-spec.id must identify the selected component")
    authority = spec.get("authority", {})
    if not isinstance(authority, dict):
        raise PackageError("design-spec.authority must be an object")
    for spec_key, package_key in (("archiveSha256", "sha256"), ("manifestSha256", "manifestSha256")):
        if authority.get(spec_key) != package.provenance["package"][package_key]:
            raise PackageError(f"Design spec source drift: authority.{spec_key}")
    for source_type in ("script", "stylesheet"):
        path = authority.get(source_type + "Path")
        if not isinstance(path, str) or package.manifest["files"].get(path) != authority.get(source_type + "Sha256"):
            raise PackageError(f"Design spec source drift: authority.{source_type}")

    def checked_local(relative_path: str, digest: str):
        relative_path = safe_member_name(relative_path)
        resolved = (spec_path.parent / relative_path).resolve(strict=True)
        if not resolved.is_relative_to(spec_path.parent.resolve()):
            raise PackageError(f"Spec local file escapes source directory: {relative_path}")
        if sha256_file(resolved) != digest:
            raise PackageError(f"Spec local file SHA-256 mismatch: {relative_path}")

    assets = spec.get("assets", [])
    evidence = spec.get("sourceEvidence", [])
    if not isinstance(assets, list) or not assets or not isinstance(evidence, list) or not evidence:
        raise PackageError("Design spec requires nonempty assets and sourceEvidence lists")
    for asset in assets:
        if not isinstance(asset, dict):
            raise PackageError("Every design-spec asset must be an object")
        raw = package.read_verified(asset.get("archivePath"))
        if sha256_bytes(raw) != asset.get("sha256") or len(raw) != asset.get("bytes"):
            raise PackageError(f"Spec asset differs from archive: {asset.get('archivePath')}")
        checked_local(asset.get("localFile"), asset.get("sha256"))
    for item in evidence:
        if not isinstance(item, dict):
            raise PackageError("Every design-spec sourceEvidence item must be an object")
        raw = package.read_verified(item.get("archivePath"))
        if sha256_bytes(raw) != item.get("sourceSha256"):
            raise PackageError(f"Spec evidence source drift: {item.get('id')}")
        source = raw.decode("utf-8")
        start, end = item.get("characterStart"), item.get("characterEndExclusive")
        if type(start) is not int or type(end) is not int or not (0 <= start < end <= len(source)):
            raise PackageError(f"Invalid source character range: {item.get('id')}")
        excerpt_hash = sha256_bytes(source[start:end].encode("utf-8"))
        if excerpt_hash != item.get("excerptSha256"):
            raise PackageError(f"Spec excerpt does not match source range: {item.get('id')}")
        checked_local(item.get("localFile"), item.get("localFileSha256", excerpt_hash))
    return {
        "formatVersion": 1,
        "specId": spec["id"],
        "specPath": str(spec_path.resolve()),
        "specSha256": sha256_bytes(spec_bytes),
        "archiveSha256": package.provenance["package"]["sha256"],
        "checks": {"sourcePackage": "pass", "localAssets": "pass", "sourceExcerpts": "pass",
                   "assetCount": len(assets), "excerptCount": len(evidence),
                   "designInterpretation": "not-evaluated", "mosaicRendering": "not-tested",
                   "userAcceptance": "pending"},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify", help="Verify package membership and every manifest SHA-256")
    verify.add_argument("package", type=Path)
    verify.add_argument("--report", type=Path, help="Write complete provenance to a new JSON file")
    extract = commands.add_parser("extract", help="Verify, safely extract and record provenance")
    extract.add_argument("package", type=Path)
    extract.add_argument("--output", required=True, type=Path, help="New directory; never overwrite")
    spec_cmd = commands.add_parser("check-spec", help="Bind a design-spec to verified package/asset/excerpt bytes")
    spec_cmd.add_argument("spec", type=Path)
    spec_cmd.add_argument("--package", required=True, type=Path)
    spec_cmd.add_argument("--report", type=Path, help="New JSON report file")
    adopt = commands.add_parser("adopt-fixture", help="Freeze a reviewed JSX/schema/data snapshot with separate evidence")
    adopt.add_argument("source", type=Path, help="Directory containing template.jsx, schema.json, data.json")
    adopt.add_argument("--spec", required=True, type=Path)
    adopt.add_argument("--package", required=True, type=Path)
    adopt.add_argument("--record", required=True, type=Path, help="Mapping/evidence record; adoption is not approval")
    adopt.add_argument("--output", required=True, type=Path)
    emit = commands.add_parser("emit", help="Replay exact frozen fixture after local integrity/data checks")
    emit.add_argument("fixture", type=Path)
    emit.add_argument("--output", required=True, type=Path)
    feedback = commands.add_parser("record-feedback", help="Record user feedback or agent review as an unverified rule proposal")
    feedback.add_argument("fixture", type=Path)
    feedback.add_argument("--feedback", required=True, type=Path)
    feedback.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command in ("adopt-fixture", "emit", "record-feedback"):
            from fixture_io import adopt_fixture, emit_fixture, record_feedback
            if args.command == "adopt-fixture":
                with LibraryPackage(args.package) as package:
                    source_check = check_spec(args.spec, package)
                record = adopt_fixture(args.source, args.spec, args.record, args.output, source_check)
            elif args.command == "emit":
                record = emit_fixture(args.fixture, args.output)
            else:
                record = record_feedback(args.fixture, args.feedback, args.output)
            print(json_text(record), end="")
            return 0
        with LibraryPackage(args.package) as package:
            if args.command == "check-spec":
                record = check_spec(args.spec, package)
                if args.report:
                    write_new_json(args.report, record)
                print(json_text(record), end="")
                return 0
            record = package.extract(args.output) if args.command == "extract" else package.provenance
            if args.command == "verify" and args.report:
                write_new_json(args.report, record)
            print(json_text({"package": record["package"], "verification": record["verification"],
                             **({"extraction": record["extraction"]} if "extraction" in record else {})}), end="")
        return 0
    except (ValueError, OSError, zipfile.BadZipFile, UnicodeError) as error:
        print(f"library-to-mosaic: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
