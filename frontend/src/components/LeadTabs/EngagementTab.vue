<template>
  <div class="flex flex-1 flex-col overflow-y-auto px-4 py-3 sm:px-10">
    <!-- Approach header + nurture state -->
    <div class="mb-4 rounded-lg border border-ink-gray-2 bg-surface-white">
      <div class="flex items-center justify-between border-b border-ink-gray-2 px-4 py-2.5">
        <span class="text-sm font-semibold text-ink-gray-9">{{ __('Engagement') }}</span>
        <div class="flex items-center gap-2">
          <span class="rounded px-2 py-0.5 text-[11px] font-medium"
                :class="data.nurture_state === 'engaged' ? 'bg-green-100 text-green-700' : 'bg-surface-gray-2 text-ink-gray-6'">
            {{ data.nurture_state === 'engaged' ? __('engaged') : __('cold') }}
          </span>
          <Button variant="subtle" :loading="loading" @click="load">
            <template #prefix><LucideRefreshCw class="h-3.5 w-3.5" /></template>
            {{ __('Refresh') }}
          </Button>
        </div>
      </div>
      <div class="px-4 py-3">
        <p class="text-sm text-ink-gray-8">
          {{ data.has_outreach
            ? __('This lead has engagement history. Review tasks, calls, and notes below.')
            : __('No engagement yet — this lead is cold. Start with a task or a first-touch outreach.') }}
        </p>
        <div class="mt-3 flex flex-wrap gap-4 text-xs text-ink-gray-6">
          <span>{{ __('Open tasks:') }} <b class="text-ink-gray-8">{{ data.open_task_count || 0 }}</b></span>
          <span>{{ __('Calls:') }} <b class="text-ink-gray-8">{{ (data.calls || []).length }}</b></span>
          <span>{{ __('Notes:') }} <b class="text-ink-gray-8">{{ (data.notes || []).length }}</b></span>
        </div>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
      <Button class="ml-2" size="sm" variant="outline" @click="load">{{ __('Retry') }}</Button>
    </div>

    <template v-else>
      <!-- Tasks -->
      <div class="mb-4">
        <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
          {{ __('Tasks') }} ({{ (data.tasks || []).length }})
        </div>
        <div v-if="data.tasks && data.tasks.length" class="space-y-2">
          <div v-for="t in data.tasks" :key="t.name"
               class="rounded-lg border border-ink-gray-2 bg-surface-white px-4 py-3">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-ink-gray-9">{{ t.title || __('(untitled task)') }}</span>
              <span class="rounded px-1.5 py-0.5 text-[10px]"
                    :class="isOpen(t) ? 'bg-surface-amber-2 text-ink-amber-3' : 'bg-surface-gray-2 text-ink-gray-6'">
                {{ t.status }}
              </span>
            </div>
            <div class="mt-1 flex flex-wrap gap-3 text-xs text-ink-gray-5">
              <span v-if="t.priority">{{ t.priority }}</span>
              <span v-if="t.due_date">{{ __('Due') }} {{ t.due_date }}</span>
            </div>
          </div>
        </div>
        <p v-else class="text-sm text-ink-gray-5">{{ __('No tasks for this lead.') }}</p>
      </div>

      <!-- Calls -->
      <div class="mb-4">
        <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
          {{ __('Calls') }} ({{ (data.calls || []).length }})
        </div>
        <div v-if="data.calls && data.calls.length" class="space-y-2">
          <div v-for="c in data.calls" :key="c.name"
               class="rounded-lg border border-ink-gray-2 bg-surface-white px-4 py-3">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-ink-gray-9">{{ c.subject || __('(call)') }}</span>
              <span class="text-xs text-ink-gray-5">{{ c.creation }}</span>
            </div>
            <p v-if="c.content" class="mt-1 line-clamp-2 text-xs text-ink-gray-6">{{ stripHtml(c.content) }}</p>
          </div>
        </div>
        <p v-else class="text-sm text-ink-gray-5">{{ __('No calls logged.') }}</p>
      </div>

      <!-- Notes -->
      <div>
        <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
          {{ __('Notes') }} ({{ (data.notes || []).length }})
        </div>
        <div v-if="data.notes && data.notes.length" class="space-y-2">
          <div v-for="n in data.notes" :key="n.name"
               class="rounded-lg border border-ink-gray-2 bg-surface-white px-4 py-3">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-ink-gray-9">{{ n.title || __('(note)') }}</span>
              <span class="text-xs text-ink-gray-5">{{ n.creation }}</span>
            </div>
            <p v-if="n.content" class="mt-1 line-clamp-3 text-xs text-ink-gray-6">{{ stripHtml(n.content) }}</p>
          </div>
        </div>
        <p v-else class="text-sm text-ink-gray-5">{{ __('No notes yet.') }}</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Button, call } from 'frappe-ui'

const props = defineProps({ leadId: { type: String, required: true } })

const loading = ref(false)
const error = ref('')
const data = ref({ ok: false, tasks: [], calls: [], notes: [], has_outreach: false, nurture_state: 'cold', open_task_count: 0 })

function isOpen(t) {
  return t.status !== 'Done' && t.status !== 'Canceled'
}
function stripHtml(s) {
  return String(s || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await call('crm.api.lead_tabs.get_tab_data', {
      lead: props.leadId,
      tab: 'engagement',
    })
    data.value = res || { ok: false, tasks: [], calls: [], notes: [] }
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || __('Failed to load engagement')
    data.value = { ok: false, tasks: [], calls: [], notes: [], has_outreach: false, nurture_state: 'cold', open_task_count: 0 }
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
