"""Decision Makers — institution hierarchy for a lead. Real data, no stubs.

infer_from_intel returns a REVIEW QUEUE (never auto-inserts); approve_inferred
is the human gate that persists a reviewed contact.
"""

from __future__ import annotations

import re

import frappe
from frappe import _

ROLES = ["Economic Buyer", "Champion", "Influencer", "Blocker", "Gatekeeper", "End User"]

TITLE_ROLE_MAP = [
    (r"\b(ceo|chief executive|president)\b", "Economic Buyer"),
    (r"\b(cmo|chief medical|chief scientific|cso|svp|vp|vice president)\b", "Economic Buyer"),
    (r"\b(chair|director|head of|department)\b", "Champion"),
    (r"\b(pi|principal investigator|professor|md|phd|investigator)\b", "Champion"),
    (r"\b(coordinator|manager|administrator|liaison)\b", "Gatekeeper"),
    (r"\b(fellow|resident|associate|scientist|researcher)\b", "Influencer"),
]


def _lead(lead):
    if not frappe.db.exists("CRM Lead", lead):
        frappe.throw(_("Lead not found: {0}").format(lead))
    return frappe.get_doc("CRM Lead", lead)


@frappe.whitelist()
def list_for_lead(lead: str):
    _lead(lead)
    rows = frappe.get_all(
        "Decision Maker", filters={"lead": lead},
        fields=["name", "contact_name", "title", "role", "reports_to", "influence",
                "warmth", "email", "phone", "source", "notes"],
        order_by="influence desc", limit=500)
    return {"ok": True, "lead": lead, "count": len(rows), "decision_makers": rows}


@frappe.whitelist()
def add(lead: str, contact_name: str, title: str = "", role: str = "Influencer",
        reports_to: str = "", influence: int = 3, warmth: str = "cold",
        email: str = "", phone: str = "", source: str = "manual", notes: str = ""):
    _lead(lead)
    if role not in ROLES:
        role = "Influencer"
    doc = frappe.get_doc({
        "doctype": "Decision Maker", "lead": lead, "contact_name": contact_name,
        "title": title, "role": role, "reports_to": reports_to or None,
        "influence": int(influence or 3), "warmth": warmth or "cold",
        "email": email, "phone": phone, "source": source, "notes": notes,
    })
    doc.insert()
    return {"ok": True, "name": doc.name}


@frappe.whitelist()
def update(name: str, **fields):
    if not frappe.db.exists("Decision Maker", name):
        frappe.throw(_("Decision Maker not found: {0}").format(name))
    doc = frappe.get_doc("Decision Maker", name)
    for k in ["contact_name", "title", "role", "reports_to", "influence", "warmth",
              "email", "phone", "source", "notes"]:
        if k in fields and fields[k] is not None:
            doc.set(k, fields[k])
    doc.save()
    return {"ok": True, "name": name}


@frappe.whitelist()
def get_hierarchy(lead: str):
    """Build the reporting tree from reports_to edges."""
    _lead(lead)
    rows = frappe.get_all(
        "Decision Maker", filters={"lead": lead},
        fields=["name", "contact_name", "title", "role", "reports_to", "influence", "warmth"],
        order_by="influence desc", limit=500)
    by_name = {r["name"]: dict(r, children=[]) for r in rows}
    roots = []
    for r in by_name.values():
        parent = r.get("reports_to")
        if parent and parent in by_name and parent != r["name"]:
            by_name[parent]["children"].append(r)
        else:
            roots.append(r)
    return {"ok": True, "lead": lead, "count": len(rows), "hierarchy": roots}


def _guess_role(title: str) -> str:
    t = (title or "").lower()
    for pat, role in TITLE_ROLE_MAP:
        if re.search(pat, t):
            return role
    return "Influencer"


def _guess_influence(role: str) -> int:
    return {"Economic Buyer": 5, "Champion": 4, "Influencer": 3,
            "Gatekeeper": 2, "Blocker": 1, "End User": 2}.get(role, 3)


@frappe.whitelist()
def infer_from_intel(lead: str):
    """Parse the lead's intel for named people + titles. Returns a REVIEW QUEUE.

    Never auto-inserts. Each candidate carries a proposed role/influence and the
    evidence snippet it was inferred from, so a human can approve or discard.
    """
    doc = _lead(lead)
    text = " ".join(filter(None, [
        doc.get("current_focus"), doc.get("pain_points"),
        doc.get("fit_rationale"), doc.get("aacr_topic"),
    ]))
    candidates = []
    # "Dr. Firstname Lastname, <title>" / "Firstname Lastname, MD" patterns
    for m in re.finditer(
            r"(?:Dr\.?\s+)?([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s*,\s*([^.;]+?))?(?=\s*(?:,|\.|;| at | of |\bMD\b|\bPhD\b|$))",
            text):
        name = m.group(1).strip()
        title = (m.group(2) or "").strip()
        # skip the lead herself and obvious non-people
        if name.lower() in ((doc.get("first_name") or "") + " " + (doc.get("last_name") or "")).lower():
            continue
        if len(name.split()) != 2:
            continue
        role = _guess_role(title)
        candidates.append({
            "contact_name": name, "title": title, "role": role,
            "influence": _guess_influence(role), "warmth": "cold",
            "source": "inferred", "evidence": m.group(0)[:120],
        })
    # dedupe by name
    seen, uniq = set(), []
    for c in candidates:
        if c["contact_name"] not in seen:
            seen.add(c["contact_name"])
            uniq.append(c)
    return {"ok": True, "lead": lead, "review_queue": uniq, "count": len(uniq),
            "auto_inserted": False}


@frappe.whitelist()
def approve_inferred(lead: str, contact_name: str, title: str = "", role: str = "",
                     influence: int = 0, reports_to: str = ""):
    """Human gate: persist a reviewed inferred contact."""
    _lead(lead)
    role = role if role in ROLES else _guess_role(title)
    influence = int(influence or _guess_influence(role))
    return add(lead=lead, contact_name=contact_name, title=title, role=role,
               reports_to=reports_to, influence=influence, warmth="cold",
               source="inferred_approved")
