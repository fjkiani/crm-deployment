<template>
  <!-- AI actions for a single communication.
       Agent B ships this functional baseline; Agent C (feat/inbox-ai) enhances
       it in place (batch triage, tone selector, NYX brain_status guard). -->
  <div class="flex items-center gap-2">
    <Button
      variant="subtle"
      size="sm"
      :loading="triaging"
      :disabled="disabled"
      @click="runTriage"
    >
      <template #prefix><SparklesIcon class="h-4 w-4" /></template>
      Triage
    </Button>
    <Button
      variant="subtle"
      size="sm"
      :loading="drafting"
      :disabled="disabled"
      @click="runDraft"
    >
      <template #prefix><PenIcon class="h-4 w-4" /></template>
      AI Draft
    </Button>
  </div>
</template>

<script>
import { ref } from 'vue'
import { call, toast, Button } from 'frappe-ui'
import SparklesIcon from '~icons/lucide/sparkles'
import PenIcon from '~icons/lucide/pen-line'

export default {
  name: 'InboxAiActions',
  components: { Button, SparklesIcon, PenIcon },
  props: {
    communication: { type: Object, required: true },
    // Agent C: bind to brain_status() so AI is disabled when NYX is unavailable.
    disabled: { type: Boolean, default: false },
  },
  emits: ['triaged', 'drafted'],
  setup(props, { emit }) {
    const triaging = ref(false)
    const drafting = ref(false)

    async function runTriage() {
      triaging.value = true
      try {
        const res = await call('crm.api.email.triage_communication', {
          communication_name: props.communication.name,
        })
        emit('triaged', res || {})
      } catch (e) {
        toast.error('Triage failed: ' + (e.messages?.[0] || e.message || 'error'))
      } finally {
        triaging.value = false
      }
    }

    async function runDraft() {
      drafting.value = true
      try {
        const res = await call('crm.api.email.draft_ai_response', {
          communication_name: props.communication.name,
          tone: 'professional',
          include_context: true,
        })
        emit('drafted', res || {})
      } catch (e) {
        toast.error('AI draft failed: ' + (e.messages?.[0] || e.message || 'error'))
      } finally {
        drafting.value = false
      }
    }

    return { triaging, drafting, runTriage, runDraft }
  },
}
</script>
