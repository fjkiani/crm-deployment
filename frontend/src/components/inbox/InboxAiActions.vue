<template>
  <!-- Per-communication AI actions: Triage + AI Draft (tone-aware), guarded by
       NYX brain_status so the UI is truthful when no LLM/EAIA backend is live. -->
  <div class="flex items-center gap-2">
    <!-- Tone selector for AI Draft -->
    <select
      v-model="tone"
      class="rounded border bg-surface-white px-1.5 py-1 text-xs text-ink-gray-7"
      :disabled="!brainOk"
      :title="brainOk ? 'Draft tone' : brainDetail"
    >
      <option v-for="t in tones" :key="t" :value="t">{{ t }}</option>
    </select>

    <Button
      variant="subtle"
      size="sm"
      :loading="triaging"
      :disabled="!brainOk"
      :title="brainOk ? 'AI triage this email' : brainDetail"
      @click="runTriage"
    >
      <template #prefix><SparklesIcon class="h-4 w-4" /></template>
      Triage
    </Button>
    <Button
      variant="subtle"
      size="sm"
      :loading="drafting"
      :disabled="!brainOk"
      :title="brainOk ? 'Generate an AI draft reply' : brainDetail"
      @click="runDraft"
    >
      <template #prefix><PenIcon class="h-4 w-4" /></template>
      AI Draft
    </Button>

    <!-- Truthful brain state indicator -->
    <span
      v-if="brainChecked && !brainOk"
      class="text-xs text-ink-gray-4"
      :title="brainDetail"
    >
      AI offline
    </span>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { call, toast, Button } from 'frappe-ui'
import SparklesIcon from '~icons/lucide/sparkles'
import PenIcon from '~icons/lucide/pen-line'

export default {
  name: 'InboxAiActions',
  components: { Button, SparklesIcon, PenIcon },
  props: {
    communication: { type: Object, required: true },
  },
  emits: ['triaged', 'drafted'],
  setup(props, { emit }) {
    const triaging = ref(false)
    const drafting = ref(false)

    // Tone options for draft_ai_response(tone=...)
    const tones = ['professional', 'friendly', 'concise', 'formal']
    const tone = ref('professional')

    // NYX brain guard: checked once on mount; keeps the UI honest.
    const brainOk = ref(false)
    const brainChecked = ref(false)
    const brainDetail = ref('Checking AI backend…')

    async function checkBrain() {
      try {
        const st = await call('crm.api.nyx_email_brain.brain_status')
        brainOk.value = !!st?.ok
        brainDetail.value =
          st?.detail || (st?.ok ? 'AI backend ready.' : 'AI backend unavailable.')
      } catch (e) {
        brainOk.value = false
        brainDetail.value =
          'AI backend unreachable: ' + (e.messages?.[0] || e.message || 'error')
      } finally {
        brainChecked.value = true
      }
    }

    async function runTriage() {
      if (!brainOk.value) return
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
      if (!brainOk.value) return
      drafting.value = true
      try {
        const res = await call('crm.api.email.draft_ai_response', {
          communication_name: props.communication.name,
          tone: tone.value,
          include_context: true,
        })
        // draft_ai_response returns { subject, content, summary, communication_name }
        emit('drafted', res || {})
      } catch (e) {
        toast.error('AI draft failed: ' + (e.messages?.[0] || e.message || 'error'))
      } finally {
        drafting.value = false
      }
    }

    onMounted(checkBrain)

    return {
      triaging,
      drafting,
      tones,
      tone,
      brainOk,
      brainChecked,
      brainDetail,
      runTriage,
      runDraft,
    }
  },
}
</script>
