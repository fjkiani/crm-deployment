<template>
  <div class="nyx-hub">
    <!-- Header -->
    <div class="mb-5 flex items-start justify-between gap-4 border-b border-ink-gray-2 pb-4">
      <div>
        <h1 class="text-xl font-semibold text-ink-gray-9">{{ __('Nyx Intelligence') }}</h1>
        <p class="mt-1 max-w-2xl text-sm text-ink-gray-5">
          {{ __('Pipeline analytics, prospect worklist, CRM knowledge search, and outreach actions — one command surface.') }}
        </p>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <span
          class="rounded-full px-2.5 py-1 text-xs font-medium"
          :class="brainOk ? 'bg-surface-green-2 text-ink-green-3' : 'bg-surface-gray-2 text-ink-gray-6'"
        >
          {{ brainOk ? '● ' + __('Brain') + ': ' + brainProvider : '○ ' + __('Brain offline') }}
        </span>
        <Button variant="subtle" @click="showModelSettings = true">
          <template #prefix><LucideSettings2 class="h-4 w-4" /></template>
          {{ __('Model') }}
        </Button>
        <Button variant="subtle" @click="reloadAll" :loading="dash.loading || pipeline.loading">
          <template #prefix><LucideRefreshCw class="h-4 w-4" /></template>
          {{ __('Refresh') }}
        </Button>
      </div>
    </div>

    <!-- Stats Bar -->
    <div class="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      <div v-for="s in statCards" :key="s.label" class="rounded-lg border border-ink-gray-2 bg-surface-white p-3">
        <div class="text-lg font-semibold" :class="s.color || 'text-ink-gray-9'">{{ s.value }}</div>
        <div class="mt-0.5 text-[11px] uppercase tracking-wide text-ink-gray-4">{{ s.label }}</div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <!-- LEFT: Pipeline + Frameworks -->
      <div class="space-y-6 lg:col-span-1">
        <!-- Pipeline funnel -->
        <div class="rounded-lg border border-ink-gray-2 bg-surface-white p-4">
          <h2 class="mb-3 text-sm font-semibold text-ink-gray-8">{{ __('Pipeline funnel') }}</h2>
          <div v-if="pipeline.loading" class="py-6 text-center text-sm text-ink-gray-5">{{ __('Loading…') }}</div>
          <div v-else-if="funnelRows.length" class="space-y-2">
            <div v-for="row in funnelRows" :key="row.label" class="flex items-center gap-2">
              <div class="w-28 shrink-0 truncate text-xs text-ink-gray-6" :title="row.label">{{ row.label }}</div>
              <div class="h-4 flex-1 overflow-hidden rounded bg-surface-gray-2">
                <div class="h-full rounded bg-ink-blue-4" :style="{ width: row.pct + '%' }"></div>
              </div>
              <div class="w-10 shrink-0 text-right text-xs font-medium text-ink-gray-8">{{ row.count }}</div>
            </div>
          </div>
          <div v-else class="py-6 text-center text-sm text-ink-gray-4">{{ __('No pipeline data') }}</div>
        </div>

        <!-- Messaging frameworks -->
        <div class="rounded-lg border border-ink-gray-2 bg-surface-white p-4">
          <h2 class="mb-3 text-sm font-semibold text-ink-gray-8">{{ __('Messaging frameworks') }}</h2>
          <div v-if="frameworkRows.length" class="space-y-2">
            <div v-for="row in frameworkRows" :key="row.label" class="flex items-center justify-between text-xs">
              <span class="capitalize text-ink-gray-6">{{ row.label }}</span>
              <span class="font-medium text-ink-gray-8">{{ row.count }}</span>
            </div>
          </div>
          <div v-else class="py-4 text-center text-sm text-ink-gray-4">{{ __('No framework tags yet') }}</div>
          <div class="mt-3 border-t border-ink-gray-2 pt-3 text-xs text-ink-gray-5">
            <div class="flex justify-between"><span>{{ __('Enrichment coverage') }}</span><span class="font-medium text-ink-gray-8">{{ enrichCoverage }}%</span></div>
          </div>
        </div>

        <!-- Actions -->
        <div class="rounded-lg border border-ink-gray-2 bg-surface-white p-4">
          <h2 class="mb-3 text-sm font-semibold text-ink-gray-8">{{ __('Actions') }}</h2>
          <div class="space-y-2">
            <Button class="w-full justify-start" variant="subtle" @click="runBatchTriage" :loading="batchTriage.loading">
              <template #prefix><LucideMailPlus class="h-4 w-4" /></template>
              {{ __('Draft top') }} {{ triageLimit }} {{ __('outreach emails') }}
            </Button>
            <router-link to="/industry" class="block">
              <Button class="w-full justify-start" variant="subtle">
                <template #prefix><LucideBuilding2 class="h-4 w-4" /></template>
                {{ __('Industry engagements') }}
              </Button>
            </router-link>
            <router-link to="/imports" class="block">
              <Button class="w-full justify-start" variant="subtle">
                <template #prefix><LucideUpload class="h-4 w-4" /></template>
                {{ __('Import prospects (CSV)') }}
              </Button>
            </router-link>
          </div>
        </div>

        <!-- Intelligence Core (honest disabled state) -->
        <div class="rounded-lg border border-dashed border-ink-gray-3 bg-surface-gray-1 p-4">
          <div class="flex items-center gap-2">
            <LucideMessageSquare class="h-4 w-4 text-ink-gray-5" />
            <h2 class="text-sm font-semibold text-ink-gray-7">{{ __('Intelligence Core (chat)') }}</h2>
          </div>
          <p class="mt-2 text-xs leading-relaxed text-ink-gray-5">
            {{ __('Conversational Nyx (ask_nyx) requires an external EAIA host. Set the EAIA_URL environment variable on the CRM server to enable live chat. Dossiers, drafting and enrichment below run natively without it.') }}
          </p>
        </div>
      </div>

      <!-- CENTER: Prospect worklist -->
      <div class="lg:col-span-1">
        <div class="rounded-lg border border-ink-gray-2 bg-surface-white p-4">
          <div class="mb-3 flex items-center justify-between">
            <h2 class="text-sm font-semibold text-ink-gray-8">{{ __('Prospect worklist') }}</h2>
            <router-link to="/contacts/view" class="text-xs text-ink-blue-6 hover:underline">{{ __('View all') }} →</router-link>
          </div>
          <div v-if="prospects.loading" class="py-8 text-center text-sm text-ink-gray-5">{{ __('Loading prospects…') }}</div>
          <div v-else-if="prospectList.length" class="space-y-1.5">
            <button
              v-for="p in prospectList"
              :key="p.prospect"
              class="flex w-full items-center gap-2 rounded-md border border-transparent px-2 py-1.5 text-left hover:border-ink-gray-2 hover:bg-surface-gray-1"
              @click="openDossier(p)"
            >
              <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-gray-3 text-[11px] font-semibold text-ink-gray-7">
                {{ initials(p.name) }}
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-1.5">
                  <span class="truncate text-sm font-medium text-ink-gray-8">{{ p.name || p.prospect }}</span>
                  <span v-if="p.engagement_slug" class="shrink-0 rounded bg-surface-blue-2 px-1 py-px text-[9px] font-medium text-ink-blue-6" :title="__('Linked to industry engagement')">◆</span>
                  <span v-if="p.needs_backfill" class="shrink-0 rounded bg-surface-amber-2 px-1 py-px text-[9px] font-medium text-ink-amber-3" :title="__('Missing/invalid email')">!</span>
                </div>
                <div class="truncate text-xs text-ink-gray-4">{{ p.institution || '—' }}</div>
              </div>
              <span class="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium" :class="tierClass(p.tier)">{{ p.tier || '—' }}</span>
              <span class="w-8 shrink-0 text-right text-xs font-semibold text-ink-gray-7">{{ fmtScore(p.lead_score) }}</span>
            </button>
          </div>
          <div v-else class="py-8 text-center text-sm text-ink-gray-4">{{ __('No prospects') }}</div>
        </div>
      </div>

      <!-- RIGHT: Knowledge search -->
      <div class="lg:col-span-1">
        <div class="rounded-lg border border-ink-gray-2 bg-surface-white p-4">
          <h2 class="mb-3 text-sm font-semibold text-ink-gray-8">{{ __('CRM knowledge search') }}</h2>
          <div class="flex gap-2">
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="__('Search leads & notes…')"
              class="flex-1 rounded-md border border-ink-gray-3 bg-surface-white px-3 py-1.5 text-sm focus:border-ink-blue-4 focus:outline-none"
              @keyup.enter="runSearch"
            />
            <Button variant="solid" @click="runSearch" :loading="search.loading">{{ __('Go') }}</Button>
          </div>

          <div v-if="search.loading" class="py-8 text-center text-sm text-ink-gray-5">{{ __('Searching…') }}</div>
          <div v-else-if="searchRan" class="mt-4 space-y-4">
            <div>
              <div class="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">{{ __('Leads') }} ({{ searchLeads.length }})</div>
              <div v-if="searchLeads.length" class="space-y-1">
                <button
                  v-for="l in searchLeads"
                  :key="l.name"
                  class="block w-full truncate rounded px-2 py-1 text-left text-sm text-ink-gray-7 hover:bg-surface-gray-1"
                  @click="openDossierById(l.name, l.lead_name || l.title)"
                >
                  {{ l.lead_name || l.title || l.name }}
                  <span v-if="l.organization" class="text-ink-gray-4">— {{ l.organization }}</span>
                </button>
              </div>
              <div v-else class="text-xs text-ink-gray-4">{{ __('No matching leads') }}</div>
            </div>
            <div>
              <div class="mb-1.5 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">{{ __('Notes') }} ({{ searchNotes.length }})</div>
              <div v-if="searchNotes.length" class="space-y-1">
                <div v-for="(n, i) in searchNotes" :key="i" class="rounded bg-surface-gray-1 px-2 py-1.5 text-xs text-ink-gray-6">
                  <div class="line-clamp-2" v-html="n.snippet || n.content || n.title"></div>
                </div>
              </div>
              <div v-else class="text-xs text-ink-gray-4">{{ __('No matching notes') }}</div>
            </div>
          </div>
          <div v-else class="py-8 text-center text-sm text-ink-gray-4">{{ __('Enter a query to search the CRM knowledge base.') }}</div>
        </div>
      </div>
    </div>

    <!-- Dossier drawer -->
    <div v-if="dossierOpen" class="fixed inset-0 z-40 flex justify-end" @click.self="dossierOpen = false">
      <div class="absolute inset-0 bg-black/30"></div>
      <div class="relative z-10 flex h-full w-full max-w-md flex-col bg-surface-white shadow-xl">
        <div class="flex items-center justify-between border-b border-ink-gray-2 px-4 py-3">
          <div class="min-w-0">
            <h3 class="truncate text-sm font-semibold text-ink-gray-9">{{ dossierTitle }}</h3>
            <p class="text-xs text-ink-gray-4">{{ __('Intelligence dossier') }}</p>
          </div>
          <button class="text-ink-gray-5 hover:text-ink-gray-8" @click="dossierOpen = false"><LucideX class="h-5 w-5" /></button>
        </div>
        <div class="flex-1 overflow-y-auto px-4 py-3">
          <div v-if="dossier.loading" class="py-8 text-center text-sm text-ink-gray-5">{{ __('Loading dossier…') }}</div>
          <pre v-else-if="dossierText" class="whitespace-pre-wrap break-words font-sans text-xs leading-relaxed text-ink-gray-7">{{ dossierText }}</pre>
          <div v-else class="py-8 text-center text-sm text-ink-gray-4">{{ __('No dossier available') }}</div>
        </div>
        <div class="flex flex-wrap gap-2 border-t border-ink-gray-2 px-4 py-3">
          <router-link v-if="dossierEngagement" :to="`/industry/${dossierEngagement}`" class="flex-1">
            <Button variant="subtle" class="w-full">{{ __('Engagement') }}</Button>
          </router-link>
          <Button v-if="dossierLeadId" variant="solid" class="flex-1" @click="goToLead(dossierLeadId)">{{ __('Open lead') }}</Button>
          <span v-if="!dossierLeadId && !dossierEngagement" class="flex-1 py-1.5 text-center text-xs text-ink-gray-4">{{ __('No linked CRM lead') }}</span>
        </div>
      </div>
    </div>

    <!-- Model settings modal -->
    <NyxModelSettingsModal v-model="showModelSettings" @saved="onModelSaved" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { createResource, Button, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'
import LucideRefreshCw from '~icons/lucide/refresh-cw'
import LucideMailPlus from '~icons/lucide/mail-plus'
import LucideBuilding2 from '~icons/lucide/building-2'
import LucideUpload from '~icons/lucide/upload'
import LucideMessageSquare from '~icons/lucide/message-square'
import LucideSettings2 from '~icons/lucide/settings-2'
import LucideX from '~icons/lucide/x'
import NyxModelSettingsModal from '@/components/Modals/NyxModelSettingsModal.vue'

const router = useRouter()
const triageLimit = 10

// Model settings modal
const showModelSettings = ref(false)
function onModelSaved() { brain.reload() }

// ---- Brain status ----
const brainOk = ref(false)
const brainProvider = ref('')
const brain = createResource({
  url: 'crm.api.nyx_email_brain.brain_status',
  auto: true,
  onSuccess(d) {
    brainOk.value = !!d?.ok
    brainProvider.value = d?.llm_provider || d?.backend || 'unknown'
  },
  onError() { brainOk.value = false },
})

// ---- Dashboard metrics (prospect totals + tiers) ----
const dash = createResource({ url: 'crm.api.leadgen.get_dashboard_metrics', auto: true })

// ---- Pipeline analytics (funnel + frameworks) ----
const pipeline = createResource({ url: 'crm.api.ai.get_pipeline_analytics', auto: true })

// ---- Activity counts ----
const counts = createResource({
  url: 'crm.api.ai.get_counts',
  auto: true,
  makeParams: () => ({ days: 7 }),
})

const statCards = computed(() => {
  const m = dash.data || {}
  const c = counts.data || {}
  const met = pipeline.data?.metrics || {}
  return [
    { label: __('Prospects'), value: m.total_prospects ?? '—' },
    { label: __('Tier 1'), value: m.tier_counts?.['Tier 1'] ?? m.tier_counts?.Tier1 ?? '—', color: 'text-ink-blue-6' },
    { label: __('Leads'), value: met.total_leads ?? '—' },
    { label: __('Drafts'), value: c.drafts ?? '—', color: 'text-ink-amber-3' },
    { label: __('Sent today'), value: c.sent_today ?? '—', color: 'text-ink-green-3' },
    { label: __('Activity 7d'), value: c.recent_total ?? '—' },
  ]
})

const funnelRows = computed(() => {
  const f = pipeline.data?.funnel
  if (!f || typeof f !== 'object') return []
  const entries = Object.entries(f).filter(([k]) => k !== 'total')
  const max = Math.max(1, ...entries.map(([, v]) => Number(v) || 0))
  return entries
    .map(([label, count]) => ({ label, count: Number(count) || 0, pct: Math.round(((Number(count) || 0) / max) * 100) }))
    .sort((a, b) => b.count - a.count)
})

const frameworkRows = computed(() => {
  const fr = pipeline.data?.frameworks
  if (!fr || typeof fr !== 'object') return []
  return Object.entries(fr).map(([label, count]) => ({ label, count: Number(count) || 0 })).sort((a, b) => b.count - a.count)
})

const enrichCoverage = computed(() => {
  const m = pipeline.data?.metrics || {}
  return m.enrichment_coverage ?? m.coverage ?? 0
})

// ---- Prospect worklist (directory.list_contacts: has email + engagement links) ----
const prospects = createResource({
  url: 'crm.api.directory.list_contacts',
  auto: true,
  makeParams: () => ({ page_length: 15 }),
})
const prospectList = computed(() => prospects.data?.rows || [])

// ---- Knowledge search ----
const searchQuery = ref('')
const searchRan = ref(false)
const search = createResource({
  url: 'crm.api.intelligence.search_crm_knowledge',
  makeParams: () => ({ query: searchQuery.value, limit: 10 }),
  onSuccess() { searchRan.value = true },
  onError(err) { toast.error(__('Search failed') + ': ' + (err?.messages?.[0] || err)) },
})
function runSearch() {
  if (!searchQuery.value.trim()) return
  search.submit()
}
const searchLeads = computed(() => search.data?.leads || [])
const searchNotes = computed(() => search.data?.notes || [])

// ---- Dossier drawer ----
const dossierOpen = ref(false)
const dossierTitle = ref('')
const dossierLeadId = ref('')
const dossierEngagement = ref('')
const dossier = createResource({ url: 'crm.api.intelligence.get_dossier' })
const dossierText = computed(() => {
  const d = dossier.data
  if (!d) return ''
  return d.formatted || (typeof d === 'string' ? d : JSON.stringify(d.data || d, null, 2))
})
function openDossier(p) {
  dossierTitle.value = p.name || p.prospect
  dossierLeadId.value = ''
  dossierEngagement.value = p.engagement_slug || ''
  dossierOpen.value = true
  const email = p.email && !p.email.endsWith('.invalid') ? p.email : ''
  if (!email) {
    // No resolvable email -> dossier keys off CRM Lead; nothing to look up
    dossier.data = { formatted: __('No email on file for this prospect. Dossiers resolve against CRM Leads by email — backfill the email to enable a full dossier.'), data: {} }
    return
  }
  dossier.submit({ email }).then(() => {
    dossierLeadId.value = dossier.data?.data?.name || ''
  })
}
function openDossierById(leadId, title) {
  dossierTitle.value = title || leadId
  dossierLeadId.value = leadId
  dossierOpen.value = true
  dossier.submit({ lead_id: leadId })
}
function goToLead(id) { router.push(`/leads/${id}`) }

// ---- Batch triage ----
const batchTriage = createResource({
  url: 'crm.api.nyx_email_brain.batch_triage_and_draft',
  onSuccess(d) {
    const queued = d?.queued_count ?? 0
    const skipped = d?.skipped_existing_draft ?? 0
    // Honest: batch_triage_and_draft ENQUEUES background LLM jobs — it does not
    // create drafts synchronously. If no working model, those jobs will fail.
    if (!brainOk.value) {
      toast.warning(
        __('Queued {0} draft job(s) — but no working model is configured; these will fail until a provider with credits is set (Configure model).', [queued]),
      )
    } else {
      toast.success(
        __('Queued {0} draft job(s). Drafts appear in the Human Inbox as they finish ({1} skipped, already had a draft).', [queued, skipped]),
      )
    }
    counts.reload()
  },
  onError(err) { toast.error(__('Batch failed') + ': ' + (err?.messages?.[0] || err)) },
})
function runBatchTriage() {
  const warn = brainOk.value
    ? __('Queue background draft jobs for the top {0} prospects with valid emails?', [triageLimit])
    : __('No working model is configured, so these jobs will fail. Queue them anyway for the top {0} prospects?', [triageLimit])
  if (!window.confirm(warn)) return
  batchTriage.submit({ limit: triageLimit, only_with_email: 1 })
}

// ---- Helpers ----
function reloadAll() { dash.reload(); pipeline.reload(); counts.reload(); prospects.reload(); brain.reload() }
function initials(name) {
  if (!name) return '?'
  const parts = String(name).trim().split(/\s+/)
  return ((parts[0]?.[0] || '') + (parts[parts.length - 1]?.[0] || '')).toUpperCase() || '?'
}
function fmtScore(s) { return s == null ? '—' : Number(s).toFixed(1) }
function tierClass(t) {
  if (t === 'Tier1' || t === 'Tier 1') return 'bg-surface-blue-2 text-ink-blue-6'
  if (t === 'Tier2' || t === 'Tier 2') return 'bg-surface-amber-2 text-ink-amber-3'
  return 'bg-surface-gray-2 text-ink-gray-6'
}
onMounted(() => {})
</script>

<style scoped>
.nyx-hub {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}
</style>
