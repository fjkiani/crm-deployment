<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
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
import { computed, watch } from 'vue'
import { createResource } from 'frappe-ui'
import IntelPanel from '@/components/intel/IntelPanel.vue'
import { gtmSchema } from '@/intel/schemas/gtm'
import { aacrIntelSchema } from '@/intel/schemas/aacr_intel'
import { aacr2026Schema } from '@/intel/schemas/aacr_2026'

// Props preserved exactly as Lead.vue passes them — no Lead.vue change required.
const props = defineProps({
  doc: { type: Object, required: true },
  leadId: { type: String, required: true },
})

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
