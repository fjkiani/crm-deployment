<template>
  <!-- slide-over drawer -->
  <div class="fixed inset-0 z-40 flex justify-end" @click.self="$emit('close')">
    <div class="absolute inset-0 bg-black/30"></div>
    <div class="relative z-50 flex h-full w-full max-w-xl flex-col overflow-hidden bg-surface-white shadow-xl">
      <!-- header -->
      <div class="flex items-start justify-between gap-3 border-b px-5 py-4">
        <div class="min-w-0">
          <div class="text-[11px] font-medium uppercase tracking-wide text-ink-gray-5">{{ __('Abstract') }}</div>
          <h2 class="mt-0.5 text-base font-semibold leading-snug text-ink-gray-9">
            {{ det?.talk_title || talkName }}
          </h2>
          <p v-if="det?.speaker_name" class="mt-1 text-sm text-ink-gray-6">
            {{ det.speaker_name }}<span v-if="det.speaker_affiliation"> · {{ det.speaker_affiliation }}</span>
          </p>
        </div>
        <button class="rounded p-1 text-ink-gray-5 hover:bg-surface-gray-2" @click="$emit('close')">
          <LucideX class="h-4 w-4" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto px-5 py-4">
        <div v-if="resource.loading" class="py-16 text-center text-ink-gray-5">{{ __('Loading abstract…') }}</div>

        <template v-else-if="det && det.found">
          <!-- badges -->
          <div class="mb-4 flex flex-wrap gap-1.5">
            <span v-if="det.clinical_stage" class="rounded bg-surface-blue-2 px-2 py-0.5 text-xs text-ink-blue-7">
              {{ (det.clinical_stage || '').replace(/_/g, ' ') }}
            </span>
            <span v-if="det.novelty_flag" class="rounded bg-surface-green-2 px-2 py-0.5 text-xs text-ink-green-7">
              {{ (det.novelty_flag || '').replace(/_/g, ' ') }}
            </span>
            <span v-for="a in det.crispro_axes || []" :key="a"
                  class="rounded bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-7">{{ a }}</span>
          </div>

          <!-- linked lead callout -->
          <div v-if="det.lead" class="mb-4 rounded-lg border border-ink-blue-3 bg-surface-blue-1 px-3 py-2">
            <div class="flex items-center justify-between">
              <div>
                <div class="text-xs uppercase text-ink-blue-6">{{ __('Linked lead') }}</div>
                <button class="text-sm font-medium text-ink-blue-7 hover:underline"
                        @click="$emit('open-lead', det.lead.name)">
                  {{ det.lead.lead_name || det.lead.name }}
                </button>
                <span v-if="det.lead.organization" class="ml-1 text-xs text-ink-gray-6">· {{ det.lead.organization }}</span>
              </div>
              <div class="text-right text-xs text-ink-gray-6">
                <div v-if="det.lead.tier">{{ det.lead.tier }}</div>
                <div v-if="det.lead.email">{{ det.lead.email }}</div>
                <div v-else class="text-ink-amber-6">{{ __('no email') }}</div>
              </div>
            </div>
          </div>

          <!-- MOA -->
          <div v-if="det.moa_summary" class="mb-4">
            <div class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Mechanism of Action') }}</div>
            <p class="text-sm leading-relaxed text-ink-gray-7">{{ det.moa_summary }}</p>
          </div>

          <!-- key findings -->
          <div v-if="kf.length" class="mb-4">
            <div class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Key Findings') }}</div>
            <ul class="list-disc space-y-1.5 pl-4 text-sm leading-relaxed text-ink-gray-7">
              <li v-for="(k, i) in kf" :key="i">{{ k }}</li>
            </ul>
          </div>

          <!-- targets & biomarkers -->
          <div class="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div v-if="det.targets && det.targets.length">
              <div class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Targets') }}</div>
              <div class="flex flex-wrap gap-1">
                <span v-for="(t, i) in det.targets" :key="i"
                      class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-7">{{ t }}</span>
              </div>
            </div>
            <div v-if="det.biomarkers && det.biomarkers.length">
              <div class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Biomarkers') }}</div>
              <div class="flex flex-wrap gap-1">
                <span v-for="(b, i) in det.biomarkers" :key="i"
                      class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-7">{{ b }}</span>
              </div>
            </div>
          </div>

          <!-- tumor types -->
          <div v-if="enr.tumor_types && enr.tumor_types.length" class="mb-4">
            <div class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Tumor Types') }}</div>
            <div class="flex flex-wrap gap-1">
              <span v-for="(t, i) in enr.tumor_types" :key="i"
                    class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-7">{{ t }}</span>
            </div>
          </div>

          <!-- open questions (the outreach hooks) -->
          <div v-if="oq.length" class="mb-4">
            <div class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Open Questions') }}</div>
            <ul class="list-disc space-y-1.5 pl-4 text-sm leading-relaxed text-ink-gray-7">
              <li v-for="(q, i) in oq" :key="i">{{ q }}</li>
            </ul>
          </div>

          <!-- readouts -->
          <div v-if="enr.readouts && enr.readouts.length" class="mb-4">
            <div class="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink-gray-5">{{ __('Readouts / Methods') }}</div>
            <div class="flex flex-wrap gap-1">
              <span v-for="(r, i) in enr.readouts" :key="i"
                    class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-7">{{ r }}</span>
            </div>
          </div>
        </template>

        <div v-else class="py-16 text-center text-ink-gray-5">{{ __('Abstract not found.') }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { createResource } from 'frappe-ui'

const props = defineProps({ talkName: { type: String, required: true } })
defineEmits(['close', 'open-lead'])

const resource = createResource({
  url: 'crm.api.session_nav.talk_detail',
  makeParams: () => ({ talk_name: props.talkName }),
})
watch(() => props.talkName, () => { if (props.talkName) resource.fetch() }, { immediate: true })

const det = computed(() => resource.data || null)
const enr = computed(() => det.value?.enrichment || {})
const kf = computed(() => enr.value.key_findings || [])
const oq = computed(() => enr.value.open_questions || [])
</script>
