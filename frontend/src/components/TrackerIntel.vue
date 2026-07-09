<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
    <!-- NYX GTM action card: per-lead "best outreach move right now" reasoning,
         intel staleness, and human-in-loop actions. Reasoning WRITES NOTHING;
         the human reviews and chooses to draft outreach or re-sync intel. -->
    <div class="mx-4 mt-3 rounded-lg border border-ink-gray-2 bg-surface-white sm:mx-10">
      <div class="flex items-center justify-between gap-3 border-b border-ink-gray-2 px-4 py-2.5">
        <div class="flex items-center gap-2">
          <span class="text-sm font-semibold text-ink-gray-9">{{ __('Nyx — best move now') }}</span>
          <span
            v-if="reasoning && reasoning.llm_used === false"
            class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] font-medium text-ink-gray-6"
            :title="__('No AI model configured — showing a deterministic template recommendation.')"
          >{{ __('template') }}</span>
          <span
            v-else-if="reasoning && reasoning.llm_used"
            class="rounded bg-surface-green-2 px-1.5 py-0.5 text-[10px] font-medium text-ink-green-3"
            :title="reasoning.llm_provider || ''"
          >{{ __('AI') }}</span>
        </div>
        <div class="flex items-center gap-2">
          <!-- Staleness badge -->
          <span
            v-if="stale"
            class="inline-flex items-center gap-1 rounded bg-surface-amber-2 px-1.5 py-0.5 text-[10px] font-medium text-ink-amber-3"
            :title="staleTitle"
          >⚠ {{ staleLabel }}</span>
          <span
            v-else-if="reasoning && reasoning.staleness && reasoning.staleness.intel_synced_at"
            class="rounded bg-surface-green-2 px-1.5 py-0.5 text-[10px] font-medium text-ink-green-3"
            :title="staleTitle"
          >{{ __('fresh') }}</span>
          <Button variant="subtle" :loading="reasoningRes.loading" @click="loadReasoning">
            <template #prefix><LucideRefreshCw class="h-3.5 w-3.5" /></template>
            {{ reasoning ? __('Re-assess') : __('Assess') }}
          </Button>
        </div>
      </div>

      <div class="px-4 py-3">
        <div v-if="reasoningRes.loading && !reasoning" class="py-3 text-center text-sm text-ink-gray-5">{{ __('Nyx is assessing this lead…') }}</div>
        <div v-else-if="reasoningRes.error" class="py-3 text-center text-sm text-ink-red-4">{{ __('Could not assess this lead right now.') }}</div>
        <div v-else-if="reasoning && reasoning.ok" class="space-y-2.5">
          <div class="flex flex-wrap items-center gap-2">
            <span class="rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="actionClass(reasoning.reasoning.recommended_action)">{{ actionLabel(reasoning.reasoning.recommended_action) }}</span>
            <span class="rounded-full bg-surface-gray-2 px-2 py-0.5 text-[11px] font-medium text-ink-gray-7">{{ __('Urgency') }}: {{ urgencyLabel(reasoning.reasoning.urgency) }}</span>
          </div>
          <p v-if="reasoning.reasoning.angle" class="text-sm text-ink-gray-8"><span class="font-medium text-ink-gray-6">{{ __('Angle') }}: </span>{{ reasoning.reasoning.angle }}</p>
          <p v-if="reasoning.reasoning.subject" class="text-xs text-ink-gray-6"><span class="font-medium">{{ __('Subject') }}: </span>{{ reasoning.reasoning.subject }}</p>
          <ul v-if="reasoning.reasoning.talking_points?.length" class="ml-4 list-disc space-y-0.5 text-xs text-ink-gray-7">
            <li v-for="(t, i) in reasoning.reasoning.talking_points" :key="i">{{ t }}</li>
          </ul>
          <p v-if="reasoning.reasoning.rationale" class="text-xs italic text-ink-gray-5">{{ reasoning.reasoning.rationale }}</p>

          <div class="flex flex-wrap gap-2 pt-1">
            <Button variant="solid" @click="draftOutreach">
              <template #prefix><LucideMailPlus class="h-3.5 w-3.5" /></template>
              {{ __('Draft outreach') }}
            </Button>
            <Button
              v-if="reasoning.lead?.has_intel"
              variant="subtle"
              :loading="syncRes.loading"
              @click="previewSync"
            >
              <template #prefix><LucideRefreshCw class="h-3.5 w-3.5" /></template>
              {{ __('Re-sync GTM from intel') }}
            </Button>
          </div>

          <!-- Human-in-loop re-sync preview: show recomputed score/tier BEFORE applying. -->
          <div v-if="syncPreview" class="mt-1 rounded-md border border-ink-blue-2 bg-surface-blue-1 px-3 py-2 text-xs">
            <div class="mb-1 font-medium text-ink-blue-6">{{ __('Re-sync preview (nothing saved yet)') }}</div>
            <div class="text-ink-gray-7">
              {{ __('Score') }}: <span class="font-semibold">{{ fmt(doc.lead_score) }}</span> → <span class="font-semibold text-ink-blue-6">{{ fmt(syncPreview.lead_score) }}</span>
              &nbsp;·&nbsp; {{ __('Tier') }}: <span class="font-semibold">{{ doc.tier || '—' }}</span> → <span class="font-semibold text-ink-blue-6">{{ syncPreview.tier || '—' }}</span>
            </div>
            <div class="mt-2 flex gap-2">
              <Button variant="solid" size="sm" :loading="applyRes.loading" @click="applySync">{{ __('Apply') }}</Button>
              <Button variant="subtle" size="sm" @click="syncPreview = null">{{ __('Discard') }}</Button>
            </div>
          </div>
        </div>
        <div v-else class="py-3 text-center text-sm text-ink-gray-4">{{ __('Click "Assess" for Nyx\'s recommended outreach move.') }}</div>
      </div>
    </div>

    <!-- GTM intel: the original tracker fields, now rendered from gtmSchema config. -->
    <IntelPanel :schema="gtmSchema" :record="doc" :empty-text="__('No GTM / tracker intel for this lead')" />

    <!-- Competitive intel (Schema B): CrisPRO opportunities first, then the
         "beatable" evidence + competitor/watchlist signal. Only shown when this
         lead's source_ref_id resolves to an AACR Intel record. -->
    <template v-if="intel">
      <div class="mx-4 mt-2 border-t border-surface-gray-3 sm:mx-10" />
      <IntelPanel :schema="aacrIntelSchema" :record="intel" :empty-text="__('No competitive intel for this talk')" />
    </template>

    <!-- Linked AACR 2026 talk detail (all 19 fields), rendered in the same GTM tab.
         Only shown when this lead links to an AACR Talk via source_ref_id. -->
    <template v-if="talk">
      <div class="mx-4 mt-2 border-t border-surface-gray-3 sm:mx-10" />
      <IntelPanel :schema="aacr2026Schema" :record="talk" :empty-text="__('No AACR talk detail recorded')" />
    </template>
  </div>
</template>

<script setup>
import { computed, watch, ref } from 'vue'
import { createResource, Button, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'
import LucideRefreshCw from '~icons/lucide/refresh-cw'
import LucideMailPlus from '~icons/lucide/mail-plus'
import IntelPanel from '@/components/intel/IntelPanel.vue'
import { gtmSchema } from '@/intel/schemas/gtm'
import { aacrIntelSchema } from '@/intel/schemas/aacr_intel'
import { aacr2026Schema } from '@/intel/schemas/aacr_2026'

// Props preserved exactly as Lead.vue passes them — no Lead.vue change required.
const props = defineProps({
  doc: { type: Object, required: true },
  leadId: { type: String, required: true },
})

const router = useRouter()

// ---- Nyx GTM reasoning (best outreach move now). WRITES NOTHING. ----
const reasoningRes = createResource({
  url: 'crm.api.nyx_campaigns.gtm_outreach_reasoning',
  makeParams: () => ({ lead_name: props.leadId }),
})
const reasoning = computed(() => reasoningRes.data || null)
function loadReasoning() {
  if (props.leadId) reasoningRes.fetch()
}
// Reset reasoning when switching leads (avoid showing a stale card).
watch(() => props.leadId, () => { reasoningRes.reset(); syncPreview.value = null }, {})

// ---- Staleness (from the reasoning payload) ----
const stale = computed(() => !!reasoning.value?.staleness?.stale)
const staleLabel = computed(() => {
  const d = reasoning.value?.staleness?.intel_age_days
  if (d == null) return __('never synced')
  return __('intel {0}d old', [d])
})
const staleTitle = computed(() => {
  const s = reasoning.value?.staleness
  if (!s) return ''
  if (!s.intel_synced_at) return __('GTM intel has never been synced for this lead.')
  return __('Intel last synced {0} (threshold {1}d).', [String(s.intel_synced_at).slice(0, 10), s.threshold_days])
})

// ---- Human-in-loop: re-sync GTM from intel (preview -> apply) ----
const syncPreview = ref(null)
const syncRes = createResource({
  url: 'crm.api.intel_bridge.synthesize_gtm_from_intel',
  onSuccess(d) {
    if (d?.status === 'synthesized') syncPreview.value = d
    else toast.error(__('Nothing to re-sync: {0}', [d?.reason || __('no intel')]))
  },
  onError() { toast.error(__('Re-sync preview failed.')) },
})
function previewSync() {
  syncPreview.value = null
  syncRes.submit({ lead_name: props.leadId, commit: 0 })
}
const applyRes = createResource({
  url: 'crm.api.intel_bridge.synthesize_gtm_from_intel',
  onSuccess() {
    toast.success(__('GTM intel re-synced. Reload the lead to see updated fields.'))
    syncPreview.value = null
    reasoningRes.fetch()
  },
  onError() { toast.error(__('Re-sync failed.')) },
})
function applySync() {
  applyRes.submit({ lead_name: props.leadId, commit: 1 })
}

// ---- Draft outreach: hand off to the Nyx outreach tab (LLM drafting seam) ----
function draftOutreach() {
  router.push({ name: 'Lead', params: { leadId: props.leadId }, hash: '#nyx' })
}

// ---- Label / class helpers ----
function fmt(v) { return v == null ? '—' : Number(v).toFixed(1) }
function actionLabel(a) {
  return {
    send_first_touch: __('Send first touch'),
    follow_up: __('Follow up'),
    re_engage: __('Re-engage'),
    nurture: __('Nurture'),
    hold: __('Hold'),
  }[a] || (a || __('Nurture'))
}
function actionClass(a) {
  if (a === 'send_first_touch' || a === 'follow_up') return 'bg-surface-green-2 text-ink-green-3'
  if (a === 're_engage') return 'bg-surface-amber-2 text-ink-amber-3'
  if (a === 'hold') return 'bg-surface-gray-2 text-ink-gray-6'
  return 'bg-surface-blue-2 text-ink-blue-6'
}
function urgencyLabel(u) {
  return { now: __('Now'), this_week: __('This week'), this_month: __('This month'), low: __('Low') }[u] || (u || __('Low'))
}

// The AACR Talk (if any) linked to this lead. A talk's talk_id is stored on the
// lead as source_ref_id during ingest/promotion, so that's the lookup key.
// get_aacr_talk returns the nested data-contract record the IntelPanel expects
// (assembled server-side from the AACR Talk doctype + its child tables), or null.
const talkResource = createResource({
  url: 'crm.fcrm.doctype.aacr_talk.aacr_talk.get_aacr_talk',
  makeParams: () => ({ talk_id: props.doc?.source_ref_id }),
})

// The competitive-intel record (Schema B), keyed by the same source_ref_id.
// get_aacr_intel returns the assembled competitive-intel contract (opportunities,
// vulnerabilities, moat weaknesses, trial risks, competitors, watchlists) or null
// when this talk has no competitive intel (e.g. award lectures / symposia).
const intelResource = createResource({
  url: 'crm.fcrm.doctype.aacr_intel.aacr_intel.get_aacr_intel',
  makeParams: () => ({ talk_id: props.doc?.source_ref_id }),
})

function fetchLinked() {
  const ref = props.doc?.source_ref_id
  if (ref) {
    talkResource.fetch()
    intelResource.fetch()
  } else {
    talkResource.reset()
    intelResource.reset()
  }
}

// Fetch on mount and whenever the linked ref changes (e.g. switching leads).
watch(
  () => props.doc?.source_ref_id,
  () => fetchLinked(),
  { immediate: true },
)

const talk = computed(() => talkResource.data || null)
const intel = computed(() => intelResource.data || null)
</script>
