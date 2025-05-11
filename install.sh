#!/usr/bin/env bash
set -euo pipefail

###——— LOAD CONFIG —————————————————————————————————————————————
eval "$(
python3 - <<'PYCODE'
import yaml, shlex
cfg = yaml.safe_load(open("config.yaml"))
req = {}
for d in cfg.get("Required", []):
    if d: req.update(d)
infra_p = req.get("apps_infra_path")    or "../hailo-apps-infra"
infra_v = req.get("apps_infra_version") or "main"
venv    = req.get("virtual_env")        or "examples_venv"
extra   = req.get("Extra_Resources")    or ""
print(f"INFRA_PATH={shlex.quote(infra_p)}")
print(f"INFRA_VERSION={shlex.quote(infra_v)}")
print(f"VENV_NAME={shlex.quote(venv)}")
print(f"EXTRA_RES={shlex.quote(extra)}")
PYCODE
)"

PIP_CMD="python3 -m pip"
PYTHON_CMD="python3"

###——— CLONE / UPDATE INFRA ————————————————————————————————————
if [[ ! -d "$INFRA_PATH" ]]; then
  echo "🔧 Cloning hailo-apps-infra@$INFRA_VERSION → $INFRA_PATH"
  git clone --branch "$INFRA_VERSION" --single-branch \
    https://github.com/hailo-ai/hailo-apps-infra.git "$INFRA_PATH"
else
  echo "🔄 Updating infra to $INFRA_VERSION"
  (cd "$INFRA_PATH" && git fetch --all && git checkout "$INFRA_VERSION")
fi

###——— ARCHITECTURE DETECTION —————————————————————————————————————
ARCH=$(uname -m)
if [[ "$ARCH" == arm* || "$ARCH" == aarch64 ]]; then
  SYS_PKG="hailo-all"
  echo "🔍 Detected ARM ($ARCH)"
else
  SYS_PKG="hailort-pcie-driver"
  echo "🔍 Detected x86 ($ARCH)"
fi

###——— ARG PARSING —————————————————————————————————————————————————
INSTALL_GSTREAMER=true
INSTALL_PIPELINES=true
SKIP_PYHAILORT=false
SKIP_TAPPAS_CORE=false
DOWNLOAD_GROUP="default"
INSTALL_TEST=false

for arg; do
  case "$arg" in
    --gstreamer-only)    INSTALL_PIPELINES=false ;;
    --pipelines-only)    INSTALL_GSTREAMER=false ;;
    --all)               INSTALL_GSTREAMER=true; INSTALL_PIPELINES=true ;;
    --skip-pyhailort)    SKIP_PYHAILORT=true ;;
    --skip-tappas-core)  SKIP_TAPPAS_CORE=true ;;
    --group)             DOWNLOAD_GROUP="$2"; shift ;;
    --all-groups)        DOWNLOAD_GROUP="all" ;;
    --test)              INSTALL_TEST=true ;;
    *)                   echo "⚠️ Ignoring unknown flag: $arg" ;;
  esac
  shift || true
done

###——— HELPERS —————————————————————————————————————————————————————
detect_system_pkg_version() {
  dpkg-query -W -f='${Version}' "$1" 2>/dev/null || echo ""
}
detect_pip_pkg_version() {
  python3 -m pip show "$1" 2>/dev/null | awk -F': ' '/^Version: /{print $2}' || echo ""
}



check_system_pkg() {
  local pkg=$1
  local v=$(detect_system_pkg_version "$pkg")
  if [[ -z "$v" ]]; then
    echo "❌ System package '$pkg' not found—please install it." >&2
    exit 1
  else
    echo "✅ $pkg (system) version: $v"
  fi
}

###——— RESOURCE DIRS —————————————————————————————————————————————————
if [[ -n "${SUDO_USER-}" ]]; then
  INSTALL_USER="$SUDO_USER"
else
  INSTALL_USER="$(id -un)"
fi
INSTALL_GROUP="$(id -gn "$INSTALL_USER")"
RESOURCE_BASE="/usr/local/hailo/resources"

echo
echo "🔧 Creating resource subdirs..."
for sub in models/hailo8 models/hailo8l videos so; do
  sudo mkdir -p "$RESOURCE_BASE/$sub"
done
sudo chown -R "$INSTALL_USER":"$INSTALL_GROUP" "$RESOURCE_BASE"
sudo chmod -R 755 "$RESOURCE_BASE"

###——— SYSTEM PKG CHECKS —————————————————————————————————————————————
echo
echo "📋 Checking system packages..."
check_system_pkg "$SYS_PKG"
check_system_pkg hailort

echo
echo "📋 Checking tappas packages..."
TP1=$(detect_system_pkg_version hailo-tappas)
TP2=$(detect_system_pkg_version hailo-tappas-core)
if [[ -n "$TP1" ]]; then
  HTC_VER="$TP1"; echo "✅ hailo-tappas (system): $TP1"
  TAPPAS_PIP_PKG="tappas-core"
elif [[ -n "$TP2" ]]; then
  HTC_VER="$TP2"; echo "✅ hailo-tappas-core (system): $TP2"
  TAPPAS_PIP_PKG="tappas-core-python-binding"
else
  echo "❌ Neither hailo-tappas nor hailo-tappas-core installed." >&2
  exit 1
fi

###——— DETECT HAILORT VERSION —————————————————————————————————————
HRT_VER=$(detect_system_pkg_version hailort)
if [[ -z "$HRT_VER" ]]; then
  HRT_VER=$(detect_system_pkg_version "$SYS_PKG")
fi
if [[ -z "$HRT_VER" ]]; then
  echo "❌ Neither 'hailort' nor '$SYS_PKG' found—install system HailoRT." >&2
  exit 1
fi
echo "✅ hailort system version: $HRT_VER"

###——— PIP PKG CHECKS & hailo-all SKIP ———————————————————————————————————
echo
echo "📋 Checking Python bindings (pip)..."
INSTALL_PYHAILORT=false
INSTALL_TAPPAS_CORE=false
USE_SYSTEM_SITE=false

if [[ "$SYS_PKG" == "hailo-all" ]]; then
  echo "🔶 'hailo-all' detected—will use system Python bindings and skip pip installs"
  USE_SYSTEM_SITE=true
else
  # hailort binding
  host_py=$(detect_pip_pkg_version hailort)
  echo "host_py = $host_py"
  if [[ -z "$host_py" ]]; then
    echo "⚠️  pip 'hailort' missing; will install in venv."
    INSTALL_PYHAILORT=true
  else
    echo "✅ pip 'hailort' version: $host_py"
  fi

  # tappas binding
  host_tc=$(detect_pip_pkg_version "$TAPPAS_PIP_PKG")
  if [[ -z "$host_tc" ]]; then
    if ! $SKIP_TAPPAS_CORE; then
      echo "⚠️ pip '$TAPPAS_PIP_PKG' missing; will install in venv"
      INSTALL_TAPPAS_CORE=true
    else
      echo "🔶 Skipping tappas per --skip-tappas-core"
    fi
  else
    echo "✅ pip '$TAPPAS_PIP_PKG' version: $host_tc"
  fi
fi

###——— VENV SETUP —————————————————————————————————————————————————————
echo
echo "🔧 Setting up virtualenv: '$VENV_NAME'"
if [[ -d "$VENV_NAME" ]]; then
  echo "✅ Exists—activating"
else
  if $USE_SYSTEM_SITE; then
    $PYTHON_CMD -m venv --system-site-packages "$VENV_NAME"
  elif $INSTALL_PYHAILORT && $INSTALL_TAPPAS_CORE; then
    $PYTHON_CMD -m venv "$VENV_NAME"
  else
    $PYTHON_CMD -m venv --system-site-packages "$VENV_NAME"
  fi
  echo "✅ Created"
fi
# shellcheck disable=SC1091
source "$VENV_NAME/bin/activate"

###——— INSTALL MISSING PIP BINDINGS —————————————————————————————————————

if ! $USE_SYSTEM_SITE && ( $INSTALL_PYHAILORT || $INSTALL_TAPPAS_CORE ); then
  echo
  echo "🔧 Installing missing Python bindings via infra’s installer"
  PY_INST="$INFRA_PATH/hailo_apps_infra/installation/hailo_installation/python_installation.py"
  cmd=( python3 "$PY_INST" --venv-path "$VENV_NAME" )
  
  if [ "$INSTALL_PYHAILORT" = true ]; then
    cmd+=( --install-pyhailort --pyhailort-version "$HRT_VER" )
  fi

  if [ "$INSTALL_TAPPAS_CORE" = true ]; then
    cmd+=( --install-tappas-core --tappas-version "$HTC_VER" )
  fi
  
  echo "Running command: ${cmd[@]}"
  "${cmd[@]}"
else
  echo "✅ Python bindings already satisfied or skipped."
fi

###——— ENV FILE —————————————————————————————————————————————————————
ENV_PATH="$(pwd)/.env"
echo
if [[ ! -f "$ENV_PATH" ]]; then
  echo "🔧 Creating .env"
  touch "$ENV_PATH" && chmod 666 "$ENV_PATH"
else
  chmod 666 "$ENV_PATH"
  echo "✅ .env exists"
fi

###——— MODULE INSTALLS ———————————————————————————————————————————————————
echo
echo "📦 Upgrading build tools"
pip install --upgrade pip setuptools wheel

echo
echo "📦 Installing hailo-apps-infra (single pkg)"
pip install -e "$INFRA_PATH"

if $INSTALL_GSTREAMER; then
  echo "📦 Installing gstreamer"
  pip install -e "$INFRA_PATH/gstreamer"
fi
if $INSTALL_PIPELINES; then
  echo "📦 Installing pipelines"
  pip install -e "$INFRA_PATH/pipelines"
fi

echo
echo "📦 Installing Examples requirements"
pip install -r requirements.txt

if $INSTALL_TEST; then
  echo "🧪 Installing test requirements"
  pip install -r tests/test_resources/requirements.txt
fi

###——— POST-INSTALL ———————————————————————————————————————————————————
echo
echo "⚙️ Running infra’s post_install"
$PYTHON_CMD -m hailo_installation.post_install

###——— RESOURCES SYMLINK —————————————————————————————————————————————————
echo
if [[ ! -L resources ]]; then
  ln -s "$RESOURCE_BASE" resources
  echo "🔗 resources → $RESOURCE_BASE"
fi

###——— MERGE EXTRA RESOURCES ————————————————————————————————————————————
if [[ -n "$EXTRA_RES" && "$EXTRA_RES" != "None" ]]; then
  echo "➡️ Merging extra from $EXTRA_RES"
  cp -r "$EXTRA_RES"/* "$RESOURCE_BASE/"
fi

###——— FINISHED —————————————————————————————————————————————————————
cat <<EOF

🎉 Setup complete!

To re‐activate:
    source $VENV_NAME/bin/activate

• infra repo: $INFRA_PATH@$INFRA_VERSION  
• resources link: ./resources → $RESOURCE_BASE  

EOF
