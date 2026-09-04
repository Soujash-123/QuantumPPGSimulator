#!/usr/bin/env bash
# Run the full digital-twin demo pipeline in one command.
# Usage:  ./run_demo.sh
# Outputs plots in quantum_ppg_output/ and quantum_source_output/.
#
# Optional: pass --with-streamlit to also launch the Streamlit UI at the end.
# (The UI is non-blocking; the script will exit when you close the browser tab.)
#
# Env:    PY=python     override interpreter (default: ./myenv/bin/python)

set -euo pipefail

cd "$(dirname "$0")"
PY="${PY:-./myenv/bin/python}"
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"

echo "============================================================"
echo " Digital-Twin Demo Pipeline"
echo "============================================================"
echo "Python:  $($PY --version 2>&1)"
echo "Date:    $(date)"
echo

echo "[1/3] SPDC source demo ..."
$PY -m quantum_source.demo

echo
echo "[2/3] SPDC source -> Arduino Uno twin demo ..."
$PY -m quantum_source.arduino_demo

echo
echo "[3/3] Full entangled-photon PPG system demo ..."
$PY -m quantum_ppg.demo

echo
echo "============================================================"
echo " Outputs"
echo "============================================================"
echo "  quantum_source_output/  :  state, measurements, correlations"
echo "  quantum_ppg_output/     :  full PPG pipeline (11 PNGs)"
echo "============================================================"

if [[ "${1:-}" == "--with-streamlit" ]]; then
    echo
    echo "Launching Streamlit UI (Ctrl-C to stop) ..."
    exec $PY -m streamlit run streamlit_app.py
fi

