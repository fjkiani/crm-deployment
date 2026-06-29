// AACR 2026 schema — field-schema descriptor for the 862-talk master dataset.
// Surfaces ALL 19 fields (nothing siloed) through the generic IntelPanel.
//
// Field types verified against the full corpus (aacr2026_schema_a_master.json):
//   scalar (3): talk_id, session_title, talk_title
//   enum   (2): clinical_stage, novelty_flag
//   paragraph (1): MOA_summary
//   list_scalar (6): tumor_types, topic_categories, readouts, key_findings,
//                    resistance_or_selectivity_notes, open_questions
//   table_obj (5): targets, biomarkers, models, clinical_data, combination_strategies
//   object (1): speaker
//   object_of_lists (1): external_follow_up
// All five "table_obj" fields are uniformly list[obj] across all 862 records
// (no bare-string drift), so they render as compact tables.

export const aacr2026Schema = {
  schema_key: 'aacr_2026',
  title: 'AACR 2026 Talk',

  groups: [
    {
      label: 'Overview',
      opened: true,
      fields: ['talk_title', 'session_title', 'clinical_stage', 'novelty_flag', 'talk_id'],
    },
    { label: 'Speaker', opened: true, fields: ['speaker'] },
    {
      label: 'Science',
      opened: true,
      fields: ['MOA_summary', 'targets', 'biomarkers', 'models', 'readouts', 'key_findings'],
    },
    {
      label: 'Clinical',
      opened: true,
      fields: ['clinical_data', 'tumor_types', 'combination_strategies'],
    },
    { label: 'Open / Risk', opened: true, fields: ['resistance_or_selectivity_notes', 'open_questions'] },
    { label: 'Follow-up', opened: true, fields: ['external_follow_up'] },
  ],

  fields: {
    // --- scalars ---
    talk_id: { label: 'Talk ID', type: 'scalar' },
    session_title: { label: 'Session', type: 'scalar' },
    talk_title: { label: 'Talk', type: 'scalar' },

    // --- enums (rendered as badges) ---
    clinical_stage: {
      label: 'Clinical stage',
      type: 'enum',
      badge: true,
      badgeTheme: (v) => {
        if (['phase_3', 'phase_2_3', 'approved'].includes(v)) return 'green'
        if (['phase_1', 'phase_1_2', 'phase_2', 'clinical_trial'].includes(v)) return 'blue'
        if (['preclinical', 'IND_enabling', 'early-stage'].includes(v)) return 'orange'
        return 'gray'
      },
    },
    novelty_flag: {
      label: 'Novelty',
      type: 'enum',
      badge: true,
      badgeTheme: (v) => {
        if (['first_in_class', 'best_in_class'].includes(v)) return 'green'
        if (['platform_technology', 'emerging_target'].includes(v)) return 'blue'
        if (v === 'negative_or_null_result') return 'red'
        return 'gray'
      },
    },

    // --- paragraph ---
    MOA_summary: { label: 'Mechanism of action', type: 'paragraph', emptyText: 'No MoA summary' },

    // --- list_scalar (chips) ---
    tumor_types: { label: 'Tumor types', type: 'list_scalar' },
    topic_categories: { label: 'Topic categories', type: 'list_scalar' },
    readouts: { label: 'Readouts', type: 'list_scalar' },
    key_findings: { label: 'Key findings', type: 'list_scalar' },
    resistance_or_selectivity_notes: { label: 'Resistance / selectivity notes', type: 'list_scalar' },
    open_questions: { label: 'Open questions', type: 'list_scalar' },

    // --- table_obj (compact tables; cols from verified key-sets) ---
    targets: {
      label: 'Targets',
      type: 'table_obj',
      cols: [
        { key: 'gene_or_protein', label: 'Gene / protein' },
        { key: 'modality', label: 'Modality' },
        { key: 'pathway', label: 'Pathway' },
        { key: 'alteration', label: 'Alteration' },
        { key: 'compound_name', label: 'Compound' },
        { key: 'target_novelty', label: 'Novelty' },
      ],
    },
    biomarkers: {
      label: 'Biomarkers',
      type: 'table_obj',
      cols: [
        { key: 'name', label: 'Name' },
        { key: 'type', label: 'Type' },
        { key: 'finding', label: 'Finding' },
        { key: 'assay', label: 'Assay' },
      ],
    },
    models: {
      label: 'Models',
      type: 'table_obj',
      cols: [
        { key: 'model_type', label: 'Model type' },
        { key: 'name', label: 'Name' },
        { key: 'genotype_or_key_features', label: 'Genotype / key features' },
      ],
    },
    clinical_data: {
      label: 'Clinical data',
      type: 'table_obj',
      cols: [
        { key: 'metric', label: 'Metric' },
        { key: 'value', label: 'Value' },
        { key: 'confidence_interval', label: '95% CI' },
        { key: 'n', label: 'n' },
        { key: 'population', label: 'Population' },
        { key: 'comparator', label: 'Comparator' },
        { key: 'maturity', label: 'Maturity' },
      ],
    },
    combination_strategies: {
      label: 'Combination strategies',
      type: 'table_obj',
      cols: [
        { key: 'with_agent', label: 'With agent' },
        { key: 'phenotype', label: 'Phenotype' },
        { key: 'rationale', label: 'Rationale' },
        { key: 'stage', label: 'Stage' },
      ],
    },

    // --- object (key/value grid) ---
    speaker: {
      label: 'Speaker',
      type: 'object',
      cols: [
        { key: 'name', label: 'Name' },
        { key: 'affiliation', label: 'Affiliation' },
        { key: 'role', label: 'Role' },
        { key: 'disclosures_noted', label: 'Disclosures noted' },
      ],
    },

    // --- object_of_lists (labelled chip rows, with deep links where possible) ---
    external_follow_up: {
      label: 'External follow-up',
      type: 'object_of_lists',
      order: ['nct_numbers', 'abstract_ids', 'cited_papers', 'company_or_sponsor', 'patent_or_ip_hints'],
      linkFor: (key, value) => {
        if (key === 'nct_numbers' && /^NCT\d+$/i.test(String(value)))
          return `https://clinicaltrials.gov/study/${value}`
        return null
      },
    },
  },
}
