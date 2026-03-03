#!/usr/bin/env python3
"""Modify selected SVG elements using Claude."""

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
from inky.utils.svg import extract_svg_from_response

SYSTEM_PROMPT = """\
You are an SVG modification assistant integrated into Inkscape.
The user will provide existing SVG elements and a description of how to modify them.

RULES:
- Return the modified SVG elements with the SAME IDs as the originals.
- Return ONLY the modified SVG elements, no explanations outside the code block.
- Preserve the element structure (same number of top-level elements).
- Return SVG inside a ```svg fenced code block.
"""


class ModifySelection(inkex.EffectExtension):
    """Inkscape effect: modify selected elements with Claude."""

    def add_arguments(self, pars: inkex.ArgumentParser) -> None:
        pars.add_argument("--instruction", type=str, default="", help="Modification instruction")
        pars.add_argument(
            "--model",
            type=str,
            default="claude-sonnet-4-5-20250929",
            help="Claude model to use",
        )
        pars.add_argument("--tab", type=str, default="", help="INX tab")

    def effect(self) -> None:
        instruction = self.options.instruction
        if not instruction.strip():
            inkex.errormsg("Please provide a modification instruction.")
            return

        if not self.svg.selection:
            inkex.errormsg("Please select one or more elements to modify.")
            return

        # Serialize selected elements
        selected_svg_parts = []
        selected_elements = list(self.svg.selection.values())
        for elem in selected_elements:
            selected_svg_parts.append(etree.tostring(elem, encoding="unicode"))

        selected_svg = "\n".join(selected_svg_parts)

        prompt = (
            f"Here are the selected SVG elements:\n\n```svg\n{selected_svg}\n```\n\n"
            f"Modification: {instruction}"
        )

        client = ClaudeClient(model=self.options.model)
        response = client.message(prompt, system=SYSTEM_PROMPT)

        svg_text = extract_svg_from_response(response)
        if not svg_text:
            inkex.errormsg("Claude did not return valid SVG. Response:\n" + response)
            return

        # Parse the modified elements
        try:
            wrapper = (
                f'<g xmlns="http://www.w3.org/2000/svg" '
                f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">'
                f'{svg_text}</g>'
            )
            parsed = etree.fromstring(wrapper.encode())
            new_elements = list(parsed)

            if len(new_elements) != len(selected_elements):
                inkex.errormsg(
                    f"Warning: Claude returned {len(new_elements)} elements "
                    f"but {len(selected_elements)} were selected. "
                    f"Replacing what we can."
                )

            # Replace each selected element with the corresponding new one
            for i, original in enumerate(selected_elements):
                if i >= len(new_elements):
                    break
                parent = original.getparent()
                if parent is not None:
                    idx = list(parent).index(original)
                    parent.remove(original)
                    parent.insert(idx, new_elements[i])

        except etree.XMLSyntaxError as e:
            inkex.errormsg(f"Failed to parse modified SVG: {e}\n\nRaw SVG:\n{svg_text}")


if __name__ == "__main__":
    ModifySelection().run()
