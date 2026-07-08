<template>
  <div class="contacts-directory">
    <!-- Header -->
    <div class="mb-4 flex items-start justify-between gap-4 border-b border-ink-gray-2 pb-4">
      <div>
        <h1 class="text-xl font-semibold text-ink-gray-9">{{ __('Contacts') }}</h1>
        <p class="mt-1 text-sm text-ink-gray-5">
          {{ __('KOL & industry contacts sourced from Lead Prospect — tier-scored, enrichment-tracked.') }}
        </p>
      </div>
      <div class="shrink-0 text-right">
        <div class="text-2xl font-semibold text-ink-gray-9">{{ list.data?.total ?? '—' }}</div>
        <div class="text-[11px] uppercase tracking-wide text-ink-gray-4">{{ __('matching contacts') }}</div>
      </div>
    </div>

    <!-- Filters -->
    <div class="mb-4 flex flex-wrap items-center gap-2">
      <div class="relative min-w-[220px] flex-1">
        <LucideSearch class="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-gray-4" />
        <input
          v-model="searchTerm"
          type="text"
          :placeholder="__('Search name, institution, or email…')"
          class="w-full rounded-md border border-ink-gray-3 bg-surface-white py-1.5 pl-8 pr-3 text-sm focus:border-ink-blue-4 focus:outline-none"
          @keyup.enter="applyFilters"
        />
      </div>
      <select v-model="tier" class="rounded-md border border-ink-gray-3 bg-surface-white px-2.5 py-1.5 text-sm text-ink-gray-7 focus:border-ink-blue-4 focus:outline-none" @change="applyFilters">
        <option value="">{{ __('All tiers') }}</option>
        <option v-for="t in facetTiers" :key="t" :value="t">{{ t }}</option>
      </select>
      <select v-model="outreachStatus" class="rounded-md border border-ink-gray-3 bg-surface-white px-2.5 py-1.5 text-sm text-ink-gray-7 focus:border-ink-blue-4 focus:outline-none" @change="applyFilters">
        <option value="">{{ __('All statuses') }}</option>
        <option v-for="s in facetStatuses" :key="s" :value="s">{{ s }}</option>
      </select>
      <Button variant="solid" @click="applyFilters" :loading="list.loading">{{ __('Apply') }}</Button>
      <Button v-if="hasFilters" variant="subtle" @click="clearFilters">{{ __('Clear') }}</Button>
    </div>

    <!-- Table -->
    <div class="overflow-hidden rounded-lg border border-ink-gray-2 bg-surface-white">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-ink-gray-2 bg-surface-gray-1 text-left text-[11px] uppercase tracking-wide text-ink-gray-5">
            <th class="px-3 py-2 font-medium">{{ __('Contact') }}</th>
            <th class="px-3 py-2 font-medium">{{ __('Institution') }}</th>
            <th class="px-3 py-2 font-medium">{{ __('Focus') }}</th>
            <th class="px-3 py-2 font-medium">{{ __('Tier') }}</th>
            <th class="px-3 py-2 text-right font-medium">{{ __('Score') }}</th>
            <th class="px-3 py-2 font-medium">{{ __('Status') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="list.loading">
            <td colspan="6" class="px-3 py-10 text-center text-ink-gray-5">{{ __('Loading contacts…') }}</td>
          </tr>
          <tr v-else-if="!rows.length">
            <td colspan="6" class="px-3 py-10 text-center text-ink-gray-4">{{ __('No contacts match these filters.') }}</td>
          </tr>
          <tr
            v-for="c in rows"
            :key="c.prospect"
            class="cursor-pointer border-b border-ink-gray-1 last:border-0 hover:bg-surface-gray-1"
            @click="openDossier(c)"
          >
            <td class="px-3 py-2">
              <div class="flex items-center gap-2">
                <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-gray-3 text-[11px] font-semibold text-ink-gray-7">{{ initials(c.name) }}</div>
                <div class="min-w-0">
                  <div class="flex items-center gap-1.5">
                    <span class="truncate font-medium text-ink-gray-8">{{ c.name || c.prospect }}</span>
                    <span v-if="c.engagement_slug" class="shrink-0 rounded bg-surface-blue-2 px-1 py-px text-[9px] font-medium text-ink-blue-6" :title="__('Linked to industry engagement')">◆</span>
                    <span v-if="c.needs_backfill" class="shrink-0 rounded bg-surface-amber-2 px-1 py-px text-[9px] font-medium text-ink-amber-3" :title="__('Email missing or placeholder — needs backfill')">! {{ __('backfill') }}</span>
                  </div>
                  <div class="truncate text-xs text-ink-gray-4">{{ c.email || __('no email') }}</div>
                </div>
              </div>
            </td>
            <td class="px-3 py-2 text-ink-gray-7">{{ c.institution || '—' }}</td>
            <td class="px-3 py-2 text-ink-gray-6">{{ c.cancer_type || '—' }}</td>
            <td class="px-3 py-2"><span class="rounded px-1.5 py-0.5 text-[10px] font-medium" :class="tierClass(c.tier)">{{ c.tier || '—' }}</span></td>
            <td class="px-3 py-2 text-right font-semibold text-ink-gray-7">{{ fmtScore(c.lead_score) }}</td>
            <td class="px-3 py-2 text-xs text-ink-gray-6">{{ c.outreach_status || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div class="mt-3 flex items-center justify-between text-sm text-ink-gray-5">
      <div>
        {{ __('Showing') }} {{ rangeStart }}–{{ rangeEnd }} {{ __('of') }} {{ list.data?.total ?? 0 }}
      </div>
      <div class="flex items-center gap-2">
        <Button variant="subtle" :disabled="start === 0 || list.loading" @click="prevPage">{{ __('Prev') }}</Button>
        <Button variant="subtle" :disabled="rangeEnd >= (list.data?.total ?? 0) || list.loading" @click="nextPage">{{ __('Next') }}</Button>
      </div>
    </div>

    <!-- Dossier drawer -->
    <div v-if="dossierOpen" class="fixed inset-0 z-40 flex justify-end" @click.self="dossierOpen = false">
      <div class="absolute inset-0 bg-black/30"></div>
      <div class="relative z-10 flex h-full w-full max-w-md flex-col bg-surface-white shadow-xl">
        <div class="flex items-center justify-between border-b border-ink-gray-2 px-4 py-3">
          <div class="min-w-0">
            <h3 class="truncate text-sm font-semibold text-ink-gray-9">{{ dossierTitle }}</h3>
            <p class="text-xs text-ink-gray-4">{{ dossierInstitution }}</p>
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
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { createResource, Button, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'
import LucideSearch from '~icons/lucide/search'
import LucideX from '~icons/lucide/x'

const router = useRouter()

// ---- Filters / paging state ----
const searchTerm = ref('')
const tier = ref('')
const outreachStatus = ref('')
const start = ref(0)
const pageLength = 50

const hasFilters = computed(() => !!(searchTerm.value || tier.value || outreachStatus.value))

// ---- List resource ----
const list = createResource({
  url: 'crm.api.directory.list_contacts',
  auto: true,
  makeParams: () => ({
    search: searchTerm.value || undefined,
    tier: tier.value || undefined,
    outreach_status: outreachStatus.value || undefined,
    start: start.value,
    page_length: pageLength,
  }),
})
const rows = computed(() => list.data?.rows || [])

const rangeStart = computed(() => (list.data?.total ? start.value + 1 : 0))
const rangeEnd = computed(() => start.value + (list.data?.returned ?? 0))

function applyFilters() { start.value = 0; list.reload() }
function clearFilters() {
  searchTerm.value = ''; tier.value = ''; outreachStatus.value = ''; start.value = 0; list.reload()
}
function nextPage() { start.value += pageLength; list.reload() }
function prevPage() { start.value = Math.max(0, start.value - pageLength); list.reload() }

// ---- Facets ----
const facetTiers = ref([])
const facetStatuses = ref([])
createResource({
  url: 'crm.api.directory.contact_facets',
  auto: true,
  onSuccess(d) { facetTiers.value = d?.tiers || []; facetStatuses.value = d?.outreach_statuses || [] },
})

// ---- Dossier drawer ----
const dossierOpen = ref(false)
const dossierTitle = ref('')
const dossierInstitution = ref('')
const dossierLeadId = ref('')
const dossierEngagement = ref('')
const dossier = createResource({ url: 'crm.api.intelligence.get_dossier' })
const dossierText = computed(() => {
  const d = dossier.data
  if (!d) return ''
  return d.formatted || (typeof d === 'string' ? d : JSON.stringify(d.data || d, null, 2))
})
function openDossier(c) {
  dossierTitle.value = c.name || c.prospect
  dossierInstitution.value = c.institution || ''
  dossierLeadId.value = ''
  dossierEngagement.value = c.engagement_slug || ''
  dossierOpen.value = true
  const email = c.email && !c.email.endsWith('.invalid') ? c.email : ''
  if (!email) {
    dossier.data = { formatted: __('No email on file for this contact. Dossiers resolve against CRM Leads by email — backfill the email to enable a full dossier.'), data: {} }
    return
  }
  dossier.submit({ email }).then(() => { dossierLeadId.value = dossier.data?.data?.name || '' })
}
function goToLead(id) { router.push(`/leads/${id}`) }

// ---- Helpers ----
function initials(name) {
  if (!name) return '?'
  const parts = String(name).trim().split(/\s+/)
  return ((parts[0]?.[0] || '') + (parts[parts.length - 1]?.[0] || '')).toUpperCase() || '?'
}
function fmtScore(s) { return s == null ? '—' : Number(s).toFixed(1) }
function tierClass(t) {
  if (t === 'Tier 1' || t === 'Tier1') return 'bg-surface-blue-2 text-ink-blue-6'
  if (t === 'Tier 2' || t === 'Tier2') return 'bg-surface-amber-2 text-ink-amber-3'
  return 'bg-surface-gray-2 text-ink-gray-6'
}
</script>

<style scoped>
.contacts-directory {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}
</style>
