import hashlib
import importlib.util
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "library_to_mosaic.py"
SPEC = importlib.util.spec_from_file_location("library_to_mosaic", MODULE)
lib = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lib)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.zip = self.root / "release.zip"

    def tearDown(self):
        self.temp.cleanup()

    def package(self, payloads=None, *, manifest_patch=None, extra=()):
        payloads = payloads or {"index.html": b"<title>Library</title>"}
        manifest = {"format": 3, "entries": {"mm-image": {"html": "index.html"}},
                    "assets": {}, "files": {k: hashlib.sha256(v).hexdigest() for k, v in payloads.items()}}
        if manifest_patch:
            manifest.update(manifest_patch)
        with zipfile.ZipFile(self.zip, "w") as archive:
            archive.writestr("BUILD-MANIFEST.json", json.dumps(manifest))
            for name, value in payloads.items():
                archive.writestr(name, value)
            for info, value in extra:
                archive.writestr(info, value)

    def test_verified_extraction_and_provenance(self):
        self.package()
        with lib.LibraryPackage(self.zip) as package:
            record = package.extract(self.root / "out")
        self.assertEqual((self.root / "out/library/index.html").read_bytes(), b"<title>Library</title>")
        self.assertEqual(record["package"]["verifiedFileCount"], 1)
        self.assertEqual(record["verification"]["mosaicRendering"], "not-tested")
        self.assertEqual(json.loads((self.root / "out/provenance.json").read_text()), record)

    def test_path_traversal_and_absolute_paths(self):
        for path in ("../outside", "/absolute", "dir/../../outside", "dir\\outside", "C:/outside", "dir//a"):
            with self.subTest(path=path):
                self.package(extra=[(path, b"unsafe")])
                with self.assertRaises(lib.PackageError):
                    lib.LibraryPackage(self.zip)
        self.assertFalse((self.root.parent / "outside").exists())

    def test_symlinks_rejected(self):
        info = zipfile.ZipInfo("link")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        self.package(extra=[(info, b"/tmp")])
        with self.assertRaisesRegex(lib.PackageError, "Symlink"):
            lib.LibraryPackage(self.zip)

    def test_hash_mismatch_rejected(self):
        self.package(manifest_patch={"files": {"index.html": "0" * 64}})
        with self.assertRaisesRegex(lib.PackageError, "SHA-256 mismatch"):
            lib.LibraryPackage(self.zip)

    def test_unlisted_member_rejected(self):
        self.package(extra=[("unexpected.js", b"extra")])
        with self.assertRaisesRegex(lib.PackageError, "unlisted"):
            lib.LibraryPackage(self.zip)

    def test_case_insensitive_collision_rejected(self):
        self.package(extra=[("INDEX.html", b"extra")])
        with self.assertRaisesRegex(lib.PackageError, "colliding"):
            lib.LibraryPackage(self.zip)

    def test_existing_output_not_modified(self):
        self.package()
        out = self.root / "out"
        out.mkdir()
        (out / "mine").write_text("user edit")
        with lib.LibraryPackage(self.zip) as package:
            with self.assertRaises(FileExistsError):
                package.extract(out)
        self.assertEqual((out / "mine").read_text(), "user edit")

    def test_missing_asset_reference_rejected(self):
        self.package(manifest_patch={"assets": {"image": "missing.png"}})
        with self.assertRaisesRegex(lib.PackageError, "unverified"):
            lib.LibraryPackage(self.zip)

    def make_spec(self):
        script, css, asset = b"const card = {width: 200};", b".card {color:white}", b"asset-bytes"
        payloads = {"index.html": b"example", "app.js": script, "app.css": css, "image.png": asset}
        self.package(payloads)
        source = self.root / "source"
        source.mkdir()
        (source / "image.png").write_bytes(asset)
        (source / "excerpt.js").write_bytes(script + b"\n")
        digest = lib.sha256_bytes
        with lib.LibraryPackage(self.zip) as package:
            spec = {"specVersion": "0.1.0", "id": "mm-image/image-cards/2x2/single-image",
                    "authority": {"archiveSha256": package.provenance["package"]["sha256"],
                                  "manifestSha256": package.provenance["package"]["manifestSha256"],
                                  "scriptPath": "app.js", "scriptSha256": digest(script),
                                  "stylesheetPath": "app.css", "stylesheetSha256": digest(css)},
                    "assets": [{"archivePath": "image.png", "localFile": "image.png",
                                "sha256": digest(asset), "bytes": len(asset)}],
                    "sourceEvidence": [{"id": "definition", "archivePath": "app.js",
                                        "sourceSha256": digest(script), "characterStart": 0,
                                        "characterEndExclusive": len(script), "localFile": "excerpt.js",
                                        "excerptSha256": digest(script),
                                        "localFileSha256": digest(script + b"\n")}]}
        path = source / "design-spec.json"
        path.write_text(json.dumps(spec))
        return path, spec

    def test_spec_bound_to_exact_source_and_local_files(self):
        path, _ = self.make_spec()
        with lib.LibraryPackage(self.zip) as package:
            result = lib.check_spec(path, package)
        self.assertEqual(result["checks"]["sourceExcerpts"], "pass")
        self.assertEqual(result["checks"]["userAcceptance"], "pending")

    def test_spec_rejects_local_asset_drift(self):
        path, _ = self.make_spec()
        (path.parent / "image.png").write_bytes(b"changed")
        with lib.LibraryPackage(self.zip) as package:
            with self.assertRaisesRegex(lib.PackageError, "local file SHA-256"):
                lib.check_spec(path, package)

    def test_spec_rejects_changed_source_range(self):
        path, spec = self.make_spec()
        spec["sourceEvidence"][0]["characterEndExclusive"] -= 1
        path.write_text(json.dumps(spec))
        with lib.LibraryPackage(self.zip) as package:
            with self.assertRaisesRegex(lib.PackageError, "does not match source range"):
                lib.check_spec(path, package)


if __name__ == "__main__":
    unittest.main()
