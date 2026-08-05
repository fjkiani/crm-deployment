<template>
  <div class="flex flex-1 flex-col overflow-y-auto px-4 py-3 sm:px-10">
    <!-- Cockpit header -->
    <div class="mb-4 rounded-lg border border-ink-gray-2 bg-surface-white">
      <div class="flex items-center justify-between border-b border-ink-gray-2 px-4 py-2.5">
        <span class="text-sm font-semibold text-ink-gray-9">{{ __('Co-Pilot cockpit') }}</span>
        <Button variant="subtle" :loading="loading" @click="load">
          <template #prefix><LucideRefreshCw class="h-3.5 w-3.5" /></template>
          {{ __('Refresh') }}
        </Button>
      </div>
      <div class="px-4 py-3">
        <p class="text-sm text-ink-gray-8">
          {{ __('One-glance state across every tab. Click a card to jump straight to it.') }}
        </p>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
      <Button class="ml-2" size="sm" variant="outline" @click="load">{{ __('Retry') }}</Button>
    </div>

    <template v-else>
      <!-- Cockpit cards -->
      <div class="mb-4 grid grid-cols-2 gap-3">
        <button type="button"
                class="rounded-lg border border-ink-gray-2 bg-surface-white px-4 py-3 text-left hover:border-ink-gray-4"
                @click="$emit('change-tab', 'strategic')">
          <div class="text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Strategic') }}</div>
          <div class="mt-1 text-sm font-medium text-ink-gray-9">
            {{ strategic.enriched ? (strategic.gtm?.tier || __('Enriched')) : __('Not enriched') }}
          </div>
          <div v-if="strategic.gtm && strategic.gtm.lead_score != null" class="text-xs text-ink-gray-6">
            {{ __('Score') }} {{ strategic.gtm.lead_score }}/10
          </div>
        </button>

        <button type="button"
                class="rounded-lg border border-ink-gray-2 bg-surface-white px-4 py-3 text-left hover:border-ink-gray-4"
                @click="$emit('change-tab', 'outreach')">
          <div class="text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Outreach') }}</div>
          <div class="mt-1 text-sm font-medium text-ink-gray-9">
            {{ data.outreach_summary?.draft_count || 0 }} {{ __('drafts') }}
          </div>
          <div class="text-xs text-ink-gray-6">
            {{ data.outreach_summary?.sequence_count || 0 }} {{ __('sequences') }}
          </div>
        </button>

        <button type="button"
                class="rounded-lg border border-ink-gray-2 bg-surface-white px-4 py-3 text-left hover:border-ink-gray-4"
                @click="$emit('change-tab', 'engagement')">
          <div class="text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Engagement') }}</div>
          <div class="mt-1 text-sm font-medium text-ink-gray-9">
            {{ data.engagement_summary?.nurture_state === 'engaged' ? __('Engaged') : __('Cold') }}
          </div>
          <div class="text-xs text-ink-gray-6">
            {{ data.engagement_summary?.open_task_count || 0 }} {{ __('open tasks') }}
          </div>
        </button>

        <button type="button"
                class="rounded-lg border border-ink-gray-2 bg-surface-white px-4 py-3 text-left hover:border-ink-gray-4"
                @click="$emit('change-tab', 'decisionmakers')">
          <div class="text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Decision makers') }}</div>
          <div class="mt-1 text-sm font-medium text-ink-gray-9">
            {{ data.decision_maker_count || 0 }} {{ __('mapped') }}
          </div>
        </button>
      </div>

      <!-- Next best action (navigational drafts only — no writes) -->
      <div class="mb-4">
        <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
          {{ __('Next best action') }}
        </div>
        <div v-if="nextActions.length" class="space-y-2">
          <div v-for="(a, i) in nextActions" :key="i"
               class="flex items-center justify-between rounded-lg border border-ink-gray-2 bg-surface-white px-4 py-3">
            <span class="text-sm text-ink-gray-8">{{ a.label }}</span>
            <Button size="sm" variant="outline" @click="$emit('change-tab', a.tab)">{{ a.cta }}</Button>
          </div>
        </div>
        <p v-else class="text-sm text-ink-gray-5">{{ __('This lead is in good shape — no obvious next step.') }}</p>
      </div>

      <!-- Agent surface -->
      <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
        {{ __('Nyx agent') }}
      </div>
      <div class="rounded-lg border border-ink-gray-2 bg-surface-white">
        <NyxTab :doc="doc" :leadId="leadId" @open-model-settings="$emit('open-model-settings')" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Button, call } from 'frappe-ui'
import NyxTab from '@/components/NyxTab.vue'

const props = defineProps({
  leadId: { type: String, required: true },
  doc: { type: Object, default: () => ({}) },
})
defineEmits(['change-tab', 'open-model-settings'])

const loading = ref(false)
const error = ref('')
const data = ref({ ok: false, strategic: {}, outreach_summary: {}, engagement_summary: {}, decision_maker_count: 0 })
const strategic = computed(() => data.value.strategic || {})

const nextActions = computed(() => {
  const out = []
  const s = strategic.value
  const o = data.value.outreach_summary || {}
  const e = data.value.engagement_summary || {}
  if (!s.enriched) {
    out.push({ label: __('Lead is not enriched — generate the GTM narrative first.'), cta: __('Go to Strategic'), tab: 'strategic' })
  }
  if ((o.draft_count || 0) > 0) {
    out.push({ label: __('You have ') + o.draft_count + __(' draft(s) awaiting review.'), cta: __('Review drafts'), tab: 'outreach' })
  } else if (s.enriched && (o.sequence_count || 0) === 0) {
    out.push({ label: __('Enriched but no outreach in flight — draft a first touch.'), cta: __('Go to Outreach'), tab: 'outreach' })
  }
  if ((data.value.decision_maker_count || 0) === 0) {
    out.push({ label: __('No decision makers mapped — map the buying committee.'), cta: __('Go to Decision Makers'), tab: 'decisionmakers' })
  }
  if ((e.open_task_count || 0) === 0) {
    out.push({ label: __('No open tasks — schedule a follow-up.'), cta: __('Go to Engagement'), tab: 'engagement' })
  }
  return out
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await call('crm.api.lead_tabs.get_tab_data', {
      lead: props.leadId,
      tab: 'copilot',
    })
    data.value = res || { ok: false, strategic: {}, outreach_summary: {}, engagement_summary: {}, decision_maker_count: 0 }
  } catch (err) {
    error.value = err?.messages?.[0] || err?.message || __('Failed to load co-pilot')
    data.value = { ok: false, strategic: {}, outreach_summary: {}, engagement_summary: {}, decision_maker_count: 0 }
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
