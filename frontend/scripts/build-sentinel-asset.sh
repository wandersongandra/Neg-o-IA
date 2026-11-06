#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
frontend_dir="$(cd "$script_dir/.." && pwd)"
asset_dir="$frontend_dir/public/models"

blender -b -t 2 --python "$script_dir/create_sentinel_model.py"
python3 - "$asset_dir/sentinel.png" "$asset_dir/sentinel.webp" <<'PY'
import sys
from PIL import Image
Image.open(sys.argv[1]).convert("RGBA").save(sys.argv[2], "WEBP", quality=87, method=6)
PY
rm "$asset_dir/sentinel.png"
printf 'Generated %s and %s\n' "$asset_dir/sentinel.glb" "$asset_dir/sentinel.webp"
