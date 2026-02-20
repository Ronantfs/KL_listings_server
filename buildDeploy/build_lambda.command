#!/bin/bash
set -euo pipefail

# Project root is one level up from this script
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

BUILD_DIR="build"
ZIP_NAME="lambda_package.zip"
REQUIREMENTS="requirements.txt"
SOURCE_FILES=("lambda_function.py" "aws.py" "http_utils.py" "data_types.py")
SOURCE_DIRS=("routes" "shared")

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment (.venv)"
  uv venv .venv
fi

source .venv/bin/activate

rm -rf "$BUILD_DIR" "$ZIP_NAME"
mkdir -p "$BUILD_DIR"

echo "Installing dependencies into $BUILD_DIR/"
uv pip install -r "$REQUIREMENTS" --target "$BUILD_DIR/"

echo "Copying Lambda source files"
for f in "${SOURCE_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "ERROR: missing source file $f"
    exit 1
  fi
  cp "$f" "$BUILD_DIR/"
  echo "  - $f copied"
done

echo "Copying Lambda source directories"
for d in "${SOURCE_DIRS[@]}"; do
  if [[ ! -d "$d" ]]; then
    echo "ERROR: missing source directory $d"
    exit 1
  fi
  cp -r "$d" "$BUILD_DIR/"
  echo "  - $d/ copied"
done

echo "Creating Lambda deployment zip"
(
  cd "$BUILD_DIR"
  zip -r "../$ZIP_NAME" .
)

echo "Lambda zip built:"
ls -lh "$ZIP_NAME"
