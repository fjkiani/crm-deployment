"""Outreach 360 — single board payload for the operator dashboard + MCP.

One call returns everything the 360 surface needs: the due/blocked/approval buckets
(from sequence_engine.get_today_worklist), per-sequence rollup, and channel health.
The Vue surface and the MCP get_today_worklist tool both read from here so the UI
and agents see the SAME truth.
"""

import frappe

from crm.api import sequence_engine as se


@frappe.whitelist()
def get_board(user: str | None = None, limit: int = 50):
	"""The 360 board: worklist buckets + sequence rollup + channel health.

	Args:
		user: Optional assignee filter.
		limit: Max items per bucket.
	"""
	worklist = se.get_today_worklist(user=user, limit=limit)

	# Per-sequence rollup: one row per Outreach Sequence with instance counts.
	sequences = frappe.get_all(
		"Outreach Sequence",
		fields=["name", "sequence_name", "tier", "status", "active"],
		order_by="modified desc",
		limit=100,
	)
	rollup = []
	for seq in sequences:
		instances = frappe.get_all(
			"Outreach Sequence Instance",
			filters={"outreach_sequence": seq["name"]},
			fields=["status"],
			limit=500,
		)
		by_status = {}
		for inst in instances:
			by_status[inst["status"]] = by_status.get(inst["status"], 0) + 1
		rollup.append({
			"sequence": seq["name"],
			"sequence_name": seq.get("sequence_name"),
			"tier": seq.get("tier"),
			"status": seq.get("status"),
			"active": seq.get("active"),
			"instances": len(instances),
			"by_status": by_status,
		})

	return {
		"ok": True,
		"due_email": worklist.get("due_email", []),
		"due_call": worklist.get("due_call", []),
		"due_whatsapp": worklist.get("due_whatsapp", []),
		"needs_approval": worklist.get("needs_approval", []),
		"blocked": worklist.get("blocked", []),
		"waiting": worklist.get("waiting", []),
		"needs_human": worklist.get("needs_human", []),
		"health": worklist.get("health", {}),
		"sequences": rollup,
		"counts": {
			"due_email": len(worklist.get("due_email", [])),
			"due_call": len(worklist.get("due_call", [])),
			"due_whatsapp": len(worklist.get("due_whatsapp", [])),
			"needs_approval": len(worklist.get("needs_approval", [])),
			"blocked": len(worklist.get("blocked", [])),
			"waiting": len(worklist.get("waiting", [])),
			"needs_human": len(worklist.get("needs_human", [])),
		},
	}
