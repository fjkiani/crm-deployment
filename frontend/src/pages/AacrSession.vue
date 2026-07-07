<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <header class="border-b px-5 py-3">
      <button class="mb-1 inline-flex items-center gap-1 text-xs text-ink-gray-5 hover:text-ink-gray-8" @click="back">
        <LucideChevronLeft class="h-3.5 w-3.5" /> {{ __('All sessions') }}
      </button>
      <h1 class="text-lg font-semibold text-ink-gray-9">{{ prettySlug(sessionSlug) }}</h1>
      <p v-if="data" class="text-sm text-ink-gray-5">
        {{ data.n_talks }} {{ __('talks') }} · {{ data.n_leads }} {{ __('linked leads') }}
      </p>
    </header>

    <div class="flex-1 overflow-y-auto px-5 py-4">
      <div v-if="talksResource.loading" class="py-10 text-center text-ink-gray-5">
        {{ __('Loading talks…') }}
      </div>
      <table v-else-if="talks.length" class="w-full text-sm">
        <thead>
          <tr class="border-b text-left text-xs uppercase text-ink-gray-5">
            <th class="py-2 pr-3">{{ __('Talk') }}</th>
            <th class="py-2 pr-3">{{ __('Speaker') }}</th>
            <th class="py-2 pr-3">{{ __('Lead') }}</th>
            <th class="py-2 pr-3">{{ __('Tier') }}</th>
            <th class="py-2 pr-3">{{ __('Intel') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="talk in talks" :key="talk.talk_id" class="border-b border-surface-gray-2 hover:bg-surface-gray-1">
            <td class="py-2 pr-3">
              <button class="flex max-w-md items-center gap-1 truncate text-left text-ink-gray-8 hover:text-ink-blue-6"
                      :title="talk.talk_title" @click="openTalk(talk)">
                <LucideFileText class="h-3.5 w-3.5 shrink-0 text-ink-gray-4" />
                <span class="truncate">{{ talk.talk_title || talk.talk_id }}</span>
              </button>
            </td>
            <td class="py-2 pr-3 text-ink-gray-7">{{ talk.speaker_name || '—' }}</td>
            <td class="py-2 pr-3">
              <button
                v-if="talk.lead_name"
                class="text-ink-blue-6 hover:underline"
                @click="openLead(talk.lead_name)"
              >
                {{ talk.lead_person || talk.lead_name }}
              </button>
              <span v-else class="text-ink-gray-4">—</span>
            </td>
            <td class="py-2 pr-3">
              <span v-if="talk.tier" class="rounded px-1.5 py-0.5 text-xs" :class="tierClass(talk.tier)">{{ talk.tier }}</span>
              <span v-else class="text-ink-gray-4">—</span>
            </td>
            <td class="py-2 pr-3">
              <LucideCheck v-if="talk.has_competitive_intel" class="h-4 w-4 text-ink-green-6" />
              <span v-else class="text-ink-gray-4">—</span>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="py-10 text-center text-ink-gray-5">{{ __('No talks in this session.') }}</div>
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

const props = defineProps({ sessionSlug: { type: String, required: true } })
const router = useRouter()
const openTalkName = ref(null)

const talksResource = createResource({
  url: 'crm.api.session_nav.list_talks_by_session',
  makeParams: () => ({ session_slug: props.sessionSlug }),
})

watch(() => props.sessionSlug, () => talksResource.fetch(), { immediate: true })

const data = computed(() => talksResource.data || null)
const talks = computed(() => data.value?.talks || [])

function prettySlug(slug) {
  if (!slug) return '(unknown)'
  return slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
function tierClass(tier) {
  if (tier === 'Tier 1') return 'bg-surface-amber-2 text-ink-amber-7'
  if (tier === 'Tier 2') return 'bg-surface-blue-2 text-ink-blue-7'
  return 'bg-surface-gray-2 text-ink-gray-7'
}
function back() {
  router.push({ name: 'AACR Sessions' })
}
function openLead(leadName) {
  router.push({ name: 'Lead', params: { leadId: leadName } })
}
function openTalk(talk) {
  openTalkName.value = talk.talk_id
}
</script>
