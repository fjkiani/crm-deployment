<template>
  <LayoutHeader>
    <template #left-header>
      <ViewBreadcrumbs v-model="viewControls" routeName="Organizations" />
    </template>
    <template #right-header>
      <CustomActions
        v-if="organizationsListView?.customListActions"
        :actions="organizationsListView.customListActions"
      />
      <Button
        variant="solid"
        :label="__('Create')"
        iconLeft="plus"
        @click="showOrganizationModal = true"
      />
    </template>
  </LayoutHeader>
  <!-- Brenus organization directory: real engagement companies + prospect
       institutions from live data. Rendered above the native CRM Organization
       list so the page is useful even when no CRM Organization records exist. -->
  <div class="brenus-orgs px-5 pt-4">
    <div class="mb-3 flex items-center justify-between gap-3">
      <div>
        <h2 class="text-base font-semibold text-ink-gray-9">{{ __('Brenus organization directory') }}</h2>
        <p class="text-xs text-ink-gray-5">{{ __('Curated engagement companies and prospect institutions, sourced from live data.') }}</p>
      </div>
      <div class="relative w-56 shrink-0">
        <LucideSearch class="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-gray-4" />
        <input
          v-model="dirSearch"
          type="text"
          :placeholder="__('Filter companies / institutions…')"
          class="w-full rounded-md border border-ink-gray-3 bg-surface-white py-1.5 pl-8 pr-3 text-sm focus:border-ink-blue-4 focus:outline-none"
          @keyup.enter="dir.reload()"
          @input="onDirSearch"
        />
      </div>
    </div>

    <div v-if="dir.loading" class="py-6 text-center text-sm text-ink-gray-5">{{ __('Loading organizations…') }}</div>
    <template v-else-if="dir.data">
      <!-- Engagement companies -->
      <div v-if="engagements.length" class="mb-4">
        <div class="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-gray-5">
          {{ __('Engagement companies') }} ({{ dir.data.engagement_count }})
        </div>
        <div class="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          <router-link
            v-for="e in engagements"
            :key="e.slug"
            :to="`/industry/${e.slug}`"
            class="block rounded-lg border border-ink-gray-2 bg-surface-white p-3 transition hover:border-ink-blue-4 hover:shadow-sm"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="truncate text-sm font-semibold text-ink-gray-9">{{ e.company }}</div>
                <div class="truncate text-xs text-ink-gray-5">{{ e.lead_drug || '—' }}<span v-if="e.target"> · {{ e.target }}</span></div>
              </div>
              <span v-if="e.rank && e.rank < 900" class="shrink-0 rounded bg-surface-blue-2 px-1.5 py-0.5 text-[10px] font-semibold text-ink-blue-6">#{{ e.rank }}</span>
            </div>
            <div class="mt-1.5 flex flex-wrap items-center gap-1.5 text-[10px]">
              <span v-if="e.trial" class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-ink-gray-6">{{ e.trial }}</span>
              <span v-if="e.phase" class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-ink-gray-6">{{ e.phase }}</span>
              <span v-if="e.claim_posture" class="rounded bg-surface-amber-2 px-1.5 py-0.5 text-ink-amber-3">{{ e.claim_posture }}</span>
            </div>
          </router-link>
        </div>
      </div>

      <!-- Prospect institutions -->
      <div v-if="institutions.length">
        <div class="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-ink-gray-5">
          {{ __('Prospect institutions') }}
          <span class="text-ink-gray-4">({{ dir.data.institution_count_shown }} {{ __('of') }} {{ dir.data.institution_count_total }})</span>
        </div>
        <div class="flex flex-wrap gap-1.5">
          <span
            v-for="i in institutions"
            :key="i.institution"
            class="inline-flex items-center gap-1.5 rounded-full border border-ink-gray-2 bg-surface-white px-2.5 py-1 text-xs text-ink-gray-7"
          >
            {{ i.institution }}
            <span class="rounded-full bg-surface-gray-3 px-1.5 text-[10px] font-semibold text-ink-gray-6">{{ i.prospect_count }}</span>
          </span>
        </div>
      </div>

      <div v-if="!engagements.length && !institutions.length" class="py-6 text-center text-sm text-ink-gray-4">
        {{ __('No organizations match this filter.') }}
      </div>
    </template>

    <div class="mt-4 border-t border-ink-gray-2 pt-3 text-[11px] uppercase tracking-wide text-ink-gray-4">{{ __('CRM Organization records') }}</div>
  </div>

  <ViewControls
    ref="viewControls"
    v-model="organizations"
    v-model:loadMore="loadMore"
    v-model:resizeColumn="triggerResize"
    v-model:updatedPageCount="updatedPageCount"
    doctype="CRM Organization"
  />
  <OrganizationsListView
    ref="organizationsListView"
    v-if="organizations.data && rows.length"
    v-model="organizations.data.page_length_count"
    v-model:list="organizations"
    :rows="rows"
    :columns="organizations.data.columns"
    :options="{
      showTooltip: false,
      resizeColumn: true,
      rowCount: organizations.data.row_count,
      totalCount: organizations.data.total_count,
    }"
    @loadMore="() => loadMore++"
    @columnWidthUpdated="() => triggerResize++"
    @updatePageCount="(count) => (updatedPageCount = count)"
    @applyFilter="(data) => viewControls.applyFilter(data)"
    @applyLikeFilter="(data) => viewControls.applyLikeFilter(data)"
    @likeDoc="(data) => viewControls.likeDoc(data)"
    @selectionsChanged="
      (selections) => viewControls.updateSelections(selections)
    "
  />
  <div
    v-else-if="organizations.data"
    class="flex h-full items-center justify-center"
  >
    <div
      class="flex flex-col items-center gap-3 text-xl font-medium text-ink-gray-4"
    >
      <OrganizationsIcon class="h-10 w-10" />
      <span>{{ __('No {0} Found', [__('Organizations')]) }}</span>
      <Button
        :label="__('Create')"
        iconLeft="plus"
        @click="showOrganizationModal = true"
      />
    </div>
  </div>
  <OrganizationModal
    v-if="showOrganizationModal"
    v-model="showOrganizationModal"
  />
</template>
<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import CustomActions from '@/components/CustomActions.vue'
import OrganizationsIcon from '@/components/Icons/OrganizationsIcon.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import OrganizationModal from '@/components/Modals/OrganizationModal.vue'
import OrganizationsListView from '@/components/ListViews/OrganizationsListView.vue'
import ViewControls from '@/components/ViewControls.vue'
import { getMeta } from '@/stores/meta'
import { formatDate, timeAgo, website } from '@/utils'
import { call, createResource } from 'frappe-ui'
import { ref, computed } from 'vue'
import LucideSearch from '~icons/lucide/search'

const { getFormattedPercent, getFormattedFloat, getFormattedCurrency } =
  getMeta('CRM Organization')

// ---- Brenus directory (real engagement companies + prospect institutions) ----
const dirSearch = ref('')
const dir = createResource({
  url: 'crm.api.directory.list_organizations',
  auto: true,
  makeParams: () => ({ search: dirSearch.value || undefined }),
})
const engagements = computed(() => dir.data?.engagements || [])
const institutions = computed(() => dir.data?.institutions || [])
let dirSearchTimer = null
function onDirSearch() {
  clearTimeout(dirSearchTimer)
  dirSearchTimer = setTimeout(() => dir.reload(), 300)
}

const organizationsListView = ref(null)
const showOrganizationModal = ref(false)

// organizations data is loaded in the ViewControls component
const organizations = ref({})
const loadMore = ref(1)
const triggerResize = ref(1)
const updatedPageCount = ref(20)
const viewControls = ref(null)

const rows = computed(() => {
  if (
    !organizations.value?.data?.data ||
    !['list', 'group_by'].includes(organizations.value.data.view_type)
  )
    return []
  return organizations.value?.data.data.map((organization) => {
    let _rows = {}
    organizations.value?.data.rows.forEach((row) => {
      _rows[row] = organization[row]

      let fieldType = organizations.value?.data.columns?.find(
        (col) => (col.key || col.value) == row,
      )?.type

      if (
        fieldType &&
        ['Date', 'Datetime'].includes(fieldType) &&
        !['modified', 'creation'].includes(row)
      ) {
        _rows[row] = formatDate(
          organization[row],
          '',
          true,
          fieldType == 'Datetime',
        )
      }

      if (fieldType && fieldType == 'Currency') {
        _rows[row] = getFormattedCurrency(row, organization)
      }

      if (fieldType && fieldType == 'Float') {
        _rows[row] = getFormattedFloat(row, organization)
      }

      if (fieldType && fieldType == 'Percent') {
        _rows[row] = getFormattedPercent(row, organization)
      }

      if (row === 'organization_name') {
        _rows[row] = {
          label: organization.organization_name,
          logo: organization.organization_logo,
        }
      } else if (row === 'website') {
        _rows[row] = website(organization.website)
      } else if (['modified', 'creation'].includes(row)) {
        _rows[row] = {
          label: formatDate(organization[row]),
          timeAgo: __(timeAgo(organization[row])),
        }
      }
    })
    return _rows
  })
})
</script>
