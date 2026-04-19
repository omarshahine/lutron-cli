#!/usr/bin/env bash
#
# Verify every version-carrying manifest agrees. Exits non-zero if any
# source disagrees, prints a table either way. Mirrors the CI check in
# .github/workflows/version-check.yml so drift is caught locally.

set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required (brew install jq / apt-get install jq)" >&2
  exit 2
fi

v_pyproject=$(python3 -c 'import tomllib;print(tomllib.loads(open("pyproject.toml","rb").read().decode())["project"]["version"])')
v_pkg=$(jq -r '.version' openclaw/package.json)
v_oc_plugin=$(jq -r '.version' openclaw/openclaw.plugin.json)
v_cc_plugin=$(jq -r '.version' .claude-plugin/plugin.json)
v_market=$(jq -r '.plugins[0].version' marketplace.json)

printf "%-36s %s\n" "File" "Version"
printf "%-36s %s\n" "----" "-------"
printf "%-36s %s\n" "pyproject.toml"                "$v_pyproject"
printf "%-36s %s\n" "openclaw/package.json"         "$v_pkg"
printf "%-36s %s\n" "openclaw/openclaw.plugin.json" "$v_oc_plugin"
printf "%-36s %s\n" ".claude-plugin/plugin.json"    "$v_cc_plugin"
printf "%-36s %s\n" "marketplace.json"              "$v_market"

uniq=$(printf '%s\n' "$v_pyproject" "$v_pkg" "$v_oc_plugin" "$v_cc_plugin" "$v_market" | sort -u | wc -l | tr -d ' ')

if [ "$uniq" != "1" ]; then
  echo
  echo "FAIL: version sources disagree." >&2
  exit 1
fi

echo
echo "OK: all version sources agree on $v_pkg"
