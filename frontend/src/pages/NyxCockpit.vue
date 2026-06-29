<template>
  <div class="nyx-cockpit">
    <!-- Header -->
    <div class="cockpit-header">
      <div class="header-left">
        <div class="nyx-logo">🔱</div>
        <div>
          <h1 class="header-title">Nyx Command Center</h1>
          <p class="header-subtitle">Revenue Orchestration System</p>
        </div>
      </div>
      <div class="header-right">
        <span class="status-pill" :class="eaiaConnected ? 'status-live' : 'status-offline'">
          {{ eaiaConnected ? '● EAIA Live' : '○ EAIA Offline' }}
        </span>
        <span class="status-pill" :class="farfalleConnected ? 'status-live' : 'status-offline'">
          {{ farfalleConnected ? '● Farfalle Live' : '○ Farfalle Offline' }}
        </span>
      </div>
    </div>

    <!-- Quick Stats Bar -->
    <div class="stats-bar" v-if="stats">
      <div class="stat-item">
        <div class="stat-value">{{ stats.total_leads }}</div>
        <div class="stat-label">Total Leads</div>
      </div>
      <div class="stat-item stat-enriched">
        <div class="stat-value">{{ stats.enriched }}</div>
        <div class="stat-label">Enriched</div>
      </div>
      <div class="stat-item stat-coverage">
        <div class="stat-value">{{ stats.coverage }}%</div>
        <div class="stat-label">Coverage</div>
      </div>
      <div class="stat-item stat-sent">
        <div class="stat-value">{{ stats.emails_sent }}</div>
        <div class="stat-label">Emails Sent</div>
      </div>
      <div class="stat-item stat-replies">
        <div class="stat-value">{{ stats.replies }}</div>
        <div class="stat-label">Replies</div>
      </div>
    </div>

    <!-- Command Cards Grid -->
    <div class="command-grid">
      <!-- Pipeline Dashboard -->
      <router-link to="/crm/nyx-dashboard" class="command-card card-pipeline">
        <div class="card-icon">📊</div>
        <div class="card-content">
          <h3>Pipeline Dashboard</h3>
          <p>Conversion funnel, A/B testing, KPIs, enrichment coverage</p>
        </div>
        <div class="card-arrow">→</div>
      </router-link>

      <!-- Lead Generation -->
      <router-link to="/crm/leadgen" class="command-card card-leadgen">
        <div class="card-icon">🎯</div>
        <div class="card-content">
          <h3>Lead Generation</h3>
          <p>ClinicalTrials.gov collection, tier scoring, bulk promote</p>
        </div>
        <div class="card-arrow">→</div>
      </router-link>

      <!-- AI Copilot -->
      <router-link to="/crm/ai" class="command-card card-copilot">
        <div class="card-icon">🧠</div>
        <div class="card-content">
          <h3>AI Copilot</h3>
          <p>Farfalle intelligence — company analysis, decision-makers, chat</p>
        </div>
        <div class="card-arrow">→</div>
      </router-link>

      <!-- Voice Operations -->
      <router-link to="/crm/voice" class="command-card card-voice">
        <div class="card-icon">📞</div>
        <div class="card-content">
          <h3>Voice Operations</h3>
          <p>Twilio + Vapi calls, AI agent Morgan, call analytics</p>
        </div>
        <div class="card-arrow">→</div>
      </router-link>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <h2 class="section-title">Quick Actions</h2>
      <div class="actions-grid">
        <button @click="quickEnrich" class="action-btn" :disabled="actionLoading === 'enrich'">
          <span class="action-icon">⚡</span>
          <span>{{ actionLoading === 'enrich' ? 'Enriching...' : 'Enrich Next Lead' }}</span>
        </button>
        <button @click="quickVulture" class="action-btn" :disabled="actionLoading === 'vulture'">
          <span class="action-icon">🦅</span>
          <span>{{ actionLoading === 'vulture' ? 'Scanning...' : 'Vulture Scan' }}</span>
        </button>
        <button @click="quickHealth" class="action-btn" :disabled="actionLoading === 'health'">
          <span class="action-icon">🩺</span>
          <span>{{ actionLoading === 'health' ? 'Checking...' : 'Health Check' }}</span>
        </button>
        <button @click="openBulkImport" class="action-btn">
          <span class="action-icon">📁</span>
          <span>CSV Import</span>
        </button>
      </div>
    </div>

    <!-- System Status -->
    <div class="system-status">
      <h2 class="section-title">System Status</h2>
      <div class="status-grid">
        <div class="status-card" v-for="svc in services" :key="svc.name">
          <div class="svc-indicator" :class="svc.ok ? 'svc-ok' : 'svc-down'"></div>
          <div class="svc-info">
            <div class="svc-name">{{ svc.name }}</div>
            <div class="svc-detail">{{ svc.detail }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'NyxCockpit',
  data() {
    return {
      eaiaConnected: false,
      farfalleConnected: false,
      actionLoading: null,
      stats: null,
      services: [
        { name: 'Frappe CRM', ok: true, detail: 'Connected' },
        { name: 'EAIA Backend', ok: false, detail: 'Checking...' },
        { name: 'Farfalle Intel', ok: false, detail: 'Checking...' },
        { name: 'Twilio Voice', ok: false, detail: 'Checking...' },
      ],
    }
  },
  mounted() {
    this.checkConnections()
    this.loadStats()
  },
  methods: {
    async checkConnections() {
      // Check EAIA
      const eaiaUrl = this.getEaiaUrl()
      try {
        const resp = await fetch(`${eaiaUrl}/health`, { method: 'GET', signal: AbortSignal.timeout(5000) })
        this.eaiaConnected = resp.ok
        this.services[1] = { name: 'EAIA Backend', ok: resp.ok, detail: resp.ok ? `${eaiaUrl}` : 'Unreachable' }
      } catch {
        this.eaiaConnected = false
        this.services[1] = { name: 'EAIA Backend', ok: false, detail: 'Unreachable' }
      }

      // Check Farfalle
      const farfalleUrl = this.getFarfalleUrl()
      try {
        const resp = await fetch(`${farfalleUrl}/health`, { method: 'GET', signal: AbortSignal.timeout(5000) })
        this.farfalleConnected = resp.ok
        this.services[2] = { name: 'Farfalle Intel', ok: resp.ok, detail: resp.ok ? `${farfalleUrl}` : 'Not running' }
      } catch {
        this.farfalleConnected = false
        this.services[2] = { name: 'Farfalle Intel', ok: false, detail: 'Not running' }
      }

      // Check Twilio via Frappe
      try {
        const resp = await frappe.call({ method: 'crm.integrations.twilio.api.is_enabled' })
        const ok = !!resp
        this.services[3] = { name: 'Twilio Voice', ok, detail: ok ? 'Configured' : 'Not configured' }
      } catch {
        this.services[3] = { name: 'Twilio Voice', ok: false, detail: 'Not configured' }
      }
    },

    async loadStats() {
      const eaiaUrl = this.getEaiaUrl()
      try {
        const resp = await fetch(`${eaiaUrl}/analytics/health`)
        if (resp.ok) {
          this.stats = await resp.json()
          return
        }
      } catch { /* fallback */ }

      // Fallback: load from Frappe
      try {
        const resp = await frappe.call({
          method: 'crm.api.mcp_server.get_pipeline_analytics'
        })
        if (resp.message) {
          const d = resp.message
          this.stats = {
            total_leads: d.funnel?.total || 0,
            enriched: d.funnel?.enriched || 0,
            coverage: d.enrichment_coverage || 0,
            emails_sent: d.funnel?.sent || 0,
            replies: d.funnel?.replied || 0,
          }
        }
      } catch {
        this.stats = { total_leads: 0, enriched: 0, coverage: 0, emails_sent: 0, replies: 0 }
      }
    },

    async quickEnrich() {
      this.actionLoading = 'enrich'
      try {
        const leads = await frappe.call({
          method: 'crm.api.doc.get_data',
          args: { doctype: 'CRM Lead', filters: { nyx_enriched: 0 }, order_by: 'creation desc', page_length: 1 }
        })
        const lead = leads?.data?.[0]
        if (lead) {
          this.$router.push(`/crm/leads/${lead.name}#nyx`)
        } else {
          alert('No unenriched leads found!')
        }
      } catch (e) {
        alert('Error: ' + (e.message || e))
      } finally {
        this.actionLoading = null
      }
    },

    async quickVulture() {
      this.actionLoading = 'vulture'
      const eaiaUrl = this.getEaiaUrl()
      try {
        const resp = await fetch(`${eaiaUrl}/cron/vulture-scan`, { method: 'POST' })
        const data = await resp.json()
        alert(`Vulture scan: ${data.scanned || 0} orgs scanned, ${data.alerts || 0} alerts`)
      } catch (e) {
        alert('Vulture scan failed — EAIA may be offline')
      } finally {
        this.actionLoading = null
      }
    },

    async quickHealth() {
      this.actionLoading = 'health'
      await this.checkConnections()
      await this.loadStats()
      this.actionLoading = null
    },

    openBulkImport() {
      this.$router.push('/crm/nyx-dashboard')
    },

    getEaiaUrl() {
      return window.EAIA_URL || localStorage.getItem('eaia_url') || 'http://localhost:8001'
    },

    getFarfalleUrl() {
      if (window.FARFALLE_BASE) return String(window.FARFALLE_BASE)
      // EAIA backend has Farfalle-compatible endpoints
      return 'http://localhost:8001'
    },
  }
}
</script>

<style scoped>
.nyx-cockpit {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  font-family: 'Inter', -apple-system, sans-serif;
}

.cockpit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(139, 92, 246, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.nyx-logo {
  font-size: 2.5rem;
  filter: drop-shadow(0 0 12px rgba(139, 92, 246, 0.4));
}

.header-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0;
}

.header-subtitle {
  font-size: 0.85rem;
  color: #6b7280;
  margin: 2px 0 0 0;
}

.header-right {
  display: flex;
  gap: 8px;
}

.status-pill {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.status-live {
  background: #ecfdf5;
  color: #059669;
  border: 1px solid #a7f3d0;
}

.status-offline {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

/* Stats Bar */
.stats-bar {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.stat-item {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  transition: all 0.2s;
}

.stat-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

.stat-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: #1a1a2e;
}

.stat-enriched .stat-value { color: #8b5cf6; }
.stat-coverage .stat-value { color: #059669; }
.stat-sent .stat-value { color: #2563eb; }
.stat-replies .stat-value { color: #d97706; }

.stat-label {
  font-size: 0.75rem;
  color: #9ca3af;
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Command Cards */
.command-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.command-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 12px;
  text-decoration: none;
  transition: all 0.25s ease;
  border: 1px solid transparent;
}

.command-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(0,0,0,0.12);
}

.card-pipeline {
  background: linear-gradient(135deg, #ede9fe, #f5f3ff);
  border-color: #c4b5fd;
}
.card-pipeline:hover { border-color: #8b5cf6; }

.card-leadgen {
  background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
  border-color: #86efac;
}
.card-leadgen:hover { border-color: #22c55e; }

.card-copilot {
  background: linear-gradient(135deg, #eff6ff, #f0f9ff);
  border-color: #93c5fd;
}
.card-copilot:hover { border-color: #3b82f6; }

.card-voice {
  background: linear-gradient(135deg, #fff7ed, #fffbeb);
  border-color: #fdba74;
}
.card-voice:hover { border-color: #f97316; }

.card-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.card-content h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #1a1a2e;
}

.card-content p {
  margin: 4px 0 0 0;
  font-size: 0.8rem;
  color: #6b7280;
  line-height: 1.4;
}

.card-arrow {
  margin-left: auto;
  font-size: 1.2rem;
  color: #9ca3af;
  transition: transform 0.2s;
}

.command-card:hover .card-arrow {
  transform: translateX(4px);
  color: #6b7280;
}

/* Quick Actions */
.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: #374151;
  margin: 0 0 12px 0;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 28px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  color: #374151;
  transition: all 0.2s;
}

.action-btn:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #8b5cf6;
  color: #8b5cf6;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-icon {
  font-size: 1.1rem;
}

/* System Status */
.status-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
}

.svc-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.svc-ok { background: #22c55e; box-shadow: 0 0 6px rgba(34, 197, 94, 0.5); }
.svc-down { background: #ef4444; box-shadow: 0 0 6px rgba(239, 68, 68, 0.3); }

.svc-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: #374151;
}

.svc-detail {
  font-size: 0.7rem;
  color: #9ca3af;
}

@media (max-width: 768px) {
  .stats-bar { grid-template-columns: repeat(3, 1fr); }
  .command-grid { grid-template-columns: 1fr; }
  .actions-grid { grid-template-columns: repeat(2, 1fr); }
  .status-grid { grid-template-columns: repeat(2, 1fr); }
  .header-right { flex-direction: column; }
}
</style>
