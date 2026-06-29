<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
    <!-- Header -->
    <div class="mx-4 my-3 flex items-center justify-between sm:mx-10 sm:mb-4 sm:mt-8">
      <div class="flex h-8 items-center text-xl font-semibold text-ink-gray-8">
        {{ __('GTM / Tracker Intel') }}
      </div>
      <a
        v-if="doc.prospect_ref"
        :href="`/app/lead-prospect/${doc.prospect_ref}`"
        target="_blank"
        class="text-xs font-medium text-ink-gray-5 underline hover:text-ink-gray-7"
      >
        {{ __('Source prospect') }}
      </a>
    </div>

    <!-- Score / Tier / Priority summary band -->
    <div v-if="hasSummary" class="mx-4 sm:mx-10">
      <div class="flex flex-wrap items-center gap-4 rounded-xl p-4" :class="scoreBgClass">
        <div
          class="flex flex-col items-center justify-center rounded-xl bg-white/90 px-4 py-2 shadow-sm"
        >
          <span class="text-3xl font-bold" :class="scoreTextClass">
            {{ score !== null ? score : '—' }}
          </span>
          <span class="text-xs font-medium uppercase text-ink-gray-5">{{ __('Score') }} / 10</span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-semibold text-ink-gray-9">{{ tierLabel }}</span>
          <div class="flex flex-wrap items-center gap-2 text-sm text-ink-gray-6">
            <span v-if="doc.tier" class="rounded-full px-2 py-0.5 text-xs font-medium" :class="tierBadgeClass">
              {{ doc.tier }}
            </span>
            <span v-if="doc.priority_rank">
              {{ __('Priority rank') }}: <span class="font-semibold text-ink-gray-8">#{{ doc.priority_rank }}</span>
            </span>
            <span v-if="doc.source_ref_id" class="text-ink-gray-5">
              · {{ doc.source_ref_id }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Narrative intel cards -->
    <div class="mx-4 mt-4 grid gap-3 sm:mx-10 sm:grid-cols-2">
      <div
        v-for="card in narrativeCards"
        :key="card.key"
        class="rounded-lg border border-surface-gray-3 bg-surface-white p-4"
        :class="{ 'sm:col-span-2': card.wide }"
      >
        <div class="text-xs font-medium uppercase text-ink-gray-4">
          {{ card.label }}
        </div>
        <div
          class="mt-1 whitespace-pre-wrap text-sm leading-relaxed"
          :class="card.value ? 'text-ink-gray-8' : 'italic text-ink-gray-4'"
        >
          {{ card.value || __('Not enriched yet') }}
        </div>
      </div>
    </div>

    <!-- Empty state: no GTM data at all -->
    <div
      v-if="!hasAnyData"
      class="flex flex-1 flex-col items-center justify-center gap-2 text-ink-gray-4"
    >
      <svg class="size-12 opacity-40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M3 3v18h18" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
        <path d="M7 15l3-3 3 3 4-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <span class="text-sm">{{ __('No GTM / tracker intel for this lead') }}</span>
      <span class="text-xs">{{ __('This lead was not imported from the tracker.') }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  doc: { type: Object, required: true },
  leadId: { type: String, required: true },
})

// lead_score is on a 0-10 scale (e.g. 9.5, 8.0) — distinct from NyxTab's 0-100 additional_data score.
const score = computed(() => {
  const v = props.doc.lead_score
  return v === null || v === undefined || v === '' ? null : Number(v)
})

const tierLabel = computed(() => {
  switch (props.doc.tier) {
    case 'Tier 1':
      return '🔥 Tier 1 — Top priority target'
    case 'Tier 2':
      return '🟡 Tier 2 — Strong fit'
    case 'Tier 3':
      return '❄️ Tier 3 — Nurture'
    default:
      return props.doc.tier || __('Unscored')
  }
})

const tierBadgeClass = computed(() => {
  switch (props.doc.tier) {
    case 'Tier 1':
      return 'bg-red-100 text-red-700'
    case 'Tier 2':
      return 'bg-yellow-100 text-yellow-700'
    case 'Tier 3':
      return 'bg-blue-100 text-blue-700'
    default:
      return 'bg-gray-100 text-gray-600'
  }
})

// Colour the summary band by tier (falls back to score thresholds when tier is blank).
const scoreBgClass = computed(() => {
  const t = props.doc.tier
  if (t === 'Tier 1' || (score.value !== null && score.value >= 8.5))
    return 'bg-gradient-to-r from-red-50 to-orange-50 border border-red-100'
  if (t === 'Tier 2' || (score.value !== null && score.value >= 6))
    return 'bg-gradient-to-r from-yellow-50 to-amber-50 border border-yellow-100'
  return 'bg-gradient-to-r from-blue-50 to-slate-50 border border-blue-100'
})

const scoreTextClass = computed(() => {
  const t = props.doc.tier
  if (t === 'Tier 1' || (score.value !== null && score.value >= 8.5)) return 'text-red-600'
  if (t === 'Tier 2' || (score.value !== null && score.value >= 6)) return 'text-yellow-600'
  return 'text-blue-600'
})

const hasSummary = computed(
  () => score.value !== null || !!props.doc.tier || !!props.doc.priority_rank || !!props.doc.source_ref_id,
)

const narrativeCards = computed(() => [
  { key: 'aacr_topic', label: __('AACR 2026 Topic'), value: props.doc.aacr_topic },
  { key: 'current_focus', label: __('Current Focus'), value: props.doc.current_focus },
  { key: 'pain_points', label: __('Pain Points'), value: props.doc.pain_points, wide: true },
  { key: 'crispro_fit', label: __('CrisPRO Fit'), value: props.doc.crispro_fit, wide: true },
  { key: 'fit_rationale', label: __('Fit Rationale'), value: props.doc.fit_rationale, wide: true },
])

const hasAnyData = computed(() => hasSummary.value || narrativeCards.value.some((c) => !!c.value))
</script>
