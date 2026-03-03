#!/usr/bin/env python3
"""Generate SVG elements from a natural language description."""

from __future__ import annotations

import os
import sys

_inky_pkg = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.dirname(_inky_pkg)
_vendor = os.path.join(_inky_pkg, "_vendor")

if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
if os.path.isdir(_vendor) and _vendor not in sys.path:
    sys.path.insert(0, _vendor)

import inkex
from lxml import etree

from inky.api.client import ClaudeClient
from inky.utils.svg import extract_svg_from_response, get_document_context

SYSTEM_PROMPT = """\
You are an SVG generation assistant integrated into Inkscape.
The user will describe a visual element they want to create.

RULES:
- Return ONLY valid SVG elements (path, rect, circle, g, etc.)
- Do NOT wrap in an <svg> root — these elements will be inserted into an existing document.
- Use the document dimensions provided for appropriate sizing.
- Use meaningful element IDs.
- Return SVG inside a ```svg fenced code block.
"""


class GenerateSVG(inkex.EffectExtension):
    """Inkscape effect: generate SVG from text description."""

    def add_arguments(self, pars: inkex.ArgumentParser) -> None:
        pars.add_argument("--description", type=str, default="", help="What to generate")
        pars.add_argument(
            "--model",
            type=str,
            default="claude-sonnet-4-5-20250929",
            help="Claude model to use",
        )
        pars.add_argument("--tab", type=str, default="", help="INX tab")

    def effect(self) -> None:
        description = self.options.description
        if not description.strip():
            inkex.errormsg("Please provide a description of what to generate.")
            return

        # Build context from current document
        doc_context = get_document_context(self.document.getroot())
        context_str = (
            f"Document dimensions: {doc_context.get('width', 'unknown')} x "
            f"{doc_context.get('height', 'unknown')}, "
            f"viewBox: {doc_context.get('viewBox', 'not set')}"
        )

        prompt = f"{context_str}\n\nGenerate: {description}"

        client = ClaudeClient(model=self.options.model)
        response = client.message(prompt, system=SYSTEM_PROMPT)

        svg_text = extract_svg_from_response(response)
        if not svg_text:
            inkex.errormsg("Claude did not return valid SVG. Response:\n" + response)
            return

        # Parse and insert into current layer
        try:
            # Wrap for parsing if needed
            if not svg_text.strip().startswith("<"):
                inkex.errormsg("Invalid SVG content received.")
                return

            # Parse as XML fragment
            wrapper = (
                f'<g xmlns="http://www.w3.org/2000/svg" '
                f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">'
                f'{svg_text}</g>'
            )
            parsed = etree.fromstring(wrapper.encode())

            layer = self.svg.get_current_layer()
            for child in parsed:
                layer.append(child)

        except etree.XMLSyntaxError as e:
            inkex.errormsg(f"Failed to parse generated SVG: {e}\n\nRaw SVG:\n{svg_text}")


if __name__ == "__main__":
    GenerateSVG().run()
