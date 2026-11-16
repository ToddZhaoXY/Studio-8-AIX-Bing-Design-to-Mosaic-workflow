import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

MODULE = Path(__file__).resolve().parents[1] / "catalog.py"
sys.path.insert(0, str(MODULE.parent))
spec = importlib.util.spec_from_file_location("workbench_catalog_tests", MODULE)
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)
ROOT = MODULE.parents[2]


class LiteralParserTests(unittest.TestCase):
    def test_strings_and_nested_data(self):
        self.assertEqual(catalog._literal('{label:"A\\x20B",values:[1,!0,!1,null],x:"a:b,c"}'),
                         {"label": "A B", "values": [1, True, False, None], "x": "a:b,c"})

    def test_code_is_not_executed(self):
        expression = 'require("fs").writeFileSync("/tmp/should-not-exist","bad")'
        self.assertEqual(catalog._literal(expression), {"$expression": expression})
        with self.assertRaises(catalog.CatalogError):
            catalog._decode_js_string('`value ${process.exit()}`')

    def test_nested_selector_fields_stay_data(self):
        self.assertEqual(catalog._literal('{x:{q:"[}]",y:["a",{"z":2}]}}')["x"]["y"][1], {"z": 2})

    def test_scoped_reused_identifiers_are_not_resolved(self):
        constants = catalog._constants('let a="x",Ab="first";function other(){let Ab="other";}')
        self.assertNotIn("a", constants)
        self.assertNotIn("Ab", constants)


@unittest.skipUnless((ROOT / catalog.ARCHIVE).is_file(), "Delivered library ZIP is not available")
class DeliveredCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = catalog.build_catalog(ROOT)

    def test_every_registry_component_is_present(self):
        self.assertEqual(self.data["coverage"]["componentsByLibrary"], {"mm-image": 19, "aigc": 17, "video": 19})
        actual = {(i["library"], i["componentId"]) for i in self.data["items"]}
        self.assertEqual(len(actual), 55)
        self.assertEqual(len({i["id"] for i in self.data["items"]}), len(self.data["items"]))

    def test_all_49_image_cards_and_13_sizes(self):
        cards = [i for i in self.data["items"] if i["componentId"] == "image-cards"]
        self.assertEqual(len(cards), 49)
        self.assertEqual(len({i["size"] for i in cards}), 13)
        card = next(i for i in cards if i["id"] == "mm-image/image-cards/2x2/single-image")
        self.assertEqual((card["width"], card["height"]), (200, 200))
        self.assertEqual(card["previewPath"], "mm-image.html#/c/image-cards?size=2x2&variant=Single%20image")

    def test_mapped_source_variants_keep_precise_geometry(self):
        variants = [i for i in self.data["items"] if i["library"] == "aigc" and i["componentId"] == "main-image-area"
                    and i["details"]["selectionKind"] == "source-configuration"]
        self.assertEqual(len(variants), 6)
        hover = next(i for i in variants if i["details"]["nodeId"] == "461:31878")
        self.assertEqual((hover["width"], hover["height"]), (909, 608))
        self.assertEqual(hover["details"]["selectionValues"]["status"], "hover")
        self.assertEqual(hover["details"]["previewSelectionMode"], "controls")
        self.assertNotIn("?", hover["previewPath"])

    def test_every_preview_targets_real_entry_and_registered_slug(self):
        for item in self.data["items"]:
            page, route = item["previewPath"].split("#", 1)
            self.assertTrue((Path(self.data["libraryRoot"]) / page).is_file())
            self.assertTrue(route.startswith("/c/"))
            self.assertEqual(route.split("?", 1)[0], "/c/" + item["componentId"])

    def test_first_selection_has_real_tree_assets_and_evidence(self):
        brief = catalog.extract_selection(ROOT, "mm-image/image-cards/2x2/single-image")
        self.assertEqual(brief["designTreeStatus"], "parsed-source-tree")
        self.assertEqual(brief["designTree"]["children"][1]["children"][1]["text"], "All image")
        self.assertEqual(len(brief["assets"]), 3)
        for asset in brief["assets"]:
            self.assertEqual(hashlib.sha256(Path(asset["localPath"]).read_bytes()).hexdigest(), asset["sha256"])
        for evidence in [brief["sourceEvidence"], *brief["supportingSourceEvidence"]]:
            text = (Path(brief["libraryRoot"]) / evidence["archivePath"]).read_text()
            self.assertEqual(text[evidence["characterStart"]:evidence["characterEndExclusive"]], evidence["excerpt"])

    def test_unknown_selection_is_rejected(self):
        with self.assertRaises(catalog.CatalogError):
            catalog.extract_selection(ROOT, "../../unknown")

    def test_existing_cache_is_reused_and_archive_is_configurable(self):
        package_class = catalog._package_class(ROOT)
        with mock.patch.object(package_class, "extract", side_effect=AssertionError("must reuse cache")):
            data = catalog.build_catalog(ROOT, archive_path=ROOT / catalog.ARCHIVE)
        self.assertEqual(data["package"]["path"], str(ROOT / catalog.ARCHIVE))
        with mock.patch.dict("os.environ", {"MOSAIC_LIBRARY_ZIP": catalog.ARCHIVE}):
            self.assertEqual(catalog.build_catalog(ROOT)["package"]["sha256"], data["package"]["sha256"])

    def test_unknown_tree_expressions_remain_explicit(self):
        brief = catalog.extract_selection(ROOT, "mm-image/image-cards/3x4/related-trends")
        self.assertEqual(brief["designTreeStatus"], "partial")
        self.assertIn("$expression", json.dumps(brief["designTree"]))
        self.assertTrue(brief["authoringReadiness"]["canAttempt"])
        self.assertTrue(any(e.get("symbol") == "u1" for e in brief["supportingSourceEvidence"]))

    def test_renderer_evidence_is_not_registry_metadata(self):
        for item_id, root_symbol in (("aigc/main-image-area/source-461-31878", "rd"),
                                     ("video/short-card/default", "$s"),
                                     ("mm-image/slideshow/default", "Jb")):
            brief = catalog.extract_selection(ROOT, item_id)
            self.assertEqual(brief["authoringReadiness"]["status"], "source-code-evidence")
            evidence = brief["supportingSourceEvidence"]
            self.assertTrue(any(e.get("symbol") == root_symbol and e.get("kind") == "renderer-function" for e in evidence))
            self.assertFalse(brief["authoringReadiness"]["runtimeVerified"])
            for record in evidence:
                original = (Path(brief["libraryRoot"]) / record["archivePath"]).read_text()
                self.assertEqual(original[record["characterStart"]:record["characterEndExclusive"]], record["excerpt"])
            if item_id.startswith("video"):
                self.assertGreater(brief["authoringReadiness"]["styleEvidenceCount"], 0)
            if item_id.startswith("aigc"):
                self.assertLess(len(brief["assets"]), 20, "Do not include the entire library asset dictionary")

    def test_source_reference_placeholder_is_not_authoring_ready(self):
        for item_id in ("video/vrp-whole-page/default", "video/serp-video-answer-go-wide/default"):
            brief = catalog.extract_selection(ROOT, item_id)
            self.assertFalse(brief["sourceEvidenceReady"])
            self.assertEqual(brief["authoringReadiness"]["status"], "needs-source-evidence")


if __name__ == "__main__":
    unittest.main()
