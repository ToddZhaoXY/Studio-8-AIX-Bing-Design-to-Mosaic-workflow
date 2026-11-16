#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path

STATUSES = {"passed", "failed", "not-tested", "blocked", "not-applicable"}
EXPRESSIONS = {".map()", "Nested .map()", "A && B", "A ? B : C"}
REQUIRED = {
    "scenario",
    "name",
    "templateId",
    "acceptedIteration",
    "viewport",
    "sdlVersion",
    "root",
    "components",
    "jsxExpressions",
    "validation",
    "runtime",
    "localServerParity",
}
HEADER = (
    "| Scenario | Name | Template ID | Iteration | Viewport | SDL | Root | "
    "Components | JSX expressions | Full validation | Preview diagnostics | "
    "Target host | Interaction QA | Parity |"
)
SEPARATOR = (
    "|---|---|---|---:|---|---|---|---|---|---|---:|---|---|---|"
)


def fail(message: str) -> None:
    raise ValueError(message)


def validate_status(value: object, field: str) -> str:
    if not isinstance(value, str) or value not in STATUSES:
        fail(f"{field} must be one of: {', '.join(sorted(STATUSES))}")
    return value


def validate(data: object) -> dict:
    if not isinstance(data, dict):
        fail("manifest root must be an object")

    missing = sorted(REQUIRED - data.keys())
    if missing:
        fail(f"missing required field(s): {', '.join(missing)}")

    for field in ("scenario", "name", "templateId", "viewport", "sdlVersion", "root"):
        if not isinstance(data[field], str) or not data[field].strip():
            fail(f"{field} must be a non-empty string")

    if not isinstance(data["acceptedIteration"], int) or data["acceptedIteration"] < 1:
        fail("acceptedIteration must be a positive integer")

    components = data["components"]
    if not isinstance(components, list) or not components or not all(
        isinstance(item, str) and item for item in components
    ):
        fail("components must be a non-empty array of strings")

    expressions = data["jsxExpressions"]
    if not isinstance(expressions, list) or not all(item in EXPRESSIONS for item in expressions):
        fail(
            "jsxExpressions may contain only: "
            + ", ".join(sorted(EXPRESSIONS))
        )

    responsive = data.get("responsiveEvidence")
    if responsive is not None:
        if not isinstance(responsive, dict):
            fail("responsiveEvidence must be an object")
        for field in ("canonical", "transition", "narrow"):
            if field in responsive:
                validate_status(
                    responsive[field], f"responsiveEvidence.{field}"
                )
        for level in ("sectionLevel", "contentLevel"):
            if level not in responsive:
                continue
            evidence = responsive[level]
            if not isinstance(evidence, dict):
                fail(f"responsiveEvidence.{level} must be an object")
            validate_status(
                evidence.get("status"), f"responsiveEvidence.{level}.status"
            )
            for field in ("canonical", "transition", "narrow"):
                if field in evidence:
                    validate_status(
                        evidence[field],
                        f"responsiveEvidence.{level}.{field}",
                    )

    validation = data["validation"]
    if not isinstance(validation, dict):
        fail("validation must be an object")
    validate_status(validation.get("savedFull"), "validation.savedFull")
    diagnostics = validation.get("previewDiagnostics")
    if not isinstance(diagnostics, int) or diagnostics < 0:
        fail("validation.previewDiagnostics must be a non-negative integer")

    runtime = data["runtime"]
    if not isinstance(runtime, dict):
        fail("runtime must be an object")
    validate_status(runtime.get("targetHostRender"), "runtime.targetHostRender")
    pointer = validate_status(runtime.get("pointer"), "runtime.pointer")
    keyboard = validate_status(runtime.get("keyboard"), "runtime.keyboard")
    validate_status(data["localServerParity"], "localServerParity")

    data["_interactionQA"] = (
        "passed"
        if pointer == keyboard == "passed"
        else f"pointer: {pointer}; keyboard: {keyboard}"
    )
    return data


def cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def row(data: dict) -> str:
    values = [
        data["scenario"],
        data["name"],
        f"`{data['templateId']}`",
        data["acceptedIteration"],
        data["viewport"],
        data["sdlVersion"],
        data["root"],
        ", ".join(data["components"]),
        ", ".join(data["jsxExpressions"]) or "None",
        data["validation"]["savedFull"],
        data["validation"]["previewDiagnostics"],
        data["runtime"]["targetHostRender"],
        data["_interactionQA"],
        data["localServerParity"],
    ]
    return "| " + " | ".join(cell(value) for value in values) + " |"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a GTX evidence manifest and emit a Markdown tracking-table row."
    )
    parser.add_argument("manifest", type=Path, help="Path to the manifest JSON file")
    parser.add_argument(
        "--header",
        action="store_true",
        help="Include the Markdown table header and separator",
    )
    args = parser.parse_args()

    try:
        data = validate(json.loads(args.manifest.read_text()))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    if args.header:
        print(HEADER)
        print(SEPARATOR)
    print(row(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
