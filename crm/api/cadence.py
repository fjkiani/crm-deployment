"""Cadence engine — DEPRECATED alias for crm.api.sequence_engine.

The cadence engine (commit 0f991dc9) has been SUBSUMED by sequence_engine, which
lifts the proven human-gated advance/refuse core and adds arm / on_channel_event /
get_today_worklist / new delay semantics (delay_days = offset from prior step
completion, not absolute from seed day).

This module is kept as a thin alias so any existing caller of
`crm.api.cadence.<endpoint>` keeps working. There is a SINGLE engine; do not add
logic here — add it to sequence_engine.
"""

import frappe

from crm.api.sequence_engine import (
	advance_call_step,
	advance_sequence_instance,
	advance_whatsapp_step,
	arm_sequence,
	get_sequence_state,
	get_today_worklist,
	mark_step_complete,
	on_channel_event,
)

__all__ = [
	"advance_sequence_instance",
	"advance_call_step",
	"advance_whatsapp_step",
	"arm_sequence",
	"get_sequence_state",
	"get_today_worklist",
	"mark_step_complete",
	"on_channel_event",
]
