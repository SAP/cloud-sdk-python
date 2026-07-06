#!/usr/bin/env bash
# lib/detect-language.sh — detect Python vs Java repo shape.
set -euo pipefail

detect_language() {
  local root="${1:-.}"
  if [ -f "$root/pyproject.toml" ] && [ -f "$root/pom.xml" ]; then
    echo "ERROR: both pyproject.toml AND pom.xml found — cannot auto-detect" >&2
    exit 3
  fi
  if [ -f "$root/pyproject.toml" ]; then
    if [ -d "$root/src/sap_cloud_sdk" ] || [ -d "$root/src" ]; then
      echo "python"; return
    fi
  fi
  if [ -f "$root/pom.xml" ]; then
    if [ -d "$root/src/main/java" ]; then
      echo "java"; return
    fi
  fi
  echo "unknown"
}

detect_language "$@"
