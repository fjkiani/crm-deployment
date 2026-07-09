<template>
  <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
    <!-- ================= LEFT: Campaign Studio ================= -->
    <div class="rounded-lg border border-ink-gray-2 bg-surface-white p-4">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-ink-gray-8">{{ __('Campaign Studio') }}</h2>
        <span
          v-if="plan"
          class="rounded-full px-2 py-0.5 text-[10px] font-medium"
          :class="plan.llm_used ? 'bg-surface-green-2 text-ink-green-3' : 'bg-surface-gray-2 text-ink-gray-6'"
        >{{ plan.llm_used ? __('Nyx-drafted') : __('Template (no model)') }}</span>
      </div>
      <p class="mb-3 text-xs leading-relaxed text-ink-gray-5">
        {{ __('Pick a segment, let Nyx propose a cadence, review it, then launch. Launching creates the sequence, enrolls prospects, and drops a kickoff task — it does not send anything until you approve.') }}
      </p>

      <!-- Step 1: pick segment -->
      <div class="space-y-2">
        <label class="block text-xs font-medium text-ink-gray-6">{{ __('Segment') }}</label>
        <select
          v-model="selectedTier"
          class="w-full rounded-md border border-ink-gray-3 bg-surface-white px-2.5 py-1.5 text-sm text-ink-gray-7 focus:border-ink-blue-4 focus:outline-none"
        >
          <option value="">{{ __('All prospects') }} ({{ segments.total_prospects ?? '—' }})</option>
          <option v-for="t in tierOpts" :key="t.value" :value="t.value">{{ t.label }} ({{ t.count }})</option>
        </select>
        <input
          v-model="goal"
          type="text"
          :placeholder="__('Optional goal — e.g. book intro calls with KRAS programs')"
          class="w-full rounded-md border border-ink-gray-3 bg-surface-white px-2.5 py-1.5 text-sm focus:border-ink-blue-4 focus:outline-none"
        />
        <Button variant="solid" class="w-full" :loading="planning" @click="askPlan">
          <template #prefix><LucideSparkles class="h-4 w-4" /></template>
          {{ __('Ask Nyx to plan this campaign') }}
        </Button>
        <p v-if="!brainOk" class="text-[11px] leading-snug text-ink-amber-3">
          {{ __('No model configured — Nyx will return a template cadence. Set a provider under “Model” for tailored copy.') }}
        </p>
      </div>

      <!-- Step 2: review plan -->
      <div v-if="plan" class="mt-4 border-t border-ink-gray-2 pt-4">
        <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-4">
          {{ __('Proposed plan') }} · {{ plan.segment.label }} ({{ plan.segment.count }})
        </div>
        <label class="mb-1 block text-[11px] font-medium text-ink-gray-6">{{ __('Campaign name') }}</label>
        <input v-model="editName" class="mb-2 w-full rounded-md border border-ink-gray-3 px-2.5 py-1.5 text-sm focus:border-ink-blue-4 focus:outline-none" />
        <label class="mb-1 block text-[11px] font-medium text-ink-gray-6">{{ __('Subject') }}</label>
        <input v-model="editSubject" class="mb-2 w-full rounded-md border border-ink-gray-3 px-2.5 py-1.5 text-sm focus:border-ink-blue-4 focus:outline-none" />
        <p v-if="plan.plan.rationale" class="mb-2 rounded bg-surface-gray-1 px-2 py-1.5 text-[11px] italic text-ink-gray-6">
          {{ plan.plan.rationale }}
        </p>
        <div class="space-y-2">
          <div v-for="(s, i) in editSteps" :key="i" class="rounded-md border border-ink-gray-2 p-2">
            <div class="mb-1 flex items-center gap-2 text-[11px] text-ink-gray-5">
              <span class="rounded bg-surface-blue-2 px-1.5 py-px font-medium text-ink-blue-6">{{ __('Step') }} {{ s.step_number }}</span>
              <span>{{ s.channel }}</span>
              <span class="ml-auto">{{ s.delay_days === 0 ? __('Day 0') : __('Day +') + s.delay_days }}</span>
            </div>
            <div class="mb-1 text-xs font-medium text-ink-gray-7">{{ s.angle }}</div>
            <textarea
              v-model="s.body"
              rows="2"
              class="w-full resize-y rounded border border-ink-gray-2 px-2 py-1 text-[11px] text-ink-gray-6 focus:border-ink-blue-4 focus:outline-none"
              :placeholder="__('Message body…')"
            ></textarea>
          </div>
        </div>

        <!-- Step 3: launch -->
        <div class="mt-3 flex items-center gap-2">
          <label class="flex items-center gap-1.5 text-[11px] text-ink-gray-6">
            {{ __('Enroll top') }}
            <input v-model.number="enrollLimit" type="number" min="0" max="200" class="w-14 rounded border border-ink-gray-3 px-1.5 py-0.5 text-xs" />
            {{ __('prospects') }}
          </label>
          <Button variant="solid" class="ml-auto" :loading="launching" @click="launch">
            <template #prefix><LucideRocket class="h-4 w-4" /></template>
            {{ __('Launch campaign') }}
          </Button>
        </div>
      </div>
    </div>

    <!-- ================= RIGHT: Suggestions + campaigns ================= -->
    <div class="space-y-6">
      <!-- Suggested next actions -->
      <div class="rounded-lg border border-ink-gray-2 bg-surface-white p-4">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-ink-gray-8">{{ __('What should I work on?') }}</h2>
          <div class="flex gap-1">
            <button
              v-for="m in moods"
              :key="m.value"
              class="rounded-full px-2 py-0.5 text-[10px] font-medium"
              :class="mood === m.value ? 'bg-ink-blue-6 text-surface-white' : 'bg-surface-gray-2 text-ink-gray-6 hover:bg-surface-gray-3'"
              @click="setMood(m.value)"
            >{{ m.label }}</button>
          </div>
        </div>
        <div v-if="suggest.loading" class="py-6 text-center text-sm text-ink-gray-5">{{ __('Nyx is thinking…') }}</div>
        <div v-else-if="suggestions.length" class="space-y-2">
          <div
            v-for="(s, i) in suggestions"
            :key="i"
            class="rounded-md border border-ink-gray-2 p-2.5"
          >
            <div class="flex items-start gap-2">
              <span
                class="mt-0.5 shrink-0 rounded px-1.5 py-px text-[9px] font-semibold uppercase"
                :class="s.priority === 'High' ? 'bg-surface-amber-2 text-ink-amber-3' : 'bg-surface-gray-2 text-ink-gray-6'"
              >{{ s.priority }}</span>
              <div class="min-w-0 flex-1">
                <div class="text-xs font-medium text-ink-gray-8">{{ s.title }}</div>
                <div class="mt-0.5 text-[11px] leading-snug text-ink-gray-5">{{ s.detail }}</div>
              </div>
            </div>
            <div class="mt-2 flex gap-2">
              <Button size="sm" variant="subtle" @click="runSuggestion(s)">{{ actionLabel(s.action) }}</Button>
              <Button size="sm" variant="ghost" :loading="creatingTask === i" @click="createTaskFromSuggestion(s, i)">
                <template #prefix><LucideListPlus class="h-3.5 w-3.5" /></template>
                {{ __('Make a task') }}
              </Button>
            </div>
          </div>
        </div>
        <div v-else class="py-6 text-center text-sm text-ink-gray-4">{{ __('Nothing urgent — pipeline looks clear.') }}</div>
      </div>

      <!-- Active campaigns -->
      <div class="rounded-lg border border-ink-gray-2 bg-surface-white p-4">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-ink-gray-8">{{ __('Campaigns') }}</h2>
          <span class="text-xs text-ink-gray-4">{{ campaigns.length }}</span>
        </div>
        <div v-if="campaignsRes.loading" class="py-6 text-center text-sm text-ink-gray-5">{{ __('Loading…') }}</div>
        <div v-else-if="campaigns.length" class="space-y-1.5">
          <div
            v-for="c in campaigns"
            :key="c.name"
            class="rounded-md border px-2.5 py-2"
            :class="[
              c.stale ? 'border-ink-amber-2 bg-surface-amber-2/30' : 'border-ink-gray-2',
              focusName === c.name ? 'ring-2 ring-ink-blue-4' : '',
            ]"
          >
            <div class="flex items-center gap-2">
              <span class="truncate text-xs font-medium text-ink-gray-8" :title="c.sequence_name">{{ c.sequence_name || c.name }}</span>
              <span v-if="c.tier" class="shrink-0 rounded bg-surface-gray-2 px-1.5 py-px text-[9px] text-ink-gray-6">{{ c.tier }}</span>
              <span v-if="c.stale" class="shrink-0 rounded bg-surface-amber-2 px-1.5 py-px text-[9px] font-medium text-ink-amber-3" :title="__('No activity in 14+ days')">{{ __('stale') }}</span>
              <span class="ml-auto shrink-0 text-[10px] text-ink-gray-4">{{ c.status }}</span>
            </div>
            <div class="mt-1 flex gap-3 text-[10px] text-ink-gray-5">
              <span>{{ c.enrolled }} {{ __('enrolled') }}</span>
              <span>{{ c.active_instances }} {{ __('active') }}</span>
              <span>{{ c.tasks }} {{ __('tasks') }}</span>
              <span class="ml-auto">{{ (c.last_activity || '').slice(0, 10) }}</span>
            </div>
          </div>
        </div>
        <div v-else class="py-6 text-center text-sm text-ink-gray-4">{{ __('No campaigns yet — launch one from the Studio.') }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { createResource, Button, toast } from 'frappe-ui'
import { useRouter } from 'vue-router'
import LucideSparkles from '~icons/lucide/sparkles'
import LucideRocket from '~icons/lucide/rocket'
import LucideListPlus from '~icons/lucide/list-plus'

const props = defineProps({
  brainOk: { type: Boolean, default: false },
  // Optional: name of an Outreach Sequence to highlight (from ?sequence= deep-link).
  focusName: { type: String, default: '' },
  // Optional: a segment tier to pre-select + auto-plan (from ?plan_tier= deep-link,
  // e.g. the Tasks-page "Plan campaign" suggestion action).
  focusTier: { type: String, default: '' },
})
const emit = defineEmits(['changed'])
const router = useRouter()

// ---- segments ----
const segments = ref({})
const segmentsRes = createResource({
  url: 'crm.api.nyx_campaigns.campaign_segments',
  auto: true,
  onSuccess(d) { segments.value = d || {} },
})
const tierOpts = computed(() => segments.value.tiers || [])

// ---- plan ----
const selectedTier = ref('')
const goal = ref('')
const plan = ref(null)
const planning = ref(false)
const editName = ref('')
const editSubject = ref('')
const editSteps = ref([])
const enrollLimit = ref(25)

const planRes = createResource({ url: 'crm.api.nyx_campaigns.plan_campaign' })
async function askPlan() {
  planning.value = true
  plan.value = null
  try {
    const d = await planRes.submit({
      segment_tier: selectedTier.value || undefined,
      goal: goal.value || undefined,
    })
    if (!d?.ok) {
      toast.error(d?.detail || __('Could not plan this segment.'))
      return
    }
    plan.value = d
    editName.value = d.plan.campaign_name
    editSubject.value = d.plan.subject
    editSteps.value = (d.plan.steps || []).map((s) => ({ ...s, body: s.body || '' }))
  } catch (err) {
    toast.error(__('Plan failed') + ': ' + (err?.messages?.[0] || err))
  } finally {
    planning.value = false
  }
}

// ---- launch ----
const launching = ref(false)
const launchRes = createResource({ url: 'crm.api.nyx_campaigns.launch_campaign' })
async function launch() {
  if (!editName.value || !editSteps.value.length) return
  launching.value = true
  try {
    const d = await launchRes.submit({
      campaign_name: editName.value,
      subject: editSubject.value,
      steps: JSON.stringify(editSteps.value),
      segment_tier: plan.value?.segment?.tier || undefined,
      enroll_limit: enrollLimit.value,
      create_kickoff_task: 1,
    })
    if (d?.ok) {
      toast.success(
        __('Launched “{0}” — {1} enrolled, kickoff task created.', [
          d.campaign_name,
          d.enrolled_count,
        ]),
      )
      plan.value = null
      campaignsRes.reload()
      suggest.reload()
      emit('changed')
    }
  } catch (err) {
    toast.error(__('Launch failed') + ': ' + (err?.messages?.[0] || err))
  } finally {
    launching.value = false
  }
}

// ---- suggestions ----
const mood = ref('')
const moods = [
  { value: '', label: __('Balanced') },
  { value: 'aggressive', label: __('Hunt') },
  { value: 'cleanup', label: __('Cleanup') },
]
const suggestions = ref([])
const suggest = createResource({
  url: 'crm.api.nyx_campaigns.suggest_tasks',
  auto: true,
  makeParams: () => ({ mood: mood.value || undefined }),
  onSuccess(d) { suggestions.value = d?.suggestions || [] },
})
function setMood(m) { mood.value = m; suggest.reload() }

function actionLabel(action) {
  return {
    plan_campaign: __('Plan it'),
    open_inbox: __('Open inbox'),
    open_campaign: __('Open'),
  }[action] || __('Go')
}
function runSuggestion(s) {
  if (s.action === 'plan_campaign') {
    selectedTier.value = s.action_params?.segment_tier || ''
    goal.value = ''
    askPlan()
  } else if (s.action === 'open_inbox') {
    router.push('/human-inbox').catch(() => { window.location.href = '/crm/human-inbox' })
  } else if (s.action === 'open_campaign' && s.action_params?.sequence) {
    router.push({ name: 'Nyx', query: { sequence: s.action_params.sequence } })
  }
}

const creatingTask = ref(-1)
const createTaskRes = createResource({ url: 'crm.api.tasks.create_task' })
async function createTaskFromSuggestion(s, i) {
  creatingTask.value = i
  try {
    await createTaskRes.submit({
      title: s.title,
      description: s.detail,
      priority: s.priority || 'Medium',
      status: 'Todo',
    })
    toast.success(__('Task created — see the Tasks page.'))
    emit('changed')
  } catch (err) {
    toast.error(__('Could not create task') + ': ' + (err?.messages?.[0] || err))
  } finally {
    creatingTask.value = -1
  }
}

// ---- campaigns list ----
const campaigns = ref([])
const campaignsRes = createResource({
  url: 'crm.api.nyx_campaigns.list_campaigns',
  auto: true,
  onSuccess(d) { campaigns.value = d?.campaigns || [] },
})

// React to ?sequence= focus changes.
watch(() => props.focusName, () => { if (props.focusName) campaignsRes.reload() })

// React to ?plan_tier= deep-link: pre-select the tier and auto-plan once.
function maybeAutoPlan() {
  const t = (props.focusTier || '').trim()
  if (!t) return
  selectedTier.value = t
  askPlan()
}
watch(() => props.focusTier, () => maybeAutoPlan())
onMounted(() => maybeAutoPlan())

defineExpose({ reload: () => { campaignsRes.reload(); suggest.reload() } })
</script>
