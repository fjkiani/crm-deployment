<template>
  <div class="voice-dashboard">
    <!-- Header -->
    <div class="dashboard-header">
      <h1 class="text-2xl font-bold text-gray-900">Voice Operations Dashboard</h1>
      <div class="header-actions">
        <button 
          @click="refreshData" 
          :disabled="loading"
          class="btn btn-primary"
        >
          <RefreshIcon class="w-4 h-4 mr-2" />
          {{ loading ? 'Refreshing...' : 'Refresh' }}
        </button>
      </div>
    </div>

    <!-- System Health Status -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
      <div class="status-card">
        <div class="status-indicator" :class="systemHealth.twilio ? 'status-healthy' : 'status-error'">
          <PhoneIcon class="w-6 h-6" />
        </div>
        <div class="status-info">
          <h3>Twilio</h3>
          <p>{{ systemHealth.twilio ? 'Connected' : 'Error' }}</p>
        </div>
      </div>
      
      <div class="status-card">
        <div class="status-indicator" :class="systemHealth.vapi ? 'status-healthy' : 'status-warning'">
          <MicrophoneIcon class="w-6 h-6" />
        </div>
        <div class="status-info">
          <h3>Vapi AI</h3>
          <p>{{ systemHealth.vapi ? 'Connected' : 'Not Configured' }}</p>
        </div>
      </div>
      
      <div class="status-card">
        <div class="status-indicator" :class="systemHealth.crm ? 'status-healthy' : 'status-error'">
          <DatabaseIcon class="w-6 h-6" />
        </div>
        <div class="status-info">
          <h3>CRM</h3>
          <p>{{ systemHealth.crm ? 'Connected' : 'Error' }}</p>
        </div>
      </div>
      
      <div class="status-card">
        <div class="status-indicator" :class="systemHealth.farfalle ? 'status-healthy' : 'status-warning'">
          <ChatBubbleLeftRightIcon class="w-6 h-6" />
        </div>
        <div class="status-info">
          <h3>Farfalle</h3>
          <p>{{ systemHealth.farfalle ? 'Connected' : 'Not Available' }}</p>
        </div>
      </div>
    </div>

    <!-- Call Analytics -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <div class="analytics-card">
        <h3>Total Calls</h3>
        <div class="metric">{{ dashboardData.total_calls || 0 }}</div>
        <p class="metric-subtitle">All time</p>
      </div>
      
      <div class="analytics-card">
        <h3>Active Calls</h3>
        <div class="metric text-blue-600">{{ dashboardData.active_calls || 0 }}</div>
        <p class="metric-subtitle">Currently in progress</p>
      </div>
      
      <div class="analytics-card">
        <h3>Success Rate</h3>
        <div class="metric text-green-600">{{ dashboardData.analytics?.success_rate || 0 }}%</div>
        <p class="metric-subtitle">Last 50 calls</p>
      </div>
    </div>

    <!-- Active Calls Section -->
    <div class="dashboard-section mb-8" v-if="dashboardData.active_call_details?.length">
      <h2 class="section-title">Active Calls</h2>
      <div class="calls-grid">
        <div 
          v-for="call in dashboardData.active_call_details" 
          :key="call.name"
          class="call-card active-call"
        >
          <div class="call-header">
            <div class="call-status" :class="`status-${call.status?.toLowerCase()}`">
              {{ call.status }}
            </div>
            <div class="call-time">{{ formatTime(call.started_at) }}</div>
          </div>
          <div class="call-details">
            <p><strong>From:</strong> {{ call.from }}</p>
            <p><strong>To:</strong> {{ call.to }}</p>
            <p v-if="call.duration"><strong>Duration:</strong> {{ call.duration }}s</p>
          </div>
          <div class="call-actions">
            <button 
              @click="viewCallDetails(call.name)"
              class="btn btn-sm btn-outline"
            >
              View Details
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Calls Section -->
    <div class="dashboard-section">
      <h2 class="section-title">Recent Calls</h2>
      <div class="calls-table">
        <table class="min-w-full">
          <thead>
            <tr>
              <th>Time</th>
              <th>From</th>
              <th>To</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="call in dashboardData.recent_calls" 
              :key="call.name"
              class="table-row"
            >
              <td>{{ formatDateTime(call.creation) }}</td>
              <td>{{ call.from }}</td>
              <td>{{ call.to }}</td>
              <td>
                <span class="status-badge" :class="`status-${call.status?.toLowerCase()}`">
                  {{ call.status }}
                </span>
              </td>
              <td>{{ call.duration ? `${call.duration}s` : '-' }}</td>
              <td>
                <div class="action-buttons">
                  <button 
                    @click="viewCallDetails(call.name)"
                    class="btn btn-xs btn-outline"
                  >
                    View
                  </button>
                  <button 
                    v-if="call.recording_url"
                    @click="playRecording(call.recording_url)"
                    class="btn btn-xs btn-outline"
                  >
                    Play
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        
        <div v-if="!dashboardData.recent_calls?.length" class="empty-state">
          <PhoneIcon class="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p class="text-gray-500">No recent calls found</p>
        </div>
      </div>
    </div>

    <!-- Call Details Modal -->
    <div v-if="selectedCall" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Call Details</h3>
          <button @click="closeModal" class="modal-close">×</button>
        </div>
        <div class="modal-body">
          <div class="detail-grid">
            <div class="detail-item">
              <label>Call ID:</label>
              <span>{{ selectedCall.name }}</span>
            </div>
            <div class="detail-item">
              <label>From:</label>
              <span>{{ selectedCall.from }}</span>
            </div>
            <div class="detail-item">
              <label>To:</label>
              <span>{{ selectedCall.to }}</span>
            </div>
            <div class="detail-item">
              <label>Status:</label>
              <span class="status-badge" :class="`status-${selectedCall.status?.toLowerCase()}`">
                {{ selectedCall.status }}
              </span>
            </div>
            <div class="detail-item" v-if="selectedCall.started_at">
              <label>Started:</label>
              <span>{{ formatDateTime(selectedCall.started_at) }}</span>
            </div>
            <div class="detail-item" v-if="selectedCall.ended_at">
              <label>Ended:</label>
              <span>{{ formatDateTime(selectedCall.ended_at) }}</span>
            </div>
            <div class="detail-item" v-if="selectedCall.duration">
              <label>Duration:</label>
              <span>{{ selectedCall.duration }} seconds</span>
            </div>
          </div>
          
          <!-- Notes and transcripts would be loaded here -->
          <div class="mt-6" v-if="selectedCall.notes?.length">
            <h4 class="font-semibold mb-2">Notes & Transcripts</h4>
            <div class="notes-list">
              <div 
                v-for="note in selectedCall.notes" 
                :key="note.name"
                class="note-item"
              >
                <h5>{{ note.title }}</h5>
                <p>{{ note.content }}</p>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="closeModal" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, reactive } from 'vue'
import { call } from 'frappe-ui'
import PhoneIcon from '~icons/lucide/phone'
import MicrophoneIcon from '~icons/lucide/mic'
import DatabaseIcon from '~icons/lucide/database'
import ChatBubbleLeftRightIcon from '~icons/lucide/message-square'
import RefreshIcon from '~icons/lucide/refresh-cw'

export default {
  name: 'VoiceDashboard',
  components: {
    PhoneIcon,
    MicrophoneIcon,
    DatabaseIcon,
    ChatBubbleLeftRightIcon,
    RefreshIcon
  },
  setup() {
    const loading = ref(false)
    const selectedCall = ref(null)
    
    const systemHealth = reactive({
      twilio: false,
      vapi: false,
      crm: true, // Assume CRM is healthy since we're in it
      farfalle: false
    })
    
    const dashboardData = reactive({
      total_calls: 0,
      active_calls: 0,
      recent_calls: [],
      active_call_details: [],
      analytics: {
        success_rate: 0,
        average_duration: 0,
        total_duration: 0
      }
    })

    const checkSystemHealth = async () => {
      try {
        const twilioStatus = await call('crm.integrations.twilio.api.is_enabled')
        systemHealth.twilio = !!twilioStatus
      } catch (error) {
        console.error('Failed to check Twilio status:', error)
        systemHealth.twilio = false
      }

      try {
        const vapiHealth = await call('crm.api.vapi.get_health')
        systemHealth.vapi = !!(vapiHealth?.vapi || vapiHealth?.configured)
      } catch (error) {
        console.error('Failed to check Vapi status:', error)
        systemHealth.vapi = false
      }

      try {
        const farfalleUrl = import.meta.env.VITE_EAIA_URL || ''
        if (farfalleUrl) {
          const response = await fetch(`${farfalleUrl.replace(/\/$/, '')}/health`, { method: 'GET' })
          systemHealth.farfalle = response.ok
        } else {
          systemHealth.farfalle = false
        }
      } catch (error) {
        systemHealth.farfalle = false
      }
    }

    const normalizeVapiCall = (row) => ({
      name: row.name || row.vapi_call_id,
      from: row.from_number || row.from || '-',
      to: row.to_number || row.to || '-',
      status: row.status,
      duration: row.duration_seconds ?? row.duration ?? 0,
      recording_url: row.recording_url,
      creation: row.creation,
      crm_lead: row.crm_lead,
      outcome: row.outcome,
    })

    const loadDashboardData = async () => {
      try {
        const dashboard = await call('crm.api.vapi.get_dashboard')
        const recent = (dashboard?.recent_calls || []).map(normalizeVapiCall)
        const active = (dashboard?.active_call_details || []).map(normalizeVapiCall)

        dashboardData.recent_calls = recent
        dashboardData.active_call_details = active
        dashboardData.total_calls = dashboard?.total_calls ?? recent.length
        dashboardData.active_calls = dashboard?.active_calls ?? active.length
        dashboardData.analytics = dashboard?.analytics || dashboardData.analytics

        if (dashboard?.vapi_health) {
          systemHealth.vapi = !!(dashboard.vapi_health.vapi || dashboard.vapi_health.configured)
        }
      } catch (error) {
        console.error('Vapi dashboard failed, falling back to CRM Call Log:', error)
        try {
          const recentCalls = await call('crm.api.doc.get_data', {
            doctype: 'CRM Call Log',
            filters: { telephony_medium: 'Vapi' },
            order_by: 'creation desc',
            page_length: 50,
          })
          dashboardData.recent_calls = (recentCalls.data || []).map((c) => ({
            name: c.name,
            from: c.from,
            to: c.to,
            status: c.status,
            duration: c.duration,
            recording_url: c.recording_url,
            creation: c.creation,
          }))
          dashboardData.total_calls = recentCalls.total_count || dashboardData.recent_calls.length
        } catch (fallbackError) {
          console.error('Failed to load dashboard data:', fallbackError)
        }
      }
    }

    const refreshData = async () => {
      loading.value = true
      try {
        await Promise.all([
          checkSystemHealth(),
          loadDashboardData()
        ])
      } finally {
        loading.value = false
      }
    }

    const viewCallDetails = async (callName) => {
      try {
        let callDetails = null
        try {
          callDetails = await call('crm.api.doc.get_doc', {
            doctype: 'Vapi Call Log',
            name: callName,
          })
        } catch {
          callDetails = await call('crm.api.doc.get_doc', {
            doctype: 'CRM Call Log',
            name: callName,
          })
        }

        const notes = await call('crm.api.doc.get_data', {
          doctype: 'FCRM Note',
          filters: {
            reference_doctype: 'CRM Lead',
            reference_docname: callDetails.crm_lead || callDetails.reference_docname,
          },
          page_length: 5,
        })
        
        selectedCall.value = {
          ...callDetails,
          from: callDetails.from_number || callDetails.from,
          to: callDetails.to_number || callDetails.to,
          duration: callDetails.duration_seconds ?? callDetails.duration,
          notes: notes.data || [],
        }
      } catch (error) {
        console.error('Failed to load call details:', error)
      }
    }

    const closeModal = () => {
      selectedCall.value = null
    }

    const playRecording = (recordingUrl) => {
      if (recordingUrl) {
        window.open(recordingUrl, '_blank')
      }
    }

    const formatTime = (dateString) => {
      if (!dateString) return '-'
      return new Date(dateString).toLocaleTimeString()
    }

    const formatDateTime = (dateString) => {
      if (!dateString) return '-'
      return new Date(dateString).toLocaleString()
    }

    onMounted(() => {
      refreshData()
      
      // Auto-refresh every 30 seconds for active calls
      const interval = setInterval(() => {
        if (dashboardData.active_calls > 0) {
          loadDashboardData()
        }
      }, 30000)
      
      // Cleanup interval on unmount
      return () => clearInterval(interval)
    })

    return {
      loading,
      systemHealth,
      dashboardData,
      selectedCall,
      refreshData,
      viewCallDetails,
      closeModal,
      playRecording,
      formatTime,
      formatDateTime
    }
  }
}
</script>

<style scoped>
.voice-dashboard {
  @apply p-6 max-w-7xl mx-auto;
}

.dashboard-header {
  @apply flex justify-between items-center mb-8;
}

.header-actions {
  @apply flex gap-3;
}

.status-card {
  @apply bg-white rounded-lg p-4 shadow-sm border flex items-center gap-4;
}

.status-indicator {
  @apply w-12 h-12 rounded-full flex items-center justify-center;
}

.status-healthy {
  @apply bg-green-100 text-green-600;
}

.status-warning {
  @apply bg-yellow-100 text-yellow-600;
}

.status-error {
  @apply bg-red-100 text-red-600;
}

.status-info h3 {
  @apply font-semibold text-gray-900;
}

.status-info p {
  @apply text-sm text-gray-600;
}

.analytics-card {
  @apply bg-white rounded-lg p-6 shadow-sm border;
}

.analytics-card h3 {
  @apply text-sm font-medium text-gray-600 mb-2;
}

.metric {
  @apply text-3xl font-bold text-gray-900 mb-1;
}

.metric-subtitle {
  @apply text-sm text-gray-500;
}

.dashboard-section {
  @apply bg-white rounded-lg shadow-sm border;
}

.section-title {
  @apply text-lg font-semibold p-6 border-b border-gray-200;
}

.calls-grid {
  @apply grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-6;
}

.call-card {
  @apply border rounded-lg p-4;
}

.active-call {
  @apply border-blue-200 bg-blue-50;
}

.call-header {
  @apply flex justify-between items-center mb-3;
}

.call-status {
  @apply px-2 py-1 rounded text-xs font-medium;
}

.status-initiated {
  @apply bg-blue-100 text-blue-800;
}

.status-ringing {
  @apply bg-yellow-100 text-yellow-800;
}

.status-completed {
  @apply bg-green-100 text-green-800;
}

.status-failed {
  @apply bg-red-100 text-red-800;
}

.call-time {
  @apply text-xs text-gray-500;
}

.call-details p {
  @apply text-sm text-gray-600 mb-1;
}

.call-actions {
  @apply mt-3 pt-3 border-t border-gray-200;
}

.calls-table {
  @apply p-6;
}

.calls-table table {
  @apply w-full;
}

.calls-table th {
  @apply text-left py-3 px-4 font-medium text-gray-600 border-b border-gray-200;
}

.calls-table td {
  @apply py-3 px-4 border-b border-gray-100;
}

.table-row:hover {
  @apply bg-gray-50;
}

.status-badge {
  @apply px-2 py-1 rounded-full text-xs font-medium;
}

.action-buttons {
  @apply flex gap-2;
}

.empty-state {
  @apply text-center py-12;
}

.modal-overlay {
  @apply fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50;
}

.modal-content {
  @apply bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto;
}

.modal-header {
  @apply flex justify-between items-center p-6 border-b border-gray-200;
}

.modal-header h3 {
  @apply text-lg font-semibold;
}

.modal-close {
  @apply text-gray-400 hover:text-gray-600 text-2xl leading-none;
}

.modal-body {
  @apply p-6;
}

.detail-grid {
  @apply grid grid-cols-2 gap-4;
}

.detail-item {
  @apply flex flex-col;
}

.detail-item label {
  @apply text-sm font-medium text-gray-600 mb-1;
}

.detail-item span {
  @apply text-sm text-gray-900;
}

.notes-list {
  @apply space-y-4;
}

.note-item {
  @apply border rounded-lg p-4;
}

.note-item h5 {
  @apply font-medium mb-2;
}

.note-item p {
  @apply text-sm text-gray-600;
}

.modal-footer {
  @apply p-6 border-t border-gray-200 flex justify-end gap-3;
}

/* Button styles */
.btn {
  @apply px-4 py-2 rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-offset-2;
}

.btn-primary {
  @apply bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500;
}

.btn-secondary {
  @apply bg-gray-300 text-gray-700 hover:bg-gray-400 focus:ring-gray-500;
}

.btn-outline {
  @apply border border-gray-300 text-gray-700 hover:bg-gray-50 focus:ring-gray-500;
}

.btn-sm {
  @apply px-3 py-1.5 text-sm;
}

.btn-xs {
  @apply px-2 py-1 text-xs;
}

.btn:disabled {
  @apply opacity-50 cursor-not-allowed;
}
</style>


