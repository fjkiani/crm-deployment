<template>
  <div class="flex flex-1 flex-col overflow-y-auto">
    <!-- Header -->
    <div class="mx-4 my-3 flex items-center justify-between sm:mx-10 sm:mb-4 sm:mt-8">
      <div class="flex h-8 items-center text-xl font-semibold text-ink-gray-8">
        {{ __('Nyx Intelligence') }}
      </div>
      <div class="flex gap-2">
        <Button
          variant="solid"
          :label="enriching ? __('Enriching...') : __('Enrich Lead')"
          iconLeft="zap"
          :loading="enriching"
          @click="runEnrichment"
        />
        <Button
          variant="subtle"
          :label="triaging ? __('Drafting...') : __('Triage & Draft')"
          iconLeft="edit"
          :loading="triaging"
          @click="triageAndDraft"
        />
        <Button
          v-if="draftReady"
          variant="solid"
          :label="approving ? __('Sending...') : __('Approve & Send')"
          iconLeft="send"
          theme="green"
          :loading="approving"
          @click="approveDraft"
        />
      </div>
    </div>

    <!-- Score Badge -->
    <div v-if="score !== null" class="mx-4 sm:mx-10">
      <div class="flex items-center gap-4 rounded-xl p-4" :class="scoreBgClass">
        <div class="flex flex-col items-center justify-center rounded-xl bg-white/90 px-4 py-2 shadow-sm">
          <span class="text-3xl font-bold" :class="scoreTextClass">{{ score }}</span>
          <span class="text-xs font-medium text-ink-gray-5 uppercase">{{ framework }}</span>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-semibold text-ink-gray-9">{{ scoreLabel }}</span>
          <span class="text-sm text-ink-gray-6">{{ reasoning }}</span>
          <span v-if="angle" class="text-xs text-ink-gray-5 italic">
            Sales Angle: {{ angle }}
          </span>
        </div>
      </div>
    </div>

    <!-- Context Tags -->
    <div v-if="contexts.length" class="mx-4 mt-3 flex flex-wrap gap-2 sm:mx-10">
      <span
        v-for="ctx in contexts"
        :key="ctx"
        class="rounded-full px-3 py-1 text-xs font-medium"
        :class="contextClass(ctx)"
      >
        {{ ctx }}
      </span>
    </div>

    <!-- Signal Cards -->
    <div v-if="signals" class="mx-4 mt-4 grid gap-3 sm:mx-10 sm:grid-cols-2">
      <div
        v-for="(value, key) in signalCards"
        :key="key"
        class="rounded-lg border border-surface-gray-3 bg-surface-white p-4"
      >
        <div class="text-xs font-medium uppercase text-ink-gray-4">
          {{ formatKey(key) }}
        </div>
        <div class="mt-1 text-sm text-ink-gray-8">
          {{ value || 'Not found' }}
        </div>
      </div>
    </div>

    <!-- Email Draft Preview -->
    <div v-if="emailDraft" class="mx-4 mt-4 sm:mx-10">
      <div class="rounded-lg border border-surface-gray-3 bg-surface-white">
        <div class="flex items-center justify-between border-b px-4 py-3">
          <span class="text-sm font-semibold text-ink-gray-8">📧 Email Draft</span>
          <span
            class="rounded-full px-2 py-0.5 text-xs font-medium"
            :class="statusBadgeClass"
          >
            {{ emailStatus }}
          </span>
        </div>
        <div class="p-4">
          <div class="text-sm font-medium text-ink-gray-7">
            Subject: {{ emailDraft.subject }}
          </div>
          <div class="mt-2 whitespace-pre-wrap text-sm text-ink-gray-6 leading-relaxed">
            {{ emailDraft.body }}
          </div>
          <div v-if="emailDraft.ps" class="mt-2 text-xs italic text-ink-gray-4">
            P.S. {{ emailDraft.ps }}
          </div>
        </div>
      </div>
    </div>

    <!-- Enrichment Sources -->
    <div v-if="sourcesUsed.length" class="mx-4 mt-4 sm:mx-10">
      <div class="text-xs font-medium uppercase text-ink-gray-4 mb-2">
        Sources Used
      </div>
      <div class="flex flex-wrap gap-1.5">
        <span
          v-for="src in sourcesUsed"
          :key="src"
          class="rounded bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-6"
        >
          {{ src }}
        </span>
      </div>
    </div>

    <!-- Reply Intelligence -->
    <div v-if="replyClassification" class="mx-4 mt-4 sm:mx-10">
      <div class="rounded-lg border border-surface-gray-3 bg-surface-white">
        <div class="flex items-center justify-between border-b px-4 py-3">
          <span class="text-sm font-semibold text-ink-gray-8">📨 Reply Intelligence</span>
          <span
            class="rounded-full px-2 py-0.5 text-xs font-medium"
            :class="replyBadgeClass"
          >
            {{ replyClassification }}
          </span>
        </div>
        <div class="p-4 space-y-2">
          <!-- Confidence bar -->
          <div v-if="replyConfidence" class="flex items-center gap-2">
            <span class="text-xs text-ink-gray-5 w-16">Confidence</span>
            <div class="flex-1 h-1.5 bg-surface-gray-2 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full"
                :class="replyConfidence > 0.7 ? 'bg-green-500' : replyConfidence > 0.4 ? 'bg-yellow-500' : 'bg-red-400'"
                :style="{ width: (replyConfidence * 100) + '%' }"
              />
            </div>
            <span class="text-xs text-ink-gray-5">{{ Math.round(replyConfidence * 100) }}%</span>
          </div>
          <!-- Reasoning -->
          <div v-if="replyReasoning" class="text-sm text-ink-gray-6">
            {{ replyReasoning }}
          </div>
          <!-- Suggested response -->
          <div v-if="replySuggestion" class="text-xs text-ink-gray-4 italic">
            💡 {{ replySuggestion }}
          </div>
          <!-- Objection type -->
          <div v-if="objectionType" class="flex items-center gap-1">
            <span class="text-xs text-ink-gray-5">Objection:</span>
            <span class="rounded bg-orange-100 px-1.5 py-0.5 text-xs font-medium text-orange-700">
              {{ objectionType }}
            </span>
          </div>
          <!-- Handoff info -->
          <div v-if="handoffName" class="flex items-center gap-1">
            <span class="text-xs text-ink-gray-5">Handed off to:</span>
            <span class="text-xs font-medium text-ink-gray-8">
              {{ handoffName }}{{ handoffEmail ? ` (${handoffEmail})` : '' }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Rebuttal Draft -->
    <div v-if="rebuttalDraft" class="mx-4 mt-3 sm:mx-10">
      <div class="rounded-lg border border-orange-200 bg-orange-50/50">
        <div class="flex items-center justify-between border-b border-orange-200 px-4 py-2">
          <span class="text-sm font-semibold text-orange-800">🔄 Auto-Drafted Rebuttal</span>
          <Button
            variant="solid"
            :label="approving ? __('Sending...') : __('Approve Rebuttal')"
            iconLeft="send"
            theme="orange"
            size="sm"
            :loading="approving"
            @click="approveDraft"
          />
        </div>
        <div class="p-4">
          <div class="text-sm font-medium text-ink-gray-7">
            Subject: {{ rebuttalDraft.subject }}
          </div>
          <div class="mt-2 whitespace-pre-wrap text-sm text-ink-gray-6 leading-relaxed">
            {{ rebuttalDraft.body }}
          </div>
        </div>
      </div>
    </div>

    <!-- Phase 10: Engagement Timeline -->
    <div v-if="engagementTimeline.length" class="mx-4 mt-3 sm:mx-10">
      <div class="rounded-lg border border-surface-gray-3 bg-surface-white">
        <div class="border-b border-surface-gray-3 px-4 py-2">
          <span class="text-sm font-semibold text-ink-gray-8">📈 Engagement Timeline</span>
        </div>
        <div class="p-4 space-y-3">
          <div v-for="(event, idx) in engagementTimeline" :key="idx" class="flex gap-3 items-start">
            <div class="flex flex-col items-center">
              <div class="w-2 h-2 rounded-full mt-1.5"
                :class="{
                  'bg-blue-500': event.type === 'enrichment',
                  'bg-green-500': event.type === 'email_sent',
                  'bg-purple-500': event.type === 'reply',
                  'bg-orange-500': event.type === 'vulture',
                  'bg-cyan-500': event.type === 'entanglement',
                  'bg-gray-400': !event.type,
                }"
              />
              <div v-if="idx < engagementTimeline.length - 1" class="w-px flex-1 bg-surface-gray-3 mt-1" />
            </div>
            <div class="flex-1 pb-2">
              <div class="text-xs font-semibold text-ink-gray-7">{{ event.label }}</div>
              <div class="text-xs text-ink-gray-5">{{ event.detail }}</div>
              <div v-if="event.date" class="text-[10px] text-ink-gray-4 mt-0.5">{{ event.date }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-if="!score && !enriching"
      class="flex flex-1 flex-col items-center justify-center gap-2 text-ink-gray-4"
    >
      <svg class="size-12 opacity-40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" stroke="currentColor" stroke-width="1.5" />
        <path d="M8 12l2 2 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
      <span class="text-sm">No enrichment data yet</span>
      <span class="text-xs">Click "Enrich Lead" to start the Nyx intelligence engine</span>
    </div>

    <!-- Loading state -->
    <div
      v-if="enriching"
      class="flex flex-1 flex-col items-center justify-center gap-3 text-ink-gray-5"
    >
      <div class="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
      <span class="text-sm font-medium">Nyx is researching {{ doc.lead_name }}...</span>
      <span class="text-xs">Searching across {{ enrichStage }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Button, toast, createResource } from 'frappe-ui'

const props = defineProps({
  doc: { type: Object, required: true },
  leadId: { type: String, required: true },
})

const enriching = ref(false)
const approving = ref(false)
const triaging = ref(false)
const draftCommName = ref(null)  // Communication name of the last brain-produced draft
const enrichStage = ref('web, Apollo, BrightData, PubMed, ClinicalTrials...')

// ── Computed from CRM Lead additional_data ───────────────────────────────────

const additionalData = computed(() => {
  try {
    return JSON.parse(props.doc.additional_data || '{}')
  } catch { return {} }
})

const score = computed(() => additionalData.value.score ?? null)
const framework = computed(() => additionalData.value.framework || '')
const reasoning = computed(() => additionalData.value.score_reasoning || '')
const angle = computed(() => additionalData.value.score_angle || '')
const contexts = computed(() => additionalData.value.detected_context || [])
const sourcesUsed = computed(() => additionalData.value.enrichment_sources_used || [])
const emailStatus = computed(() => additionalData.value.email_status || 'None')
const draftReady = computed(() => emailStatus.value === 'Draft Ready')

const signals = computed(() => additionalData.value.distilled_signals || null)
const signalCards = computed(() => {
  if (!signals.value) return {}
  const { specific_number, recent_event, strategic_detail, blind_spot, competitor_name } = signals.value
  return { specific_number, recent_event, strategic_detail, blind_spot, competitor_name }
})

const emailDraft = computed(() => {
  const draft = additionalData.value.email_draft
  if (!draft || draft.quarantined) return null
  return draft.email || draft
})

const scoreLabel = computed(() => {
  if (score.value >= 70) return '🔥 HOT — High-priority target'
  if (score.value >= 40) return '🟡 WARM — Needs nurturing'
  return '❄️ COLD — Low priority'
})

const scoreBgClass = computed(() => {
  if (score.value >= 70) return 'bg-gradient-to-r from-red-50 to-orange-50 border border-red-100'
  if (score.value >= 40) return 'bg-gradient-to-r from-yellow-50 to-amber-50 border border-yellow-100'
  return 'bg-gradient-to-r from-blue-50 to-slate-50 border border-blue-100'
})

const scoreTextClass = computed(() => {
  if (score.value >= 70) return 'text-red-600'
  if (score.value >= 40) return 'text-yellow-600'
  return 'text-blue-600'
})

const statusBadgeClass = computed(() => {
  switch (emailStatus.value) {
    case 'Draft Ready': return 'bg-yellow-100 text-yellow-700'
    case 'Approved': return 'bg-blue-100 text-blue-700'
    case 'Sent': return 'bg-green-100 text-green-700'
    case 'Quarantined': return 'bg-red-100 text-red-700'
    case 'Rebuttal Draft Ready': return 'bg-orange-100 text-orange-700'
    case 'Reply Received': return 'bg-purple-100 text-purple-700'
    case 'Handoff Received': return 'bg-teal-100 text-teal-700'
    default: return 'bg-gray-100 text-gray-600'
  }
})

// ── Reply Intelligence ─────────────────────────────────────────────────────

const replyClassification = computed(() => additionalData.value.reply_classification || '')
const replyConfidence = computed(() => additionalData.value.reply_confidence || 0)
const replyReasoning = computed(() => additionalData.value.reply_reasoning || '')
const replySuggestion = computed(() => additionalData.value.reply_suggested_response || '')
const objectionType = computed(() => additionalData.value.objection_type || '')
const handoffName = computed(() => additionalData.value.handoff_to || '')
const handoffEmail = computed(() => additionalData.value.handoff_email || '')
const rebuttalDraft = computed(() => {
  if (emailStatus.value !== 'Rebuttal Draft Ready') return null
  return additionalData.value.email_draft || null
})

const replyBadgeClass = computed(() => {
  const classes = {
    'INTERESTED': 'bg-green-100 text-green-700',
    'NOT_INTERESTED': 'bg-red-100 text-red-700',
    'OBJECTION': 'bg-orange-100 text-orange-700',
    'WARM_HANDOFF': 'bg-teal-100 text-teal-700',
    'UNSUBSCRIBE': 'bg-red-200 text-red-800',
    'OOO': 'bg-blue-100 text-blue-700',
    'QUESTION': 'bg-purple-100 text-purple-700',
    'UNKNOWN': 'bg-gray-100 text-gray-600',
  }
  return classes[replyClassification.value] || 'bg-gray-100 text-gray-600'
})

// ── Engagement Timeline (Phase 10) ─────────────────────────────────────────

const engagementTimeline = computed(() => {
  const events = []
  const data = additionalData.value

  // Enrichment events
  if (data.enrichment_sources_used) {
    events.push({
      type: 'enrichment',
      label: '🔍 Enrichment Complete',
      detail: `Sources: ${(data.enrichment_sources_used || []).join(', ')}`,
      date: data.enriched_at || '',
    })
  }

  // Score event
  if (data.score != null) {
    events.push({
      type: 'enrichment',
      label: `📊 Scored ${data.score}/100 (${data.framework || 'N/A'})`,
      detail: data.reasoning || '',
      date: '',
    })
  }

  // Entanglement event
  if (data.entangled) {
    const coworkers = data.entangled_coworkers || []
    events.push({
      type: 'entanglement',
      label: '🕸️ Entanglement Detected',
      detail: coworkers.length ? `Linked: ${coworkers.join(', ')}` : 'Portfolio links found',
      date: '',
    })
  }

  // Email draft event
  if (data.email_draft) {
    events.push({
      type: 'email_sent',
      label: `📨 Email Draft (${emailStatus.value})`,
      detail: data.email_draft.subject || data.email_draft.email?.subject || '',
      date: data.email_sent_at || '',
    })
  }

  // Reply event
  if (replyClassification.value) {
    events.push({
      type: 'reply',
      label: `💬 Reply: ${replyClassification.value}`,
      detail: replyReasoning.value || '',
      date: data.reply_received_at || '',
    })
  }

  // Vulture event
  if (data.vulture_event_detected) {
    events.push({
      type: 'vulture',
      label: '🦅 Vulture Protocol Triggered',
      detail: data.vulture_draft_subject || 'Competitor disruption detected',
      date: data.vulture_event_date || '',
    })
  }

  return events
})

function contextClass(ctx) {
  const classes = {
    core: 'bg-blue-100 text-blue-700',
    financial: 'bg-green-100 text-green-700',
    clinical: 'bg-purple-100 text-purple-700',
    biotech: 'bg-cyan-100 text-cyan-700',
    pharma: 'bg-pink-100 text-pink-700',
  }
  return classes[ctx] || 'bg-gray-100 text-gray-600'
}

function formatKey(key) {
  return key.replace(/_/g, ' ')
}

// ── Actions ──────────────────────────────────────────────────────────────────

const EAIA_URL = window.nyx_config?.eaia_url || 'http://localhost:8002'

const enrichResource = createResource({
  url: 'crm.api.enrichment.enrich_lead_email',
  makeParams: () => ({ lead_name: props.leadId, write: true }),
})

// NYX Email Brain (runtime-swappable): on-demand triage -> draft into Human Inbox.
// Inbound-reply drafting is handled separately by the EAIA Gmail cron loop; this
// button covers proactive/outbound drafting from inside the app.
const triageResource = createResource({
  url: 'crm.api.nyx_email_brain.triage_and_draft',
  makeParams: () => ({ lead_name: props.leadId, force: true }),
})

// Approve & send always routes through the Frappe send gate (auditable),
// regardless of which brain backend produced the draft.
const sendResource = createResource({
  url: 'crm.api.nyx_email_brain.approve_and_send',
  makeParams: (name) => ({ communication_name: name }),
})

// Fallback lookup: latest draft Communication linked to this lead, used when the
// draft was produced out-of-band (e.g. by the EAIA inbound loop, not this session).
const draftLookup = createResource({
  url: 'crm.api.email.get_inbox',
  makeParams: () => ({ doctype: 'CRM Lead', docname: props.leadId, limit: 5 }),
})

async function resolvePendingDraft() {
  if (draftCommName.value) return draftCommName.value
  const rows = (await draftLookup.submit()) || []
  const draft = rows.find(
    (r) => r.communication_type === 'Communication' && r.status !== 'Sent',
  )
  return draft ? draft.name : null
}

async function runEnrichment() {
  enriching.value = true
  enrichStage.value = 'discovering verified email (Tavily two-gate)...'

  try {
    // In-app enrichment (deployed): resolves a verified email via Tavily two-gate
    // adjudication. Runtime-agnostic — does NOT depend on the external EAIA service.
    const result = (await enrichResource.submit()) || {}
    const decision = result.decision

    if (decision === 'written') {
      toast({ variant: 'success', title: `Email verified & saved: ${result.email}` })
      window.location.reload()
    } else if (decision === 'skip_has_email') {
      toast({ variant: 'info', title: `Lead already has an email: ${result.email}` })
    } else if (decision === 'held') {
      toast({
        variant: 'warning',
        title: 'Enrichment held',
        text: `Candidates found but none passed the verification gate: ${(result.candidates || []).join(', ') || 'n/a'}`,
      })
    } else if (decision === 'no_candidate') {
      toast({
        variant: 'warning',
        title: 'No email candidates found',
        text: result.error ? `Reason: ${result.error}` : 'The web scout returned no candidate emails for this lead.',
      })
    } else {
      toast({ variant: 'info', title: `Enrichment result: ${decision || 'unknown'}` })
    }
  } catch (err) {
    toast({ variant: 'error', title: `Enrichment error: ${err.message || err}` })
  } finally {
    enriching.value = false
  }
}

async function triageAndDraft() {
  triaging.value = true
  try {
    // In-app brain: triage the lead and, if warranted, draft a reply into the
    // Human Inbox for approval. force=true so a proactive outbound draft is made.
    const result = (await triageResource.submit()) || {}
    const decision = result.decision

    if (decision === 'drafted') {
      draftCommName.value = result.communication || null
      toast({
        variant: 'success',
        title: 'Draft ready for approval',
        text: `Subject: ${result.subject || '(none)'} — review it in the Human Inbox, then Approve & Send.`,
      })
      window.location.reload()
    } else if (decision === 'ignore' || decision === 'notify') {
      toast({
        variant: 'info',
        title: `Triage: ${decision}`,
        text: result.reason || 'No draft was created.',
      })
    } else if (decision === 'no_llm') {
      toast({ variant: 'error', title: 'No LLM provider configured for the email brain.' })
    } else if (decision === 'draft_failed') {
      toast({ variant: 'error', title: 'Draft generation failed', text: result.error || '' })
    } else if (decision && decision.startsWith('eaia')) {
      toast({ variant: 'info', title: `EAIA backend: ${decision}`, text: result.error || '' })
    } else {
      toast({ variant: 'info', title: `Triage result: ${decision || 'unknown'}` })
    }
  } catch (err) {
    toast({ variant: 'error', title: `Triage error: ${err.message || err}` })
  } finally {
    triaging.value = false
  }
}

async function approveDraft() {
  approving.value = true
  try {
    // Route the pending draft through the Frappe send gate (frappe.sendmail).
    // Runtime-agnostic: does NOT depend on the external EAIA service.
    const name = await resolvePendingDraft()
    if (!name) {
      toast({ variant: 'warning', title: 'No pending draft found for this lead to send.' })
      return
    }
    const result = (await sendResource.submit(name)) || {}
    if (result.ok) {
      toast({ variant: 'success', title: 'Email sent' })
      draftCommName.value = null
      window.location.reload()
    } else {
      toast({ variant: 'error', title: result.error || 'Send failed' })
    }
  } catch (err) {
    toast({ variant: 'error', title: `Approve error: ${err.message || err}` })
  } finally {
    approving.value = false
  }
}
</script>
