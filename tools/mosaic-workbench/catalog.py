"""Read-only catalog adapter for the delivered MM library (no JS execution).

Only JSON and a deliberately small JavaScript data-literal subset are parsed.
Unknown expressions remain evidence, never get evaluated. Source hashes bind all
selection records to the package actually being served by the workbench.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
import threading
from pathlib import Path
from urllib.parse import quote, urlencode
from settings import load_settings

VERSION = 1
ARCHIVE = "MM_design_library/MM-Design-Libraries-compat-00f36936859b.zip"
LIBRARIES = {"mm-image": "MM Image", "aigc": "AIGC", "video": "Video"}
_LOCK = threading.RLock()


class CatalogError(ValueError):
    pass


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _decode_js_string(raw: str) -> str:
    """Decode a string token; template interpolation is explicitly forbidden."""
    if raw[0] == "`" and "${" in raw:
        raise CatalogError("Interpolated template strings are not data")
    content = raw[1:-1]
    escapes = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}
    return re.sub(r"\\(?:x([0-9a-fA-F]{2})|u([0-9a-fA-F]{4})|([\s\S]))",
                  lambda m: chr(int(m[1] or m[2], 16)) if m[1] or m[2] else escapes.get(m[3], m[3]), content)


def _string_end(text: str, start: int) -> int:
    quote_char = text[start]
    i = start + 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
        elif text[i] == quote_char:
            return i + 1
        else:
            i += 1
    raise CatalogError("Unclosed source string")


def _end(text: str, start: int) -> int:
    pairs = {"[": "]", "{": "}", "(": ")"}
    stack = [pairs[text[start]]]
    i = start + 1
    while i < len(text):
        char = text[i]
        if char in "\"'`":
            i = _string_end(text, i)
            continue
        if char in pairs:
            stack.append(pairs[char])
        elif char in "]})":
            if char != stack.pop():
                raise CatalogError("Unbalanced data expression")
            if not stack:
                return i + 1
        i += 1
    raise CatalogError("Unclosed data expression")


def _split(text: str, delimiter=",") -> list[str]:
    result, start, i = [], 0, 0
    while i < len(text):
        char = text[i]
        if char in "\"'`":
            i = _string_end(text, i)
            continue
        if char in "[{(":
            i = _end(text, i)
            continue
        if char == delimiter:
            result.append(text[start:i].strip())
            start = i + 1
        i += 1
    result.append(text[start:].strip())
    return result


def _literal(text: str, constants=None):
    """Parse data only. Function calls and other code remain $expression."""
    text = text.strip()
    constants = constants or {}
    if not text:
        return None
    if text[0] in "\"'`" and _string_end(text, 0) == len(text):
        return _decode_js_string(text)
    if text in ("true", "!0"):
        return True
    if text in ("false", "!1"):
        return False
    if text in ("null", "undefined", "void 0"):
        return None
    if re.fullmatch(r"-?\d+(?:\.\d+)?(?:e[+-]?\d+)?", text, re.I):
        return float(text) if any(c in text.lower() for c in ".e") else int(text)
    if text in constants:
        return constants[text]
    if text[0] == "[" and _end(text, 0) == len(text):
        return [_literal(x, constants) for x in _split(text[1:-1]) if x]
    if text[0] == "{" and _end(text, 0) == len(text):
        result = {}
        for field in _split(text[1:-1]):
            parts = _split(field, ":")
            if len(parts) < 2:
                if field:
                    result.setdefault("$unresolvedFields", []).append(field)
                continue
            key = parts[0]
            key = _decode_js_string(key) if key[:1] in "\"'`" else key
            result[key] = _literal(":".join(parts[1:]), constants)
        return result
    return {"$expression": text}


def _constants(text):
    result, seen = {}, set()
    # Minified locals are reused across scopes. Resolve only uniquely assigned
    # names, and never single-letter locals from arbitrary functions.
    for m in re.finditer(r"\b([\w$]+)=(?=[\"'])", text):
        if len(m[1]) < 2:
            continue
        end = _string_end(text, m.end())
        if m[1] in seen:
            result.pop(m[1], None)
            continue
        seen.add(m[1])
        result[m[1]] = _decode_js_string(text[m.end():end])
    return result


def _registry(text, library):
    if library in ("aigc", "video"):
        for m in re.finditer(r"\b[\w$]+=JSON\.parse\(`", text):
            start = m.end() - 1
            end = _string_end(text, start)
            data = json.loads(_decode_js_string(text[start:end]))
            if isinstance(data, list) and data and isinstance(data[0], dict) and "slug" in data[0]:
                for component in data:
                    marker = '{"slug":' + json.dumps(component["slug"])
                    a = text.index(marker, start, end)
                    component["_sourceRange"] = (a, _end(text, a))
                return data, (start, end)
        raise CatalogError(f"No literal component registry in {library}")
    m = re.search(r"\b[\w$]+=\[\{slug:\"slideshow\",name:\"SlideShow\"", text)
    if not m:
        raise CatalogError("MM Image registry signature changed")
    start = text.index("[", m.start())
    end = _end(text, start)
    data = []
    constants = _constants(text)
    for raw in _split(text[start + 1:end - 1]):
        value = _literal(raw, constants)
        if isinstance(value, dict) and isinstance(value.get("slug"), str):
            a = text.index(raw, start, end)
            value["_sourceRange"] = (a, a + len(raw))
            data.append(value)
    return data, (start, end)


def _image_cards(text):
    groups = []
    constants = _constants(text)
    for m in re.finditer(r'\{size:"\d+x\d+",width:\d+,height:\d+,variants:\[', text):
        end = _end(text, m.start())
        group = _literal(text[m.start():end], constants)
        for index, variant in enumerate(group["variants"]):
            expression = variant.get("$expression", "")
            if expression.startswith("Ie(") and expression.endswith(")"):
                if 'Ie=(e,t,n,i,r)=>({id:e,label:t,nodeId:n,tree:i,notes:r})' not in text:
                    raise CatalogError("ImageCard variant constructor changed")
                args = [_literal(x, constants) for x in _split(expression[3:-1])]
                group["variants"][index] = dict(zip(("id", "label", "nodeId", "tree", "notes"), args))
        group["sourceRange"] = [m.start(), end]
        groups.append(group)
    if len(groups) != 13 or sum(len(g["variants"]) for g in groups) != 49:
        raise CatalogError("ImageCards source inventory changed; expected 13 sizes / 49 variants")
    return groups


def _data_tree(value, constants):
    """Bounded interpreter for three audited tree constructors, never JavaScript."""
    if isinstance(value, list):
        return [_data_tree(x, constants) for x in value]
    if not isinstance(value, dict):
        return value
    if "$expression" not in value:
        return {k: _data_tree(v, constants) for k, v in value.items()}
    expression = value["$expression"]
    call = re.fullmatch(r"(Lt|St|Dn)\((.*)\)", expression, re.S)
    if not call:
        return value
    args = [_data_tree(_literal(x, constants), constants) for x in _split(call[2])]
    family = "Roboto, 'Segoe UI', sans-serif"
    if call[1] == "St":
        width, height = args[:2]
        radius = args[2] if len(args) > 2 else 0
        oversize = args[3] if len(args) > 3 else False
        return {"kind": "action", "action": "open", "style": {"width": width, "height": height, "borderRadius": radius,
                "overflow": "hidden", "display": "flex", "alignItems": "center", "justifyContent": "center", "flexShrink": 0},
                "children": [{"kind": "image", "src": "mm-image-figma-fy25-windows-bloom.png", "alt": "Windows blue bloom",
                "style": {"width": width * 1.1518987 if oversize else width, "height": height * 1.15 if oversize else height,
                          "maxWidth": "none", "objectFit": "cover", "flexShrink": 0}}]}
    if call[1] == "Dn":
        small = bool(args and args[0])
        return {"kind": "action", "action": "more", "style": {"position": "absolute", "right": 12, "bottom": 12,
                "width": 88 if small else 95, "height": 28, "display": "flex", "alignItems": "center", "justifyContent": "center",
                "gap": 2, "padding": 4, "borderRadius": 9999, "background": "#000", "color": "#fff",
                "boxShadow": "inset 0 0 0 1px rgba(0,0,0,.1)"}, "children": [
                {"kind": "box", "style": {"width": 20, "height": 20, "display": "flex", "alignItems": "center", "justifyContent": "center"},
                 "children": [{"kind": "image", "src": "mm-image-figma-fy25-small-image-multiple.svg", "alt": "", "style": {"flexShrink": 0, "objectFit": "contain"}}]},
                {"kind": "text", "text": "All image" if small else "All images", "style": {"fontFamily": family, "fontSize": 13,
                 "lineHeight": "20px", "paddingRight": 4, "whiteSpace": "nowrap"}}]}
    width, height, children = args[:3]
    style = {"width": width, "height": height, "position": "relative", "display": "flex", "overflow": "hidden", "borderRadius": 16,
             "background": "#fff", "fontFamily": family, "fontSize": 13, "lineHeight": "20px", "color": "#000"}
    if len(args) > 3 and isinstance(args[3], dict):
        style.update(args[3])
    return {"kind": "box", "style": style, "children": children, **({"id": args[4]} if len(args) > 4 else {})}


def _selections(component):
    """Named axes are selectable; don't invent a Cartesian product of states."""
    props = component.get("props", [])
    props = props if isinstance(props, list) else []
    defaults = {p["name"]: p.get("default") for p in props if isinstance(p, dict) and "name" in p and not isinstance(p.get("default"), dict)}
    yield "default", "Default", defaults, "default", None
    seen = {json.dumps(defaults, sort_keys=True)}
    for prop in props:
        if not isinstance(prop, dict) or prop.get("kind") != "select" or not isinstance(prop.get("values"), list):
            continue
        for value in prop["values"]:
            if not isinstance(value, (str, int, float)):
                continue
            values = {**defaults, prop["name"]: value}
            # Honor declared dependent options after changing their parent.
            for child in props:
                dep = child.get("valuesByParent", {}) if isinstance(child, dict) else {}
                if not isinstance(dep, dict) or dep.get("prop") != prop["name"]:
                    continue
                options = dep.get("options", {}).get(str(value), [])
                if options and values.get(child["name"]) not in options:
                    values[child["name"]] = options[0]
            key = json.dumps(values, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            yield f"{quote(prop['name'], safe='')}={quote(str(value), safe='')}", f"{prop['name']}: {value}", values, "axis-choice-with-defaults", prop["name"]


def _source_configurations(component):
    """Use explicit source→React mappings only, never guess matching names."""
    defaults = {p["name"]: p.get("default") for p in component.get("props", []) if isinstance(p, dict) and "name" in p}
    mapping = component.get("propertyMapping", {})
    for variant in component.get("variants", []):
        if not isinstance(variant, dict) or not variant.get("nodeId"):
            continue
        properties = variant.get("properties", {})
        values = {react: properties[source] for react, source in mapping.items() if source in properties}
        if values:
            yield variant, {**defaults, **values}
    axes = component.get("originalAxes", {})
    mapped_axes = [v for v in axes.values() if isinstance(v, dict) and v.get("reactProp")]
    for variant in component.get("configurations", []):
        if not isinstance(variant, dict) or not variant.get("nodeId") or "value" not in variant:
            continue
        matches = [a for a in mapped_axes if variant["value"] in a.get("values", [])]
        if len(matches) == 1:
            yield variant, {**defaults, matches[0]["reactProp"]: variant["value"]}


def _package_class(root):
    name = "_mosaic_catalog_verified_package"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, root / "tools/library-to-mosaic/library_to_mosaic.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[name] = module
    return sys.modules[name].LibraryPackage


def build_catalog(project_root: Path, *, archive_path: Path | str | None = None) -> dict:
    root = Path(project_root).resolve()
    configured = archive_path or load_settings(root)['libraryZip']
    archive = Path(configured).expanduser()
    if not archive.is_absolute():
        archive = root / archive
    with _LOCK, _package_class(root)(archive) as package:
        sha = package.provenance["package"]["sha256"]
        cache = root / "tools/mosaic-workbench/state/catalog" / sha
        library_root = cache / "library"
        if cache.is_symlink() or library_root.is_symlink():
            raise CatalogError("Catalog cache must not be a symlink")
        if not cache.exists():
            package.extract(cache)
        else:
            # Cached scripts/assets are served to a browser: verify their bytes,
            # not just the archive or an editable cache metadata file.
            for name, digest in package.manifest["files"].items():
                path = library_root / name
                if path.is_symlink() or not path.is_file() or _digest(path.read_bytes()) != digest:
                    raise CatalogError(f"Extracted library cache changed: {name}")
        items = []
        counts = {}
        for library, label in LIBRARIES.items():
            entry = package.manifest["entries"][library]
            script = entry["script"]
            text = package.read_verified(script).decode("utf-8")
            registry, source_range = _registry(text, library)
            counts[library] = len(registry)
            for component in registry:
                slug = component["slug"]
                component_range = component.get("_sourceRange", source_range)
                if library == "mm-image" and slug == "image-cards":
                    for group in _image_cards(text):
                        for variant in group["variants"]:
                            values = {"size": group["size"], "variant": variant["label"]}
                            item = _item(library, label, component, f"{group['size']}/{variant['id']}", variant["label"], values, script,
                                         package.manifest["files"][script], group["sourceRange"], entry["html"])
                            item.update(size=group["size"], width=group["width"], height=group["height"],
                                        previewPath=entry["html"] + "#/c/image-cards?" + urlencode(values, quote_via=quote))
                            item["details"].update(selectionKind="source-variant", previewSelectionMode="query",
                                                   nodeId=variant["nodeId"], rawDesignTree=variant.get("tree"),
                                                   geometryStatus="declared-source-variant", thumbnailRole="source-image-not-card-screenshot")
                            item["thumbnail"] = "mm-image-figma-fy25-windows-bloom.png"
                            items.append(item)
                    continue
                for key, variant, values, kind, axis in _selections(component):
                    item = _item(library, label, component, key, variant, values, script,
                                 package.manifest["files"][script], component_range, entry["html"])
                    item["details"].update(selectionKind=kind, changedAxis=axis, previewSelectionMode="controls" if key != "default" else "default")
                    items.append(item)
                for configuration, values in _source_configurations(component):
                    item = _item(library, label, component, "source-" + configuration["nodeId"].replace(":", "-"),
                                 configuration.get("name", str(configuration.get("value"))), values, script,
                                 package.manifest["files"][script], component_range, entry["html"])
                    item.update(width=configuration.get("width"), height=configuration.get("height"))
                    item["details"].update(selectionKind="source-configuration", previewSelectionMode="controls",
                                           geometryStatus="declared-source-configuration", nodeId=configuration["nodeId"],
                                           sourceConfiguration=configuration)
                    items.append(item)
        ids = [i["id"] for i in items]
        if len(set(ids)) != len(ids):
            raise CatalogError("Duplicate stable selection IDs")
        result = {"catalogVersion": VERSION,
                  "package": {"name": package.path.name, "path": str(package.path), "sha256": sha, "builtAt": package.manifest.get("builtAt")},
                  "items": items, "libraryRoot": str(library_root),
                  "coverage": {"componentsByLibrary": counts, "selectionCount": len(items), "imageCardVariants": 49,
                               "variantPolicy": "ImageCards: every source variant. Other components: explicit mapped source configurations, default and each declared select-axis choice with other values at defaults; not all Cartesian combinations."}}
        (cache / "catalog.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        return result


def _item(library, label, component, key, variant, values, script, digest, source_range, html):
    size = values.get("size")
    preview_sizes = component.get("previewSizes", {})
    preview = preview_sizes.get(str(size), {}) if isinstance(preview_sizes, dict) else {}
    if not preview:
        preview = component.get("previewSize", {})
    if not isinstance(preview, dict):
        preview = {}
    return {"id": f"{library}/{component['slug']}/{key}", "library": library, "libraryName": label,
            "componentId": component["slug"], "name": component["name"], "category": component.get("tier", "Unspecified"),
            "variant": variant, "size": size, "width": preview.get("width"), "height": preview.get("height"),
            "description": component.get("overview", ""), "previewPath": html + "#/c/" + quote(component["slug"]), "thumbnail": None,
            "source": {"archivePath": script, "sha256": digest, "characterStart": source_range[0], "characterEndExclusive": source_range[1]},
            "details": {"selectionValues": values, "props": component.get("props", []), "notes": component.get("notes", []),
                        "componentTag": component.get("tag"), "sourceStatus": component.get("sourceStatus"),
                        "nodeId": component.get("nodeId"), "partOf": component.get("partOf"), "sourceVerifiedFlag": component.get("verified"),
                        "configurationEvidence": component.get("configurations", []), "geometryStatus": "declared-preview" if preview else "unknown"}}


def _mask_strings(text):
    result, start, i = [], 0, 0
    while i < len(text):
        if text[i] == "/":
            previous = text[:i].rstrip()
            regex_start = not previous or previous[-1] in "(=:[,!&|?{};" or previous.endswith("return")
            if text[i:i + 2] == "//":
                end = text.find("\n", i)
                end = len(text) if end < 0 else end
            elif text[i:i + 2] == "/*":
                end = text.find("*/", i + 2)
                end = len(text) if end < 0 else end + 2
            elif regex_start:
                end, in_class = i + 1, False
                while end < len(text):
                    char = text[end]
                    if char == "\\":
                        end += 2
                        continue
                    if char == "[":
                        in_class = True
                    elif char == "]":
                        in_class = False
                    elif char == "/" and not in_class:
                        end += 1
                        while end < len(text) and text[end].isalpha():
                            end += 1
                        break
                    end += 1
            else:
                i += 1
                continue
            result.extend((text[start:i], " " * (end - i)))
            i = start = end
            continue
        if text[i] in "\"'`":
            result.append(text[start:i])
            end = _string_end(text, i)
            # Keep interpolation code as unresolved evidence rather than trying
            # to interpret template expressions in this dependency scanner.
            result.append(text[i] + " " * (end - i - 2) + text[end - 1])
            i = start = end
        else:
            i += 1
    result.append(text[start:])
    return "".join(result)


def _source_support(text, item, library_root):
    """Collect bounded actual renderer/data/CSS evidence, without executing it."""
    library, slug = item["library"], item["componentId"]
    map_marker = {"mm-image": "const Gl={", "aigc": "Pa={", "video": "Hg=tf({"}[library]
    if map_marker not in text:
        return [], [], "Renderer registry signature unavailable"
    map_start = text.index("{", text.index(map_marker))
    map_end = _end(text, map_start)
    mapping = _literal(text[map_start:map_end], _constants(text))
    if library == "video":
        expression = mapping.get(item["details"].get("componentTag"), {})
    else:
        expression = mapping.get(slug, {})
    if library == "mm-image" and slug == "image-cards":
        tree_text = json.dumps(item["details"].get("rawDesignTree", {}))
        roots = ["Mp", *sorted(set(re.findall(r"\b([A-Za-z_$][\w$]*)\(", tree_text)))]
    else:
        raw = expression.get("$expression", "") if isinstance(expression, dict) else ""
        roots = re.findall(r"=>([A-Za-z_$][\w$]*)", raw) if library == "video" else re.findall(r"\.jsx[s]?\)?\(([A-Za-z_$][\w$]*)", raw)
        roots = list(dict.fromkeys(x for x in roots if x not in ("String", "Number")))
    if not roots:
        return [], [], "No component renderer binding could be statically identified"
    floor = text.index("const Vs=") if library == "mm-image" else _registry(text, library)[1][0]
    masked = _mask_strings(text[floor:])
    declarations, duplicates = {}, set()
    for m in re.finditer(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(", masked):
        start = floor + m.start()
        symbol = m[1]
        try:
            params_end = _end(text, floor + m.end() - 1)
            body_start = params_end
            while text[body_start].isspace():
                body_start += 1
            if text[body_start] != "{":
                continue
            end = _end(text, body_start)
        except (CatalogError, IndexError):
            continue
        if symbol in declarations:
            duplicates.add(symbol)
        declarations[symbol] = (start, end, "renderer-function")
    # Literal sample arrays, icon dictionaries and image URL maps are often
    # imported by the renderer. Preserve exact declarations, not inferred data.
    for m in re.finditer(r"\b([A-Za-z_$][\w$]*)=(?=[\[{\"'])", masked):
        symbol = m[1]
        if len(symbol) < 2:
            continue
        a = floor + m.end()
        try:
            end = _string_end(text, a) if text[a] in "\"'" else _end(text, a)
        except (CatalogError, IndexError):
            continue
        if symbol in declarations:
            duplicates.add(symbol)
        declarations[symbol] = (floor + m.start(), end, "sample-data")
    # Pure arrow constructors are retained as source, not run or interpreted.
    for m in re.finditer(r"\b([A-Za-z_$][\w$]*)=((?:\([^;{}]*?\)|[A-Za-z_$][\w$]*)=>)", masked):
        symbol = m[1]
        a = floor + m.start()
        pos = floor + m.end()
        try:
            while pos < len(text) and text[pos] not in ",;":
                if text[pos] in "([{":
                    pos = _end(text, pos)
                elif text[pos] in "\"'`":
                    pos = _string_end(text, pos)
                else:
                    pos += 1
        except (CatalogError, IndexError):
            continue
        if symbol in declarations:
            duplicates.add(symbol)
        declarations[symbol] = (a, pos, "renderer-constructor")
    for symbol in duplicates:
        declarations.pop(symbol, None)
    source = item["source"]
    evidence, unresolved, visited = [], [], set()
    queue = [(symbol, 0) for symbol in roots]
    budget = 100_000
    while queue and len(evidence) < 40:
        symbol, depth = queue.pop(0)
        if symbol in visited:
            continue
        visited.add(symbol)
        declaration = declarations.get(symbol)
        if declaration is None:
            unresolved.append(symbol)
            continue
        a, b, kind = declaration
        fragment = text[a:b]
        if len(fragment) > budget:
            unresolved.append(symbol + ": evidence budget exceeded")
            continue
        budget -= len(fragment)
        evidence.append({**source, "characterStart": a, "characterEndExclusive": b, "excerpt": fragment,
                         "excerptSha256": _digest(fragment.encode()), "kind": kind, "symbol": symbol,
                         "dependencyDepth": depth})
        masked_fragment = _mask_strings(fragment)
        tokens = {match[1] for match in re.finditer(r"(?<![\w$.])([A-Za-z_$][\w$]*)", masked_fragment)
                  if not masked_fragment[match.end():].lstrip().startswith(":")}
        dependencies = sorted(x for x in tokens.intersection(declarations) - visited if len(x) >= 2)
        if library == "mm-image" and slug == "image-cards":
            dependencies = [x for x in dependencies if x not in ("Qs", "Ys", "ve")]
        if depth < 3:
            queue.extend((dependency, depth + 1) for dependency in dependencies)
        else:
            unresolved.extend(dependencies)
    unresolved.extend(symbol for symbol, _ in queue if symbol not in visited)
    if not any(e.get("symbol") in roots and e["kind"] in ("renderer-function", "renderer-constructor") for e in evidence):
        return evidence, sorted(set(unresolved)), "Primary renderer function could not be collected"
    # CSS class prefixes are derived from the exact selected implementation.
    # Preserve only matching rules plus custom-property rules they reference.
    classes = set()
    for record in evidence:
        for m in re.finditer(r'className:["`]([^"`]+)', record["excerpt"]):
            classes.update(re.findall(r"\b[a-z][a-z0-9]*(?:-[a-z0-9]+)+", m[1].split("${", 1)[0]))
    manifest = json.loads((library_root / "BUILD-MANIFEST.json").read_text())
    css_path = manifest["entries"][library]["css"]
    css = (library_root / css_path).read_text()
    rules = []
    variables = set()
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        if any(re.search(r"\." + re.escape(name) + r"(?:-[a-zA-Z0-9_-]+)?(?=[^a-zA-Z0-9_-]|$)", m[1]) for name in classes):
            rules.append(m)
            variables.update(re.findall(r"var\((--[a-zA-Z0-9_-]+)", m[2]))
    for m in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        if variables and any(var + ":" in m[2] for var in variables) and m not in rules:
            rules.append(m)
    for m in rules[:120]:
        fragment = m[0]
        if len(fragment) > budget:
            break
        budget -= len(fragment)
        evidence.append({"archivePath": css_path, "sha256": manifest["files"][css_path],
                         "characterStart": m.start(), "characterEndExclusive": m.end(), "excerpt": fragment,
                         "excerptSha256": _digest(fragment.encode()), "kind": "style-rule",
                         "scopeNote": "Read original stylesheet for enclosing media conditions; this excerpt records the selector rule."})
    return evidence, sorted(set(unresolved)), None


def extract_selection(project_root: Path, item_id: str, *, archive_path: Path | str | None = None) -> dict:
    catalog = build_catalog(project_root, archive_path=archive_path)
    item = next((x for x in catalog["items"] if x["id"] == item_id), None)
    if item is None:
        raise CatalogError(f"Unknown selection: {item_id}")
    library_root = Path(catalog["libraryRoot"])
    text = (library_root / item["source"]["archivePath"]).read_text()
    source = item["source"]
    excerpt = text[source["characterStart"]:source["characterEndExclusive"]]
    raw_tree = item["details"].get("rawDesignTree")
    contracts = json.loads((Path(__file__).parent / "catalog_data/adapter-contract.json").read_text())
    matched_adapter = source["sha256"] == contracts["imageCardConstructorBundleSha256"]
    tree = _data_tree(raw_tree, _constants(text)) if raw_tree and matched_adapter else raw_tree
    evidence_text = json.dumps(tree, ensure_ascii=False) if tree else excerpt
    support = []
    if item["library"] == "mm-image" and item["componentId"] == "image-cards":
        for start_marker, end_marker in [("const Vs=", "function Gs("), ("function Mp(", "const wb=")]:
            if start_marker in text and end_marker in text:
                a = text.index(start_marker)
                b = text.index(end_marker, a)
                part = text[a:b]
                support.append({"archivePath": source["archivePath"], "sha256": source["sha256"],
                                "characterStart": a, "characterEndExclusive": b, "excerpt": part,
                                "excerptSha256": _digest(part.encode())})
        evidence_text += " mm-image-assets-roboto-400-BqEyEoaF.woff2"
    complete = tree is not None and "$expression" not in json.dumps(tree)
    if complete:
        renderer_support, unresolved, renderer_issue = [], [], None
    else:
        renderer_support, unresolved, renderer_issue = _source_support(text, item, library_root)
    support.extend(renderer_support)
    evidence_text += " ".join(record["excerpt"] for record in renderer_support)
    # Do not turn a whole-library image manifest into the selected component's
    # assets. A hashed image must also be referenced outside that broad map.
    scoped_asset_text = " ".join(record["excerpt"] for record in renderer_support
                                 if len(re.findall(r"\.(?:png|webp|jpg|svg)", record["excerpt"])) < 20)
    scoped_hashes = set(re.findall(r"[0-9a-f]{40}", scoped_asset_text))
    assets = []
    for path in library_root.iterdir():
        if path.suffix.lower() not in (".png", ".svg", ".webp", ".jpg", ".jpeg", ".woff2"):
            continue
        if path.name in evidence_text:
            hashes = re.findall(r"[0-9a-f]{40}", path.name)
            if hashes and renderer_support and not any(h in scoped_hashes for h in hashes):
                continue
            assets.append({"archivePath": path.name, "localPath": str(path), "sha256": _digest(path.read_bytes()), "bytes": path.stat().st_size,
                           "role": "exact-tree-asset" if complete else "renderer-dependency-asset",
                           "selectionScope": "Selected tree" if complete else "Selected renderer dependency; may include sibling variant samples in a shared data table."})
    missing_design = item["details"].get("sourceStatus") in ("in-progress", "reference-only") or item["componentId"] in ("serp-video-answer-go-wide", "vrp-whole-page")
    can_attempt = not missing_design and (complete or renderer_issue is None)
    readiness = {"canAttempt": can_attempt, "hasSourceEvidence": can_attempt,
                 "status": "parsed-source-tree" if complete else "source-code-evidence" if can_attempt else "needs-source-evidence",
                 "reason": "Source marks this design as unfinished or reference-only." if missing_design else renderer_issue or "Actual renderer and bounded dependencies were collected; AI must inspect and resolve remaining gaps.",
                 "rendererEvidenceCount": sum(e.get("kind") in ("renderer-function", "renderer-constructor") for e in support),
                 "styleEvidenceCount": sum(e.get("kind") == "style-rule" for e in support),
                 "assetEvidenceCount": len(assets), "unresolvedDependencies": unresolved, "runtimeVerified": False}
    result = {"selection": item, "package": catalog["package"], "libraryRoot": catalog["libraryRoot"],
              "sourceEvidence": {**source, "excerpt": excerpt, "excerptSha256": _digest(excerpt.encode())},
              "supportingSourceEvidence": support,
              "designTree": tree, "designTreeStatus": "parsed-source-tree" if complete else "partial" if tree else "unknown",
              "assets": assets, "knownRules": item["details"].get("notes", []), "referenceScreenshot": None,
              "sourceEvidenceReady": can_attempt, "authoringReadiness": readiness,
              "unknowns": ["Mosaic rendering/interaction support must be verified live.", "Relative library assets are not automatically reachable by Mosaic."]}
    if not complete:
        result["unknowns"].append("Read the supplied preview and unresolved source expressions for full geometry/behavior; do not infer missing details.")
    result["previewInstructions"] = {"path": item["previewPath"], "selectionMode": item["details"]["previewSelectionMode"],
                                     "values": item["details"]["selectionValues"],
                                     "controlLocatorStrategy": "Exact accessible label equal to the property name; AIGC/Video IDs have a runtime-generated prefix.",
                                     "note": "For controls mode set the named component property controls. The URL opens the component, not a fictional variant deep link."}
    return result
