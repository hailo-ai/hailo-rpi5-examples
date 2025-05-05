#!/usr/bin/env bash
set -euo pipefail

# --- CONFIG -------------------------------------------------------------------
# Where to clone/find hailo-apps-infra
: "${HAILO_INFRA_PATH:=../hailo-apps-infra}"
# Name of the venv folder, *inside* your examples dir
: "${VENV_NAME:=hailo_infra_venv}"

# --- ARGS ---------------------------------------------------------------------
PYHAILORT_WHL=""
PYTAPPAS_WHL=""
INSTALL_TEST_REQUIREMENTS=false
DOWNLOAD_RESOURCES_FLAG=""
INFRA_FLAGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pyhailort)  PYHAILORT_WHL="$2"; shift ;;
    --pytappas)   PYTAPPAS_WHL="$2"; shift ;;
    --test)       INSTALL_TEST_REQUIREMENTS=true ;;
    --all)        DOWNLOAD_RESOURCES_FLAG="--all" ;;
    --gstreamer-only|--pipelines-only)
                  INFRA_FLAGS+=("$1") ;;
    *)
      echo "Unknown parameter: $1" >&2
      exit 1
      ;;
  esac
  shift
done

# --- 1) CLONE INFRA IF NEEDED --------------------------------------------------
if [[ ! -d "$HAILO_INFRA_PATH" ]]; then
  echo "Cloning hailo-apps-infra ? $HAILO_INFRA_PATH"
  git clone https://github.com/hailo-ai/hailo-apps-infra.git "$HAILO_INFRA_PATH"
fi

# --- 2) RUN INFRA INSTALLER INTO *THIS* VENV -----------------------------------
EXAMPLES_ROOT="$(pwd)"
ABS_VENV_PATH="$EXAMPLES_ROOT/$VENV_NAME"

echo "Running infra/install.sh with VENV_NAME=$ABS_VENV_PATH"
(
  cd "$HAILO_INFRA_PATH"
  # override where the infra script builds/activates its venv:
  export VENV_NAME="$ABS_VENV_PATH"
  ./install.sh "${INFRA_FLAGS[@]}"
)

# --- 3) ACTIVATE THAT VENV ----------------------------------------------------
echo "Activating virtualenv: $ABS_VENV_PATH"
# shellcheck disable=SC1091
source "$ABS_VENV_PATH/bin/activate"

# --- 4) EXAMPLE-SPECIFIC SYSTEM DEPS -------------------------------------------
echo "Installing system deps for examples"
sudo apt update
sudo apt install -y rapidjson-dev

# --- 5) OPTIONAL WHEELS --------------------------------------------------------
if [[ -n "$PYHAILORT_WHL" ]]; then
  echo "Installing custom hailort wheel: $PYHAILORT_WHL"
  pip install "$PYHAILORT_WHL"
fi
if [[ -n "$PYTAPPAS_WHL" ]]; then
  echo "Installing custom tappas wheel: $PYTAPPAS_WHL"
  pip install "$PYTAPPAS_WHL"
fi

# --- 6) PYTHON REQS FOR EXAMPLES -----------------------------------------------
echo "Installing example Python requirements"
pip install -r requirements.txt

# --- 7) OPTIONAL TEST REQS ----------------------------------------------------
if [[ "$INSTALL_TEST_REQUIREMENTS" == true ]]; then
  echo "Installing test requirements"
  pip install -r tests/test_resources/requirements.txt
fi

# --- 8) PIPELINE RESOURCES ----------------------------------------------------
echo "Downloading pipeline resources"
./download_resources.sh $DOWNLOAD_RESOURCES_FLAG

# --- DONE ----------------------------------------------------------------------
echo
echo "? All set! Re-activate with:"
echo "    source $VENV_NAME/bin/activate"
