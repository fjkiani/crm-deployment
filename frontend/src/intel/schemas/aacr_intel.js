// AACR competitive-intel schema — field-schema descriptor for the Schema-B
// competitive-intelligence layer (929-doc corpus). Written against the exact
// output of crm.fcrm.doctype.aacr_intel.aacr_intel.get_aacr_intel / _assemble.
//
// OPPORTUNITY-FIRST: the CrisPRO opportunities are the actionable GTM payload, so
// they lead. Vulnerabilities / moat weaknesses / trial risks follow (the "why they
// are beatable" evidence), then the competitor + watchlist signal lists.
//
// Field types map onto the generic IntelPanel renderer registry:
//   table_obj       -> compact tables (the 5 dict-arrays)
//   list_scalar     -> chip rows (the 7 watch string-arrays)
//   scalar / enum   -> single values / badges (parent meta)

export const aacrIntelSchema = {
  schema_key: 'aacr_intel',
  title: 'Competitive Intel',

  groups: [
    {
      label: 'CrisPRO Opportunities',
      opened: true,
      fields: ['crispro_opportunity'],
    },
    {
      label: 'Why they are beatable',
      opened: true,
      fields: ['vulnerability_identified', 'competitive_moat_weakness', 'trial_dilution_risk'],
    },
    {
      label: 'Competitors cited',
      opened: true,
      fields: ['cited_competitors'],
    },
    {
      label: 'Watchlist signals',
      opened: false,
      fields: [
        'companies_to_monitor', 'assets_to_track', 'key_data_gaps',
        'unresolved_questions', 'cognitive_dissonance', 'rhetorical_signals', 'nct_candidates',
      ],
    },
    {
      label: 'Talk context',
      opened: false,
      fields: [
        'talk_title', 'session_title', 'speaker_name', 'institution',
        'presentation_type', 'data_maturity', 'sample_size_adequacy', 'follow_up_adequacy',
      ],
    },
  ],

  fields: {
    // --- the actionable payload: CrisPRO opportunities (opportunity-first) ---
    crispro_opportunity: {
      label: 'CrisPRO opportunities',
      type: 'table_obj',
      cols: [
        { key: 'priority', label: 'Priority' },
        { key: 'opportunity_type', label: 'Type' },
        { key: 'description', label: 'Opportunity' },
        { key: 'crispro_angle', label: 'CrisPRO angle' },
        { key: 'transcript_evidence', label: 'Evidence' },
        { key: 'external_validation_needed', label: 'External validation' },
      ],
    },

    // --- the "beatable" evidence ---
    vulnerability_identified: {
      label: 'Vulnerabilities',
      type: 'table_obj',
      cols: [
        { key: 'failure_type', label: 'Failure type' },
        { key: 'evidence_strength', label: 'Evidence strength' },
        { key: 'failing_compound_or_target', label: 'Failing compound / target' },
        { key: 'mechanistic_blindspot', label: 'Mechanistic blindspot' },
        { key: 'hidden_tox_signal', label: 'Hidden tox signal' },
        { key: 'ghost_responder_admission', label: 'Ghost-responder admission' },
        { key: 'unexplained_resistance_quote', label: 'Unexplained resistance' },
      ],
    },
    competitive_moat_weakness: {
      label: 'Moat weaknesses',
      type: 'table_obj',
      cols: [
        { key: 'vulnerable_ip_or_chemistry', label: 'Vulnerable IP / chemistry' },
        { key: 'ip_vulnerability_note', label: 'IP vulnerability note' },
        { key: 'clinical_strategy_weakness', label: 'Clinical strategy weakness' },
        { key: 'scale_or_manufacturing_bottleneck', label: 'Scale / manufacturing bottleneck' },
      ],
    },
    trial_dilution_risk: {
      label: 'Trial dilution risks',
      type: 'table_obj',
      cols: [
        { key: 'severity', label: 'Severity' },
        { key: 'target_biology', label: 'Target biology' },
        { key: 'missing_biomarker', label: 'Missing biomarker' },
        { key: 'trial_name_or_nct', label: 'Trial / NCT' },
        { key: 'statistical_concern', label: 'Statistical concern' },
        { key: 'flawed_enrollment_criteria', label: 'Flawed enrollment criteria' },
        { key: 'static_vs_dynamic_failure', label: 'Static-vs-dynamic failure' },
      ],
    },

    // --- competitors cited (name re-keyed from name1 server-side) ---
    cited_competitors: {
      label: 'Competitors cited',
      type: 'table_obj',
      cols: [
        { key: 'name', label: 'Competitor' },
        { key: 'context', label: 'Context' },
        { key: 'sentiment', label: 'Sentiment' },
      ],
    },

    // --- watchlist string-arrays (chips) ---
    companies_to_monitor: { label: 'Companies to monitor', type: 'list_scalar' },
    assets_to_track: { label: 'Assets to track', type: 'list_scalar' },
    key_data_gaps: { label: 'Key data gaps', type: 'list_scalar' },
    unresolved_questions: { label: 'Unresolved questions', type: 'list_scalar' },
    cognitive_dissonance: { label: 'Cognitive dissonance', type: 'list_scalar' },
    rhetorical_signals: { label: 'Rhetorical signals', type: 'list_scalar' },
    nct_candidates: { label: 'NCT candidates', type: 'list_scalar' },

    // --- parent context (scalars + enums) ---
    talk_title: { label: 'Talk', type: 'scalar' },
    session_title: { label: 'Session', type: 'scalar' },
    speaker_name: { label: 'Speaker', type: 'scalar' },
    institution: { label: 'Institution', type: 'scalar' },
    presentation_type: { label: 'Presentation type', type: 'scalar' },
    data_maturity: {
      label: 'Data maturity',
      type: 'enum',
      badge: true,
      badgeTheme: (v) => {
        if (['mature', 'clinical', 'phase_3'].includes(v)) return 'green'
        if (['preliminary', 'preclinical_only', 'pilot_only'].includes(v)) return 'orange'
        return 'gray'
      },
    },
    sample_size_adequacy: {
      label: 'Sample size adequacy',
      type: 'enum',
      badge: true,
      badgeTheme: (v) => {
        if (v === 'adequately_powered') return 'green'
        if (['underpowered', 'pilot_only'].includes(v)) return 'orange'
        if (v === 'not_applicable') return 'gray'
        return 'gray'
      },
    },
    follow_up_adequacy: { label: 'Follow-up adequacy', type: 'scalar' },
  },
}
