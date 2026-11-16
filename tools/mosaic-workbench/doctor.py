#!/usr/bin/env python3
"""Check this checkout offline by default; --live adds read-only account checks.

Offline checks never start a CLI, authenticate, read credential files, or call a
remote API. Verifying the source release may create its normal local hash cache.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {"components": 55, "selections": 464, "imageCardVariants": 49}


def _read_catalog(root):
    from catalog import build_catalog
    from settings import load_settings
    return build_catalog(root, archive_path=load_settings(root)["libraryZip"])


def _read_skill(root):
    from skills import metadata
    return metadata(root / ".agents/skills/mosaic-gen-workflow")


def _resolve_codex():
    from codex_runtime import resolve_codex_binary
    return resolve_codex_binary()


def _resolve_mosaic():
    from engine import _cli_path
    return _cli_path()


def _live_environment(root):
    from codex_engine import get_environment
    return get_environment(root)


def _is_posix():
    return os.name == "posix"


def _binary_check(resolver, name):
    try:
        value = resolver()
        path = Path(value).expanduser().resolve()
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ValueError("Resolved path is not an executable file")
        return {"status": "pass", "available": True, "path": str(path), "started": False}
    except Exception as error:
        return {"status": "warning", "available": False, "path": None, "started": False,
                "message": f"{name}  CLI is not ready. You can still browse the source library.", "detail": type(error).__name__,
                "nextStep": f"Install {name} CLI or set its binary path in workbench.local.json. Run doctor --live to check sign-in before generating."}


def run_checks(project_root=None, *, live=False):
    root = Path(project_root or ROOT).resolve()
    python_ok = tuple(sys.version_info[:2]) >= (3, 9)
    posix_ok = _is_posix()
    checks = {
        "python": {"status": "pass" if python_ok else "error", "version": platform.python_version(), "required": ">=3.9"},
        "platform": {"status": "pass" if posix_ok else "warning", "system": platform.system(), "posix": posix_ok,
                     "message": "POSIX process controls available." if posix_ok else "The executor requires POSIX process controls. On Windows, run this project in WSL."},
    }
    report = {"doctorVersion": 1, "mode": "live" if live else "offline", "projectRoot": str(root), "checks": checks,
              "sourceReady": False, "executionPrerequisites": {"platformSupported": posix_ok, "liveChecked": False, "ready": None},
              "remoteWrites": False, "generationStarted": False,
              "scope": "These checks verify sources and prerequisites, not Mosaic rendering, reconstruction fidelity, or publication readiness."}
    if not python_ok:
        checks["python"]["message"] = "Use Python 3.9 or later."
        report["exitCode"] = 1
        return report
    try:
        info = _read_skill(root)
        checks["skill"] = {"status": "pass", "path": str(root / ".agents/skills/mosaic-gen-workflow"), **info,
                           "verification": "Frontmatter, version, relative references, no symlinks, and complete package digest."}
    except Exception as error:
        checks["skill"] = {"status": "error", "message": str(error)}
    try:
        catalog = _read_catalog(root)
        items = catalog.get("items", [])
        actual = {"components": len({(i["library"], i["componentId"]) for i in items}), "selections": len(items),
                  "imageCardVariants": sum(i.get("library") == "mm-image" and i.get("componentId") == "image-cards" for i in items)}
        library_root = Path(catalog["libraryRoot"]).resolve()
        if not library_root.is_dir() or not (library_root / "BUILD-MANIFEST.json").is_file():
            raise ValueError("Verified library extraction directory is missing")
        matches = actual == EXPECTED
        checks["library"] = {"status": "pass" if matches else "error", "package": catalog["package"],
                             "libraryRoot": str(library_root), "expected": EXPECTED, "actual": actual,
                             "message": "The bundled ZIP was read, verified, and extracted." if matches else "The source inventory does not match this release. Check the library package and adapter version."}
    except Exception as error:
        checks["library"] = {"status": "error", "message": str(error)}
    report["sourceReady"] = all(checks.get(name, {}).get("status") == "pass" for name in ("python", "skill", "library"))
    execution = report["executionPrerequisites"]
    execution["codex"] = _binary_check(_resolve_codex, "Codex")
    execution["mosaic"] = _binary_check(_resolve_mosaic, "Mosaic")
    execution["binariesAvailable"] = all(execution[name]["available"] for name in ("codex", "mosaic"))
    execution["message"] = "Offline checks do not inspect sign-in or API access. Finding a CLI does not establish generation readiness."
    if live and posix_ok:
        execution["liveChecked"] = True
        try:
            environment = _live_environment(root)
            codex = environment.get("codex", {})
            mosaic = environment.get("cli", {})
            # Only expose readiness booleans and non-secret diagnostic messages;
            # never dump account/session/profile records into doctor output.
            execution["live"] = {"codex": {"available": codex.get("available") is True, "ready": codex.get("ready") is True,
                                                "authenticated": codex.get("authenticated") is True},
                                 "mosaic": {"available": mosaic.get("available") is True, "authenticated": mosaic.get("authenticated") is True,
                                            "apiReachable": mosaic.get("apiReachable") is True}}
            execution["ready"] = (report["sourceReady"] and execution["live"]["codex"]["ready"]
                                  and execution["live"]["mosaic"]["authenticated"] and execution["live"]["mosaic"]["apiReachable"])
            execution["message"] = "Read-only connection checks passed. No templates were generated." if execution["ready"] else "Execution prerequisites are incomplete. Check Codex access, Mosaic sign-in, and your network or VPN. The source library can still be browsed offline."
        except Exception as error:
            execution["ready"] = False
            execution["live"] = {"status": "error", "detail": type(error).__name__}
            execution["message"] = "Read-only connection checks failed. No templates were generated. Check sign-in and network access for both CLIs."
    elif live:
        execution["ready"] = False
        execution["message"] = "Use WSL on Windows. No CLI was started and no remote service was contacted."
    # Missing CLIs are warnings in offline browsing mode. --live explicitly
    # requests execution readiness, so an unavailable live prerequisite is exit2.
    report["exitCode"] = 1 if not report["sourceReady"] else (2 if live and execution["ready"] is not True else 0)
    return report


def format_human(report):
    lines = ["AIXA Bing Design Library · doctor (" + report["mode"] + ")"]
    for name in ("python", "platform", "skill", "library"):
        check = report["checks"].get(name)
        if not check:
            continue
        detail = check.get("message") or ("v" + check["version"] if check.get("version") else "Verified")
        lines.append(f"[{check['status'].upper()}] {name}: {detail}")
    library = report["checks"].get("library", {})
    if library.get("actual"):
        counts = library["actual"]
        lines.append(f"  Source: {counts['components']} components / {counts['selections']} entries / {counts['imageCardVariants']} Image cards variants")
    execution = report["executionPrerequisites"]
    for name in ("codex", "mosaic"):
        check = execution.get(name)
        if check:
            lines.append(f"[{check['status'].upper()}] {name}: " + (check.get("path") or check["message"]))
    lines.append("sourceReady=" + str(report["sourceReady"]).lower())
    lines.append(execution.get("message", ""))
    lines.append(report["scope"])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print structured JSON instead of human-readable output")
    parser.add_argument("--live", action="store_true", help="Explicitly perform read-only Codex/Mosaic readiness checks; never generate")
    args = parser.parse_args(argv)
    report = run_checks(live=args.live)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_human(report))
    return report["exitCode"]


if __name__ == "__main__":
    raise SystemExit(main())
