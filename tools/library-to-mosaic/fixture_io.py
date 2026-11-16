"""Freeze and replay reviewed Mosaic fixtures without inventing conversions.

No networking or JSX execution. Evidence is preserved as evidence, not promoted
to runtime success for a newly emitted bundle.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


class FixtureError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def read_json(path: Path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise FixtureError(f"Duplicate JSON key {key!r}: {path}")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def schema_check(value, schema, location="data"):
    """Validate the explicit Draft-07 subset used by this selected fixture.

    Unknown validation keywords are rejected; this never presents itself as a
    full JSON Schema implementation or replaces Mosaic's saved validation.
    """
    supported = {"$schema", "title", "description", "default", "examples", "type", "properties",
                 "required", "additionalProperties", "anyOf", "const", "enum", "minLength",
                 "maxLength", "pattern", "minimum", "maximum", "items", "minItems", "maxItems"}
    if location == "data":
        def inspect(node):
            if not isinstance(node, dict) or set(node) - supported:
                raise FixtureError("Unsupported JSON Schema keywords (including unused branches)")
            properties = node.get("properties", {})
            if not isinstance(properties, dict):
                raise FixtureError("Schema properties must be an object")
            for child in properties.values():
                inspect(child)
            for child in node.get("anyOf", []):
                inspect(child)
            for key in ("items", "additionalProperties"):
                if isinstance(node.get(key), dict):
                    inspect(node[key])
        inspect(schema)
    if not isinstance(schema, dict) or set(schema) - supported:
        raise FixtureError(f"Unsupported JSON Schema keywords at {location}")
    if "anyOf" in schema:
        branches = schema["anyOf"]
        if not isinstance(branches, list) or not branches:
            raise FixtureError(f"Invalid anyOf at {location}")
        matches = False
        for branch in branches:
            try:
                schema_check(value, branch, location)
                matches = True
            except FixtureError:
                pass
        if not matches:
            raise FixtureError(f"No schema anyOf branch accepts {location}")
    types = {"object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list),
             "string": lambda v: isinstance(v, str), "boolean": lambda v: isinstance(v, bool),
             "integer": lambda v: type(v) is int, "number": lambda v: type(v) in (int, float),
             "null": lambda v: v is None}
    if "type" in schema:
        kind = schema["type"]
        if not isinstance(kind, str) or kind not in types or not types[kind](value):
            raise FixtureError(f"Invalid type at {location}: expected {kind!r}")
    if "const" in schema and json.dumps(value, sort_keys=True) != json.dumps(schema["const"], sort_keys=True):
        raise FixtureError(f"Wrong const at {location}")
    if "enum" in schema and not any(json.dumps(value, sort_keys=True) == json.dumps(v, sort_keys=True) for v in schema["enum"]):
        raise FixtureError(f"Value outside enum at {location}")
    if isinstance(value, dict):
        missing = set(schema.get("required", [])) - value.keys()
        if missing:
            raise FixtureError(f"Missing data fields at {location}: {sorted(missing)}")
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                schema_check(item, properties[key], f"{location}.{key}")
            elif schema.get("additionalProperties") is False:
                raise FixtureError(f"Unexpected data field: {location}.{key}")
            elif isinstance(schema.get("additionalProperties"), dict):
                schema_check(item, schema["additionalProperties"], f"{location}.{key}")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", float("inf")):
            raise FixtureError(f"String length outside schema bounds: {location}")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise FixtureError(f"String does not match schema pattern: {location}")
    if type(value) in (int, float):
        if value < schema.get("minimum", -float("inf")) or value > schema.get("maximum", float("inf")):
            raise FixtureError(f"Number outside schema bounds: {location}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
            raise FixtureError(f"Array length outside schema bounds: {location}")
        if "items" in schema:
            for index, item in enumerate(value):
                schema_check(item, schema["items"], f"{location}[{index}]")


def lookup(value: dict, path: str):
    if not isinstance(path, str) or not path:
        raise FixtureError("Missing dotted property path")
    for key in path.split("."):
        if isinstance(value, list) and key.isdigit() and int(key) < len(value):
            value = value[int(key)]
            continue
        if not isinstance(value, dict) or key not in value:
            raise FixtureError(f"Missing property: {path}")
        value = value[key]
    return value


def check_record(record: dict, spec: dict, data: dict):
    if not isinstance(record, dict) or not isinstance(spec, dict) or not isinstance(data, dict):
        raise FixtureError("Record, design spec and schemaData must be objects")
    if record.get("formatVersion") != 1 or record.get("selectionId") != spec.get("id"):
        raise FixtureError("Mapping record must identify the exact design-spec selection")
    if record.get("adapter") != "verbatim-fixture@1":
        raise FixtureError("Only the explicit verbatim-fixture@1 adapter is implemented")
    if not isinstance(record.get("target"), dict) or record["target"].get("sdlVersion") != "v1.5":
        raise FixtureError("This first adapter requires an explicit SDL v1.5 target")
    if record.get("stage") not in ("candidate", "runtime-checked", "user-accepted"):
        raise FixtureError("Fixture stage must be candidate, runtime-checked or user-accepted")
    if record.get("userAcceptance") not in ("pending", "changes-requested", "accepted"):
        raise FixtureError("Invalid userAcceptance")
    evidence = record.get("evidence", [])
    if not isinstance(evidence, list) or not evidence:
        raise FixtureError("At least one concrete evidence artifact is required")
    identifiers = [item.get("id") for item in evidence]
    if any(not isinstance(key, str) or not re.fullmatch(r"[a-z0-9-]+", key) for key in identifiers):
        raise FixtureError("Evidence ids use lowercase letters, digits and hyphens")
    if len(identifiers) != len(set(identifiers)):
        raise FixtureError("Evidence ids must be unique")
    if record["userAcceptance"] == "accepted" or record["stage"] == "user-accepted":
        if record["userAcceptance"] != "accepted" or record["stage"] != "user-accepted":
            raise FixtureError("Accepted user evidence and stage must agree")
        if not any(item.get("kind") == "user-feedback" for item in evidence):
            raise FixtureError("User acceptance requires a referenced user-feedback artifact")
    mappings = record.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise FixtureError("Source requirements, contract support and runtime evidence must be separated")
    for mapping in mappings:
        requirement = mapping.get("sourceRequirement", {})
        actual = lookup(spec, requirement.get("path"))
        if actual != requirement.get("value"):
            raise FixtureError(f"Mapping source requirement drift: {mapping.get('id')}")
        if mapping.get("contractSupport", {}).get("status") not in ("allowed", "unsupported", "not-checked"):
            raise FixtureError(f"Missing contractSupport status: {mapping.get('id')}")
        if mapping.get("runtime", {}).get("status") not in ("pass", "fail", "not-tested", "not-applicable"):
            raise FixtureError(f"Missing runtime status: {mapping.get('id')}")
        if mapping.get("fidelity", {}).get("status") not in ("direct", "approximate", "unsupported", "pending"):
            raise FixtureError(f"Missing fidelity status: {mapping.get('id')}")
        for group in ("contractSupport", "runtime"):
            refs = mapping[group].get("evidenceIds", [])
            if not isinstance(refs, list) or set(refs) - set(identifiers):
                raise FixtureError(f"Unknown {group} evidence reference: {mapping.get('id')}")
            if mapping[group]["status"] in ("allowed", "unsupported", "pass", "fail") and not refs:
                raise FixtureError(f"Status requires evidence: {mapping.get('id')}.{group}")
    if record["stage"] != "candidate" and any(m["runtime"]["status"] == "not-tested" for m in mappings):
        raise FixtureError("Unchecked mappings cannot be promoted beyond candidate")
    for binding in record.get("sourceBindings", []):
        if lookup(spec, binding.get("sourcePath")) != lookup(data, binding.get("dataPath")):
            raise FixtureError(f"Data/source binding drift: {binding.get('dataPath')}")
    for paths in record.get("dataEqualities", []):
        if not isinstance(paths, list) or len(paths) < 2:
            raise FixtureError("Data equality groups need at least two dotted paths")
        values = [lookup(data, path) for path in paths]
        if any(value != values[0] for value in values[1:]):
            raise FixtureError(f"Related data fields disagree: {paths}")


def write_directory(output: Path, payloads: dict[str, bytes]):
    output.mkdir(parents=True, exist_ok=False)
    try:
        for name, raw in payloads.items():
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(raw)
    except BaseException:
        shutil.rmtree(output)
        raise


def adopt_fixture(source: Path, spec_path: Path, record_path: Path, output: Path, spec_check: dict) -> dict:
    spec, record = read_json(spec_path), read_json(record_path)
    if spec_check.get("specId") != spec.get("id") or spec_check.get("specSha256") != digest(spec_path.read_bytes()):
        raise FixtureError("Source specification changed after its provenance check")
    payloads = {name: (source / name).read_bytes() for name in ("template.jsx", "schema.json", "data.json")}
    if (source / "notes.md").is_file():
        payloads["notes.md"] = (source / "notes.md").read_bytes()
    expected = record.get("expectedBundleFiles", {})
    if set(expected) != set(payloads) or any(digest(raw) != expected[name] for name, raw in payloads.items()):
        raise FixtureError("Bundle bytes differ from the version tied to this evidence record")
    schema, data = read_json(source / "schema.json"), read_json(source / "data.json")
    schema_check(data, schema)
    check_record(record, spec, data)
    # This catches missing simple bindings; full JSX parsing stays with Mosaic.
    simple_bindings = set(re.findall(r"=\{\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\}", payloads["template.jsx"].decode("utf-8"))) - {"true", "false", "null"}
    if not simple_bindings <= data.keys():
        raise FixtureError(f"JSX references data fields missing from the snapshot: {sorted(simple_bindings - data.keys())}")
    evidence_records = []
    for item in record["evidence"]:
        path = Path(item["path"])
        if not path.is_absolute():
            path = record_path.parent / path
        raw = path.read_bytes()
        snapshot = f"evidence/{item['id']}{path.suffix}"
        payloads[snapshot] = raw
        evidence_records.append({**item, "originalPath": str(path.resolve()), "path": snapshot,
                                 "sha256": digest(raw), "bytes": len(raw)})
    record = {**record, "evidence": evidence_records}
    payloads.update({"source-spec.json": spec_path.read_bytes(), "source-check.json": encode(spec_check),
                     "mapping-record.json": encode(record)})
    manifest = {"formatVersion": 1, "adapter": "verbatim-fixture@1", "selectionId": spec["id"],
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "sourceDirectory": str(source.resolve()), "stage": record["stage"],
                "userAcceptance": record["userAcceptance"], "target": record["target"],
                "files": {name: digest(raw) for name, raw in payloads.items()},
                "scope": "Frozen exact selected fixture; not a general JSX compiler or new runtime validation."}
    payloads["fixture-manifest.json"] = encode(manifest)
    write_directory(output, payloads)
    return {"fixture": str(output.resolve()), "selectionId": spec["id"], "stage": record["stage"],
            "userAcceptance": record["userAcceptance"], "fileCount": len(payloads)}


def checked_fixture(fixture: Path):
    manifest = read_json(fixture / "fixture-manifest.json")
    if manifest.get("formatVersion") != 1 or manifest.get("adapter") != "verbatim-fixture@1":
        raise FixtureError("Unsupported fixture format or adapter")
    files = manifest.get("files", {})
    if not isinstance(files, dict) or not {"template.jsx", "schema.json", "data.json", "source-spec.json", "source-check.json", "mapping-record.json"} <= files.keys():
        raise FixtureError("Incomplete fixture manifest")
    root = fixture.resolve(strict=True)
    for name, checksum in files.items():
        path = (fixture / name).resolve(strict=True)
        if not path.is_relative_to(root) or path == root:
            raise FixtureError(f"Fixture path escapes its directory: {name}")
        if digest(path.read_bytes()) != checksum:
            raise FixtureError(f"Fixture changed since adoption: {name}")
    schema, data = read_json(fixture / "schema.json"), read_json(fixture / "data.json")
    record, spec = read_json(fixture / "mapping-record.json"), read_json(fixture / "source-spec.json")
    checked_source = read_json(fixture / "source-check.json")
    if checked_source.get("specId") != spec.get("id") or checked_source.get("specSha256") != files["source-spec.json"]:
        raise FixtureError("Frozen source check does not match the design specification")
    schema_check(data, schema)
    check_record(record, spec, data)
    bundle_names = {"template.jsx", "schema.json", "data.json"} | ({"notes.md"} if "notes.md" in files else set())
    if set(record.get("expectedBundleFiles", {})) != bundle_names or any(
            record["expectedBundleFiles"].get(name) != files.get(name) for name in bundle_names):
        raise FixtureError("Fixture bundle hashes disagree with the evidence record")
    if record["stage"] != manifest["stage"] or record["userAcceptance"] != manifest["userAcceptance"]:
        raise FixtureError("Fixture stage/acceptance drift")
    return manifest, record


def emit_fixture(fixture: Path, output: Path) -> dict:
    manifest, record = checked_fixture(fixture)
    payloads = {name: (fixture / name).read_bytes() for name in ("template.jsx", "schema.json", "data.json")}
    if "notes.md" in manifest["files"]:
        payloads["notes.md"] = (fixture / "notes.md").read_bytes()
    report = {"formatVersion": 1, "adapter": manifest["adapter"], "selectionId": manifest["selectionId"],
              "fixturePath": str(fixture.resolve()), "fixtureManifestSha256": digest((fixture / "fixture-manifest.json").read_bytes()),
              "referenceStage": manifest["stage"], "referenceUserAcceptance": manifest["userAcceptance"],
              "target": record["target"], "files": {name: digest(raw) for name, raw in payloads.items()},
              "currentChecks": {"fixtureIntegrity": "pass", "schemaDataSubsetCheck": "pass",
                                "savedValidation": "not-tested", "rendering": "not-tested", "userAcceptance": "pending"},
              "fidelity": [{"id": m["id"], **m["fidelity"]} for m in record["mappings"]],
              "nextStep": "Use current Mosaic skill/CLI to save and verify this emitted bundle. Existing template edits require fetch-before-edit."}
    payloads["emission.json"] = encode(report)
    write_directory(output, payloads)
    return {"output": str(output.resolve()), **report}


def record_feedback(fixture: Path, feedback_path: Path, output: Path) -> dict:
    manifest, _ = checked_fixture(fixture)
    feedback = read_json(feedback_path)
    if not isinstance(feedback, dict):
        raise FixtureError("Feedback must be an object")
    for key in ("origin", "area", "observation", "requestedChange"):
        if not isinstance(feedback.get(key), str) or not feedback[key].strip():
            raise FixtureError(f"Feedback requires {key}")
    if feedback["origin"] not in ("user-feedback", "agent-review"):
        raise FixtureError("Feedback origin must be user-feedback or agent-review")
    if feedback.get("acceptance", "pending") not in ("pending", "changes-requested", "accepted"):
        raise FixtureError("Invalid feedback acceptance")
    if feedback.get("acceptance") == "accepted" and feedback["origin"] != "user-feedback":
        raise FixtureError("Agent review cannot represent user acceptance")
    result = {"formatVersion": 1, "selectionId": manifest["selectionId"],
              "fixtureManifestSha256": digest((fixture / "fixture-manifest.json").read_bytes()),
              "recordedAt": datetime.now(timezone.utc).isoformat(), "feedback": feedback,
              "ruleStatus": "proposed", "regressionVerification": "not-tested",
              "note": "Recording feedback does not mutate the fixture or promote a rule to verified."}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(encode(result))
    return result
