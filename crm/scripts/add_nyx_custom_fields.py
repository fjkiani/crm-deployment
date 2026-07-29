import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """
    Creates the required custom fields on the CRM Lead doctype for Nyx orchestration data.

    Run via:
        bench --site crm.localhost execute crm.scripts.add_nyx_custom_fields.execute

    This is idempotent — running it again won't duplicate fields.

    Fields created:
    ┌──────────────────────────────────────────────────────────────────────┐
    │ Section: Nyx Intelligence                                          │
    │ ┌────────────────────┬────────────────────────────────────────────┐ │
    │ │ nyx_enriched       │ Check: whether lead has been enriched     │ │
    │ │ nyx_score          │ Int: 0-100 lead score from enrichment     │ │
    │ │ nyx_framework      │ Data: challenger/pas/aida                 │ │
    │ │ lead_score         │ Int: alias for nyx_score (legacy compat)  │ │
    │ └────────────────────┴────────────────────────────────────────────┘ │
    │ ┌────────────────────┬────────────────────────────────────────────┐ │
    │ │ email_status       │ Select: Draft Ready/Sent/Bounced/etc.     │ │
    │ │ outreach_status    │ Select: None/Contacted/Interested/Lost    │ │
    │ └────────────────────┴────────────────────────────────────────────┘ │
    │ Section: Nyx Sequence                                              │
    │ ┌────────────────────┬────────────────────────────────────────────┐ │
    │ │ nyx_sequence_step  │ Int: current step in 21-day siege         │ │
    │ │ nyx_sequence_status│ Select: Active/Paused/Complete/Quarantine │ │
    │ └────────────────────┴────────────────────────────────────────────┘ │
    │ Section: Nyx Internal                                              │
    │ ┌────────────────────┬────────────────────────────────────────────┐ │
    │ │ nyx_signal_gate    │ Data: signal gate result (PASS/FAIL)      │ │
    │ │ nyx_quarantine_rsn │ Data: quarantine reason if signal gate    │ │
    │ │ nyx_last_pipeline  │ Datetime: last enrichment run time        │ │
    │ │ nyx_enrichment_json│ Long Text: full enrichment JSON (hidden)  │ │
    │ │ nyx_sources_used   │ Data: comma-sep enrichment sources        │ │
    │ │ nyx_detected_ctx   │ Data: comma-sep contexts (core,financial) │ │
    │ └────────────────────┴────────────────────────────────────────────┘ │
    └──────────────────────────────────────────────────────────────────────┘
    """
    custom_fields = {
        "CRM Lead": [
            # ── Section: Nyx Intelligence ──────────────────────────────────
            {
                "fieldname": "nyx_intelligence_section",
                "label": "Nyx Intelligence",
                "fieldtype": "Section Break",
                "insert_after": "email",
                "collapsible": 1,
            },
            {
                "fieldname": "nyx_enriched",
                "label": "Enriched",
                "fieldtype": "Check",
                "default": "0",
                "read_only": 1,
                "in_standard_filter": 1,
                "insert_after": "nyx_intelligence_section",
                "description": "Set to 1 after successful enrichment pipeline run",
            },
            {
                "fieldname": "nyx_score",
                "label": "Nyx Score",
                "fieldtype": "Int",
                "non_negative": 1,
                "read_only": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "nyx_enriched",
                "description": "Lead score 0-100 from enrichment pipeline",
            },
            {
                "fieldname": "nyx_framework",
                "label": "Framework",
                "fieldtype": "Select",
                "options": "\nchallenger\npas\naida",
                "read_only": 1,
                "in_list_view": 1,
                "insert_after": "nyx_score",
                "description": "Email framework: challenger (>=70), pas (40-69), aida (<40)",
            },
            {
                "fieldname": "lead_score",
                "label": "Lead Score (Legacy)",
                "fieldtype": "Int",
                "non_negative": 1,
                "read_only": 1,
                "hidden": 1,
                "insert_after": "nyx_framework",
                "description": "Legacy alias for nyx_score — used by LeadGen collectors",
            },

            # ── Column Break ──────────────────────────────────────────────
            {
                "fieldname": "nyx_col_break_1",
                "fieldtype": "Column Break",
                "insert_after": "lead_score",
            },

            # ── Outreach Status ───────────────────────────────────────────
            {
                "fieldname": "email_status",
                "label": "Email Status",
                "fieldtype": "Select",
                "options": "\nDraft Ready\nSent\nBounced\nQuarantined\nReply Received\nRejected\nRebuttal Draft Ready\nHandoff Received\nQuestion Received\nUnsubscribed\nOOO\nNeeds Review",
                "read_only": 1,
                "in_list_view": 1,
                "in_standard_filter": 1,
                "insert_after": "nyx_col_break_1",
                "description": "Current email lifecycle status",
            },
            {
                "fieldname": "outreach_status",
                "label": "Outreach Status",
                "fieldtype": "Select",
                "options": "\nNone\nContacted\nInterested\nMeeting Booked\nLost\nDo Not Contact",
                "read_only": 1,
                "in_standard_filter": 1,
                "insert_after": "email_status",
                "description": "Roll-up outreach status across email + calls",
            },

            # ── Section: Nyx Sequence ─────────────────────────────────────
            {
                "fieldname": "nyx_sequence_section",
                "label": "Nyx Sequence",
                "fieldtype": "Section Break",
                "insert_after": "outreach_status",
                "collapsible": 1,
            },
            {
                "fieldname": "nyx_sequence_step",
                "label": "Sequence Step",
                "fieldtype": "Int",
                "read_only": 1,
                "insert_after": "nyx_sequence_section",
                "description": "Current step in 21-day siege engine (0-4 = Day 0/3/7/14/21)",
            },
            {
                "fieldname": "nyx_sequence_status",
                "label": "Sequence Status",
                "fieldtype": "Select",
                "options": "\nActive\nPaused\nComplete\nQuarantined",
                "read_only": 1,
                "in_standard_filter": 1,
                "insert_after": "nyx_sequence_step",
            },

            # ── Section: Nyx Internal (hidden from standard view) ────────
            {
                "fieldname": "nyx_internal_section",
                "label": "Nyx Internal",
                "fieldtype": "Section Break",
                "insert_after": "nyx_sequence_status",
                "collapsible": 1,
            },
            {
                "fieldname": "nyx_signal_gate",
                "label": "Signal Gate",
                "fieldtype": "Select",
                "options": "\nPASS\nFAIL",
                "read_only": 1,
                "insert_after": "nyx_internal_section",
                "description": "PASS if >= 1 real signal, FAIL if 3/3 UNKNOWN",
            },
            {
                "fieldname": "nyx_quarantine_reason",
                "label": "Quarantine Reason",
                "fieldtype": "Small Text",
                "read_only": 1,
                "insert_after": "nyx_signal_gate",
                "description": "Why this lead was quarantined (signal gate failure, etc.)",
            },
            {
                "fieldname": "nyx_last_pipeline_run",
                "label": "Last Pipeline Run",
                "fieldtype": "Datetime",
                "read_only": 1,
                "insert_after": "nyx_quarantine_reason",
            },
            {
                "fieldname": "nyx_sources_used",
                "label": "Enrichment Sources",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "nyx_last_pipeline_run",
                "description": "Comma-separated list: tavily,apollo,brightdata_sec,pubmed",
            },
            {
                "fieldname": "nyx_detected_context",
                "label": "Detected Context",
                "fieldtype": "Data",
                "read_only": 1,
                "insert_after": "nyx_sources_used",
                "description": "Comma-separated: core,financial,clinical,risk,competitive",
            },

            # ── Column Break ──────────────────────────────────────────────
            {
                "fieldname": "nyx_col_break_2",
                "fieldtype": "Column Break",
                "insert_after": "nyx_detected_context",
            },
            {
                "fieldname": "nyx_enrichment_json",
                "label": "Enrichment JSON",
                "fieldtype": "Long Text",
                "read_only": 1,
                "hidden": 1,
                "insert_after": "nyx_col_break_2",
                "description": "Full enrichment payload — consumed by NyxTab.vue",
            },
        ]
    }

    create_custom_fields(custom_fields, ignore_validate=True)
    frappe.db.commit()

    # ── Post-migration: verify all fields exist ──────────────────────────────
    expected_fields = [
        "nyx_enriched", "nyx_score", "nyx_framework", "lead_score",
        "email_status", "outreach_status",
        "nyx_sequence_step", "nyx_sequence_status",
        "nyx_signal_gate", "nyx_quarantine_reason",
        "nyx_last_pipeline_run", "nyx_sources_used",
        "nyx_detected_context", "nyx_enrichment_json",
    ]

    meta = frappe.get_meta("CRM Lead")
    missing = []
    for field_name in expected_fields:
        if not meta.has_field(field_name):
            missing.append(field_name)

    if missing:
        print(f"⚠️  WARNING: {len(missing)} fields still missing after migration: {missing}")
    else:
        print(f"✅ All {len(expected_fields)} Nyx custom fields verified on CRM Lead doctype")

    return {"created": len(expected_fields) - len(missing), "missing": missing}
