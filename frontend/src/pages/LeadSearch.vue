<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <header class="flex flex-col gap-3 border-b px-5 py-3">
      <div class="flex items-center gap-2">
        <h1 class="text-lg font-semibold text-ink-gray-9">{{ __('Lead Search') }}</h1>
        <span v-if="resource.data" class="text-sm text-ink-gray-5">
          {{ resource.data.total_count }} {{ __('matches') }}
        </span>
        <span v-if="resource.loading" class="text-sm text-ink-gray-5">{{ __('searching…') }}</span>
      </div>

      <!-- free-text + facet controls -->
      <div class="flex flex-wrap items-center gap-2">
        <FormControl
          class="min-w-[260px] flex-1"
          type="text"
          :placeholder="__('Search name, organization, email, session…')"
          v-model="q"
          @input="debouncedSearch"
        >
          <template #prefix><LucideSearch class="h-4 w-4 text-ink-gray-5" /></template>
        </FormControl>

        <FormControl
          type="select"
          :options="tierOptions"
          v-model="tier"
          @change="runSearch"
        />

        <FormControl
          type="select"
          :options="scoreOptions"
          v-model="scoreMin"
          @change="runSearch"
        />

        <FormControl
          type="select"
          :options="sessionOptions"
          v-model="sessionSlug"
          @change="runSearch"
        />

        <label class="flex items-center gap-1.5 text-sm text-ink-gray-7">
          <input type="checkbox" v-model="hasOpps" @change="runSearch" />
          {{ __('Has opportunities') }}
        </label>

        <label class="flex items-center gap-1.5 text-sm text-ink-gray-7">
          <input type="checkbox" v-model="hasIntel" @change="runSearch" />
          {{ __('Has intel') }}
        </label>

        <Button variant="subtle" :label="__('Reset')" @click="resetFilters" />
      </div>
    </header>

    <div class="flex-1 overflow-y-auto px-5 py-4">
      <div v-if="resource.loading && !rows.length" class="py-10 text-center text-ink-gray-5">
        {{ __('Searching…') }}
      </div>
      <div v-else-if="!rows.length" class="py-10 text-center text-ink-gray-5">
        {{ __('No leads match these filters.') }}
      </div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="border-b text-left text-xs uppercase text-ink-gray-5">
            <th class="py-2 pr-3">{{ __('Name') }}</th>
            <th class="py-2 pr-3">{{ __('Organization') }}</th>
            <th class="py-2 pr-3">{{ __('Tier') }}</th>
            <th class="py-2 pr-3 text-right">{{ __('Score') }}</th>
            <th class="py-2 pr-3 text-right">{{ __('Opps') }}</th>
            <th class="py-2 pr-3 text-right">{{ __('Vulns') }}</th>
            <th class="py-2 pr-3">{{ __('Session') }}</th>
            <th class="py-2 pr-3">{{ __('Email') }}</th>
            <th class="py-2 pr-3 text-right">{{ __('Action') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in rows"
            :key="r.name"
            class="cursor-pointer border-b border-surface-gray-2 hover:bg-surface-gray-1"
            @click="openLead(r.name)"
          >
            <td class="py-2 pr-3 font-medium text-ink-gray-9">{{ r.lead_name || '—' }}</td>
            <td class="py-2 pr-3 text-ink-gray-7">{{ r.organization || '—' }}</td>
            <td class="py-2 pr-3">
              <span :class="tierClass(r.tier)" class="rounded px-1.5 py-0.5 text-xs font-medium">
                {{ r.tier || '—' }}
              </span>
            </td>
            <td class="py-2 pr-3 text-right tabular-nums text-ink-gray-8">{{ fmtScore(r.lead_score) }}</td>
            <td class="py-2 pr-3 text-right tabular-nums text-ink-gray-7">{{ r.n_opportunities ?? 0 }}</td>
            <td class="py-2 pr-3 text-right tabular-nums text-ink-gray-7">{{ r.n_vulnerabilities ?? 0 }}</td>
            <td class="py-2 pr-3 text-ink-gray-6" :title="r.session_slug">{{ prettySlug(r.session_slug) }}</td>
            <td class="py-2 pr-3 text-ink-gray-6">{{ r.email || '—' }}</td>
            <td class="py-2 pr-3 text-right">
              <Button variant="subtle" :loading="generatingName === r.name"
                      iconLeft="target" @click.stop="generatePlanForRow(r)">
                {{ __('Generate plan') }}
              </Button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- pagination -->
      <div v-if="rows.length" class="mt-4 flex items-center justify-between text-sm text-ink-gray-6">
        <span>{{ __('Showing') }} {{ start + 1 }}–{{ start + rows.length }} {{ __('of') }} {{ resource.data.total_count }}</span>
        <div class="flex gap-2">
          <Button variant="subtle" :label="__('Prev')" :disabled="start === 0" @click="prevPage" />
          <Button variant="subtle" :label="__('Next')" :disabled="start + pageLength >= resource.data.total_count" @click="nextPage" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { createResource, FormControl, Button, call, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'

const router = useRouter()

const q = ref('')
const tier = ref('')
const scoreMin = ref('')
const sessionSlug = ref('')
const hasOpps = ref(false)
const hasIntel = ref(false)
const start = ref(0)
const pageLength = 25

const tierOptions = [
  { label: 'Any tier', value: '' },
  { label: 'Tier 1', value: 'Tier 1' },
  { label: 'Tier 2', value: 'Tier 2' },
  { label: 'Tier 3', value: 'Tier 3' },
]
const scoreOptions = [
  { label: 'Any score', value: '' },
  { label: 'Score ≥ 8', value: '8' },
  { label: 'Score ≥ 6', value: '6' },
  { label: 'Score ≥ 4', value: '4' },
  { label: 'Score ≥ 1', value: '1' },
]

// session options loaded from the session-nav backend built earlier this session
const sessionsResource = createResource({
  url: 'crm.api.session_nav.list_sessions',
  makeParams: () => ({ limit: 0 }),
  auto: true,
})
const sessionOptions = computed(() => {
  const base = [{ label: 'Any session', value: '' }]
  const list = sessionsResource.data?.sessions || []
  return base.concat(
    list.map((s) => ({ label: prettySlug(s.session_slug), value: s.session_slug })),
  )
})

function buildFacetFilters() {
  const ff = {}
  if (hasOpps.value) ff['n_opportunities'] = ['>', 0]
  if (hasIntel.value) ff['has_competitive_intel'] = 1
  if (sessionSlug.value) ff['session_slug'] = sessionSlug.value
  return ff
}

const resource = createResource({
  url: 'crm.api.intel_facets.search_leads',
  makeParams: () => ({
    q: q.value || '',
    tier: tier.value || '',
    score_min: scoreMin.value || null,
    facet_filters: buildFacetFilters(),
    page_length: pageLength,
    start: start.value,
    order_by: 'lead_score desc',
  }),
  auto: true,
})

const rows = computed(() => resource.data?.rows || [])

function runSearch() {
  start.value = 0
  resource.fetch()
}
let t = null
function debouncedSearch() {
  clearTimeout(t)
  t = setTimeout(runSearch, 250)
}
function nextPage() {
  start.value += pageLength
  resource.fetch()
}
function prevPage() {
  start.value = Math.max(0, start.value - pageLength)
  resource.fetch()
}
function resetFilters() {
  q.value = ''
  tier.value = ''
  scoreMin.value = ''
  sessionSlug.value = ''
  hasOpps.value = false
  hasIntel.value = false
  runSearch()
}

function fmtScore(v) {
  if (v === null || v === undefined || v === '') return '—'
  return Number(v).toFixed(1)
}
function tierClass(t) {
  if (t === 'Tier 1') return 'bg-surface-green-2 text-ink-green-3'
  if (t === 'Tier 2') return 'bg-surface-amber-2 text-ink-amber-3'
  return 'bg-surface-gray-2 text-ink-gray-6'
}
function prettySlug(slug) {
  if (!slug) return '—'
  return slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
function openLead(name) {
  router.push({ name: 'Lead', params: { leadId: name } })
}

// WP7.1 — discovery -> action in one hop: seed a Roche-depth plan for this KOL
// and open its industry card. Search results are a starting line, not a dossier.
const generatingName = ref('')
async function generatePlanForRow(r) {
  if (!r?.name) return
  generatingName.value = r.name
  try {
    const res = await call('crm.api.plan_generator.generate_and_seed_plan', {
      subject_type: 'Lead', subject_key: r.name, option: 'A', use_enrich: 1,
    })
    const c = res?.counts || {}
    toast.success(__('Plan seeded') + `: ${c.tasks ?? 0} ${__('tasks')}, ${c.drafts ?? 0} ${__('drafts')}`)
    if (res?.slug) {
      router.push({
        name: 'Industry Engagement',
        params: { slug: res.slug },
        query: { subject_type: 'Lead', subject_key: r.name },
      })
    }
  } catch (e) {
    toast.error(__('Generate plan failed') + ': ' + (e?.messages?.[0] || e?.message || 'error'))
  } finally {
    generatingName.value = ''
  }
}
</script>
