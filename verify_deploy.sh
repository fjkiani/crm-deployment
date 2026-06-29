#!/usr/bin/env bash
set -euo pipefail

SITE="${SITE:-https://alpha-crm.v.frappe.cloud}"
EXPECTED_INDEX="${EXPECTED_INDEX:-index-28bebeae.js}"
EXPECTED_LEAD="${EXPECTED_LEAD:-Lead-2f576e22.js}"
LEAD_URL="${LEAD_URL:-$SITE/crm/leads/CRM-LEAD-2026-00872}"

echo "== TrackerIntel deploy verify =="
echo "Site: $SITE"

INDEX_HTML=$(curl -fsSL "$SITE/assets/crm/frontend/index.html")
LIVE_INDEX=$(echo "$INDEX_HTML" | grep -oE 'index-[a-f0-9]+\.js' | head -1 || true)
echo "Entry chunk: ${LIVE_INDEX:-MISSING} (want $EXPECTED_INDEX)"

if [ "$LIVE_INDEX" = "$EXPECTED_INDEX" ]; then
  echo "Entry chunk: OK"
else
  echo "Entry chunk: NOT YET"
fi

LEAD_CODE=$(curl -sS -o /tmp/lead-chunk.js -w "%{http_code}" "$SITE/assets/crm/frontend/assets/$EXPECTED_LEAD")
echo "Lead chunk HTTP: $LEAD_CODE (want 200)"

if [ "$LEAD_CODE" = "200" ] && grep -q 'TrackerIntel\|GTM Intel' /tmp/lead-chunk.js; then
  echo "TrackerIntel in Lead chunk: OK"
else
  echo "TrackerIntel in Lead chunk: NOT YET"
fi

echo "Lead URL: $LEAD_URL"

if [ "$LIVE_INDEX" = "$EXPECTED_INDEX" ] && [ "$LEAD_CODE" = "200" ] && grep -q 'TrackerIntel\|GTM Intel' /tmp/lead-chunk.js; then
  echo "OVERALL: LIVE"
  exit 0
fi

echo "OVERALL: NOT YET"
exit 1
