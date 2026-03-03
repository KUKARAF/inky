#!/usr/bin/env bash
# Install inky extension into Inkscape's user extensions directory.
# Supports both native and Flatpak Inkscape installations.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect Flatpak vs native Inkscape
FLATPAK_EXT_DIR="${HOME}/.var/app/org.inkscape.Inkscape/config/inkscape/extensions"
NATIVE_EXT_DIR="${HOME}/.config/inkscape/extensions"

if [ -d "${HOME}/.var/app/org.inkscape.Inkscape" ]; then
    EXT_DIR="${FLATPAK_EXT_DIR}"
    echo "Detected Flatpak Inkscape installation."
elif [ -d "${NATIVE_EXT_DIR}" ] || command -v inkscape &>/dev/null; then
    EXT_DIR="${NATIVE_EXT_DIR}"
    echo "Detected native Inkscape installation."
else
    echo "Could not detect Inkscape. Install to Flatpak path? [Y/n]"
    read -r answer
    if [[ "${answer,,}" == "n" ]]; then
        EXT_DIR="${NATIVE_EXT_DIR}"
    else
        EXT_DIR="${FLATPAK_EXT_DIR}"
    fi
fi

echo "Installing inky to ${EXT_DIR}..."
mkdir -p "${EXT_DIR}"

# Symlink .inx files
for inx in "${SCRIPT_DIR}"/inx/*.inx; do
    name="$(basename "$inx")"
    ln -sfv "$inx" "${EXT_DIR}/${name}"
done

# Symlink the source package
ln -sfnv "${SCRIPT_DIR}/src/inky" "${EXT_DIR}/inky"

# Vendor Python dependencies inside the inky package itself.
# This ensures they're found via the resolved symlink path (Python resolves
# __file__ through symlinks, so deps must live in the source tree).
VENDOR_DIR="${SCRIPT_DIR}/src/inky/_vendor"
echo ""
echo "Installing Python dependencies to ${VENDOR_DIR}..."
mkdir -p "${VENDOR_DIR}"
uv pip install --target "${VENDOR_DIR}" httpx 2>&1

echo ""
echo "Done! Restart Inkscape to see 'Extensions > Claude AI' menu."
echo ""
echo "Authentication:"
echo "  Option A: Set ANTHROPIC_API_KEY environment variable"
echo "  Option B: The extension will open your browser for OAuth login on first use"
echo ""
echo "Installed to: ${EXT_DIR}"
