#!/usr/bin/env bash
set -e

# --- Defaults ---
BASE_URL="http://dev-public.hailo.ai/2025_01"
HAILORT_VERSION="4.20.0"
TAPPAS_CORE_VERSION="3.31.0"
DOWNLOAD_DIR="hailo_temp_resources"

# By default install both
INSTALL_TAPPAS=true
INSTALL_HAILORT=true

# --- Parse flags ---
while [[ $# -gt 0 ]]; do
  case $1 in
    --hailort-version=*)
      HAILORT_VERSION="${1#*=}"
      shift
      ;;
    --tappas-core-version=*)
      TAPPAS_CORE_VERSION="${1#*=}"
      shift
      ;;
    --download-dir=*)
      DOWNLOAD_DIR="${1#*=}"
      shift
      ;;
    --only-tappas)
      INSTALL_HAILORT=false
      INSTALL_TAPPAS=true
      shift
      ;;
    --only-hailort)
      INSTALL_TAPPAS=false
      INSTALL_HAILORT=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--hailort-version=X] [--tappas-core-version=Y] [--download-dir=DIR] [--only-tappas] [--only-hailort]"
      exit 1
      ;;
  esac
done

# Ensure you haven't disabled both
if [[ "$INSTALL_TAPPAS" = false && "$INSTALL_HAILORT" = false ]]; then
  echo "Error: Cannot use both --only-tappas and --only-hailort together."
  exit 1
fi

echo "→ HAILORT_VERSION    = $HAILORT_VERSION"
echo "→ TAPPAS_CORE_VERSION= $TAPPAS_CORE_VERSION"
echo "→ DOWNLOAD_DIR       = $DOWNLOAD_DIR"
echo "→ install Tapas?     = $INSTALL_TAPPAS"
echo "→ install HailoRT?   = $INSTALL_HAILORT"

mkdir -p "$DOWNLOAD_DIR"

# --- Compute Python and Arch tags ---
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
PY_TAG="cp${PY_MAJOR}${PY_MINOR}-cp${PY_MAJOR}${PY_MINOR}"
ARCH_TAG="$(uname -m | sed -e 's/x86_64/linux_x86_64/' -e 's/aarch64/linux_aarch64/')"

# --- Download wheels ---

if [[ "$INSTALL_TAPPAS" = true ]]; then
  echo "→ Downloading Tapas-core wheel..."
  # NOTE: We keep the original filename (tappas_core_python_binding-…)
  wget "${BASE_URL}/tappas_core_python_binding-${TAPPAS_CORE_VERSION}-py3-none-any.whl" \
       -O "${DOWNLOAD_DIR}/tappas_core_python_binding-${TAPPAS_CORE_VERSION}-py3-none-any.whl"
fi

if [[ "$INSTALL_HAILORT" = true ]]; then
  echo "→ Downloading HailoRT wheel..."
  # HailoRT wheel already matches its metadata name
  wget "${BASE_URL}/hailort-${HAILORT_VERSION}-${PY_TAG}-${ARCH_TAG}.whl" \
       -O "${DOWNLOAD_DIR}/hailort-${HAILORT_VERSION}-${PY_TAG}-${ARCH_TAG}.whl"
fi

# --- Install into current venv ---
echo "→ Upgrading pip…"
python3 -m pip install --upgrade pip

if [[ "$INSTALL_HAILORT" = true ]]; then
  echo "→ Installing HailoRT…"
  python3 -m pip install "${DOWNLOAD_DIR}/hailort-${HAILORT_VERSION}-${PY_TAG}-${ARCH_TAG}.whl"
fi

if [[ "$INSTALL_TAPPAS" = true ]]; then
  echo "→ Installing Tapas-core…"
  python3 -m pip install "${DOWNLOAD_DIR}/tappas_core_python_binding-${TAPPAS_CORE_VERSION}-py3-none-any.whl"
fi

echo "✅ Installation complete."
