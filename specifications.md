# inky — Specifications

An Inkscape extension that integrates Claude AI directly into the Inkscape editor, enabling users to generate, modify, analyze SVG elements and chat with Claude from within the application.

---

## 1. Project Overview

| Field | Value |
|-------|-------|
| **Name** | `inky` |
| **Target** | Inkscape 1.2+ |
| **Language** | Python 3.10+ |
| **Package Manager** | `uv` |
| **API** | Anthropic API via OAuth 2.0 |
| **Platforms** | Linux (primary), macOS, Windows |

---

## 2. Authentication

Authentication follows the same OAuth 2.0 + PKCE flow used by the official Anthropic Chrome extension.

### 2.1 OAuth 2.0 Endpoints

| Endpoint | URL |
|----------|-----|
| Authorization | `https://claude.ai/oauth/authorize` |
| Token | `https://platform.claude.com/v1/oauth/token` |
| Profile | `https://api.anthropic.com/api/oauth/profile` |

### 2.2 OAuth Scopes

```
user:profile user:inference user:chat
```

### 2.3 PKCE Flow

1. Generate a random 32-byte **code verifier**
2. Compute SHA-256 hash → base64url-encode → **code challenge** (`S256`)
3. Generate a random **state** parameter for CSRF protection
4. Open the system browser to the authorization URL with:
   - `response_type=code`
   - `client_id=<registered_client_id>`
   - `redirect_uri=http://localhost:<port>/oauth/callback`
   - `scope=user:profile user:inference user:chat`
   - `code_challenge=<challenge>`
   - `code_challenge_method=S256`
   - `state=<state>`
5. Start a temporary local HTTP server on `localhost:<port>` to receive the redirect
6. On callback, validate the `state` parameter, exchange the authorization `code` for tokens at the token endpoint
7. Store `access_token`, `refresh_token`, and `token_expiry` securely

### 2.4 Token Management

- **Storage**: tokens are stored in `~/.config/inky/tokens.json` with `600` file permissions (owner read/write only)
- **Auto-refresh**: refresh the access token when it is within 1 hour of expiry
- **Retry**: up to 3 refresh attempts on failure before clearing tokens and requiring re-login
- **Fallback**: if the environment variable `ANTHROPIC_API_KEY` is set, use it directly (skip OAuth). This supports headless/CI use cases

### 2.5 API Request Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
anthropic-client-platform: inky
```

---

## 3. Features

### 3.1 Generate SVG from Text

**Menu**: `Extensions > Claude AI > Generate SVG...`

**Behavior**:
1. User opens the dialog and types a natural language description (e.g., "a red circle with a blue border, 100px diameter")
2. The current document dimensions and units are sent as context
3. Claude generates SVG element(s) matching the description
4. The generated SVG is parsed, validated, and inserted into the current layer at the canvas center (or at a user-specified position)

**Prompt strategy**:
- System prompt instructs Claude to return **only** valid SVG elements (no `<svg>` root wrapper) suitable for insertion into an existing document
- Include document metadata: canvas size, current layer ID, existing color palette

**INX dialog fields**:
- `description` (multiline text) — what to generate
- `model` (dropdown) — model selection

### 3.2 Modify Selected Elements

**Menu**: `Extensions > Claude AI > Modify Selection...`

**Behavior**:
1. User selects one or more elements on the canvas
2. Opens the dialog and describes the desired modification (e.g., "make it 50% larger and change the fill to gradient from blue to purple")
3. The serialized SVG of the selected elements is sent to Claude along with the instruction
4. Claude returns modified SVG elements
5. The original elements are replaced with Claude's output, preserving element IDs and layer position

**Prompt strategy**:
- System prompt instructs Claude to return the modified SVG elements with the same IDs
- Include the parent layer context for spatial awareness

**INX dialog fields**:
- `instruction` (multiline text) — what to change
- `model` (dropdown) — model selection

**Guard rails**:
- Validate that returned element IDs match the originals
- Warn if Claude returns more/fewer elements than selected

### 3.3 Explain / Analyze SVG

**Menu**: `Extensions > Claude AI > Explain Selection...`

**Behavior**:
1. User selects elements on the canvas
2. Claude analyzes the SVG and returns a human-readable explanation
3. The explanation is displayed in a GTK dialog (read-only text view)

**Prompt strategy**:
- System prompt asks Claude to describe what the SVG elements represent, their visual properties, and suggest potential improvements
- Include the full document context if the selection references external elements (e.g., `<use>`, `<defs>`, gradients)

**INX**: model selector only — directly opens the result window after processing

### 3.4 Chat Assistant Dialog

**Menu**: `Extensions > Claude AI > Chat Assistant...`

**Behavior**:
1. Opens a persistent GTK window (non-modal) alongside Inkscape
2. Multi-turn conversation with Claude about the current document
3. User can ask questions, request modifications, or generate content
4. When Claude returns SVG in its response, an "Insert into Document" button appears next to the SVG block
5. The full document SVG is included as context in the first message and can be refreshed

**UI components** (GTK 3 via PyGObject):
- Scrollable message history (alternating user/assistant bubbles)
- Text input area with send button (Enter to send, Shift+Enter for newline)
- Model selector dropdown (Sonnet 4.5 / Opus 4.6)
- "Refresh document context" button
- "Insert SVG" buttons on assistant messages containing SVG code
- "Clear conversation" button

**Conversation management**:
- Conversation history is maintained in memory for the session
- Document SVG context is attached as a system message
- Streaming responses rendered in real-time

---

## 4. Architecture

### 4.1 File Layout

```
inky/
├── specifications.md
├── pyproject.toml                    # uv project config
├── uv.lock
├── src/
│   └── inky/
│       ├── __init__.py
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── oauth.py             # OAuth 2.0 + PKCE flow
│       │   ├── token_store.py       # Token persistence & refresh
│       │   └── server.py            # Local HTTP callback server
│       ├── api/
│       │   ├── __init__.py
│       │   └── client.py            # Anthropic API client wrapper
│       ├── extensions/
│       │   ├── __init__.py
│       │   ├── generate.py          # Generate SVG extension
│       │   ├── modify.py            # Modify selection extension
│       │   ├── explain.py           # Explain selection extension
│       │   └── chat.py              # Chat assistant launcher
│       ├── ui/
│       │   ├── __init__.py
│       │   └── chat_window.py       # GTK chat assistant window
│       └── utils/
│           ├── __init__.py
│           └── svg.py               # SVG parsing & validation helpers
├── inx/
│   ├── inky_generate.inx            # Generate SVG menu entry
│   ├── inky_modify.inx              # Modify Selection menu entry
│   ├── inky_explain.inx             # Explain Selection menu entry
│   └── inky_chat.inx                # Chat Assistant menu entry
└── install.sh                       # Symlinks extension into Inkscape
```

### 4.2 Extension Registration

Each `.inx` file registers a menu item under `Extensions > Claude AI` and points to the corresponding Python entry point. Example structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<inkscape-extension xmlns="http://www.inkscape.org/namespace/inkscape/extension">
    <name>Generate SVG</name>
    <id>com.inky.generate</id>
    <param name="description" type="string" gui-text="Describe what to generate:"></param>
    <param name="model" type="optiongroup" appearance="combo" gui-text="Model:">
        <option value="claude-sonnet-4-5-20250929">Sonnet 4.5 (Fast)</option>
        <option value="claude-opus-4-6">Opus 4.6 (Powerful)</option>
    </param>
    <effect>
        <object-type>all</object-type>
        <effects-menu>
            <submenu name="Claude AI"/>
        </effects-menu>
    </effect>
    <script>
        <command location="inx" interpreter="python">../src/inky/extensions/generate.py</command>
    </script>
</inkscape-extension>
```

### 4.3 API Client

The API client wraps HTTP requests to the Anthropic Messages API:

- **Endpoint**: `https://api.anthropic.com/v1/messages`
- **Authentication**: Bearer token from OAuth or raw API key via `x-api-key` header
- **Streaming**: SSE streaming for the chat assistant (real-time response rendering)
- **Non-streaming**: standard request/response for generate, modify, and explain features
- **Error handling**: rate limit retry with backoff, token refresh on 401

### 4.4 SVG Context Extraction

For each feature, relevant SVG context is extracted from the Inkscape document:

| Feature | Context sent to Claude |
|---------|----------------------|
| Generate | Document dimensions, units, current layer ID, color palette from existing elements |
| Modify | Serialized SVG of selected elements + parent layer + referenced `<defs>` |
| Explain | Serialized SVG of selected elements + referenced `<defs>` + full document (if small) |
| Chat | Full document SVG (attached on first message, refreshable) |

### 4.5 Model Selection

Users can choose the model per-request:

| Model | ID | Use Case |
|-------|----|----------|
| **Sonnet 4.5** (default) | `claude-sonnet-4-5-20250929` | Fast generation, simple modifications |
| **Opus 4.6** | `claude-opus-4-6` | Complex multi-element generation, nuanced analysis |

---

## 5. Dependencies

### 5.1 Python Packages (managed by `uv`)

| Package | Purpose |
|---------|---------|
| `httpx` | HTTP client for OAuth flow and API requests |

### 5.2 System Dependencies (not pip-installed)

| Package | Purpose |
|---------|---------|
| Inkscape 1.2+ | Host application (provides `inkex` and `lxml`) |
| GTK 3 | UI toolkit (bundled with Inkscape on Linux) |
| PyGObject / `gi` | Python GTK bindings (typically system-installed) |

---

## 6. Installation

### 6.1 From Source

```bash
git clone <repo_url>
cd inky
uv sync
./install.sh
```

`install.sh` performs:
1. Symlinks `inx/*.inx` → `~/.config/inkscape/extensions/`
2. Symlinks `src/inky/` → `~/.config/inkscape/extensions/inky/`
3. Installs Python dependencies via `uv sync`

### 6.2 First-Time Authentication

1. Open Inkscape
2. Go to `Extensions > Claude AI > Chat Assistant` (or any feature)
3. If no valid token exists, the system browser opens to `claude.ai` for OAuth login
4. After authorizing, the browser redirects to `localhost`, the extension captures the code
5. Tokens are stored and subsequent uses are automatic

### 6.3 API Key Override

For users who prefer using an API key directly:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

When this env var is set, OAuth is skipped entirely.

---

## 7. Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Token storage | File permissions `600`, stored in `~/.config/inky/tokens.json` |
| PKCE | Code challenge via SHA-256 prevents authorization code interception |
| State parameter | Random state validated on callback prevents CSRF |
| Local callback server | Binds to `127.0.0.1` only, ephemeral port, shuts down immediately after receiving callback |
| API key in env | Never written to disk by the extension |
| SVG injection | All SVG returned by Claude is parsed and validated via `lxml` before insertion |
| Token refresh | Automatic refresh with retry; tokens cleared on persistent failure |

---

## 8. Future Considerations

These are **not** in scope for v1 but noted for potential future development:

- **Vision input**: send a rasterized screenshot of the canvas to Claude for visual understanding
- **Batch operations**: apply modifications across multiple elements/pages
- **Prompt templates**: saved prompt presets for common operations
- **Undo integration**: tie Claude modifications to Inkscape's undo stack as a single operation
- **MCP server**: expose Inkscape as an MCP tool server for Claude Desktop
