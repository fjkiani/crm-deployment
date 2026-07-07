<template>
  <div class="flex min-h-0 flex-1 flex-col">
    <!-- Thread header -->
    <div class="flex items-start justify-between gap-3 border-b px-4 py-3">
      <div class="min-w-0">
        <div class="truncate text-base font-semibold text-ink-gray-9">
          {{ subject || '(no subject)' }}
        </div>
        <div class="mt-0.5 truncate text-xs text-ink-gray-5">
          {{ communication.reference_doctype }} · {{ communication.reference_name }}
        </div>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <!-- Agent C mounts AI actions here (triage + AI draft) -->
        <InboxAiActions
          :communication="communication"
          @triaged="onTriaged"
          @drafted="onDrafted"
        />
      </div>
    </div>

    <!-- Triage result (populated by AI actions) -->
    <div
      v-if="triage"
      class="border-b bg-surface-blue-1 px-4 py-2 text-sm text-ink-gray-8"
    >
      <span class="font-medium">Triage:</span>
      <span v-if="triage.priority" class="ml-1 font-medium">[{{ triage.priority }}]</span>
      <span v-if="triage.action" class="ml-1 uppercase">{{ triage.action }}</span>
      <span v-if="triage.reason" class="ml-1 text-ink-gray-7">— {{ triage.reason }}</span>
      <span v-if="triage.suggested_response" class="ml-1 italic text-ink-gray-6">
        ({{ triage.suggested_response }})
      </span>
    </div>

    <!-- Thread messages (reading pane) -->
    <div class="min-h-0 flex-1 overflow-y-auto px-4 py-3">
      <div v-if="threadLoading" class="text-sm text-ink-gray-5">Loading thread…</div>
      <div
        v-for="msg in thread"
        :key="msg.name"
        class="mb-3 rounded border"
        :class="msg.sent_or_received === 'Sent' ? 'bg-surface-gray-1' : 'bg-surface-white'"
      >
        <div class="flex items-center justify-between gap-2 border-b px-3 py-1.5">
          <span class="truncate text-xs font-medium text-ink-gray-8">
            {{ msg.sent_or_received === 'Sent' ? 'To: ' + (msg.recipients || '—') : (msg.sender || '—') }}
          </span>
          <span class="shrink-0 text-xs text-ink-gray-4">{{ fmtDate(msg.creation) }}</span>
        </div>
        <TextEditor
          :content="msg.content || '<em>(no content)</em>'"
          :editable="false"
          editor-class="prose-sm max-w-none px-3 py-2 text-ink-gray-7 focus:outline-none"
        />
      </div>
    </div>

    <!-- Composer (inline edit-then-send; replaces the /app/communication bounce-out) -->
    <div class="border-t bg-surface-gray-1 px-4 py-3">
      <div class="mb-2 flex items-center gap-2">
        <span class="text-xs font-medium text-ink-gray-6">To</span>
        <input
          v-model="reply.to"
          type="text"
          class="flex-1 rounded border px-2 py-1 text-sm"
          placeholder="recipient@example.com"
        />
      </div>
      <div class="mb-2 flex items-center gap-2">
        <span class="text-xs font-medium text-ink-gray-6">Subject</span>
        <input
          v-model="reply.subject"
          type="text"
          class="flex-1 rounded border px-2 py-1 text-sm"
        />
      </div>
      <div class="rounded border bg-surface-white">
        <TextEditor
          ref="composer"
          :content="reply.html"
          @change="reply.html = $event"
          editor-class="prose-sm max-w-none min-h-[7rem] px-3 py-2 focus:outline-none"
          placeholder="Write a reply, or use AI Draft above…"
        />
      </div>
      <div class="mt-2 flex items-center justify-end gap-2">
        <Button
          v-if="reply.draftName"
          variant="ghost"
          :loading="discarding"
          @click="discardDraft"
        >
          Discard
        </Button>
        <Button variant="subtle" :loading="savingDraft" @click="saveDraft">
          Save draft
        </Button>
        <Button variant="solid" :loading="sending" @click="sendReply">
          <template #prefix><SendIcon class="h-4 w-4" /></template>
          Send
        </Button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, watch, onMounted } from 'vue'
import { call, toast, Button, TextEditor } from 'frappe-ui'
import SendIcon from '~icons/lucide/send'
import InboxAiActions from '@/components/inbox/InboxAiActions.vue'

export default {
  name: 'InboxReader',
  components: { Button, TextEditor, SendIcon, InboxAiActions },
  props: {
    communication: { type: Object, required: true },
  },
  emits: ['sent', 'discarded'],
  setup(props, { emit }) {
    const thread = ref([])
    const threadLoading = ref(false)
    const subject = ref('')
    const triage = ref(null)

    const reply = reactive({
      to: '',
      subject: '',
      html: '',
      draftName: null, // set when a Draft Communication exists (AI draft or saved)
    })

    const savingDraft = ref(false)
    const sending = ref(false)
    const discarding = ref(false)

    function fmtDate(dt) {
      if (!dt) return ''
      const d = new Date(dt.replace(' ', 'T'))
      return isNaN(d) ? '' : d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    }

    async function loadThread() {
      threadLoading.value = true
      triage.value = null
      try {
        const rows = await call('crm.api.email.thread_context', {
          communication: props.communication.name,
          limit: 50,
        })
        thread.value = Array.isArray(rows) ? rows : []
        // Seed reply defaults from the latest inbound message.
        const inbound = [...thread.value].reverse().find((m) => m.sent_or_received === 'Received')
        const base = inbound || thread.value[thread.value.length - 1] || props.communication
        subject.value = base.subject || ''
        reply.subject = base.subject ? (base.subject.startsWith('Re:') ? base.subject : 'Re: ' + base.subject) : ''
        reply.to = inbound ? inbound.sender || '' : base.recipients || ''
        reply.html = ''
        reply.draftName = null
      } catch (e) {
        toast.error('Failed to load thread: ' + (e.messages?.[0] || e.message || 'error'))
        thread.value = []
      } finally {
        threadLoading.value = false
      }
    }

    // Agent C events -----------------------------------------------------
    function onTriaged(result) {
      triage.value = result || { message: 'Triage complete' }
    }
    function onDrafted(result) {
      // draft_ai_response returns a dict; pull draft body + name if present.
      const html = result?.html || result?.draft || result?.body || result?.content || ''
      if (html) reply.html = html
      if (result?.communication_name || result?.draft_name || result?.name) {
        reply.draftName = result.communication_name || result.draft_name || result.name
      }
      if (result?.subject) reply.subject = result.subject
      toast.success('AI draft loaded — edit and send.')
    }

    // Composer actions ---------------------------------------------------
    function _refDoc() {
      return {
        reference_doctype: props.communication.reference_doctype,
        reference_name: props.communication.reference_name,
      }
    }

    async function saveDraft() {
      if (!reply.to || !reply.subject || !reply.html) {
        toast.error('To, subject and body are required.')
        return
      }
      savingDraft.value = true
      try {
        // Upsert: pass the existing draft name so re-saving updates the same doc
        // (no orphan duplicates) and persists the current editor contents.
        const name = await call('crm.api.email.save_draft', {
          ..._refDoc(),
          to: reply.to,
          subject: reply.subject,
          html: reply.html,
          provider_thread_id: props.communication.provider_thread_id || null,
          communication_name: reply.draftName || null,
        })
        reply.draftName = name
        toast.success('Draft saved.')
      } catch (e) {
        toast.error('Save draft failed: ' + (e.messages?.[0] || e.message || 'error'))
      } finally {
        savingDraft.value = false
      }
    }

    async function sendReply() {
      if (!reply.to || !reply.subject || !reply.html) {
        toast.error('To, subject and body are required.')
        return
      }
      sending.value = true
      try {
        // Always persist the CURRENT editor contents before sending. Upsert onto
        // the existing draft (reply.draftName) when present so edits made to an
        // AI-populated or previously-saved draft are the ones that get sent —
        // otherwise Send would transmit the stale original draft.
        const commName = await call('crm.api.email.save_draft', {
          ..._refDoc(),
          to: reply.to,
          subject: reply.subject,
          html: reply.html,
          provider_thread_id: props.communication.provider_thread_id || null,
          communication_name: reply.draftName || null,
        })
        reply.draftName = commName
        const res = await call('crm.api.email.send', { communication_name: commName })
        if (res?.ok) {
          toast.success('Email sent.')
          emit('sent', commName)
        } else {
          toast.error('Send did not confirm.')
        }
      } catch (e) {
        toast.error('Send failed: ' + (e.messages?.[0] || e.message || 'error'))
      } finally {
        sending.value = false
      }
    }

    async function discardDraft() {
      if (!reply.draftName) {
        emit('discarded')
        return
      }
      discarding.value = true
      try {
        await call('frappe.client.delete', { doctype: 'Communication', name: reply.draftName })
        toast.success('Draft discarded.')
        emit('discarded')
      } catch (e) {
        toast.error('Discard failed: ' + (e.messages?.[0] || e.message || 'error'))
      } finally {
        discarding.value = false
      }
    }

    watch(() => props.communication && props.communication.name, loadThread)
    onMounted(loadThread)

    return {
      thread,
      threadLoading,
      subject,
      triage,
      reply,
      savingDraft,
      sending,
      discarding,
      fmtDate,
      onTriaged,
      onDrafted,
      saveDraft,
      sendReply,
      discardDraft,
    }
  },
}
</script>
