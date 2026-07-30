<template>
  <div class="flex h-full w-full flex-col bg-surface-white">
    <!-- Header -->
    <div class="flex items-center justify-between border-b px-4 py-3">
      <div class="flex items-center gap-2">
        <InboxIcon class="h-5 w-5 text-ink-gray-7" />
        <h1 class="text-lg font-semibold text-ink-gray-9">Human Inbox</h1>
        <span
          v-if="!loading"
          class="rounded bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-6"
        >
          {{ items.length }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <Button
          :loading="batchBusy"
          variant="subtle"
          @click="runBatchTriage"
        >
          <template #prefix><SparklesIcon class="h-4 w-4" /></template>
          Batch triage
        </Button>
        <Button variant="ghost" :loading="loading" @click="loadInbox">
          <template #prefix><RefreshIcon class="h-4 w-4" /></template>
          Refresh
        </Button>
      </div>
    </div>

    <!-- Two-pane body -->
    <div class="flex min-h-0 flex-1">
      <!-- LEFT: list pane -->
      <div class="flex w-[380px] shrink-0 flex-col border-r">
        <!-- Filter tabs -->
        <div class="flex items-center gap-1 border-b px-2 py-2">
          <button
            v-for="f in filters"
            :key="f.key"
            class="rounded px-2.5 py-1 text-sm"
            :class="
              activeFilter === f.key
                ? 'bg-surface-gray-3 font-medium text-ink-gray-9'
                : 'text-ink-gray-6 hover:bg-surface-gray-2'
            "
            @click="setFilter(f.key)"
          >
            {{ f.label }}
          </button>
        </div>

        <!-- List -->
        <div class="min-h-0 flex-1 overflow-y-auto">
          <div
            v-if="loading"
            class="p-4 text-sm text-ink-gray-5"
          >
            Loading…
          </div>
          <div
            v-else-if="!items.length"
            class="p-6 text-center text-sm text-ink-gray-5"
          >
            No messages in {{ activeFilterLabel }}.
          </div>
          <button
            v-for="row in items"
            :key="row.name"
            class="flex w-full flex-col gap-1 border-b px-3 py-2.5 text-left hover:bg-surface-gray-1"
            :class="
              selected && selected.name === row.name
                ? 'bg-surface-blue-1'
                : ''
            "
            @click="selectRow(row)"
          >
            <div class="flex items-center justify-between gap-2">
              <span class="truncate text-sm font-medium text-ink-gray-9">
                {{ displaySender(row) }}
              </span>
              <span class="shrink-0 text-xs text-ink-gray-4">
                {{ shortDate(row.creation) }}
              </span>
            </div>
            <div class="truncate text-sm text-ink-gray-7">
              {{ row.subject || '(no subject)' }}
            </div>
            <div class="flex items-center gap-1.5">
              <span
                class="rounded px-1.5 py-0.5 text-[10px] font-medium uppercase"
                :class="directionBadge(row).cls"
              >
                {{ directionBadge(row).text }}
              </span>
              <span
                v-if="row.status === 'Draft'"
                class="rounded bg-surface-amber-2 px-1.5 py-0.5 text-[10px] font-medium uppercase text-ink-amber-3"
              >
                Draft
              </span>
              <span class="truncate text-[11px] text-ink-gray-4">
                {{ row.reference_doctype }} · {{ row.reference_name }}
              </span>
            </div>
          </button>
        </div>
      </div>

      <!-- RIGHT: reader + composer pane.
           Agent B replaces this placeholder block with <InboxReader> (thread_context + inline TextEditor).
           Agent C mounts <InboxAiActions> in the reader action bar. -->
      <div class="flex min-h-0 flex-1 flex-col">
        <div
          v-if="!selected"
          class="flex flex-1 items-center justify-center text-sm text-ink-gray-4"
        >
          Select a message to read and reply.
        </div>
        <InboxReader
          v-else
          :communication="selected"
          @sent="onSentOrChanged"
          @discarded="onSentOrChanged"
        />
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { call, toast, Button } from 'frappe-ui'
import InboxIcon from '~icons/lucide/inbox'
import RefreshIcon from '~icons/lucide/refresh-cw'
import SparklesIcon from '~icons/lucide/sparkles'
import InboxReader from '@/components/inbox/InboxReader.vue'

export default {
  name: 'HumanInbox',
  components: { Button, InboxIcon, RefreshIcon, SparklesIcon, InboxReader },
  setup() {
    const route = useRoute()
    const loading = ref(false)
    const batchBusy = ref(false)
    const items = ref([])
    const selected = ref(null)

    const filters = [
      { key: 'needs_triage', label: 'Needs Triage' },
      { key: 'drafts', label: 'Drafts' },
      { key: 'sent', label: 'Sent' },
      { key: 'all', label: 'All' },
    ]
    const activeFilter = ref('needs_triage')
    const activeFilterLabel = computed(
      () => (filters.find((f) => f.key === activeFilter.value) || {}).label || ''
    )

    // Map filter key -> get_inbox args (contract: status/direction).
    function argsForFilter(key) {
      if (key === 'needs_triage') return { direction: 'inbound', limit: 50 }
      if (key === 'drafts') return { status: 'Draft', limit: 50 }
      if (key === 'sent') return { status: 'Sent', limit: 50 }
      return { limit: 50 } // all
    }

    async function loadInbox() {
      loading.value = true
      try {
        const rows = await call('crm.api.email.get_inbox', argsForFilter(activeFilter.value))
        items.value = Array.isArray(rows) ? rows : []
      } catch (e) {
        toast.error('Failed to load inbox: ' + (e.messages?.[0] || e.message || 'error'))
        items.value = []
      } finally {
        loading.value = false
      }
    }

    function setFilter(key) {
      if (activeFilter.value === key) return
      activeFilter.value = key
      selected.value = null
      loadInbox()
    }

    function selectRow(row) {
      selected.value = row
    }

    function onSentOrChanged() {
      // After a send/discard, refresh the list and clear selection.
      selected.value = null
      loadInbox()
    }

    async function runBatchTriage() {
      batchBusy.value = true
      try {
        const res = await call('crm.api.nyx_email_brain.batch_triage_and_draft', {
          limit: 10,
          only_with_email: 1,
        })
        // batch_triage_and_draft returns { ok, queued_count, queued, skipped_existing_draft }
        const queued = res?.queued_count ?? 0
        const skipped = res?.skipped_existing_draft ?? 0
        toast.success(
          `Batch triage: ${queued} queued` + (skipped ? `, ${skipped} skipped (already drafted)` : '') + '.',
        )
        loadInbox()
      } catch (e) {
        toast.error('Batch triage failed: ' + (e.messages?.[0] || e.message || 'error'))
      } finally {
        batchBusy.value = false
      }
    }

    // --- display helpers ---
    function displaySender(row) {
      if (row.sent_or_received === 'Sent') {
        return 'To: ' + (row.recipients || '—')
      }
      return row.sender || '—'
    }
    function directionBadge(row) {
      if (row.sent_or_received === 'Sent') {
        return { text: 'Sent', cls: 'bg-surface-gray-3 text-ink-gray-6' }
      }
      return { text: 'Inbound', cls: 'bg-surface-green-2 text-ink-green-3' }
    }
    function shortDate(dt) {
      if (!dt) return ''
      const d = new Date(dt.replace(' ', 'T'))
      if (isNaN(d)) return ''
      const now = new Date()
      const sameDay = d.toDateString() === now.toDateString()
      return sameDay
        ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : d.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }

    // WP2.4 — deep-link support: /human_inbox?comm=<name> (from an Industry plan
    // draft, a Task, or LinkedDocs) lands on that exact Communication. Engagement
    // drafts live under the Drafts tab; fall back to All if it is elsewhere.
    onMounted(async () => {
      const commName = route.query.comm ? String(route.query.comm) : ''
      if (commName) activeFilter.value = 'drafts'
      await loadInbox()
      if (commName) {
        let row = items.value.find((r) => String(r.name) === commName)
        if (!row) {
          activeFilter.value = 'all'
          await loadInbox()
          row = items.value.find((r) => String(r.name) === commName)
        }
        if (row) selectRow(row)
      }
    })

    return {
      loading,
      batchBusy,
      items,
      selected,
      filters,
      activeFilter,
      activeFilterLabel,
      loadInbox,
      setFilter,
      selectRow,
      onSentOrChanged,
      runBatchTriage,
      displaySender,
      directionBadge,
      shortDate,
    }
  },
}
</script>
