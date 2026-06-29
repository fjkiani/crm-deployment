<template>
  <div class="nyx-dashboard">
    <!-- Header -->
    <div class="nyx-dashboard-header">
      <div class="nyx-logo">
        <span class="nyx-glyph">🔱</span>
        <span>Nyx Intelligence — Pipeline Command Center</span>
      </div>
      <div class="nyx-header-actions">
        <label class="nyx-btn nyx-btn-upload">
          📎 Upload CSV
          <input type="file" accept=".csv,.tsv" @change="handleCSVUpload" style="display:none" />
        </label>
        <button class="nyx-btn nyx-btn-secondary" @click="loadData" :disabled="loading">
          {{ loading ? '⟳ Refreshing...' : '↻ Refresh' }}
        </button>
        <button class="nyx-btn nyx-btn-fire" @click="fireDueSteps" :disabled="firing">
          {{ firing ? '⚡ Firing...' : '⚡ Fire Due Steps' }}
        </button>
      </div>
    </div>

    <!-- Bulk Enrichment Progress -->
    <div v-if="bulkStatus" class="nyx-bulk-progress">
      <div class="nyx-bulk-header">
        <span>{{ bulkStatus.message }}</span>
        <span class="nyx-bulk-count">{{ bulkStatus.done }}/{{ bulkStatus.total }}</span>
      </div>
      <div class="nyx-bulk-bar">
        <div class="nyx-bulk-fill" :style="{ width: bulkPct + '%' }"></div>
      </div>
      <div v-if="bulkStatus.current" class="nyx-bulk-current">
        Processing: {{ bulkStatus.current }}
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <!-- PHASE 10: ANALYTICS PANELS                                        -->
    <!-- ═══════════════════════════════════════════════════════════════════ -->

    <!-- KPI Bar (upgraded) -->
    <div class="nyx-kpi-bar">
      <div class="nyx-kpi">
        <div class="nyx-kpi-value">{{ analytics.total_leads }}</div>
        <div class="nyx-kpi-label">Total Leads</div>
      </div>
      <div class="nyx-kpi">
        <div class="nyx-kpi-value nyx-green">{{ analytics.total_enriched }}</div>
        <div class="nyx-kpi-label">Enriched</div>
      </div>
      <div class="nyx-kpi">
        <div class="nyx-kpi-value nyx-blue">{{ analytics.enrichment_coverage }}%</div>
        <div class="nyx-kpi-label">Coverage</div>
      </div>
      <div class="nyx-kpi">
        <div class="nyx-kpi-value nyx-accent">{{ analytics.total_entangled }}</div>
        <div class="nyx-kpi-label">Entangled</div>
      </div>
      <div class="nyx-kpi">
        <div class="nyx-kpi-value nyx-red">{{ analytics.total_vulture_events }}</div>
        <div class="nyx-kpi-label">Vulture Events</div>
      </div>
    </div>

    <!-- Funnel + A/B Row -->
    <div class="nyx-analytics-row">
      <!-- Conversion Funnel -->
      <div class="nyx-panel">
        <div class="nyx-panel-title">📊 Conversion Funnel</div>
        <div class="nyx-funnel">
          <div v-for="(stage, idx) in funnelStages" :key="stage.label" class="nyx-funnel-stage">
            <div class="nyx-funnel-bar-wrap">
              <div class="nyx-funnel-bar" :style="{ width: stage.pct + '%', background: stage.color }"></div>
            </div>
            <div class="nyx-funnel-info">
              <span class="nyx-funnel-label">{{ stage.label }}</span>
              <span class="nyx-funnel-count">{{ stage.count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- A/B Framework Testing -->
      <div class="nyx-panel">
        <div class="nyx-panel-title">🧪 Framework A/B Testing</div>
        <div class="nyx-ab-grid">
          <div v-for="fw in frameworkStats" :key="fw.name" class="nyx-ab-card" :style="{ borderColor: fw.color }">
            <div class="nyx-ab-name">{{ fw.name }}</div>
            <div class="nyx-ab-value" :style="{ color: fw.color }">{{ fw.count }}</div>
            <div class="nyx-ab-pct">{{ fw.pct }}%</div>
            <div class="nyx-ab-bar">
              <div class="nyx-ab-fill" :style="{ width: fw.pct + '%', background: fw.color }"></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Fire Steps Result -->
    <div v-if="fireResult" class="nyx-alert" :class="fireResult.errors > 0 ? 'nyx-alert-warning' : 'nyx-alert-success'">
      ⚡ Fired {{ fireResult.fired }} steps | {{ fireResult.errors }} errors
    </div>

    <!-- Leads Table -->
    <div class="nyx-table-wrapper">
      <table class="nyx-table">
        <thead>
          <tr>
            <th>Lead</th>
            <th>Company</th>
            <th>Title</th>
            <th>Email</th>
            <th>Phone</th>
            <th>Intel</th>
            <th>Status</th>
            <th>Added</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="8" class="nyx-loading">Loading CRM leads...</td>
          </tr>
          <tr v-else-if="leads.length === 0">
            <td colspan="8" class="nyx-loading">No enriched leads yet. Run a pipeline from <a href="/crm/nyx" class="nyx-link">Nyx</a> or upload a CSV.</td>
          </tr>
          <tr v-for="lead in leads" :key="lead.name" class="nyx-row" @click="goToLead(lead.name)" style="cursor: pointer;">
            <td>
              <div class="nyx-name">{{ lead.lead_name || '—' }}</div>
            </td>
            <td>{{ lead.organization || '—' }}</td>
            <td class="nyx-subject">{{ lead.job_title || '—' }}</td>
            <td>
              <span class="nyx-email-small">{{ lead.email || '—' }}</span>
            </td>
            <td>
              <span class="nyx-email-small">{{ lead.mobile_no || '—' }}</span>
            </td>
            <td>
              <span v-if="lead.latest_note_title" class="nyx-badge-intel" :title="lead.latest_note_title">
                📝 {{ lead.latest_note_title.substring(0, 30) }}
              </span>
              <span v-else class="nyx-muted">—</span>
            </td>
            <td>
              <span class="nyx-status-badge" :class="statusClass(lead.status)">
                {{ lead.status || 'Open' }}
              </span>
            </td>
            <td class="nyx-date">{{ formatDate(lead.creation) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const EAIA_URL = 'http://127.0.0.1:8787'

export default {
  name: 'NyxDashboard',
  setup() {
    const router = useRouter()
    const leads = ref([])
    const loading = ref(false)
    const firing = ref(false)
    const fireResult = ref(null)
    const bulkStatus = ref(null)

    // Phase 10: Analytics state
    const analyticsRaw = ref({})
    const analytics = computed(() => {
      const m = analyticsRaw.value?.metrics || {}
      return {
        total_leads: m.total_leads || 0,
        total_enriched: m.total_enriched || 0,
        enrichment_coverage: m.enrichment_coverage || 0,
        total_entangled: m.total_entangled || 0,
        total_vulture_events: m.total_vulture_events || 0,
      }
    })

    // Funnel stages computed from analytics
    const funnelStages = computed(() => {
      const funnel = analyticsRaw.value?.funnel || {}
      const total = analytics.value.total_leads || 1
      const stages = [
        { label: 'Open', count: funnel['Open'] || 0, color: '#3b82f6' },
        { label: 'Draft Ready', count: funnel['Draft Ready'] || 0, color: '#8b5cf6' },
        { label: 'Contacted', count: funnel['Contacted'] || 0, color: '#a855f7' },
        { label: 'Replied', count: funnel['Replied'] || 0, color: '#10b981' },
        { label: 'Qualified', count: funnel['Qualified'] || 0, color: '#059669' },
        { label: 'Converted', count: funnel['Converted'] || 0, color: '#eab308' },
        { label: 'Do Not Contact', count: funnel['Do Not Contact'] || 0, color: '#ef4444' },
      ]
      return stages.map(s => ({ ...s, pct: Math.round((s.count / total) * 100) }))
    })

    // A/B framework stats
    const frameworkStats = computed(() => {
      const fw = analyticsRaw.value?.frameworks || {}
      const total = (fw.challenger || 0) + (fw.pas || 0) + (fw.aida || 0) + (fw.unknown || 0) || 1
      return [
        { name: 'CHALLENGER', count: fw.challenger || 0, color: '#6366f1', pct: Math.round(((fw.challenger || 0) / total) * 100) },
        { name: 'PAS', count: fw.pas || 0, color: '#f59e0b', pct: Math.round(((fw.pas || 0) / total) * 100) },
        { name: 'AIDA', count: fw.aida || 0, color: '#10b981', pct: Math.round(((fw.aida || 0) / total) * 100) },
      ]
    })

    const bulkPct = computed(() => {
      if (!bulkStatus.value) return 0
      return Math.round((bulkStatus.value.done / bulkStatus.value.total) * 100)
    })

    const loadData = async () => {
      loading.value = true
      try {
        const res = await fetch(`${EAIA_URL}/crm-leads`)
        const data = await res.json()
        leads.value = data.leads || []
      } catch (e) {
        console.error('Dashboard load error:', e)
        try {
          const res = await fetch('/api/method/crm.api.sequence_manager.get_pipeline_runs', {
            headers: { 'X-Frappe-Csrf-Token': window.csrf_token || '' }
          })
          const data = await res.json()
          leads.value = (data.message || []).map(r => ({
            name: r.name,
            lead_name: r.pi_name,
            email: r.pi_email,
            organization: r.institution,
            status: r.outreach_status || 'Open',
            creation: r.creation,
            latest_note_title: r.email_subject ? `Score: ${r.lead_score}` : '',
          }))
        } catch (e2) {
          console.error('Fallback load also failed:', e2)
        }
      } finally {
        loading.value = false
      }
    }

    // Phase 10: Load analytics from EAIA backend
    const loadAnalytics = async () => {
      try {
        const res = await fetch(`${EAIA_URL}/analytics/health`)
        const json = await res.json()
        if (json.status === 'success' && json.data) {
          analyticsRaw.value = json.data
        }
      } catch (e) {
        console.error('Analytics load error:', e)
        // If EAIA is down and we loaded leads, compute basic stats client-side
        if (leads.value.length > 0) {
          const funnel = {}
          leads.value.forEach(l => {
            const s = l.status || 'Open'
            funnel[s] = (funnel[s] || 0) + 1
          })
          analyticsRaw.value = {
            funnel,
            frameworks: {},
            metrics: {
              total_leads: leads.value.length,
              total_enriched: leads.value.filter(l => l.latest_note_title).length,
              enrichment_coverage: Math.round((leads.value.filter(l => l.latest_note_title).length / leads.value.length) * 100),
              total_entangled: 0,
              total_vulture_events: 0,
            }
          }
        }
      }
    }

    const goToLead = (leadName) => {
      if (leadName) {
        router.push(`/leads/${leadName}`)
      }
    }

    const handleCSVUpload = async (event) => {
      const file = event.target.files?.[0]
      if (!file) return

      const text = await file.text()
      const lines = text.trim().split('\n')
      if (lines.length < 2) {
        alert('CSV must have a header row and at least one data row')
        return
      }

      const headers = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/"/g, ''))
      const nameIdx = headers.findIndex(h => h.includes('name') || h === 'prospect')
      const companyIdx = headers.findIndex(h => h.includes('company') || h.includes('org'))

      if (nameIdx === -1 || companyIdx === -1) {
        alert('CSV must have "Name" and "Company" columns')
        return
      }

      const csvLeads = []
      for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(',').map(c => c.trim().replace(/"/g, ''))
        if (cols[nameIdx] && cols[companyIdx]) {
          csvLeads.push({
            prospect_name: cols[nameIdx],
            company_name: cols[companyIdx]
          })
        }
      }

      if (csvLeads.length === 0) {
        alert('No valid leads found in CSV')
        return
      }

      bulkStatus.value = {
        message: `Enriching ${csvLeads.length} leads...`,
        total: csvLeads.length,
        done: 0,
        current: csvLeads[0]?.prospect_name || ''
      }

      try {
        const res = await fetch(`${EAIA_URL}/bulk-enrich`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ leads: csvLeads })
        })

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop()

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            try {
              const evt = JSON.parse(line.slice(6))
              if (evt.event === 'bulk-lead-start') {
                bulkStatus.value.current = `${evt.name} @ ${evt.company}`
              } else if (evt.event === 'bulk-lead-complete') {
                bulkStatus.value.done = evt.index + 1
                bulkStatus.value.message = `Enriched ${evt.index + 1}/${bulkStatus.value.total}`
              } else if (evt.event === 'bulk-lead-error') {
                bulkStatus.value.done = evt.index + 1
                bulkStatus.value.message = `Error on ${evt.name}: ${evt.error?.substring(0, 80)}`
              } else if (evt.event === 'bulk-complete') {
                bulkStatus.value.message = `✅ Done — ${bulkStatus.value.total} leads processed`
                bulkStatus.value.current = ''
                await loadData()
                await loadAnalytics()
              }
            } catch (pe) { /* ignore parse errors */ }
          }
        }
      } catch (e) {
        console.error('Bulk enrich error:', e)
        bulkStatus.value.message = `❌ Error: ${e.message}`
      }

      event.target.value = ''
    }

    const fireDueSteps = async () => {
      firing.value = true
      fireResult.value = null
      try {
        const res = await fetch('/api/method/crm.api.sequence_manager.fire_due_steps', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Frappe-Csrf-Token': window.csrf_token || ''
          }
        })
        const data = await res.json()
        fireResult.value = data.message
        await loadData()
      } catch (e) {
        console.error('Fire due steps error:', e)
      } finally {
        firing.value = false
      }
    }

    const statusClass = (status) => {
      const map = {
        'Replied': 'nyx-status-sent',
        'Open': 'nyx-status-pending',
        'Converted': 'nyx-status-done',
        'Do Not Contact': 'nyx-status-unsub',
        'Draft Ready': 'nyx-status-draft',
        'Contacted': 'nyx-status-contacted',
        'Qualified': 'nyx-status-qualified',
      }
      return map[status] || 'nyx-status-pending'
    }

    const formatDate = (dt) => {
      if (!dt) return '—'
      return new Date(dt).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    }

    onMounted(async () => {
      await loadData()
      await loadAnalytics()
    })

    return {
      leads, loading, firing, fireResult, bulkStatus, bulkPct,
      analytics, analyticsRaw, funnelStages, frameworkStats,
      loadData, goToLead, handleCSVUpload, fireDueSteps, statusClass, formatDate
    }
  }
}
</script>

<style scoped>
.nyx-dashboard {
  background: #0f172a;
  min-height: 100vh;
  padding: 24px;
  font-family: 'Inter', system-ui, sans-serif;
  color: #e2e8f0;
}

.nyx-dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.nyx-logo {
  font-size: 18px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(135deg, #a855f7, #6366f1);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.nyx-glyph { font-size: 22px; -webkit-text-fill-color: #a855f7; }

.nyx-header-actions { display: flex; gap: 10px; }

.nyx-btn {
  padding: 8px 18px;
  border-radius: 8px;
  border: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.nyx-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.nyx-btn-secondary { background: #1e293b; color: #94a3b8; border: 1px solid #334155; }
.nyx-btn-secondary:hover:not(:disabled) { background: #334155; color: #e2e8f0; }
.nyx-btn-fire { background: linear-gradient(135deg, #6366f1, #a855f7); color: white; }
.nyx-btn-fire:hover:not(:disabled) { opacity: 0.85; transform: translateY(-1px); }
.nyx-btn-upload {
  background: linear-gradient(135deg, #10b981, #059669);
  color: white;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.nyx-btn-upload:hover { opacity: 0.85; transform: translateY(-1px); }

/* Bulk progress */
.nyx-bulk-progress {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}
.nyx-bulk-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
}
.nyx-bulk-count { color: #a855f7; }
.nyx-bulk-bar {
  height: 6px;
  background: #334155;
  border-radius: 3px;
  overflow: hidden;
}
.nyx-bulk-fill {
  height: 100%;
  background: linear-gradient(90deg, #6366f1, #a855f7);
  border-radius: 3px;
  transition: width 0.4s ease;
}
.nyx-bulk-current { font-size: 11px; color: #64748b; margin-top: 6px; }

/* KPI Bar */
.nyx-kpi-bar {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.nyx-kpi {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  transition: border-color 0.2s, transform 0.2s;
}
.nyx-kpi:hover {
  border-color: #6366f1;
  transform: translateY(-2px);
}

.nyx-kpi-value { font-size: 28px; font-weight: 800; }
.nyx-kpi-label { font-size: 11px; color: #64748b; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.05em; }
.nyx-green { color: #10b981; }
.nyx-blue { color: #3b82f6; }
.nyx-accent { color: #6366f1; }
.nyx-red { color: #ef4444; }

/* Analytics Row */
.nyx-analytics-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.nyx-panel {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 20px;
}
.nyx-panel-title {
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 16px;
  color: #e2e8f0;
}

/* Funnel */
.nyx-funnel { display: flex; flex-direction: column; gap: 8px; }
.nyx-funnel-stage { display: flex; flex-direction: column; gap: 3px; }
.nyx-funnel-bar-wrap {
  height: 8px;
  background: #0f172a;
  border-radius: 4px;
  overflow: hidden;
}
.nyx-funnel-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
  min-width: 2px;
}
.nyx-funnel-info {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
}
.nyx-funnel-label { color: #94a3b8; }
.nyx-funnel-count { font-weight: 700; color: #e2e8f0; }

/* A/B Testing */
.nyx-ab-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.nyx-ab-card {
  background: #0f172a;
  border: 1px solid #334155;
  border-left: 3px solid;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}
.nyx-ab-name { font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
.nyx-ab-value { font-size: 24px; font-weight: 800; }
.nyx-ab-pct { font-size: 11px; color: #64748b; margin-bottom: 6px; }
.nyx-ab-bar { height: 4px; background: #1e293b; border-radius: 2px; overflow: hidden; }
.nyx-ab-fill { height: 100%; border-radius: 2px; transition: width 0.6s ease; }

/* Alerts */
.nyx-alert {
  padding: 10px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
  font-weight: 600;
}
.nyx-alert-success { background: #064e3b; color: #6ee7b7; border: 1px solid #10b981; }
.nyx-alert-warning { background: #451a03; color: #fcd34d; border: 1px solid #f59e0b; }

/* Table */
.nyx-table-wrapper {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  overflow: hidden;
}

.nyx-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.nyx-table thead th {
  background: #0f172a;
  padding: 12px 14px;
  text-align: left;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #475569;
  border-bottom: 1px solid #334155;
}

.nyx-row {
  border-bottom: 1px solid #1e293b;
  transition: background 0.1s;
}
.nyx-row:hover { background: #243044; }

.nyx-table td { padding: 12px 14px; vertical-align: middle; }

.nyx-name { font-weight: 600; color: #e2e8f0; }
.nyx-email-small { font-size: 11px; color: #475569; }
.nyx-muted { color: #475569; font-size: 12px; }
.nyx-date { font-size: 12px; color: #475569; white-space: nowrap; }
.nyx-subject { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: #94a3b8; }
.nyx-loading { text-align: center; padding: 40px; color: #475569; }
.nyx-link { color: #6366f1; text-decoration: none; }

/* Intel badge */
.nyx-badge-intel {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #6366f120;
  color: #818cf8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
  display: inline-block;
}

/* Status badges */
.nyx-status-badge { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600; white-space: nowrap; }
.nyx-status-sent { background: #1d4ed820; color: #60a5fa; }
.nyx-status-done { background: #064e3b; color: #6ee7b7; }
.nyx-status-unsub { background: #450a0a; color: #f87171; }
.nyx-status-pending { background: #1e293b; color: #475569; }
.nyx-status-draft { background: #6366f120; color: #818cf8; }
.nyx-status-contacted { background: #a855f720; color: #c084fc; }
.nyx-status-qualified { background: #059669; color: #d1fae5; }
</style>
