<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <!-- Header -->
    <header class="border-b px-6 py-4">
      <h1 class="text-xl font-semibold text-ink-gray-9">{{ __('Industry Engagements') }}</h1>
      <p class="mt-0.5 text-sm text-ink-gray-5">
        {{ __('CrisPRO outreach strategies for CRC pharma/biotech programs — sequenced, draft-rendered, pipeline-synced') }}
      </p>
      <div v-if="d" class="mt-3 flex flex-wrap gap-2">
        <div v-for="s in headlineStats" :key="s.label"
             class="rounded-lg border border-surface-gray-3 bg-surface-white px-3 py-2">
          <div class="text-lg font-semibold text-ink-gray-9">{{ s.value }}</div>
          <div class="text-xs text-ink-gray-5">{{ s.label }}</div>
        </div>
        <button
          class="ml-auto self-center rounded-lg bg-ink-gray-9 px-3 py-2 text-sm font-medium text-surface-white transition hover:bg-ink-gray-8 disabled:opacity-50"
          :disabled="seedAll.loading"
          @click="onSeedAll">
          <LucideZap class="mr-1 inline h-4 w-4" />
          {{ seedAll.loading ? __('Generating…') : __('Generate all plans') }}
        </button>
      </div>
    </header>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <div v-if="dash.loading" class="py-20 text-center text-ink-gray-5">{{ __('Loading engagements…') }}</div>

      <template v-else-if="d">
        <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          <button
            v-for="e in engagements"
            :key="e.slug"
            class="group flex flex-col rounded-xl border border-surface-gray-3 bg-surface-white p-4 text-left transition hover:border-ink-blue-4 hover:shadow-md"
            @click="openEngagement(e.slug)"
          >
            <div class="flex items-start justify-between gap-2">
              <div>
                <div class="text-sm font-semibold text-ink-gray-9">{{ e.company }}</div>
                <div class="mt-0.5 text-xs text-ink-gray-5">{{ e.lead_drug }}</div>
              </div>
              <div class="flex shrink-0 flex-col items-end gap-1">
                <span class="rounded-full px-2 py-0.5 text-[10px] font-medium"
                      :class="tierClass(e.tier)">{{ e.tier }}</span>
                <span class="text-[10px] text-ink-gray-4">{{ __('rank') }} {{ e.priority_rank }}</span>
              </div>
            </div>

            <!-- target + trial -->
            <div class="mt-2 space-y-0.5 text-xs text-ink-gray-6">
              <div><span class="text-ink-gray-4">{{ __('Target') }}:</span> {{ e.target }}</div>
              <div class="truncate" :title="e.trial"><span class="text-ink-gray-4">{{ __('Trial') }}:</span> {{ e.trial }}</div>
            </div>

            <!-- fit bar -->
            <div class="mt-3">
              <div class="flex items-center justify-between text-xs text-ink-gray-5">
                <span>{{ __('CrisPRO fit') }}</span>
                <span class="font-medium text-ink-gray-8">{{ e.composite_fit }}/5</span>
              </div>
              <div class="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-gray-2">
                <div class="h-full rounded-full" :class="fitBarClass(e.composite_fit)"
                     :style="{ width: fitPct(e.composite_fit) }"></div>
              </div>
            </div>

            <!-- posture + contact -->
            <div class="mt-3 flex flex-wrap items-center gap-1 text-[11px]">
              <span class="rounded px-1.5 py-0.5"
                    :class="postureClass(e.claim_posture)">{{ e.claim_posture }}</span>
              <span class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-ink-gray-7">{{ e.preferred_channel }}</span>
            </div>

            <!-- contact + seed status footer -->
            <div class="mt-3 flex items-center justify-between border-t border-surface-gray-2 pt-2 text-xs">
              <span class="truncate text-ink-gray-6" :title="e.primary_contact + ' · ' + e.primary_institution">
                <LucideUser class="mr-1 inline h-3.5 w-3.5" />{{ e.primary_contact }}
              </span>
              <span v-if="e.seeded" class="shrink-0 rounded bg-surface-green-2 px-1.5 py-0.5 text-[10px] text-ink-green-7">
                <LucideCheck class="mr-0.5 inline h-3 w-3" />{{ e.task_count }} {{ __('tasks') }}
              </span>
              <span v-else class="shrink-0 text-ink-gray-4">{{ __('not seeded') }}</span>
            </div>
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { createResource } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { toast } from 'frappe-ui'

const router = useRouter()

const dash = createResource({
  url: 'crm.api.industry.industry_dashboard',
  auto: true,
})
const d = computed(() => dash.data || null)
const engagements = computed(() => d.value?.engagements || [])

const seedAll = createResource({
  url: 'crm.api.industry.seed_all_engagements',
  onSuccess() {
    toast.success(__('Outreach plans generated'))
    dash.reload()
  },
  onError(err) {
    toast.error(__('Seeding failed') + ': ' + (err?.messages?.[0] || err))
  },
})
function onSeedAll() {
  seedAll.submit({ option: 'A' })
}

const headlineStats = computed(() => {
  if (!d.value) return []
  const seeded = engagements.value.filter((e) => e.seeded).length
  const tasks = engagements.value.reduce((a, e) => a + (e.task_count || 0), 0)
  return [
    { label: 'engagements', value: d.value.count },
    { label: 'plans generated', value: seeded },
    { label: 'sequenced tasks', value: tasks },
  ]
})

function fitPct(x) {
  const v = parseFloat(x)
  if (isNaN(v)) return '0%'
  return `${Math.round((v / 5) * 100)}%`
}
function fitBarClass(x) {
  const v = parseFloat(x)
  if (isNaN(v)) return 'bg-surface-gray-4'
  if (v >= 4) return 'bg-ink-green-6'
  if (v >= 3.5) return 'bg-ink-blue-6'
  return 'bg-ink-amber-6'
}
function tierClass(tier) {
  if (tier === 'Tier 1') return 'bg-surface-green-2 text-ink-green-7'
  if (tier === 'Tier 2') return 'bg-surface-blue-2 text-ink-blue-7'
  return 'bg-surface-gray-2 text-ink-gray-7'
}
function postureClass(p) {
  if (p === 'gap-hook') return 'bg-surface-amber-2 text-ink-amber-7'
  return 'bg-surface-blue-2 text-ink-blue-7'
}
function openEngagement(slug) {
  router.push({ name: 'Industry Engagement', params: { slug } })
}
</script>
