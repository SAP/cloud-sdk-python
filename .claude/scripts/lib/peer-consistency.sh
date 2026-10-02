#!/usr/bin/env bash
# lib/peer-consistency.sh — compute peer-adoption fractions and fire only when
# a new module diverges from a widely-adopted element (>=80%).
#
# The v2 rule engine originally hard-coded "every client module MUST have a
# Factory" — but empirical review of the JV corpus showed only `destination`
# has a Factory; `objectstore`, `agentgateway`, `adms`, `aicore` are all
# valid module designs without one. Encoding one module's shape as universal
# law is FP-G-01 (see docs/plans 09-FP-REMEDIATION §Pattern G).
#
# This helper answers: "of all existing modules under src/**/<mod>/, what
# fraction have <element>?" A rule can then say `if fraction >= 0.8 and new
# module lacks it, emit FLAG`.
#
# All emissions from peer-consistency checks are FLAG tier, never BLOCK.
#
# API:
#   peer_modules <repo_root> <lang>             → prints one module name/line
#   peer_element_fraction <repo_root> <lang> <element>
#     → prints "count/total" and returns 0. `element` is one of:
#         user-guide.md, exceptions, factory, client, config, py.typed
#   should_flag_peer_divergence <mod_dir> <element> <fraction_str>
#     → returns 0 if the module lacks the element AND fraction >= 0.8

set -uo pipefail

peer_modules() {
  local repo_root="${1:-.}" lang="${2:-python}"
  if [ "$lang" = "python" ]; then
    find "$repo_root/src/sap_cloud_sdk" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | \
      awk -F/ '{print $NF}' | grep -vE '^(__pycache__|core)$' | sort -u
  else
    find "$repo_root/src/main/java/com/sap/cloud/sdk" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | \
      awk -F/ '{print $NF}' | grep -vE '^(core)$' | sort -u
  fi
}

# has_element <mod_dir> <element> <lang>
#   Returns 0 if the module dir contains the element.
#   Elements:
#     user-guide.md    a user-guide.md at module root
#     exceptions       exceptions.py OR any Exception subclass in module (python)
#                      exceptions/ dir (java)
#     factory          create_*_client() function or *ClientFactory class
#     client           Client class (python: client.py; java: *Client.java)
#     config           config.py or *Config.java
#     py.typed         py.typed marker (python only)
has_element() {
  local mod_dir="$1" el="$2" lang="${3:-python}"
  [ -d "$mod_dir" ] || return 1
  case "$el" in
    user-guide.md)
      [ -f "$mod_dir/user-guide.md" ]
      ;;
    exceptions)
      if [ "$lang" = "python" ]; then
        [ -f "$mod_dir/exceptions.py" ] && return 0
        # Fallback: any Exception subclass anywhere in module tree
        grep -rEIlq 'class [A-Z][A-Za-z0-9_]+\((Base)?Exception|[A-Z][A-Za-z]+(Error|Exception))\)' \
          "$mod_dir" 2>/dev/null
      else
        [ -d "$mod_dir/exceptions" ]
      fi
      ;;
    factory)
      if [ "$lang" = "python" ]; then
        grep -rEIlq '^def create_[a-z_]*client\(' "$mod_dir" 2>/dev/null
      else
        grep -rEIlq 'class [A-Z][A-Za-z]*ClientFactory' "$mod_dir" 2>/dev/null
      fi
      ;;
    client)
      if [ "$lang" = "python" ]; then
        [ -f "$mod_dir/client.py" ] && return 0
        grep -rEIlq '^class [A-Z][A-Za-z0-9_]+Client\b' "$mod_dir" 2>/dev/null
      else
        find "$mod_dir" -name '*Client.java' 2>/dev/null | grep -q .
      fi
      ;;
    config)
      if [ "$lang" = "python" ]; then
        [ -f "$mod_dir/config.py" ]
      else
        find "$mod_dir" -name '*Config.java' 2>/dev/null | grep -q .
      fi
      ;;
    py.typed)
      [ -f "$mod_dir/py.typed" ]
      ;;
    *)
      return 2
      ;;
  esac
}

# peer_element_fraction <repo_root> <lang> <element>
#   Prints "adopted total fraction" where fraction is a float 0.0-1.0.
peer_element_fraction() {
  local repo_root="$1" lang="$2" el="$3"
  local mod adopted=0 total=0 mod_dir
  while IFS= read -r mod; do
    [ -z "$mod" ] && continue
    if [ "$lang" = "python" ]; then
      mod_dir="$repo_root/src/sap_cloud_sdk/$mod"
    else
      mod_dir="$repo_root/src/main/java/com/sap/cloud/sdk/$mod"
    fi
    total=$((total + 1))
    if has_element "$mod_dir" "$el" "$lang"; then
      adopted=$((adopted + 1))
    fi
  done < <(peer_modules "$repo_root" "$lang")
  if [ "$total" -eq 0 ]; then
    echo "0 0 0.0"
    return
  fi
  # bash arithmetic can't do floats — compute via awk
  local frac
  frac=$(awk -v a="$adopted" -v t="$total" 'BEGIN{printf "%.3f", a/t}')
  echo "$adopted $total $frac"
}

# should_flag_peer_divergence <mod_dir> <element> <lang> <threshold>
#   Returns 0 (should flag) if:
#     - module lacks the element, AND
#     - peer adoption fraction (excluding this module) >= threshold (default 0.80)
#   The caller supplies the module dir, element name, and the repo/lang context.
should_flag_peer_divergence() {
  local mod_dir="$1" el="$2" lang="${3:-python}" threshold="${4:-0.80}"
  # Guard: if module has the element already, no flag.
  if has_element "$mod_dir" "$el" "$lang"; then return 1; fi
  # Compute fraction across peers, EXCLUDING the module itself.
  local repo_root this_mod
  this_mod="$(basename "$mod_dir")"
  if [ "$lang" = "python" ]; then
    repo_root="$(cd "$mod_dir/../../.." && pwd)"
  else
    repo_root="$(cd "$mod_dir/../../../../../../.." && pwd)"
  fi
  local mod adopted=0 total=0 peer_dir
  while IFS= read -r mod; do
    [ -z "$mod" ] && continue
    # Skip the module under review — we only care about peer adoption.
    [ "$mod" = "$this_mod" ] && continue
    if [ "$lang" = "python" ]; then
      peer_dir="$repo_root/src/sap_cloud_sdk/$mod"
    else
      peer_dir="$repo_root/src/main/java/com/sap/cloud/sdk/$mod"
    fi
    total=$((total + 1))
    if has_element "$peer_dir" "$el" "$lang"; then
      adopted=$((adopted + 1))
    fi
  done < <(peer_modules "$repo_root" "$lang")
  # need at least 2 peers to draw a "pattern"
  [ "$total" -ge 2 ] || return 1
  local frac
  frac=$(awk -v a="$adopted" -v t="$total" 'BEGIN{printf "%.3f", a/t}')
  awk -v f="$frac" -v t="$threshold" 'BEGIN{exit !(f+0 >= t+0)}'
}

# CLI dispatch (only when executed, not when sourced)
if [ "${BASH_SOURCE[0]:-}" = "${0:-}" ] && [ -n "${BASH_SOURCE[0]:-}" ]; then
  case "${1:-}" in
    peer_modules)         shift; peer_modules "$@" ;;
    has_element)          shift; has_element "$@" ;;
    peer_element_fraction) shift; peer_element_fraction "$@" ;;
    should_flag_peer_divergence) shift; should_flag_peer_divergence "$@" ;;
    *) echo "Usage: peer-consistency.sh {peer_modules|has_element|peer_element_fraction|should_flag_peer_divergence} ..." >&2; exit 2 ;;
  esac
fi
