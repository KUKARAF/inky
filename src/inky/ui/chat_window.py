#!/usr/bin/env python3
"""GTK 3 chat assistant window for Claude + Inkscape."""

from __future__ import annotations

import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango  # noqa: E402

from inky.api.client import ClaudeClient, DEFAULT_MODEL  # noqa: E402
from inky.utils.svg import extract_svg_from_response  # noqa: E402

SYSTEM_PROMPT = """\
You are an SVG and design assistant integrated into Inkscape via the "inky" extension.
You help users create, modify, and understand SVG graphics.

When the user asks you to generate or modify SVG:
- Return SVG elements inside a ```svg fenced code block.
- Do NOT wrap in an <svg> root unless asked.
- Keep explanations concise.

You have access to the user's current Inkscape document SVG for context.
"""

MODELS = [
    ("claude-sonnet-4-5-20250929", "Sonnet 4.5 (Fast)"),
    ("claude-opus-4-6", "Opus 4.6 (Powerful)"),
]


class ChatWindow(Gtk.Window):
    """Multi-turn chat window for Claude AI assistance."""

    def __init__(self, document_svg: str = "") -> None:
        super().__init__(title="inky — Claude Chat Assistant")
        self.set_default_size(520, 700)
        self.set_keep_above(True)

        self.document_svg = document_svg
        self.conversation: list[dict] = []
        self._streaming = False

        # Callbacks for SVG insertion (set by the extension runner)
        self.on_insert_svg: callable | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(vbox)

        # --- Toolbar ---
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.set_margin_start(8)
        toolbar.set_margin_end(8)
        toolbar.set_margin_top(8)
        toolbar.set_margin_bottom(4)

        model_label = Gtk.Label(label="Model:")
        toolbar.pack_start(model_label, False, False, 0)

        self.model_combo = Gtk.ComboBoxText()
        for model_id, label in MODELS:
            self.model_combo.append(model_id, label)
        self.model_combo.set_active(0)
        toolbar.pack_start(self.model_combo, False, False, 0)

        refresh_btn = Gtk.Button(label="Refresh Doc Context")
        refresh_btn.connect("clicked", self._on_refresh_context)
        toolbar.pack_end(refresh_btn, False, False, 0)

        clear_btn = Gtk.Button(label="Clear Chat")
        clear_btn.connect("clicked", self._on_clear)
        toolbar.pack_end(clear_btn, False, False, 0)

        vbox.pack_start(toolbar, False, False, 0)

        # --- Separator ---
        vbox.pack_start(Gtk.Separator(), False, False, 0)

        # --- Message area ---
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        self.messages_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=8
        )
        self.messages_box.set_margin_start(8)
        self.messages_box.set_margin_end(8)
        self.messages_box.set_margin_top(8)
        self.messages_box.set_margin_bottom(8)
        scrolled.add(self.messages_box)
        self.scrolled = scrolled

        vbox.pack_start(scrolled, True, True, 0)

        # --- Input area ---
        vbox.pack_start(Gtk.Separator(), False, False, 0)

        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_box.set_margin_start(8)
        input_box.set_margin_end(8)
        input_box.set_margin_top(8)
        input_box.set_margin_bottom(8)

        input_scroll = Gtk.ScrolledWindow()
        input_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        input_scroll.set_min_content_height(60)
        input_scroll.set_max_content_height(150)

        self.input_view = Gtk.TextView()
        self.input_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.input_view.set_left_margin(8)
        self.input_view.set_right_margin(8)
        self.input_view.set_top_margin(4)
        self.input_view.set_bottom_margin(4)
        self.input_view.connect("key-press-event", self._on_key_press)
        input_scroll.add(self.input_view)

        input_box.pack_start(input_scroll, True, True, 0)

        self.send_btn = Gtk.Button(label="Send")
        self.send_btn.connect("clicked", self._on_send)
        self.send_btn.set_valign(Gtk.Align.END)
        input_box.pack_end(self.send_btn, False, False, 0)

        vbox.pack_start(input_box, False, False, 0)

    def _on_key_press(self, widget: Gtk.TextView, event) -> bool:
        """Send on Enter (without Shift)."""
        from gi.repository import Gdk
        if event.keyval == Gdk.KEY_Return and not (event.state & Gdk.ModifierType.SHIFT_MASK):
            self._on_send(None)
            return True
        return False

    def _on_send(self, _btn: Gtk.Button | None) -> None:
        if self._streaming:
            return

        buf = self.input_view.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()
        if not text:
            return

        buf.set_text("")
        self._add_message("user", text)
        self.conversation.append({"role": "user", "content": text})

        # Start streaming response in background thread
        self._streaming = True
        self.send_btn.set_sensitive(False)
        assistant_label = self._add_message("assistant", "...")

        model_id = self.model_combo.get_active_id() or DEFAULT_MODEL
        thread = threading.Thread(
            target=self._stream_response,
            args=(text, model_id, assistant_label),
            daemon=True,
        )
        thread.start()

    def _stream_response(
        self, user_text: str, model: str, label: Gtk.Label
    ) -> None:
        """Run streaming request in background, updating UI via GLib.idle_add."""
        client = ClaudeClient(model=model)

        # Build system prompt with document context
        system = SYSTEM_PROMPT
        if self.document_svg:
            system += (
                f"\n\nCurrent Inkscape document SVG:\n```svg\n{self.document_svg}\n```"
            )

        full_response = ""
        try:
            for chunk in client.message_stream(
                user_text,
                system=system,
                conversation=self.conversation[:-1],  # exclude current user msg (already in prompt)
            ):
                full_response += chunk
                snapshot = full_response
                GLib.idle_add(label.set_text, snapshot)
                GLib.idle_add(self._scroll_to_bottom)
        except Exception as e:
            full_response = f"Error: {e}"
            GLib.idle_add(label.set_text, full_response)

        self.conversation.append({"role": "assistant", "content": full_response})

        # Check if response contains SVG and add insert button
        svg_text = extract_svg_from_response(full_response)
        if svg_text:
            GLib.idle_add(self._add_insert_button, svg_text)

        GLib.idle_add(self._finish_streaming)

    def _finish_streaming(self) -> None:
        self._streaming = False
        self.send_btn.set_sensitive(True)

    def _add_message(self, role: str, text: str) -> Gtk.Label:
        """Add a message bubble to the message area. Returns the label."""
        frame = Gtk.Frame()
        if role == "user":
            frame.set_label("You")
        else:
            frame.set_label("Claude")

        label = Gtk.Label(label=text)
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_selectable(True)
        label.set_xalign(0)
        label.set_margin_start(8)
        label.set_margin_end(8)
        label.set_margin_top(4)
        label.set_margin_bottom(4)

        frame.add(label)
        self.messages_box.pack_start(frame, False, False, 0)
        frame.show_all()

        GLib.idle_add(self._scroll_to_bottom)
        return label

    def _add_insert_button(self, svg_text: str) -> None:
        """Add an 'Insert SVG' button after the last message."""
        btn = Gtk.Button(label="Insert SVG into Document")
        btn.connect("clicked", lambda _: self._do_insert_svg(svg_text))
        self.messages_box.pack_start(btn, False, False, 0)
        btn.show()

    def _do_insert_svg(self, svg_text: str) -> None:
        if self.on_insert_svg:
            self.on_insert_svg(svg_text)

    def _scroll_to_bottom(self) -> None:
        adj = self.scrolled.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())

    def _on_refresh_context(self, _btn: Gtk.Button) -> None:
        """Placeholder — the extension runner should update document_svg."""
        self._add_message(
            "assistant",
            "(Document context refreshed. Next message will use the latest SVG.)",
        )

    def _on_clear(self, _btn: Gtk.Button) -> None:
        for child in self.messages_box.get_children():
            self.messages_box.remove(child)
        self.conversation.clear()


def run_chat_window(document_svg: str = "", on_insert_svg=None) -> None:
    """Launch the chat window as a standalone GTK application."""
    win = ChatWindow(document_svg=document_svg)
    win.on_insert_svg = on_insert_svg
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
