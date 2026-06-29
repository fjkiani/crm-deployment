# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AACRTalk(Document):
	pass


@frappe.whitelist()
def get_aacr_talk(talk_id):
	"""Return the AACR Talk as the nested data-contract record the frontend
	IntelPanel expects (the inverse of the ingest upsert). The component layer is
	storage-agnostic: it reads field names from the aacr_2026 schema, so this
	method re-assembles the doctype + its child tables back into that shape.

	Returns None if the talk does not exist (frontend treats null as "no talk").
	"""
	if not talk_id or not frappe.db.exists("AACR Talk", talk_id):
		return None

	doc = frappe.get_doc("AACR Talk", talk_id)

	# 6 list[str] fields, reconstructed from the generic Tag child table by `kind`.
	tag_lists = {
		"tumor_types": [],
		"topic_categories": [],
		"readouts": [],
		"key_findings": [],
		"resistance_or_selectivity_notes": [],
		"open_questions": [],
	}
	for row in (doc.tags or []):
		if row.kind in tag_lists and row.value not in (None, ""):
			tag_lists[row.kind].append(row.value)

	# external_follow_up: object-of-lists, rebuilt from the Reference child table.
	efu = {
		"nct_numbers": [],
		"abstract_ids": [],
		"cited_papers": [],
		"company_or_sponsor": [],
		"patent_or_ip_hints": [],
	}
	for row in (doc.refs or []):
		if row.ref_type in efu and row.value not in (None, ""):
			efu[row.ref_type].append(row.value)

	def clean(d, keys):
		"""Keep only the contract keys; drop empty values so renderers show '—'."""
		out = {}
		for k in keys:
			v = d.get(k)
			if v not in (None, ""):
				out[k] = v
		return out

	targets = [
		clean(t.as_dict(), [
			"gene_or_protein", "modality", "pathway", "alteration", "compound_name",
			"compound_id", "ligase_or_cofactor", "dependency_context", "target_novelty",
		])
		for t in (doc.targets or [])
	]
	biomarkers = [
		clean(b.as_dict(), ["name", "type", "finding", "assay"])
		for b in (doc.biomarkers or [])
	]
	# `name` is reserved in child rows, so it is stored as `name1` -> re-key to `name`.
	models = []
	for m in (doc.models or []):
		md = m.as_dict()
		models.append(clean(
			{"model_type": md.get("model_type"), "name": md.get("name1"),
			 "genotype_or_key_features": md.get("genotype_or_key_features")},
			["model_type", "name", "genotype_or_key_features"],
		))
	clinical_data = [
		clean(c.as_dict(), [
			"metric", "value", "confidence_interval", "n", "population", "comparator", "maturity",
		])
		for c in (doc.clinical_data or [])
	]
	combination_strategies = [
		clean(c.as_dict(), ["with_agent", "phenotype", "rationale", "stage"])
		for c in (doc.combinations or [])
	]

	record = {
		"talk_id": doc.talk_id,
		"talk_title": doc.talk_title,
		"session_title": doc.session_title,
		"clinical_stage": doc.clinical_stage,
		"novelty_flag": doc.novelty_flag,
		"MOA_summary": doc.moa_summary,
		"speaker": clean({
			"name": doc.speaker_name,
			"affiliation": doc.speaker_affiliation,
			"role": doc.speaker_role,
			"disclosures_noted": bool(doc.speaker_disclosures_noted),
		}, ["name", "affiliation", "role", "disclosures_noted"]),
		"targets": targets,
		"biomarkers": biomarkers,
		"models": models,
		"clinical_data": clinical_data,
		"combination_strategies": combination_strategies,
		"external_follow_up": efu,
	}
	record.update(tag_lists)
	return record
