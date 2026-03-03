"""SVG parsing, validation, and context extraction utilities."""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
XLINK_NS = "http://www.w3.org/1999/xlink"

NAMESPACES = {
    "svg": SVG_NS,
    "inkscape": INKSCAPE_NS,
    "xlink": XLINK_NS,
}


def extract_svg_from_response(text: str) -> str | None:
    """Extract SVG content from a Claude response.

    Looks for SVG inside ```svg or ```xml fenced code blocks,
    or raw <svg>...</svg> / bare SVG elements.
    """
    # Try fenced code blocks first
    patterns = [
        r"```(?:svg|xml)\s*\n(.*?)```",
        r"```\s*\n(<(?:svg|g|path|rect|circle|ellipse|line|polyline|polygon|text|defs|use)[\s>].*?)```",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

    # Try raw SVG element
    match = re.search(
        r"(<(?:svg|g|path|rect|circle|ellipse|line|polyline|polygon|text|defs|use)[\s>].*)",
        text,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip()

    return None


def validate_svg(svg_string: str) -> ET.Element:
    """Parse and validate an SVG string.

    Returns the parsed Element tree root.
    Raises ValueError if the SVG is invalid.
    """
    # Register namespaces so they serialize cleanly
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)

    # Wrap bare elements in a group if they don't have a root
    stripped = svg_string.strip()
    if not stripped.startswith("<"):
        raise ValueError("SVG content does not start with an element")

    try:
        root = ET.fromstring(svg_string)
    except ET.ParseError as e:
        # Try wrapping in an SVG namespace context
        try:
            wrapped = f'<g xmlns="{SVG_NS}">{svg_string}</g>'
            root = ET.fromstring(wrapped)
        except ET.ParseError:
            raise ValueError(f"Invalid SVG: {e}") from e

    return root


def element_to_string(element: ET.Element) -> str:
    """Serialize an Element back to an SVG string."""
    for prefix, uri in NAMESPACES.items():
        ET.register_namespace(prefix, uri)
    return ET.tostring(element, encoding="unicode")


def get_document_context(svg_root: ET.Element) -> dict:
    """Extract document metadata for Claude context.

    Returns a dict with width, height, viewBox, and other useful info.
    """
    context = {}
    for attr in ("width", "height", "viewBox"):
        val = svg_root.get(attr)
        if val:
            context[attr] = val

    # Count elements by type
    element_counts: dict[str, int] = {}
    for elem in svg_root.iter():
        tag = elem.tag
        # Strip namespace
        if "}" in tag:
            tag = tag.split("}", 1)[1]
        element_counts[tag] = element_counts.get(tag, 0) + 1
    context["element_counts"] = element_counts

    return context


def extract_defs(svg_root: ET.Element) -> str | None:
    """Extract <defs> section from an SVG document."""
    for defs in svg_root.iter(f"{{{SVG_NS}}}defs"):
        return element_to_string(defs)
    # Try without namespace
    for defs in svg_root.iter("defs"):
        return element_to_string(defs)
    return None


def extract_referenced_defs(
    elements: list[ET.Element], svg_root: ET.Element
) -> str | None:
    """Extract only the defs referenced by the given elements."""
    # Collect all href/url references
    refs: set[str] = set()
    for elem in elements:
        for attr_val in elem.attrib.values():
            # url(#id) references
            for match in re.finditer(r"url\(#([^)]+)\)", attr_val):
                refs.add(match.group(1))
            # xlink:href="#id" references
            if attr_val.startswith("#"):
                refs.add(attr_val[1:])
        # Check xlink:href
        href = elem.get(f"{{{XLINK_NS}}}href") or elem.get("href")
        if href and href.startswith("#"):
            refs.add(href[1:])

    if not refs:
        return None

    # Find matching defs
    matched: list[ET.Element] = []
    for defs in svg_root.iter(f"{{{SVG_NS}}}defs"):
        for child in defs:
            elem_id = child.get("id")
            if elem_id and elem_id in refs:
                matched.append(child)

    if not matched:
        return None

    defs_el = ET.Element(f"{{{SVG_NS}}}defs")
    for m in matched:
        defs_el.append(m)
    return element_to_string(defs_el)
