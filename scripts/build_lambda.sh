#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="$project_root/lambda_firewall"
output_path="${1:-$project_root/api_gateway/lambda_function.zip}"
build_dir="$(mktemp -d)"
trap 'rm -rf "$build_dir"' EXIT

python3 -m pip install \
  --disable-pip-version-check \
  --implementation cp \
  --python-version 3.10 \
  --platform manylinux2014_x86_64 \
  --only-binary=:all: \
  --target "$build_dir/package" \
  -r "$source_dir/requirements.txt"

cp "$source_dir"/*.py "$build_dir/package/"
find "$build_dir/package" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
find "$build_dir/package" -type d -name '__pycache__' -empty -delete
mkdir -p "$(dirname "$output_path")"

(
  cd "$build_dir/package"
  python3 -m zipfile -c "$output_path" .
)

echo "Built $output_path"
