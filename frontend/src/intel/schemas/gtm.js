// GTM schema — the field-schema descriptor that reproduces the original
// TrackerIntel GTM tab as a *configuration* of the generic IntelPanel.
// Reads the dedicated GTM fields straight off the CRM Lead `doc`.
//
// This is intentionally a faithful port of the hand-written TrackerIntel.vue:
// same 0-10 score band, same tier emoji headlines, same gradient colours, same
// five narrative cards in the same order. The difference is that all of it now
// lives in config, not in component code.

export const gtmSchema = {
  schema_key: 'gtm',
  title: 'GTM / Tracker Intel',

  // "Source prospect" link, shown in the panel header when prospect_ref is set.
  sourceLink: {
    label: 'Source prospect',
    href: (doc) => (doc.prospect_ref ? `/app/lead-prospect/${doc.prospect_ref}` : null),
  },

  // Score / tier / priority summary band (0-10 scale, distinct from Nyx's 0-100).
  score: {
    field: 'lead_score',
    scale: [0, 10],
    tierField: 'tier',
    tierLabel: (tier) => {
      switch (tier) {
        case 'Tier 1':
          return '🔥 Tier 1 — Top priority target'
        case 'Tier 2':
          return '🟡 Tier 2 — Strong fit'
        case 'Tier 3':
          return '❄️ Tier 3 — Nurture'
        default:
          return tier || 'Unscored'
      }
    },
    tierBadgeTheme: (tier) => {
      switch (tier) {
        case 'Tier 1':
          return 'bg-red-100 text-red-700'
        case 'Tier 2':
          return 'bg-yellow-100 text-yellow-700'
        case 'Tier 3':
          return 'bg-blue-100 text-blue-700'
        default:
          return 'bg-gray-100 text-gray-600'
      }
    },
    bandClass: (tier, score) => {
      if (tier === 'Tier 1' || (score !== null && score >= 8.5))
        return 'bg-gradient-to-r from-red-50 to-orange-50 border border-red-100'
      if (tier === 'Tier 2' || (score !== null && score >= 6))
        return 'bg-gradient-to-r from-yellow-50 to-amber-50 border border-yellow-100'
      return 'bg-gradient-to-r from-blue-50 to-slate-50 border border-blue-100'
    },
    scoreTextClass: (tier, score) => {
      if (tier === 'Tier 1' || (score !== null && score >= 8.5)) return 'text-red-600'
      if (tier === 'Tier 2' || (score !== null && score >= 6)) return 'text-yellow-600'
      return 'text-blue-600'
    },
    meta: [
      { label: 'Priority rank', field: 'priority_rank', prefix: '#' },
      { label: 'Ref', field: 'source_ref_id' },
    ],
  },

  groups: [
    {
      label: 'GTM narrative',
      opened: true,
      fields: ['aacr_topic', 'current_focus', 'pain_points', 'crispro_fit', 'fit_rationale'],
    },
  ],

  fields: {
    aacr_topic: { label: 'AACR 2026 Topic', type: 'paragraph', emptyText: 'Not enriched yet' },
    current_focus: { label: 'Current Focus', type: 'paragraph', emptyText: 'Not enriched yet' },
    pain_points: { label: 'Pain Points', type: 'paragraph', emptyText: 'Not enriched yet', wide: true },
    crispro_fit: { label: 'CrisPRO Fit', type: 'paragraph', emptyText: 'Not enriched yet', wide: true },
    fit_rationale: { label: 'Fit Rationale', type: 'paragraph', emptyText: 'Not enriched yet', wide: true },
  },
}
