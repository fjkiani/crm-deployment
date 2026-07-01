<template>
  <div class="ci-page">
    <!-- Header -->
    <div class="ci-header">
      <h1>Competitive Intel</h1>
      <div class="ci-sub">
        AACR-2026 competitive-intelligence corpus — CrisPRO opportunities, vulnerabilities, and moat weaknesses
        mined per talk. Opportunity-first.
      </div>
    </div>

    <!-- Metric band -->
    <div class="ci-metrics">
      <div class="ci-metric">
        <div class="ci-metric-val">{{ total }}</div>
        <div class="ci-metric-label">Talks in corpus</div>
      </div>
      <div class="ci-metric opp">
        <div class="ci-metric-val">{{ withOpps }}</div>
        <div class="ci-metric-label">With CrisPRO opportunities</div>
      </div>
      <div class="ci-metric">
        <div class="ci-metric-val">{{ shown }}</div>
        <div class="ci-metric-label">Shown (filtered)</div>
      </div>
    </div>

    <!-- Filters -->
    <div class="ci-filters">
      <input
        v-model="search"
        @input="debouncedReload"
        type="text"
        class="ci-input"
        placeholder="Search talk, session, speaker, institution…"
      />
      <select v-model="presentationType" @change="reload" class="ci-select">
        <option value="">All presentation types</option>
        <option v-for="pt in presentationTypes" :key="pt" :value="pt">{{ pt }}</option>
      </select>
      <label class="ci-check">
        <input type="checkbox" v-model="onlyOpps" @change="reload" />
        Only with opportunities
      </label>
      <button class="ci-btn" @click="reload">Refresh</button>
    </div>

    <!-- Loading / empty -->
    <div v-if="loading" class="ci-state">Loading competitive intel…</div>
    <div v-else-if="rows.length === 0" class="ci-state">No talks match these filters.</div>

    <!-- Corpus table -->
    <div v-else class="ci-table-wrap">
      <table class="ci-table">
        <thead>
          <tr>
            <th class="num">Opps</th>
            <th class="num">Vuln</th>
            <th class="num">Moat</th>
            <th class="num">Risk</th>
            <th class="num">Comp</th>
            <th>Talk</th>
            <th>Speaker</th>
            <th>Institution</th>
            <th>Type</th>
            <th>Lead</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in rows"
            :key="r.intel_id"
            :class="{ 'has-opps': r.n_opportunities > 0, selected: selected && selected.intel_id === r.intel_id }"
            @click="openDetail(r)"
          >
            <td class="num strong">{{ r.n_opportunities }}</td>
            <td class="num">{{ r.n_vulnerabilities }}</td>
            <td class="num">{{ r.n_moat_weaknesses }}</td>
            <td class="num">{{ r.n_trial_risks }}</td>
            <td class="num">{{ r.n_competitors }}</td>
            <td class="ttl">{{ r.talk_title || r.intel_id }}</td>
            <td>{{ r.speaker_name }}</td>
            <td>{{ r.institution }}</td>
            <td>{{ r.presentation_type }}</td>
            <td>
              <a v-if="r.crm_lead" :href="`/crm/leads/${r.crm_lead}`" @click.stop>{{ r.crm_lead }}</a>
              <span v-else class="muted">—</span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div class="ci-pager">
        <button class="ci-btn sm" :disabled="start === 0" @click="prevPage">Prev</button>
        <span>{{ start + 1 }}–{{ Math.min(start + limit, total) }} of {{ total }}</span>
        <button class="ci-btn sm" :disabled="start + limit >= total" @click="nextPage">Next</button>
      </div>
    </div>

    <!-- Detail drawer: full competitive-intel record via get_aacr_intel -->
    <div v-if="selected" class="ci-drawer-backdrop" @click.self="closeDetail">
      <div class="ci-drawer">
        <div class="ci-drawer-head">
          <div class="ci-drawer-title">{{ selected.talk_title || selected.intel_id }}</div>
          <button class="ci-close" @click="closeDetail">×</button>
        </div>
        <div v-if="detailLoading" class="ci-state">Loading detail…</div>
        <IntelPanel
          v-else-if="detail"
          :schema="aacrIntelSchema"
          :record="detail"
          :empty-text="__('No competitive intel for this talk')"
        />
      </div>
    </div>
  </div>
</template>

<script>
import IntelPanel from '@/components/intel/IntelPanel.vue'
import { aacrIntelSchema } from '@/intel/schemas/aacr_intel'

export default {
  name: 'CompetitiveIntel',
  components: { IntelPanel },
  data() {
    return {
      aacrIntelSchema,
      rows: [],
      total: 0,
      withOpps: 0,
      loading: false,
      search: '',
      presentationType: '',
      onlyOpps: false,
      presentationTypes: [
        'translational_science',
        'clinical_trial_results',
        'preclinical_research',
        'basic_science',
        'review_or_perspective',
      ],
      limit: 50,
      start: 0,
      searchTimer: null,
      // detail drawer
      selected: null,
      detail: null,
      detailLoading: false,
    }
  },
  computed: {
    shown() {
      return this.rows.length
    },
  },
  mounted() {
    this.reload()
    this.loadWithOppsCount()
  },
  methods: {
    async reload() {
      this.loading = true
      try {
        const response = await frappe.call({
          method: 'crm.fcrm.doctype.aacr_intel.aacr_intel.list_aacr_intel',
          args: {
            search: this.search || null,
            presentation_type: this.presentationType || null,
            has_opportunities: this.onlyOpps ? 1 : null,
            limit: this.limit,
            start: this.start,
          },
        })
        const data = response.message || { total: 0, rows: [] }
        this.rows = data.rows || []
        this.total = data.total || 0
      } catch (error) {
        frappe.msgprint('Error loading competitive intel: ' + (error.message || error))
      } finally {
        this.loading = false
      }
    },
    async loadWithOppsCount() {
      // Count of corpus talks that have >=1 opportunity (for the metric band).
      try {
        const response = await frappe.call({
          method: 'crm.fcrm.doctype.aacr_intel.aacr_intel.list_aacr_intel',
          args: { has_opportunities: 1, limit: 1, start: 0 },
        })
        this.withOpps = (response.message && response.message.total) || 0
      } catch (e) {
        this.withOpps = 0
      }
    },
    debouncedReload() {
      clearTimeout(this.searchTimer)
      this.searchTimer = setTimeout(() => {
        this.start = 0
        this.reload()
      }, 300)
    },
    nextPage() {
      if (this.start + this.limit < this.total) {
        this.start += this.limit
        this.reload()
      }
    },
    prevPage() {
      if (this.start > 0) {
        this.start = Math.max(0, this.start - this.limit)
        this.reload()
      }
    },
    async openDetail(row) {
      this.selected = row
      this.detail = null
      this.detailLoading = true
      try {
        const response = await frappe.call({
          method: 'crm.fcrm.doctype.aacr_intel.aacr_intel.get_aacr_intel',
          args: { talk_id: row.intel_id },
        })
        this.detail = response.message || null
      } catch (error) {
        frappe.msgprint('Error loading detail: ' + (error.message || error))
      } finally {
        this.detailLoading = false
      }
    },
    closeDetail() {
      this.selected = null
      this.detail = null
    },
  },
}
</script>

<style scoped>
.ci-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  font-family: 'Liberation Sans', 'Arimo', 'Inter', sans-serif;
}
.ci-header h1 {
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
}
.ci-sub {
  color: #6b7280;
  font-size: 13px;
  margin-top: 4px;
  max-width: 760px;
}
.ci-metrics {
  display: flex;
  gap: 16px;
  margin: 20px 0;
}
.ci-metric {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px 20px;
  min-width: 150px;
}
.ci-metric.opp {
  background: linear-gradient(to right, #fef2f2, #fff7ed);
  border-color: #fecaca;
}
.ci-metric-val {
  font-size: 26px;
  font-weight: 700;
  color: #111827;
}
.ci-metric.opp .ci-metric-val {
  color: #dc2626;
}
.ci-metric-label {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}
.ci-filters {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.ci-input {
  flex: 1;
  min-width: 280px;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
}
.ci-select {
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
}
.ci-check {
  font-size: 13px;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 6px;
}
.ci-btn {
  padding: 8px 14px;
  background: #0279ee;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}
.ci-btn.sm {
  padding: 5px 10px;
}
.ci-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ci-state {
  padding: 40px;
  text-align: center;
  color: #9ca3af;
}
.ci-table-wrap {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}
.ci-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.ci-table thead th {
  background: #f9fafb;
  text-align: left;
  padding: 10px 12px;
  font-weight: 600;
  color: #374151;
  border-bottom: 1px solid #e5e7eb;
}
.ci-table th.num,
.ci-table td.num {
  text-align: center;
  width: 52px;
}
.ci-table tbody tr {
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;
}
.ci-table tbody tr:hover {
  background: #f9fafb;
}
.ci-table tbody tr.has-opps {
  background: #fffbf5;
}
.ci-table tbody tr.selected {
  background: #eff6ff;
}
.ci-table td {
  padding: 9px 12px;
  color: #374151;
}
.ci-table td.strong {
  font-weight: 700;
  color: #dc2626;
}
.ci-table td.ttl {
  max-width: 360px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.muted {
  color: #d1d5db;
}
.ci-pager {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 10px 12px;
  font-size: 12px;
  color: #6b7280;
}
.ci-drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 50;
  display: flex;
  justify-content: flex-end;
}
.ci-drawer {
  width: 640px;
  max-width: 92vw;
  background: #fff;
  height: 100%;
  overflow-y: auto;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.12);
}
.ci-drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #e5e7eb;
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 1;
}
.ci-drawer-title {
  font-weight: 700;
  font-size: 15px;
  color: #111827;
}
.ci-close {
  border: none;
  background: none;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  color: #6b7280;
}
</style>
