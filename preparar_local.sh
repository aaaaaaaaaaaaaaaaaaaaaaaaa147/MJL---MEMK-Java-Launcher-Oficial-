#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPSTREAM="${ROOT}/source"
if [ ! -d "${UPSTREAM}/.git" ]; then
  git clone --recursive --branch v3_openjdk https://github.com/AngelAuraMC/Amethyst-Android.git "$UPSTREAM"
fi
cd "$UPSTREAM"
git checkout 28d6e12d68121b7dd75f2e841058a6b7cdfe4a29
git submodule update --init --recursive
python3 "${ROOT}/customize.py" "$UPSTREAM"
echo "Personalizado. Com os runtimes instalados, rode: cd source && ./gradlew :app_pojavlauncher:assembleDebug"
