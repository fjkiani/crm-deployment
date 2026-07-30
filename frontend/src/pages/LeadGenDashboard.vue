<template>
  <div class="leadgen-dashboard">
    <!-- Header -->
    <div class="dashboard-header">
      <h1>Lead Generation Dashboard</h1>
      <div class="header-actions">
        <button @click="runCollectionJob" class="btn btn-primary" :disabled="isJobRunning">
          <i class="fas fa-play"></i> Run Collection
        </button>
        <button @click="runConsolidation" class="btn btn-secondary" :disabled="isJobRunning">
          <i class="fas fa-compress"></i> Consolidate
        </button>
        <button @click="refreshData" class="btn btn-outline">
          <i class="fas fa-sync-alt"></i> Refresh
        </button>
      </div>
    </div>

    <!-- Metrics Cards -->
    <div class="metrics-grid">
      <div class="metric-card">
        <div class="metric-value">{{ metrics.total_prospects }}</div>
        <div class="metric-label">Total Prospects</div>
      </div>
      <div class="metric-card tier-1">
        <div class="metric-value">{{ metrics.tier_counts['Tier 1'] || 0 }}</div>
        <div class="metric-label">Tier 1 Prospects</div>
      </div>
      <div class="metric-card tier-2">
        <div class="metric-value">{{ metrics.tier_counts['Tier 2'] || 0 }}</div>
        <div class="metric-label">Tier 2 Prospects</div>
      </div>
      <div class="metric-card tier-3">
        <div class="metric-value">{{ metrics.tier_counts['Tier 3'] || 0 }}</div>
        <div class="metric-label">Tier 3 Prospects</div>
      </div>
    </div>

    <!-- Filters and Search -->
    <div class="filters-section">
      <div class="filter-group">
        <label>Tier:</label>
        <select v-model="filters.tier" @change="loadProspects">
          <option value="">All Tiers</option>
          <option value="Tier 1">Tier 1</option>
          <option value="Tier 2">Tier 2</option>
          <option value="Tier 3">Tier 3</option>
          <option value="Unassigned">Unassigned</option>
        </select>
      </div>
      <div class="filter-group">
        <label>Source:</label>
        <select v-model="filters.source" @change="loadProspects">
          <option value="">All Sources</option>
          <option value="ClinicalTrials.gov">ClinicalTrials.gov</option>
          <option value="NIH RePORTER">NIH RePORTER</option>
          <option value="ASCO Abstracts">ASCO Abstracts</option>
        </select>
      </div>
      <div class="filter-group">
        <label>Status:</label>
        <select v-model="filters.status" @change="loadProspects">
          <option value="">All Statuses</option>
          <option value="New">New</option>
          <option value="Contacted">Contacted</option>
          <option value="Qualified">Qualified</option>
          <option value="Promoted to CRM Lead">Promoted</option>
          <option value="Discarded">Discarded</option>
        </select>
      </div>
      <div class="filter-group">
        <label>Search:</label>
        <input 
          v-model="searchQuery" 
          @input="debouncedSearch" 
          placeholder="Search by name or institution..."
          class="search-input"
        />
      </div>
    </div>

    <!-- Prospects Table -->
    <div class="prospects-section">
      <div class="section-header">
        <h2>Prospects ({{ prospects.length }})</h2>
        <div class="table-actions">
          <button @click="selectAll" class="btn btn-sm btn-outline">Select All</button>
          <button @click="clearSelection" class="btn btn-sm btn-outline">Clear</button>
          <button @click="promoteSelected" class="btn btn-sm btn-primary" :disabled="selectedProspects.length === 0">
            Promote to CRM Lead ({{ selectedProspects.length }})
          </button>
          <button @click="startOutreachSelected" class="btn btn-sm btn-success" :disabled="selectedProspects.length === 0">
            Start Outreach ({{ selectedProspects.length }})
          </button>
        </div>
      </div>

      <div class="table-container">
        <table class="prospects-table">
          <thead>
            <tr>
              <th><input type="checkbox" v-model="selectAllChecked" @change="toggleSelectAll" /></th>
              <th @click="sortBy('pi_name')" class="sortable">
                Name <i :class="getSortIcon('pi_name')"></i>
              </th>
              <th @click="sortBy('institution')" class="sortable">
                Institution <i :class="getSortIcon('institution')"></i>
              </th>
              <th @click="sortBy('cancer_type')" class="sortable">
                Cancer Type <i :class="getSortIcon('cancer_type')"></i>
              </th>
              <th @click="sortBy('tier')" class="sortable">
                Tier <i :class="getSortIcon('tier')"></i>
              </th>
              <th @click="sortBy('lead_score')" class="sortable">
                Score <i :class="getSortIcon('lead_score')"></i>
              </th>
              <th @click="sortBy('source')" class="sortable">
                Source <i :class="getSortIcon('source')"></i>
              </th>
              <th @click="sortBy('status')" class="sortable">
                Status <i :class="getSortIcon('status')"></i>
              </th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="prospect in paginatedProspects" :key="prospect.name" 
                :class="{ 'selected': selectedProspects.includes(prospect.name) }">
              <td>
                <input type="checkbox" 
                       :value="prospect.name" 
                       v-model="selectedProspects" />
              </td>
              <td>{{ prospect.pi_name }}</td>
              <td>{{ prospect.institution }}</td>
              <td>{{ prospect.cancer_type }}</td>
              <td>
                <span :class="`tier-badge tier-${prospect.tier?.toLowerCase().replace(' ', '-')}`">
                  {{ prospect.tier }}
                </span>
              </td>
              <td>
                <div class="score-bar">
                  <div class="score-fill" :style="{ width: (prospect.lead_score * 100) + '%' }"></div>
                  <span class="score-text">{{ (prospect.lead_score * 100).toFixed(1) }}%</span>
                </div>
              </td>
              <td>{{ prospect.source }}</td>
              <td>
                <span :class="`status-badge status-${prospect.status?.toLowerCase().replace(' ', '-')}`">
                  {{ prospect.status }}
                </span>
              </td>
              <td class="actions">
                <button @click="viewProspect(prospect)" class="btn btn-sm btn-outline">
                  <i class="fas fa-eye"></i>
                </button>
                <button @click="editProspect(prospect)" class="btn btn-sm btn-outline">
                  <i class="fas fa-edit"></i>
                </button>
                <button @click="promoteProspect(prospect)" class="btn btn-sm btn-primary">
                  <i class="fas fa-arrow-up"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="pagination">
        <button @click="previousPage" :disabled="currentPage === 1" class="btn btn-sm btn-outline">
          <i class="fas fa-chevron-left"></i> Previous
        </button>
        <span class="page-info">
          Page {{ currentPage }} of {{ totalPages }} ({{ prospects.length }} total)
        </span>
        <button @click="nextPage" :disabled="currentPage === totalPages" class="btn btn-sm btn-outline">
          Next <i class="fas fa-chevron-right"></i>
        </button>
      </div>
    </div>

    <!-- Job Status Modal -->
    <div v-if="showJobModal" class="modal-overlay" @click="closeJobModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Job Status</h3>
          <button @click="closeJobModal" class="btn btn-sm btn-outline">×</button>
        </div>
        <div class="modal-body">
          <div v-if="currentJob" class="job-status">
            <div class="job-info">
              <strong>{{ currentJob.job_type }}</strong>
              <span :class="`status-badge status-${currentJob.status.toLowerCase()}`">
                {{ currentJob.status }}
              </span>
            </div>
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: currentJob.progress + '%' }"></div>
            </div>
            <div class="job-details">
              <p>Records Processed: {{ currentJob.records_processed || 0 }}</p>
              <p v-if="currentJob.log">{{ currentJob.log }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Prospect Detail Modal -->
    <div v-if="showProspectModal" class="modal-overlay" @click="closeProspectModal">
      <div class="modal-content large" @click.stop>
        <div class="modal-header">
          <h3>{{ selectedProspect?.pi_name }}</h3>
          <button @click="closeProspectModal" class="btn btn-sm btn-outline">×</button>
        </div>
        <div class="modal-body">
          <div v-if="selectedProspect" class="prospect-details">
            <div class="detail-grid">
              <div class="detail-item">
                <label>Institution:</label>
                <span>{{ selectedProspect.institution }}</span>
              </div>
              <div class="detail-item">
                <label>Cancer Type:</label>
                <span>{{ selectedProspect.cancer_type }}</span>
              </div>
              <div class="detail-item">
                <label>Tier:</label>
                <span :class="`tier-badge tier-${selectedProspect.tier?.toLowerCase().replace(' ', '-')}`">
                  {{ selectedProspect.tier }}
                </span>
              </div>
              <div class="detail-item">
                <label>Lead Score:</label>
                <span>{{ (selectedProspect.lead_score * 100).toFixed(1) }}%</span>
              </div>
              <div class="detail-item">
                <label>Source:</label>
                <span>{{ selectedProspect.source }}</span>
              </div>
              <div class="detail-item">
                <label>Status:</label>
                <span :class="`status-badge status-${selectedProspect.status?.toLowerCase().replace(' ', '-')}`">
                  {{ selectedProspect.status }}
                </span>
              </div>
            </div>
            <div v-if="selectedProspect.notes" class="notes-section">
              <h4>Notes:</h4>
              <p>{{ selectedProspect.notes }}</p>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="promoteProspect(selectedProspect)" class="btn btn-primary">
            Promote to CRM Lead
          </button>
          <button @click="startOutreach(selectedProspect)" class="btn btn-success">
            Start Outreach
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LeadGenDashboard',
  data() {
    return {
      prospects: [],
      metrics: {
        total_prospects: 0,
        tier_counts: {},
        status_counts: {},
        recent_jobs: []
      },
      filters: {
        tier: '',
        source: '',
        status: ''
      },
      searchQuery: '',
      selectedProspects: [],
      selectAllChecked: false,
      sortField: 'lead_score',
      sortOrder: 'desc',
      currentPage: 1,
      pageSize: 20,
      showJobModal: false,
      showProspectModal: false,
      currentJob: null,
      selectedProspect: null,
      isJobRunning: false,
      searchTimeout: null
    }
  },
  computed: {
    filteredProspects() {
      let filtered = this.prospects

      // Apply filters
      if (this.filters.tier) {
        filtered = filtered.filter(p => p.tier === this.filters.tier)
      }
      if (this.filters.source) {
        filtered = filtered.filter(p => p.source === this.filters.source)
      }
      if (this.filters.status) {
        filtered = filtered.filter(p => p.status === this.filters.status)
      }

      // Apply search
      if (this.searchQuery) {
        const query = this.searchQuery.toLowerCase()
        filtered = filtered.filter(p => 
          p.pi_name?.toLowerCase().includes(query) ||
          p.institution?.toLowerCase().includes(query) ||
          p.cancer_type?.toLowerCase().includes(query)
        )
      }

      // Apply sorting
      filtered.sort((a, b) => {
        const aVal = a[this.sortField] || ''
        const bVal = b[this.sortField] || ''
        
        if (this.sortOrder === 'asc') {
          return aVal > bVal ? 1 : -1
        } else {
          return aVal < bVal ? 1 : -1
        }
      })

      return filtered
    },
    paginatedProspects() {
      const start = (this.currentPage - 1) * this.pageSize
      const end = start + this.pageSize
      return this.filteredProspects.slice(start, end)
    },
    totalPages() {
      return Math.ceil(this.filteredProspects.length / this.pageSize)
    }
  },
  mounted() {
    this.loadData()
  },
  methods: {
    async loadData() {
      await Promise.all([
        this.loadProspects(),
        this.loadMetrics()
      ])
    },
    async loadProspects() {
      try {
        const filters = {}
        if (this.filters.tier) filters.tier = this.filters.tier
        if (this.filters.source) filters.source = this.filters.source
        if (this.filters.status) filters.status = this.filters.status

        const response = await frappe.call({
          method: 'crm.api.leadgen.get_prospects',
          args: {
            filters: filters,
            limit: 1000
          }
        })

        this.prospects = response.message || []
      } catch (error) {
        frappe.msgprint('Error loading prospects: ' + error.message)
      }
    },
    async loadMetrics() {
      try {
        const response = await frappe.call({
          method: 'crm.api.leadgen.get_dashboard_metrics'
        })

        this.metrics = response.message || {}
      } catch (error) {
        frappe.msgprint('Error loading metrics: ' + error.message)
      }
    },
    debouncedSearch() {
      clearTimeout(this.searchTimeout)
      this.searchTimeout = setTimeout(() => {
        this.currentPage = 1
      }, 300)
    },
    sortBy(field) {
      if (this.sortField === field) {
        this.sortOrder = this.sortOrder === 'asc' ? 'desc' : 'asc'
      } else {
        this.sortField = field
        this.sortOrder = 'desc'
      }
    },
    getSortIcon(field) {
      if (this.sortField !== field) return 'fas fa-sort'
      return this.sortOrder === 'asc' ? 'fas fa-sort-up' : 'fas fa-sort-down'
    },
    selectAll() {
      this.selectedProspects = this.paginatedProspects.map(p => p.name)
      this.selectAllChecked = true
    },
    clearSelection() {
      this.selectedProspects = []
      this.selectAllChecked = false
    },
    toggleSelectAll() {
      if (this.selectAllChecked) {
        this.selectAll()
      } else {
        this.clearSelection()
      }
    },
    previousPage() {
      if (this.currentPage > 1) {
        this.currentPage--
        this.clearSelection()
      }
    },
    nextPage() {
      if (this.currentPage < this.totalPages) {
        this.currentPage++
        this.clearSelection()
      }
    },
    async runCollectionJob() {
      this.isJobRunning = true
      try {
        const response = await frappe.call({
          method: 'crm.api.leadgen.run_leadgen_job',
          args: {
            job_type: 'clinicaltrials',
            params: { max_pages: 5 }
          }
        })

        this.currentJob = {
          name: response.message.job_name,
          job_type: 'ClinicalTrials Collection',
          status: 'Queued',
          progress: 0,
          records_processed: 0
        }
        this.showJobModal = true
        this.pollJobStatus()
      } catch (error) {
        frappe.msgprint('Error starting collection job: ' + error.message)
      } finally {
        this.isJobRunning = false
      }
    },
    async runConsolidation() {
      this.isJobRunning = true
      try {
        const response = await frappe.call({
          method: 'crm.api.leadgen.consolidate_prospects'
        })

        this.currentJob = {
          name: response.message.job_name,
          job_type: 'Consolidation',
          status: 'Queued',
          progress: 0,
          records_processed: 0
        }
        this.showJobModal = true
        this.pollJobStatus()
      } catch (error) {
        frappe.msgprint('Error starting consolidation: ' + error.message)
      } finally {
        this.isJobRunning = false
      }
    },
    async pollJobStatus() {
      if (!this.currentJob) return

      try {
        const response = await frappe.call({
          method: 'crm.api.leadgen.job_status',
          args: { job_name: this.currentJob.name }
        })

        this.currentJob = { ...this.currentJob, ...response.message }

        if (this.currentJob.status === 'Running') {
          setTimeout(() => this.pollJobStatus(), 2000)
        } else if (this.currentJob.status === 'Completed') {
          setTimeout(() => {
            this.closeJobModal()
            this.loadData()
          }, 2000)
        }
      } catch (error) {
        console.error('Error polling job status:', error)
      }
    },
    async promoteSelected() {
      if (this.selectedProspects.length === 0) return

      try {
        const response = await frappe.call({
          method: 'crm.api.leadgen.promote_prospects',
          args: { prospect_names: this.selectedProspects }
        })

        frappe.msgprint(response.message.message)
        this.clearSelection()
        this.loadData()
      } catch (error) {
        frappe.msgprint('Error promoting prospects: ' + error.message)
      }
    },
    async promoteProspect(prospect) {
      try {
        const response = await frappe.call({
          method: 'crm.api.leadgen.promote_prospects',
          args: { prospect_names: [prospect.name] }
        })

        frappe.msgprint(response.message.message)
        this.loadData()
        // WP7.3 — a promotion is a real step forward: land on the new CRM Lead.
        const leadName = response.message.promoted_to_lead
        if (leadName) this.$router.push({ name: 'Lead', params: { leadId: leadName } })
      } catch (error) {
        frappe.msgprint('Error promoting prospect: ' + error.message)
      }
    },
    async startOutreachSelected() {
      if (this.selectedProspects.length === 0) return

      // For now, use the default Tier 1 sequence
      const sequenceName = 'Tier 1 - High Priority Outreach'
      
      try {
        const response = await frappe.call({
          method: 'crm.api.leadgen.start_outreach_sequence',
          args: { 
            prospect_names: this.selectedProspects,
            sequence_name: sequenceName
          }
        })

        frappe.msgprint(response.message.message)
        this.clearSelection()
        this.loadData()
      } catch (error) {
        frappe.msgprint('Error starting outreach: ' + error.message)
      }
    },
    async startOutreach(prospect) {
      const sequenceName = 'Tier 1 - High Priority Outreach'
      
      try {
        const response = await frappe.call({
          method: 'crm.api.leadgen.start_outreach_sequence',
          args: { 
            prospect_names: [prospect.name],
            sequence_name: sequenceName
          }
        })

        const r = response.message || {}
        frappe.msgprint(r.message)
        this.loadData()
        // WP7.3 — jump to the Nyx campaign surface focused on this sequence.
        if ((r.started_count || 0) > 0) {
          this.$router.push({ name: 'Nyx', query: { sequence: sequenceName } })
        }
      } catch (error) {
        frappe.msgprint('Error starting outreach: ' + error.message)
      }
    },
    viewProspect(prospect) {
      this.selectedProspect = prospect
      this.showProspectModal = true
    },
    editProspect(prospect) {
      // Open prospect form for editing
      frappe.set_route('Form', 'Lead Prospect', prospect.name)
    },
    refreshData() {
      this.loadData()
    },
    closeJobModal() {
      this.showJobModal = false
      this.currentJob = null
    },
    closeProspectModal() {
      this.showProspectModal = false
      this.selectedProspect = null
    }
  }
}
</script>

<style scoped>
.leadgen-dashboard {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid #e0e0e0;
}

.dashboard-header h1 {
  margin: 0;
  color: #2c3e50;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.metric-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  text-align: center;
}

.metric-value {
  font-size: 2.5em;
  font-weight: bold;
  color: #2c3e50;
}

.metric-label {
  color: #7f8c8d;
  margin-top: 5px;
}

.tier-1 .metric-value { color: #e74c3c; }
.tier-2 .metric-value { color: #f39c12; }
.tier-3 .metric-value { color: #27ae60; }

.filters-section {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-weight: 500;
  min-width: 60px;
}

.search-input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  min-width: 250px;
}

.prospects-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.table-actions {
  display: flex;
  gap: 10px;
}

.table-container {
  overflow-x: auto;
}

.prospects-table {
  width: 100%;
  border-collapse: collapse;
}

.prospects-table th,
.prospects-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.prospects-table th {
  background: #f8f9fa;
  font-weight: 600;
  cursor: pointer;
}

.prospects-table th.sortable:hover {
  background: #e9ecef;
}

.prospects-table tr.selected {
  background: #e3f2fd;
}

.tier-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: 500;
}

.tier-tier-1 { background: #ffebee; color: #c62828; }
.tier-tier-2 { background: #fff3e0; color: #ef6c00; }
.tier-tier-3 { background: #e8f5e8; color: #2e7d32; }
.tier-unassigned { background: #f5f5f5; color: #666; }

.status-badge {
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: 500;
}

.status-new { background: #e3f2fd; color: #1976d2; }
.status-contacted { background: #fff3e0; color: #f57c00; }
.status-qualified { background: #e8f5e8; color: #388e3c; }
.status-promoted-to-crm-lead { background: #f3e5f5; color: #7b1fa2; }
.status-discarded { background: #ffebee; color: #d32f2f; }

.score-bar {
  position: relative;
  width: 80px;
  height: 20px;
  background: #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  background: linear-gradient(90deg, #e74c3c, #f39c12, #27ae60);
  transition: width 0.3s ease;
}

.score-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.7em;
  font-weight: 500;
  color: #2c3e50;
}

.actions {
  display: flex;
  gap: 5px;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  padding: 20px;
  border-top: 1px solid #e0e0e0;
}

.page-info {
  font-weight: 500;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-content.large {
  max-width: 800px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.job-status {
  text-align: center;
}

.job-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.progress-bar {
  width: 100%;
  height: 20px;
  background: #e0e0e0;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 15px;
}

.progress-fill {
  height: 100%;
  background: #27ae60;
  transition: width 0.3s ease;
}

.job-details p {
  margin: 5px 0;
  color: #666;
}

.prospect-details {
  max-height: 400px;
  overflow-y: auto;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.detail-item label {
  font-weight: 600;
  color: #2c3e50;
}

.notes-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
}

.notes-section h4 {
  margin-bottom: 10px;
  color: #2c3e50;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
}

.btn-secondary {
  background: #95a5a6;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #7f8c8d;
}

.btn-success {
  background: #27ae60;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background: #229954;
}

.btn-outline {
  background: transparent;
  color: #3498db;
  border: 1px solid #3498db;
}

.btn-outline:hover:not(:disabled) {
  background: #3498db;
  color: white;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}
</style>


