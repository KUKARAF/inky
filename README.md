# inky

An Inkscape extension that brings Claude AI into your SVG workflow. Generate graphics from text descriptions, modify selected elements with natural language, get explanations of complex SVG, and chat with Claude — all from within Inkscape.

## Features

**Generate SVG** — Describe what you want and Claude creates it. "A red gear icon with 8 teeth" becomes SVG inserted directly into your document.

**Modify Selection** — Select elements on your canvas, describe the change ("make it blue and rotate 45 degrees"), and Claude rewrites the SVG in place.

**Explain Selection** — Select any elements and Claude explains what they are, how they work, and suggests improvements.

**Chat Assistant** — A persistent chat window for multi-turn conversations about your document. Claude sees your full SVG context and can generate insertable elements on the fly.

## Requirements

- Inkscape 1.2+ (native or Flatpak)
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- An [Anthropic API key](https://console.anthropic.com/settings/keys)

## Installation

### 1. Clone the repo

```bash
git clone git@github.com:KUKARAF/inky.git
cd inky
```

### 2. Run the installer

```bash
./install.sh
```

This will:
- Auto-detect your Inkscape installation (Flatpak or native)
- Symlink the extension files into Inkscape's extensions directory
- Vendor Python dependencies (`httpx`) into the project

### 3. Set your API key

Pick one of these methods:

**Environment variable** (per session):
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

**Config file** (persistent):
```bash
mkdir -p ~/.config/inky
echo 'sk-ant-YOUR-KEY-HERE' > ~/.config/inky/api_key
chmod 600 ~/.config/inky/api_key
```

### 4. Restart Inkscape

Open Inkscape and navigate to **Extensions > Claude AI**. You should see four menu entries:

- Generate SVG...
- Modify Selection...
- Explain Selection...
- Chat Assistant...

## Usage

### Generate SVG

1. Go to **Extensions > Claude AI > Generate SVG...**
2. Type a description of what you want to create
3. Pick a model (Sonnet 4.5 for speed, Opus 4.6 for quality)
4. Click Apply — the generated SVG is inserted into your current layer

### Modify Selection

1. Select one or more elements on the canvas
2. Go to **Extensions > Claude AI > Modify Selection...**
3. Describe the modification you want
4. Click Apply — the selected elements are replaced with Claude's modified version

### Explain Selection

1. Select elements you want to understand
2. Go to **Extensions > Claude AI > Explain Selection...**
3. A dialog appears with Claude's analysis of the selected SVG

### Chat Assistant

1. Go to **Extensions > Claude AI > Chat Assistant...**
2. A chat window opens alongside Inkscape
3. Ask questions, request SVG generation, or discuss your document
4. Click "Insert SVG" on any response containing SVG code to add it to your canvas

## Project Structure

```
inky/
├── src/inky/
│   ├── auth/          # API key management
│   ├── api/           # Anthropic API client (streaming + non-streaming)
│   ├── extensions/    # Inkscape effect extensions (generate, modify, explain, chat)
│   ├── ui/            # GTK 3 chat window
│   └── utils/         # SVG parsing and validation
├── inx/               # Inkscape menu registration files
├── install.sh         # Installer (Flatpak + native)
└── specifications.md  # Full technical specification
```

## License

MIT
