<template>
  <div class="flex flex-1 flex-col overflow-y-auto px-4 py-3 sm:px-10">
    <!-- Approach header -->
    <div class="mb-4 rounded-lg border border-ink-gray-2 bg-surface-white">
      <div class="flex items-center justify-between border-b border-ink-gray-2 px-4 py-2.5">
        <span class="text-sm font-semibold text-ink-gray-9">{{ __('Outreach approach') }}</span>
        <Button variant="subtle" :loading="loading" @click="load">
          <template #prefix><LucideRefreshCw class="h-3.5 w-3.5" /></template>
          {{ __('Refresh') }}
        </Button>
      </div>
      <div class="px-4 py-3">
        <p class="text-sm text-ink-gray-8">
          {{ data.has_outreach
            ? __('Active outreach in flight. Review drafts, then arm or advance the sequence — every send is human-approved.')
            : __('No outreach yet. Draft a first email or add this lead to a sequence.') }}
        </p>
        <div class="mt-3 flex gap-2">
          <Button size="sm" variant="solid" @click="$emit('draft-email')">{{ __('Draft email') }}</Button>
          <Button size="sm" variant="outline" @click="$emit('add-sequence')">{{ __('Add to sequence') }}</Button>
        </div>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
      <Button class="ml-2" size="sm" variant="outline" @click="load">{{ __('Retry') }}</Button>
    </div>

    <template v-else>
    <!-- Sequences -->
    <div class="mb-4">
      <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
        {{ __('Sequences') }} ({{ data.sequence_count || 0 }})
      </div>
      <div v-if="data.sequences && data.sequences.length" class="space-y-2">
        <div v-for="s in data.sequences" :key="s.instance"
             class="rounded-lg border border-ink-gray-2 bg-surface-white px-4 py-3">
          <div class="flex items-center justify-between">
            <div>
              <span class="text-sm font-medium text-ink-gray-9">{{ s.sequence || s.instance }}</span>
              <span class="ml-2 rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] text-ink-gray-6">{{ s.status }}</span>
            </div>
            <span class="text-xs text-ink-gray-6">
              {{ __('Step') }} {{ s.current_step }}/{{ s.total_steps }}
            </span>
          </div>
          <div v-if="s.next_send_date" class="mt-1 text-xs text-ink-gray-5">
            {{ __('Next send:') }} {{ s.next_send_date }}
          </div>
          <div class="mt-2 flex gap-2">
            <Button size="sm" variant="outline" :loading="acting === s.instance" @click="previewNext(s)">
              {{ __('Preview next step') }}
            </Button>
            <Button size="sm" variant="subtle" @click="draftNext(s)">{{ __('Draft step email') }}</Button>
          </div>
          <div v-if="preview && previewFor === s.instance" class="mt-3 rounded border border-ink-gray-2 bg-surface-gray-1 p-3">
            <div class="text-xs font-semibold text-ink-gray-7">{{ __('Subject:') }} {{ preview.subject }}</div>
            <p class="mt-1 whitespace-pre-wrap text-xs text-ink-gray-6">{{ preview.body }}</p>
            <span class="mt-2 inline-block rounded bg-surface-amber-2 px-1.5 py-0.5 text-[10px] text-ink-amber-3">{{ __('draft — human approves before send') }}</span>
          </div>
        </div>
      </div>
      <p v-else class="text-sm text-ink-gray-5">{{ __('Not in any sequence.') }}</p>
    </div>

    <!-- Drafts -->
    <div>
      <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
        {{ __('Drafts') }} ({{ data.draft_count || 0 }})
      </div>
      <div v-if="data.drafts && data.drafts.length" class="space-y-2">
        <div v-for="d in data.drafts" :key="d.name"
             class="rounded-lg border border-ink-gray-2 bg-surface-white px-4 py-3">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-ink-gray-9">{{ d.subject || __('(no subject)') }}</span>
            <span class="rounded bg-surface-amber-2 px-1.5 py-0.5 text-[10px] text-ink-amber-3">{{ __('draft') }}</span>
          </div>
          <div class="mt-1 text-xs text-ink-gray-5">{{ d.recipients }}</div>
          <div class="mt-2 flex gap-2">
            <Button size="sm" variant="outline" @click="$emit('review-draft', d)">{{ __('Review & send') }}</Button>
          </div>
        </div>
      </div>
      <p v-else class="text-sm text-ink-gray-5">{{ __('No drafts. Draft one to start outreach.') }}</p>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Button, call } from 'frappe-ui'

const props = defineProps({
  leadId: { type: String, required: true },
})
defineEmits(['draft-email', 'add-sequence', 'review-draft'])

const loading = ref(false)
const error = ref('')
const acting = ref('')
const preview = ref(null)
const previewFor = ref('')
const data = ref({ ok: false, drafts: [], sequences: [], has_outreach: false })

async function previewNext(s) {
  acting.value = s.instance
  try {
    const res = await call('crm.api.outreach_steps.next_step_preview', {
      lead: props.leadId, instance_name: s.instance,
    })
    preview.value = res
    previewFor.value = s.instance
  } catch (e) { preview.value = null } finally { acting.value = '' }
}

async function draftNext(s) {
  acting.value = s.instance
  try {
    await call('crm.api.outreach_steps.draft_step_email', {
      lead: props.leadId, instance_name: s.instance,
    })
    load()
  } finally { acting.value = '' }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await call('crm.api.lead_tabs.get_tab_data', {
      lead: props.leadId,
      tab: 'outreach',
    })
    data.value = res || { ok: false, drafts: [], sequences: [] }
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || __('Failed to load outreach')
    data.value = { ok: false, drafts: [], sequences: [], has_outreach: false }
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
