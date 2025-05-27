#!/bin/bash
set -euo pipefail

# —————————————————————————————
# 1. Read config 
# —————————————————————————————
CONFIG_FILE="config.yaml"
if [[ -n "$CONFIG_FILE" ]]; then
  echo "📄 Loading configuration from $CONFIG_FILE"
    while IFS= read -r line; do
    # 1) Remove any inline comment (everything from the first unescaped “#” to end of line)
    line="${line%%#*}"

    # 2) Skip blank lines
    [[ -z "${line//[[:space:]]/}" ]] && continue

    # 3) Split on the *first* colon
    key=${line%%:*}
    val=${line#*:}

    # 4) Trim whitespace and surrounding quotes
    key=$(echo "$key" | xargs)
    val=$(echo "$val" | sed -e 's/^[[:space:]]*"\{0,1\}//' \
                            -e 's/"\{0,1\}[[:space:]]*$//')


    case "$key" in
      server_url)          server_url="$val"          ;;
      storage_dir)         storage_dir="$val"         ;;
      hailort_version)     hailort_version="$val"     ;;
      tappas_version)      tappas_version="$val"      ;;
      virtual_env_name)    virtual_env_name="$val"    ;;
      hailo_apps_infra_repo_url)   hailo_apps_infra_repo_url="$val"   ;;
      hailo_apps_infra_branch_tag) hailo_apps_infra_branch_tag="$val" ;;
      hailo_apps_infra_path)  hailo_apps_infra_path="$val"  ;;
      tappas_variant) tappas_variant="$val" ;;
      # you can add more mappings here…
    esac
  done < <(grep -E '^[[:space:]]*[a-z_]+:' "$CONFIG_FILE")
fi

# —————————————————————————————
# 2. Fallback to old defaults
# —————————————————————————————
: "${server_url:=http://dev-public.hailo.ai/2025_01}"
: "${storage_dir:=hailo_temp_resources}"
: "${hailort_version:=4.20.0}"
: "${tappas_version:=3.31.0}"
: "${virtual_env_name:="hailo_venv"}"
: "${hailo_apps_infra_repo_url:=https://github.com/hailo-ai/hailo-apps-infra.git}"
: "${hailo_apps_infra_branch_tag:=dev}"
: "${hailo_apps_infra_path:="auto"}"  # or "auto" for latest
: "${tappas_variant:="hailo-tappas-core"}"  # or "x86_64"

# Now use those
BASE_URL="$server_url"
DOWNLOAD_DIR="$storage_dir"
HAILORT_VERSION="$hailort_version"
TAPPAS_CORE_VERSION="$tappas_version"
VENV_NAME="$virtual_env_name"
HAILO_INFRA_PATH="$hailo_apps_infra_path"
TAPPAS_PIP_PKG="$tappas_variant"

# —————————————————————————————
# Rest of your existing checks & installs…
# —————————————————————————————

echo "Using config from $CONFIG_FILE (or defaults):"
echo "  BASE_URL           = $BASE_URL"
echo "  DOWNLOAD_DIR       = $DOWNLOAD_DIR"
echo "  HAILORT_VERSION    = $HAILORT_VERSION"
echo "  TAPPAS_CORE_VERSION= $TAPPAS_CORE_VERSION"
echo "  VENV_NAME          = $VENV_NAME"
echo "  Hailo-Apps-Infra   = $hailo_apps_infra_repo_url @ $hailo_apps_infra_branch_tag"
echo "  TAPPAS_PIP_PKG     = $TAPPAS_PIP_PKG"
echo "  TAPPAS_VARIANT     = $tappas_variant"
echo "  HAILO_INFRA_PATH   = $HAILO_INFRA_PATH"
echo "  CONFIG_FILE        = $CONFIG_FILE"


###——— HELPERS —————————————————————————————————————————————————————
detect_system_pkg_version() {
  dpkg-query -W -f='${Version}' "$1" 2>/dev/null || echo ""
}

detect_pip_pkg_version() {
  if pip show "$1" >/dev/null 2>&1; then
    pip show "$1" \
      | awk -F': ' '/^Version: /{print $2; exit}'
  else
    echo ""
  fi
}

check_system_pkg() {
  pkg="$1"
  ver=$(detect_system_pkg_version "$pkg")
  if [[ -z "$ver" ]]; then
    echo "❌ System package '$pkg' not found."
    echo "    Please install it before proceeding."
    exit 1
  else
    echo "✅ $pkg (system) version: $ver"
  fi
}

###——— SYSTEM PKG CHECKS —————————————————————————————————————————————
echo
echo "📋 Checking required system packages…"
check_system_pkg hailort

echo
echo "📋 Checking for HailoRT system version"
HRT_VER=$(detect_system_pkg_version hailort)
echo "📋 Checking for hailo-tappas vs hailo-tappas-core…"
HT1=$(detect_system_pkg_version hailo-tappas)
HT2=$(detect_system_pkg_version hailo-tappas-core)
HTC_VER="none"
if [[ -n "$HT1" ]]; then
  echo "✅ hailo-tappas version: $HT1"
  HTC_VER="$HT1"
  TAPPAS_PIP_PKG="hailo-tappas"
elif [[ -n "$HT2" ]]; then
  echo "✅ hailo-tappas-core version: $HT2"
  TAPPAS_PIP_PKG="hailo-tappas-core-python-binding"
  HTC_VER="$HT2"
else
  echo "❌ Neither hailo-tappas nor hailo-tappas-core is installed."
  exit 1
fi


###——— PIP PKG CHECKS —————————————————————————————————————————————————
echo
echo "📋 Checking host-Python pip packages…"
INSTALL_PYHAILORT=false
INSTALL_TAPPAS_CORE=false

# hailort
host_py=$(detect_pip_pkg_version hailort)
if [[ -z "$host_py" ]]; then
  echo "⚠️  pip 'hailort' missing; will install in venv."
  INSTALL_PYHAILORT=true
else
  echo "✅ pip 'hailort' version: $host_py"
fi

# tappas binding pkg (RPi vs x86)
host_tc=$(detect_pip_pkg_version "$TAPPAS_PIP_PKG")
if [[ -z "$host_tc" ]]; then
  echo "⚠️  pip '$TAPPAS_PIP_PKG' missing; will install in venv."
  INSTALL_TAPPAS_CORE=true
else
  echo "✅ pip '$TAPPAS_PIP_PKG' version: $host_tc"
fi

###——— VENV SETUP —————————————————————————————————————————————————————
echo
if [[ -d "$VENV_NAME" ]]; then
  echo "✅ Virtualenv '$VENV_NAME' exists. Activating…"
  source "$VENV_NAME/bin/activate"
else
  echo "🔧 Creating virtualenv '$VENV_NAME'…"
  if $INSTALL_PYHAILORT && $INSTALL_TAPPAS_CORE; then
    python3 -m venv "$VENV_NAME"
  else
    python3 -m venv --system-site-packages "$VENV_NAME"
  fi
  echo "✅ Created. Activating…"
  source "$VENV_NAME/bin/activate"
fi


###——— INSTALL MISSING PIP PACKAGES —————————————————————————————————————
echo
echo "📦 Installing missing pip packages…"

if $INSTALL_PYHAILORT && $INSTALL_TAPPAS_CORE; then
    echo "📦 Installing 'hailort' and '$TAPPAS_PIP_PKG'…"
    ./hailo_python_installation.sh
elif $INSTALL_PYHAILORT; then
  echo "📦 Installing 'hailort'…"
    ./hailo_python_installation.sh --only-hailort
elif $INSTALL_TAPPAS_CORE; then
  echo "📦 Installing '$TAPPAS_PIP_PKG'…"
    ./hailo_python_installation.sh --only-tappas
else
  echo "✅ All pip packages are already installed."
fi



###——— ENV FILE —————————————————————————————————————————————————————
ENV_FILE=".env"
ENV_PATH="$(pwd)/$ENV_FILE"
export HAILO_ENV_FILE="${ENV_PATH}"
echo $HAILO_ENV_FILE

CONFIG_PATH="$(pwd)/$CONFIG_FILE"

# Step 1: Create the .env file if it doesn't exist
if [[ ! -f "$ENV_PATH" ]]; then
    echo "🔧 Creating .env file at $ENV_PATH"
    touch "$ENV_PATH"
    chmod 666 "$ENV_PATH"  # rw-rw-r-- for user/group
else
    echo "✅ .env already exists at $ENV_PATH"
    chmod 666 "$ENV_PATH"
fi


###——— MODULE INSTALLS ———————————————————————————————————————————————————
echo
echo "📦 Upgrading pip/setuptools/wheel…"
pip install --upgrade pip setuptools wheel

pip install -r requirements.txt
echo $"📦 Installing Hailo-Apps-Infra… $HAILO_INFRA_PATH"
if [[ "$HAILO_INFRA_PATH" != "auto" ]]; then
  echo "📦 Installing Hailo-Apps-Infra from $HAILO_INFRA_PATH…"
  pip install -e "$HAILO_INFRA_PATH"
else
    echo "📦 Installing hailo-apps-infra from Git ($hailo_apps_infra_branch_tag)…"
    pip install "git+${hailo_apps_infra_repo_url}@${hailo_apps_infra_branch_tag}#egg=hailo-apps-infra"
fi


echo "📦 Installing shared runtime deps…"


###——— POST-INSTALL ———————————————————————————————————————————————————
echo
echo "⚙️  Running post-install…"
python3 -m hailo_apps_infra.hailo_core.hailo_installation.post_install \
    --dotenv "$ENV_PATH" \
    --config "$CONFIG_PATH"


###——— FINISHED —————————————————————————————————————————————————————
cat <<EOF

🎉  All done!

To reactivate your environment later:
    source $VENV_NAME/bin/activate

EOF