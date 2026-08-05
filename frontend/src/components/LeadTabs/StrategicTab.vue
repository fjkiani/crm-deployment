<template>
  <div class="flex flex-1 flex-col overflow-y-auto px-4 py-3 sm:px-10">
    <!-- Targeting approach header: one-line strategy + on-click actions -->
    <div class="mb-4 rounded-lg border border-ink-gray-2 bg-surface-white">
      <div class="flex items-center justify-between border-b border-ink-gray-2 px-4 py-2.5">
        <span class="text-sm font-semibold text-ink-gray-9">{{ __('Targeting approach') }}</span>
        <Button variant="subtle" :loading="loading" @click="load">
          <template #prefix><LucideRefreshCw class="h-3.5 w-3.5" /></template>
          {{ __('Refresh') }}
        </Button>
      </div>
      <div class="px-4 py-3">
        <p v-if="data.approach" class="text-sm text-ink-gray-8">{{ data.approach }}</p>
        <p v-else class="text-sm text-ink-gray-5">
          {{ __('No strategy yet — enrich this lead to generate the GTM narrative.') }}
        </p>
        <div class="mt-3 flex gap-2">
          <Button size="sm" variant="solid" @click="$emit('add-sequence')">
            {{ __('Add to sequence') }}
          </Button>
          <Button size="sm" variant="outline" @click="$emit('enrich')">
            {{ data.enriched ? __('Re-enrich') : __('Enrich') }}
          </Button>
        </div>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
      <Button class="ml-2" size="sm" variant="outline" @click="load">{{ __('Retry') }}</Button>
    </div>

    <template v-else>
    <!-- Score / tier band -->
    <div v-if="gtm.tier || gtm.lead_score != null" class="mb-4 rounded-lg border px-4 py-3"
         :class="bandClass">
      <div class="flex items-center justify-between">
        <span class="text-base font-semibold" :class="scoreTextClass">{{ tierLabel }}</span>
        <span v-if="gtm.lead_score != null" class="text-2xl font-bold" :class="scoreTextClass">
          {{ gtm.lead_score }}<span class="text-sm font-normal text-ink-gray-5">/10</span>
        </span>
      </div>
      <div class="mt-1 flex gap-4 text-xs text-ink-gray-6">
        <span v-if="gtm.priority_rank">#{{ gtm.priority_rank }} priority</span>
        <span v-if="gtm.source_ref_id">Ref {{ gtm.source_ref_id }}</span>
      </div>
    </div>

    <!-- GTM narrative cards -->
    <div v-if="data.enriched" class="space-y-3">
      <IntelCard :title="__('AACR 2026 Topic')" :text="gtm.aacr_topic" />
      <IntelCard :title="__('Current Focus')" :text="gtm.current_focus" />
      <IntelCard :title="__('Pain Points')" :text="gtm.pain_points" wide />
      <IntelCard :title="__('CrisPRO Fit')" :text="gtm.crispro_fit" wide />
      <IntelCard :title="__('Fit Rationale')" :text="gtm.fit_rationale" wide />
    </div>
    <div v-else class="rounded-lg border border-dashed border-ink-gray-3 px-4 py-8 text-center">
      <p class="text-sm text-ink-gray-5">{{ __('Not enriched yet.') }}</p>
      <Button class="mt-3" size="sm" variant="solid" @click="$emit('enrich')">
        {{ __('Enrich Lead') }}
      </Button>
    </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { Button, call } from 'frappe-ui'
import IntelCard from './IntelCard.vue'

const props = defineProps({
  leadId: { type: String, required: true },
})
defineEmits(['add-sequence', 'enrich'])

const loading = ref(false)
const error = ref('')
const data = ref({ ok: false, enriched: false, gtm: {}, approach: '' })
const gtm = computed(() => data.value.gtm || {})

const tierLabel = computed(() => {
  const t = gtm.value.tier
  if (t === 'Tier 1') return '🔥 Tier 1 — Top priority target'
  if (t === 'Tier 2') return '🟡 Tier 2 — Strong fit'
  if (t === 'Tier 3') return '❄️ Tier 3 — Nurture'
  return t || 'Unscored'
})
const bandClass = computed(() => {
  const t = gtm.value.tier, s = gtm.value.lead_score
  if (t === 'Tier 1' || (s != null && s >= 8.5)) return 'bg-red-50 border-red-100'
  if (t === 'Tier 2' || (s != null && s >= 6)) return 'bg-yellow-50 border-yellow-100'
  return 'bg-blue-50 border-blue-100'
})
const scoreTextClass = computed(() => {
  const t = gtm.value.tier, s = gtm.value.lead_score
  if (t === 'Tier 1' || (s != null && s >= 8.5)) return 'text-red-600'
  if (t === 'Tier 2' || (s != null && s >= 6)) return 'text-yellow-600'
  return 'text-blue-600'
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await call('crm.api.lead_tabs.get_tab_data', {
      lead: props.leadId,
      tab: 'strategic',
    })
    data.value = res || { ok: false, enriched: false, gtm: {} }
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || __('Failed to load strategy')
    data.value = { ok: false, enriched: false, gtm: {}, approach: '' }
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
