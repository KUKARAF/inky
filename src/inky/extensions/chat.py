#!/usr/bin/env python3
"""Launch the Claude Chat Assistant window from Inkscape."""

from __future__ import annotations

import os
import sys

# Add src/ to path for `import inky`, and _vendor/ for third-party deps (httpx).
# Python resolves __file__ through symlinks, so paths are relative to source tree.
_inky_pkg = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # src/inky/
_src_dir = os.path.dirname(_inky_pkg)                                     # src/
_vendor = os.path.join(_inky_pkg, "_vendor")                              # src/inky/_vendor/

if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)
if os.path.isdir(_vendor) and _vendor not in sys.path:
    sys.path.insert(0, _vendor)

import inkex
from lxml import etree

from inky.ui.chat_window import run_chat_window


class ChatAssistant(inkex.EffectExtension):
    """Inkscape effect: open the Claude chat assistant."""

    def add_arguments(self, pars: inkex.ArgumentParser) -> None:
        pars.add_argument("--tab", type=str, default="", help="INX tab")

    def effect(self) -> None:
        # Serialize the full document for context
        document_svg = etree.tostring(
            self.document.getroot(), encoding="unicode"
        )

        # Callback to insert SVG from chat into the document
        layer = self.svg.get_current_layer()

        def insert_svg(svg_text: str) -> None:
            try:
                wrapper = (
                    f'<g xmlns="http://www.w3.org/2000/svg" '
                    f'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">'
                    f'{svg_text}</g>'
                )
                parsed = etree.fromstring(wrapper.encode())
                for child in parsed:
                    layer.append(child)
            except etree.XMLSyntaxError as e:
                inkex.errormsg(f"Failed to insert SVG: {e}")

        run_chat_window(
            document_svg=document_svg,
            on_insert_svg=insert_svg,
        )


if __name__ == "__main__":
    ChatAssistant().run()
