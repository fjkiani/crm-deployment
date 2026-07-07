<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <!-- Header -->
    <header class="border-b px-6 py-4">
      <h1 class="text-xl font-semibold text-ink-gray-9">{{ __('AACR 2026 Intelligence') }}</h1>
      <p v-if="d" class="mt-0.5 text-sm text-ink-gray-5">
        {{ __('CrisPRO synthetic-lethality landscape across the AACR 2026 abstract corpus') }}
        <span v-if="d.generated"> · {{ __('generated') }} {{ d.generated }}</span>
      </p>
      <!-- stat strip -->
      <div v-if="d" class="mt-3 flex flex-wrap gap-2">
        <div v-for="s in headlineStats" :key="s.label"
             class="rounded-lg border border-surface-gray-3 bg-surface-white px-3 py-2">
          <div class="text-lg font-semibold text-ink-gray-9">{{ s.value }}</div>
          <div class="text-xs text-ink-gray-5">{{ s.label }}</div>
        </div>
      </div>
    </header>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <div v-if="dash.loading" class="py-20 text-center text-ink-gray-5">{{ __('Loading intelligence…') }}</div>

      <template v-else-if="d">
        <!-- ===================== AXIS GRID ===================== -->
        <section>
          <h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-6">
            {{ __('CrisPRO Axes') }} <span class="text-ink-gray-4">({{ axisList.length }})</span>
          </h2>
          <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            <button
              v-for="ax in axisList"
              :key="ax.key"
              class="group flex flex-col rounded-xl border border-surface-gray-3 bg-surface-white p-4 text-left transition hover:border-ink-blue-4 hover:shadow-md"
              @click="openAxis(ax.key)"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="text-sm font-semibold text-ink-gray-9">{{ ax.label }}</div>
                <span v-if="ax.clinical_gap"
                      class="shrink-0 rounded-full bg-surface-amber-2 px-2 py-0.5 text-[10px] font-medium text-ink-amber-7">
                  {{ __('CLINICAL GAP') }}
                </span>
              </div>

              <!-- fit-score bar -->
              <div class="mt-3">
                <div class="flex items-center justify-between text-xs text-ink-gray-5">
                  <span>{{ __('Avg fit') }}</span>
                  <span class="font-medium text-ink-gray-8">{{ pct(ax.avg_fit_score) }}</span>
                </div>
                <div class="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-gray-2">
                  <div class="h-full rounded-full" :class="fitBarClass(ax.avg_fit_score)"
                       :style="{ width: pct(ax.avg_fit_score) }"></div>
                </div>
              </div>

              <!-- metrics row -->
              <div class="mt-3 grid grid-cols-3 gap-2 text-center">
                <div>
                  <div class="text-base font-semibold text-ink-gray-9">{{ ax.total_abstracts ?? '—' }}</div>
                  <div class="text-[10px] uppercase text-ink-gray-5">{{ __('abstracts') }}</div>
                </div>
                <div>
                  <div class="text-base font-semibold text-ink-blue-6">{{ ax.high_fit_opportunities ?? '—' }}</div>
                  <div class="text-[10px] uppercase text-ink-gray-5">{{ __('high-fit') }}</div>
                </div>
                <div>
                  <div class="text-base font-semibold text-ink-gray-9">{{ ax.clinical_trials ?? '—' }}</div>
                  <div class="text-[10px] uppercase text-ink-gray-5">{{ __('trials') }}</div>
                </div>
              </div>

              <!-- top genes -->
              <div v-if="topKeys(ax.top_genes).length" class="mt-3 flex flex-wrap gap-1">
                <span v-for="g in topKeys(ax.top_genes)" :key="g"
                      class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] text-ink-gray-7">{{ g }}</span>
              </div>

              <!-- lead linkage footer -->
              <div class="mt-3 flex items-center justify-between border-t border-surface-gray-2 pt-2 text-xs">
                <span class="text-ink-gray-5">
                  <LucideUsers class="mr-1 inline h-3.5 w-3.5" />{{ leadCount(ax.key) }} {{ __('leads') }}
                </span>
                <span class="text-ink-blue-6 opacity-0 transition group-hover:opacity-100">
                  {{ __('View talks →') }}
                </span>
              </div>
            </button>
          </div>
        </section>

        <!-- ===================== GAP ANALYSIS ===================== -->
        <section v-if="gaps.length" class="mt-8">
          <h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-6">
            {{ __('White-space & Gap Analysis') }}
          </h2>
          <div class="overflow-hidden rounded-xl border border-surface-gray-3">
            <table class="w-full text-sm">
              <thead class="bg-surface-gray-1 text-left text-xs uppercase text-ink-gray-5">
                <tr>
                  <th class="px-4 py-2">{{ __('Axis') }}</th>
                  <th class="px-4 py-2 text-right">{{ __('Preclinical') }}</th>
                  <th class="px-4 py-2 text-right">{{ __('Clinical trials') }}</th>
                  <th class="px-4 py-2 text-right">{{ __('Gap score') }}</th>
                  <th class="px-4 py-2">{{ __('Top genes') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="g in gaps" :key="g.axis"
                    class="cursor-pointer border-t border-surface-gray-2 hover:bg-surface-gray-1"
                    @click="openAxis(g.axis)">
                  <td class="px-4 py-2 font-medium text-ink-gray-8">
                    {{ g.label || g.axis }}
                    <span v-if="g.white_space"
                          class="ml-1 rounded bg-surface-green-2 px-1.5 py-0.5 text-[10px] text-ink-green-7">
                      {{ __('WHITE SPACE') }}
                    </span>
                  </td>
                  <td class="px-4 py-2 text-right text-ink-gray-7">{{ g.preclinical_signal }}</td>
                  <td class="px-4 py-2 text-right text-ink-gray-7">{{ g.clinical_trials }}</td>
                  <td class="px-4 py-2 text-right font-semibold text-ink-gray-9">{{ g.gap_score }}</td>
                  <td class="px-4 py-2 text-xs text-ink-gray-6">{{ (g.top_genes || []).slice(0, 5).join(', ') }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- ===================== COMPETITIVE LANDSCAPE ===================== -->
        <section v-if="companies.length" class="mt-8">
          <h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-6">
            {{ __('Competitive Landscape') }}
            <span class="text-ink-gray-4">({{ d.companies_identified || companies.length }} {{ __('companies') }})</span>
          </h2>
          <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <div v-for="c in companies.slice(0, 18)" :key="c.company || c.name"
                 class="rounded-lg border border-surface-gray-3 bg-surface-white px-3 py-2">
              <div class="truncate text-sm font-medium text-ink-gray-9">{{ c.company || c.name }}</div>
              <div class="mt-1 flex flex-wrap items-center gap-1 text-[11px] text-ink-gray-6">
                <span v-if="c.primary_axis" class="rounded bg-surface-blue-2 px-1.5 py-0.5 text-ink-blue-7">{{ c.primary_axis }}</span>
                <span v-if="c.mentions">· {{ c.mentions }} {{ __('mentions') }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- ===================== TOP OPPORTUNITIES ===================== -->
        <section v-if="opportunities.length" class="mt-8 pb-8">
          <h2 class="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-gray-6">
            {{ __('Top CrisPRO Opportunities') }}
          </h2>
          <div class="overflow-hidden rounded-xl border border-surface-gray-3">
            <table class="w-full text-sm">
              <thead class="bg-surface-gray-1 text-left text-xs uppercase text-ink-gray-5">
                <tr>
                  <th class="px-4 py-2">{{ __('Abstract') }}</th>
                  <th class="px-4 py-2">{{ __('Cancer') }}</th>
                  <th class="px-4 py-2">{{ __('Axis') }}</th>
                  <th class="px-4 py-2 text-right">{{ __('Fit') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(o, i) in opportunities.slice(0, 15)" :key="i" class="border-t border-surface-gray-2">
                  <td class="max-w-md px-4 py-2">
                    <div class="truncate text-ink-gray-8" :title="stripHtml(o.title)">{{ stripHtml(o.title) }}</div>
                  </td>
                  <td class="px-4 py-2 text-ink-gray-7">{{ o.cancer_type || '—' }}</td>
                  <td class="px-4 py-2">
                    <span v-for="a in (o.crispro_axes || []).slice(0, 2)" :key="a"
                          class="mr-1 rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] text-ink-gray-7">{{ a }}</span>
                  </td>
                  <td class="px-4 py-2 text-right font-semibold" :class="fitTextClass(o.fit_score)">{{ pct(o.fit_score) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { createResource } from 'frappe-ui'
import { useRouter } from 'vue-router'

const router = useRouter()

const dash = createResource({
  url: 'crm.api.session_nav.axis_dashboard',
  auto: true,
})

const d = computed(() => dash.data || null)

const axisList = computed(() => {
  const axes = d.value?.axes || {}
  return Object.entries(axes)
    .map(([key, v]) => ({ key, ...v }))
    .sort((a, b) => (b.total_abstracts || 0) - (a.total_abstracts || 0))
})

const gaps = computed(() => (d.value?.gap_analysis || []).slice().sort((a, b) => (b.gap_score || 0) - (a.gap_score || 0)))
const companies = computed(() => d.value?.companies || [])
const opportunities = computed(() => d.value?.top_opportunities || [])

const headlineStats = computed(() => {
  if (!d.value) return []
  return [
    { label: 'abstracts analyzed', value: fmt(d.value.corpus_size) },
    { label: 'LLM-enriched', value: fmt(d.value.llm_enriched) },
    { label: 'axes', value: axisList.value.length },
    { label: 'companies', value: fmt(d.value.companies_identified) },
    { label: 'linked leads', value: fmt(totalLeads.value) },
  ]
})

const totalLeads = computed(() => {
  const c = d.value?.axis_lead_counts || {}
  return Object.values(c).reduce((a, b) => a + (b || 0), 0)
})

function leadCount(axisKey) {
  return d.value?.axis_lead_counts?.[axisKey] ?? 0
}
function topKeys(obj) {
  if (!obj) return []
  return Object.keys(obj).slice(0, 6)
}
function pct(x) {
  if (x == null) return '—'
  return `${Math.round(x * 100)}%`
}
function fmt(n) {
  if (n == null) return '—'
  return Number(n).toLocaleString()
}
function stripHtml(s) {
  return (s || '').replace(/<[^>]+>/g, '')
}
function fitBarClass(x) {
  if (x == null) return 'bg-surface-gray-4'
  if (x >= 0.7) return 'bg-ink-green-6'
  if (x >= 0.5) return 'bg-ink-blue-6'
  return 'bg-ink-amber-6'
}
function fitTextClass(x) {
  if (x == null) return 'text-ink-gray-5'
  if (x >= 0.7) return 'text-ink-green-6'
  if (x >= 0.5) return 'text-ink-blue-6'
  return 'text-ink-amber-6'
}
function openAxis(axis) {
  router.push({ name: 'AACR Axis', params: { axis } })
}
</script>
