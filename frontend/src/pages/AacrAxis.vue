<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <header class="border-b px-6 py-4">
      <button class="mb-1 inline-flex items-center gap-1 text-xs text-ink-gray-5 hover:text-ink-gray-8" @click="back">
        <LucideChevronLeft class="h-3.5 w-3.5" /> {{ __('Intelligence dashboard') }}
      </button>
      <h1 class="text-xl font-semibold text-ink-gray-9">{{ prettyAxis(axis) }}</h1>
      <p v-if="data" class="text-sm text-ink-gray-5">
        {{ data.n }} {{ __('talks') }} · {{ data.n_leads }} {{ __('linked leads') }}
      </p>
    </header>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <div v-if="res.loading" class="py-16 text-center text-ink-gray-5">{{ __('Loading axis talks…') }}</div>
      <div v-else-if="!talks.length" class="py-16 text-center text-ink-gray-5">{{ __('No talks mapped to this axis.') }}</div>
      <div v-else class="overflow-hidden rounded-xl border border-surface-gray-3">
        <table class="w-full text-sm">
          <thead class="bg-surface-gray-1 text-left text-xs uppercase text-ink-gray-5">
            <tr>
              <th class="px-4 py-2">{{ __('Talk') }}</th>
              <th class="px-4 py-2">{{ __('Speaker') }}</th>
              <th class="px-4 py-2">{{ __('Session') }}</th>
              <th class="px-4 py-2">{{ __('Stage') }}</th>
              <th class="px-4 py-2">{{ __('Lead') }}</th>
              <th class="px-4 py-2">{{ __('Tier') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in talks" :key="t.talk_id" class="border-t border-surface-gray-2 hover:bg-surface-gray-1">
              <td class="max-w-sm px-4 py-2">
                <button class="truncate text-left text-ink-gray-8 hover:text-ink-blue-6" :title="t.talk_title"
                        @click="openTalk(t)">
                  {{ t.talk_title || t.talk_id }}
                </button>
              </td>
              <td class="px-4 py-2 text-ink-gray-7">{{ t.speaker_name || '—' }}</td>
              <td class="max-w-[12rem] px-4 py-2">
                <button class="truncate text-left text-xs text-ink-gray-5 hover:text-ink-blue-6"
                        :title="t.session_title" @click="openSession(t.session_title)">
                  {{ prettyAxis(t.session_title) }}
                </button>
              </td>
              <td class="px-4 py-2 text-xs text-ink-gray-6">{{ (t.clinical_stage || '').replace(/_/g, ' ') || '—' }}</td>
              <td class="px-4 py-2">
                <button v-if="t.lead_name" class="text-ink-blue-6 hover:underline" @click="openLead(t.lead_name)">
                  {{ t.lead_person || t.lead_name }}
                </button>
                <span v-else class="text-ink-gray-4">—</span>
              </td>
              <td class="px-4 py-2">
                <span v-if="t.tier" class="rounded px-1.5 py-0.5 text-xs" :class="tierClass(t.tier)">{{ t.tier }}</span>
                <span v-else class="text-ink-gray-4">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- abstract detail drawer -->
    <AacrTalkDetail v-if="openTalkName" :talk-name="openTalkName" @close="openTalkName = null" @open-lead="openLead" />
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { createResource } from 'frappe-ui'
import { useRouter } from 'vue-router'
import AacrTalkDetail from '@/components/aacr/AacrTalkDetail.vue'

const props = defineProps({ axis: { type: String, required: true } })
const router = useRouter()
const openTalkName = ref(null)

const res = createResource({
  url: 'crm.api.session_nav.talks_by_axis',
  makeParams: () => ({ axis: props.axis, limit: 100 }),
})
watch(() => props.axis, () => res.fetch(), { immediate: true })

const data = computed(() => res.data || null)
const talks = computed(() => data.value?.talks || [])

function prettyAxis(s) {
  if (!s) return '(unknown)'
  return s.replace(/[_-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
function tierClass(tier) {
  if (tier === 'Tier 1') return 'bg-surface-amber-2 text-ink-amber-7'
  if (tier === 'Tier 2') return 'bg-surface-blue-2 text-ink-blue-7'
  return 'bg-surface-gray-2 text-ink-gray-7'
}
function back() {
  router.push({ name: 'AACR Intelligence' })
}
function openTalk(t) {
  openTalkName.value = t.talk_id
}
function openSession(slug) {
  if (slug) router.push({ name: 'AACR Session', params: { sessionSlug: slug } })
}
function openLead(leadName) {
  router.push({ name: 'Lead', params: { leadId: leadName } })
}
</script>
