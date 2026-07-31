<template>
  <div class="outreach-360 p-6">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Outreach 360</h1>
        <p class="text-sm text-gray-500">Omnichannel sequence command center</p>
      </div>
      <button
        @click="loadBoard"
        :disabled="loading"
        class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
      >
        {{ loading ? 'Refreshing…' : 'Refresh' }}
      </button>
    </div>

    <!-- Channel health cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="border rounded p-4 bg-white">
        <div class="text-xs uppercase text-gray-500">Email</div>
        <div class="text-lg font-semibold" :class="health.email ? 'text-green-600' : 'text-gray-400'">
          {{ health.email ? 'Ready' : 'Not configured' }}
        </div>
      </div>
      <div class="border rounded p-4 bg-white">
        <div class="text-xs uppercase text-gray-500">Voice (Vapi)</div>
        <div class="text-lg font-semibold" :class="health.vapi ? 'text-green-600' : 'text-gray-400'">
          {{ health.vapi ? 'Ready' : 'Not configured' }}
        </div>
      </div>
      <div class="border rounded p-4 bg-white">
        <div class="text-xs uppercase text-gray-500">WhatsApp</div>
        <div class="text-lg font-semibold" :class="whatsappStatusClass">
          {{ whatsappStatusLabel }}
        </div>
      </div>
    </div>

    <!-- Worklist buckets -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div v-for="b in buckets" :key="b.key" class="border rounded p-4 bg-white cursor-pointer hover:border-blue-400"
           @click="activeBucket = b.key">
        <div class="text-xs uppercase text-gray-500">{{ b.label }}</div>
        <div class="text-3xl font-bold" :class="b.color">{{ counts[b.key] || 0 }}</div>
      </div>
    </div>

    <!-- Active bucket table -->
    <div class="bg-white border rounded">
      <div class="px-4 py-3 border-b font-semibold text-gray-800">
        {{ activeBucketLabel }}
      </div>
      <div v-if="activeItems.length === 0" class="p-6 text-center text-gray-400">
        No items.
      </div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-gray-500 border-b">
            <th class="px-4 py-2">Instance</th>
            <th class="px-4 py-2">Sequence</th>
            <th class="px-4 py-2">Step</th>
            <th class="px-4 py-2">Channel</th>
            <th class="px-4 py-2">Due</th>
            <th class="px-4 py-2">Subject / Reason</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(it, i) in activeItems" :key="i" class="border-b hover:bg-gray-50">
            <td class="px-4 py-2 font-mono text-xs">{{ it.instance || '—' }}</td>
            <td class="px-4 py-2">{{ it.sequence || '—' }}</td>
            <td class="px-4 py-2">{{ it.step_number || '—' }} / {{ it.total_steps || '—' }}</td>
            <td class="px-4 py-2">{{ it.channel || '—' }}</td>
            <td class="px-4 py-2 text-xs">{{ formatDate(it.due_date) }}</td>
            <td class="px-4 py-2 text-xs">{{ it.subject || it.blocked_reason || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Sequence rollup -->
    <div class="mt-6 bg-white border rounded">
      <div class="px-4 py-3 border-b font-semibold text-gray-800">Sequences</div>
      <div v-if="sequences.length === 0" class="p-6 text-center text-gray-400">No sequences.</div>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-gray-500 border-b">
            <th class="px-4 py-2">Name</th>
            <th class="px-4 py-2">Tier</th>
            <th class="px-4 py-2">Status</th>
            <th class="px-4 py-2">Instances</th>
            <th class="px-4 py-2">By status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in sequences" :key="s.sequence" class="border-b hover:bg-gray-50">
            <td class="px-4 py-2">{{ s.sequence_name || s.sequence }}</td>
            <td class="px-4 py-2">{{ s.tier || '—' }}</td>
            <td class="px-4 py-2">
              <span class="px-2 py-0.5 rounded text-xs"
                    :class="s.active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'">
                {{ s.status }}{{ s.active ? ' · active' : '' }}
              </span>
            </td>
            <td class="px-4 py-2">{{ s.instances }}</td>
            <td class="px-4 py-2 text-xs text-gray-500">{{ byStatus(s.by_status) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Outreach360',
  data() {
    return {
      loading: false,
      counts: {},
      sequences: [],
      health: {},
      board: {},
      activeBucket: 'due_email',
      buckets: [
        { key: 'due_email', label: 'Due Email', color: 'text-blue-600' },
        { key: 'due_call', label: 'Due Call', color: 'text-indigo-600' },
        { key: 'due_whatsapp', label: 'Due WhatsApp', color: 'text-green-600' },
        { key: 'needs_approval', label: 'Needs Approval', color: 'text-amber-600' },
        { key: 'blocked', label: 'Blocked', color: 'text-red-600' },
        { key: 'waiting', label: 'Waiting', color: 'text-gray-600' },
        { key: 'needs_human', label: 'Needs Human', color: 'text-purple-600' },
      ],
    }
  },
  computed: {
    activeItems() {
      return this.board[this.activeBucket] || []
    },
    activeBucketLabel() {
      const b = this.buckets.find((x) => x.key === this.activeBucket)
      return b ? b.label : ''
    },
    whatsappStatusLabel() {
      const w = this.health.whatsapp || {}
      if (w.status === 'ready') return 'Ready'
      if (w.status === 'installed_disabled') return 'Installed · Disabled'
      return 'Not installed'
    },
    whatsappStatusClass() {
      const w = this.health.whatsapp || {}
      return w.status === 'ready' ? 'text-green-600' : 'text-gray-400'
    },
  },
  mounted() {
    this.loadBoard()
  },
  methods: {
    async loadBoard() {
      this.loading = true
      try {
        const response = await frappe.call({
          method: 'crm.api.outreach_360.get_board',
          args: { limit: 50 },
        })
        const data = response.message || {}
        this.board = data
        this.counts = data.counts || {}
        this.sequences = data.sequences || []
        this.health = data.health || {}
      } catch (error) {
        frappe.msgprint('Error loading Outreach 360: ' + (error.message || error))
      } finally {
        this.loading = false
      }
    },
    formatDate(d) {
      if (!d) return '—'
      try {
        return new Date(d).toLocaleString()
      } catch (e) {
        return d
      }
    },
    byStatus(obj) {
      if (!obj) return '—'
      return Object.entries(obj)
        .map(([k, v]) => `${k}: ${v}`)
        .join(' · ')
    },
  },
}
</script>
