#!/bin/zsh

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

if [ ! -x ".venv/bin/python" ]; then
  echo "Gerekli kurulum bulunamadi."
  echo "Lutfen bu proje klasorundeki sanal ortami yeniden kurun."
  read -k 1 "?Kapatmak icin bir tusa basin..."
  echo
  exit 1
fi

exec ".venv/bin/python" -m streamlit run "$SCRIPT_DIR/app.py"
