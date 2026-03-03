#!/usr/bin/env python3
"""Explain selected SVG elements using Claude."""

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

SYSTEM_PROMPT = """\
You are an SVG analysis assistant integrated into Inkscape.
The user will provide SVG elements from their document.

Explain:
1. What the elements visually represent.
2. Key attributes and their effects (fill, stroke, transforms, etc.).
3. Any potential improvements or issues you notice.

Keep the explanation concise and practical.
"""


def _show_explanation(text: str) -> None:
    """Show the explanation in a GTK dialog."""
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk

        dialog = Gtk.Dialog(
            title="Claude — SVG Explanation",
            flags=Gtk.DialogFlags.MODAL,
        )
        dialog.set_default_size(600, 400)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        textview = Gtk.TextView()
        textview.set_editable(False)
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textview.set_left_margin(12)
        textview.set_right_margin(12)
        textview.set_top_margin(12)
        textview.set_bottom_margin(12)
        buf = textview.get_buffer()
        buf.set_text(text)

        scrolled.add(textview)
        dialog.get_content_area().pack_start(scrolled, True, True, 0)
        dialog.show_all()
        dialog.run()
        dialog.destroy()
    except (ImportError, ValueError):
        # Fallback: print to stderr which Inkscape shows as a message
        inkex.errormsg("=== Claude Explanation ===\n\n" + text)


class ExplainSelection(inkex.EffectExtension):
    """Inkscape effect: explain selected SVG elements."""

    def add_arguments(self, pars: inkex.ArgumentParser) -> None:
        pars.add_argument(
            "--model",
            type=str,
            default="claude-sonnet-4-5-20250929",
            help="Claude model to use",
        )
        pars.add_argument("--tab", type=str, default="", help="INX tab")

    def effect(self) -> None:
        if not self.svg.selection:
            inkex.errormsg("Please select one or more elements to explain.")
            return

        # Serialize selected elements
        selected_svg_parts = []
        for elem in self.svg.selection.values():
            selected_svg_parts.append(etree.tostring(elem, encoding="unicode"))

        selected_svg = "\n".join(selected_svg_parts)

        prompt = f"Explain these SVG elements:\n\n```svg\n{selected_svg}\n```"

        client = ClaudeClient(model=self.options.model)
        response = client.message(prompt, system=SYSTEM_PROMPT)

        _show_explanation(response)


if __name__ == "__main__":
    ExplainSelection().run()
