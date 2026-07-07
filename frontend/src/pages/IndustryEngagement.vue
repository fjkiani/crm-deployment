<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <!-- Header -->
    <header class="border-b px-6 py-4">
      <button class="mb-2 text-xs text-ink-gray-5 hover:text-ink-gray-8" @click="goBack">
        <LucideChevronLeft class="inline h-3.5 w-3.5" /> {{ __('All engagements') }}
      </button>
      <div v-if="e" class="flex items-start justify-between gap-4">
        <div>
          <h1 class="text-xl font-semibold text-ink-gray-9">{{ fm.company }}</h1>
          <p class="mt-0.5 text-sm text-ink-gray-5">{{ fm.lead_drug }} · {{ fm.target }}</p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <button
            v-if="!detail.data?.seeded"
            class="rounded-lg bg-ink-gray-9 px-3 py-2 text-sm font-medium text-surface-white transition hover:bg-ink-gray-8 disabled:opacity-50"
            :disabled="seed.loading"
            @click="onSeed">
            <LucideZap class="mr-1 inline h-4 w-4" />
            {{ seed.loading ? __('Generating…') : __('Generate outreach plan') }}
          </button>
          <span v-else class="rounded-lg bg-surface-green-2 px-3 py-2 text-sm font-medium text-ink-green-7">
            <LucideCheck class="mr-1 inline h-4 w-4" />{{ __('Plan generated') }}
          </span>
        </div>
      </div>
    </header>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <div v-if="detail.loading" class="py-20 text-center text-ink-gray-5">{{ __('Loading engagement…') }}</div>

      <template v-else-if="e">
        <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <!-- LEFT: strategy + fit + governance -->
          <div class="space-y-6 lg:col-span-1">
            <!-- snapshot -->
            <section class="rounded-xl border border-surface-gray-3 bg-surface-white p-4">
              <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-6">{{ __('Snapshot') }}</h2>
              <dl class="space-y-1 text-sm">
                <div><dt class="inline text-ink-gray-5">{{ __('Trial') }}: </dt><dd class="inline text-ink-gray-8">{{ fm.trial }}</dd></div>
                <div><dt class="inline text-ink-gray-5">{{ __('Phase') }}: </dt><dd class="inline text-ink-gray-8">{{ fm.phase }}</dd></div>
                <div><dt class="inline text-ink-gray-5">{{ __('Posture') }}: </dt><dd class="inline text-ink-gray-8">{{ fm.claim_posture }}</dd></div>
                <div><dt class="inline text-ink-gray-5">{{ __('Priority rank') }}: </dt><dd class="inline text-ink-gray-8">{{ fm.outreach_priority_rank }}</dd></div>
              </dl>
              <div class="mt-2 flex flex-wrap gap-1">
                <span v-for="t in (fm.tags || [])" :key="t"
                      class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] text-ink-gray-7">{{ t }}</span>
              </div>
            </section>

            <!-- fit score table -->
            <section class="rounded-xl border border-surface-gray-3 bg-surface-white p-4">
              <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-6">
                {{ __('CrisPRO Fit') }} <span class="text-ink-gray-4">({{ fit.composite }}/5)</span>
              </h2>
              <table class="w-full text-xs">
                <tbody>
                  <tr v-for="(r, i) in (fit.score_table || [])" :key="i" class="border-t border-surface-gray-2 first:border-0">
                    <td class="py-1 pr-2 text-ink-gray-7">{{ r.dimension }}</td>
                    <td class="py-1 text-right font-medium text-ink-gray-9">{{ r.score }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-if="fit.sharpest_hook" class="mt-2 rounded bg-surface-blue-1 p-2 text-xs text-ink-gray-7">
                <span class="font-medium text-ink-blue-7">{{ __('Hook') }}:</span> {{ fit.sharpest_hook }}
              </p>
            </section>

            <!-- governance -->
            <section class="rounded-xl border border-surface-amber-2 bg-surface-amber-1 p-4">
              <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-amber-7">{{ __('Governance') }}</h2>
              <div v-if="(gov.not_safe_to_say || []).length" class="mb-2">
                <div class="text-[11px] font-medium text-ink-amber-7">{{ __('Not safe to say') }}:</div>
                <ul class="mt-1 space-y-0.5 text-xs text-ink-gray-7">
                  <li v-for="(n, i) in gov.not_safe_to_say.slice(0, 6)" :key="i" class="flex gap-1">
                    <LucideX class="mt-0.5 h-3 w-3 shrink-0 text-ink-red-5" /><span>{{ n.claim }}</span>
                  </li>
                </ul>
              </div>
              <div v-if="(gov.company_specific_constraints || []).length">
                <div class="text-[11px] font-medium text-ink-amber-7">{{ __('Constraints') }}:</div>
                <ul class="mt-1 space-y-1 text-xs text-ink-gray-7">
                  <li v-for="(c, i) in gov.company_specific_constraints" :key="i"
                      v-html="renderConstraint(c)"></li>
                </ul>
              </div>
            </section>
          </div>

          <!-- RIGHT: sequenced plan + tasks/drafts -->
          <div class="space-y-6 lg:col-span-2">
            <!-- contact -->
            <section class="rounded-xl border border-surface-gray-3 bg-surface-white p-4">
              <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-6">{{ __('Primary Contact') }}</h2>
              <div class="text-sm font-medium text-ink-gray-9">{{ contact.primary?.name }}</div>
              <div class="text-xs text-ink-gray-6">{{ contact.primary?.title }} · {{ contact.primary?.institution }}</div>
              <div class="mt-1 text-xs text-ink-gray-5">
                {{ __('Channel') }}: {{ contact.preferred_channel }} ·
                {{ __('Email verified') }}: {{ contact.primary?.public_email_verified || 'NO' }}
              </div>
            </section>

            <!-- SEQUENCED PLAN -->
            <section class="rounded-xl border border-surface-gray-3 bg-surface-white p-4">
              <div class="mb-3 flex items-center justify-between">
                <h2 class="text-xs font-semibold uppercase tracking-wide text-ink-gray-6">
                  {{ __('Sequenced Outreach Plan') }} <span class="text-ink-gray-4">({{ __('Option A') }})</span>
                </h2>
                <span v-if="detail.data?.sequence_name" class="text-[11px] text-ink-gray-5">
                  {{ detail.data.sequence_name }}
                </span>
              </div>

              <!-- timeline of steps -->
              <ol class="relative space-y-4 border-l border-surface-gray-3 pl-5">
                <li v-for="(s, i) in steps" :key="i" class="relative">
                  <span class="absolute -left-[26px] flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold"
                        :class="stepDotClass(s)">{{ s.step_number }}</span>
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-semibold text-ink-gray-9">{{ s.sender }}</span>
                    <span class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] text-ink-gray-6">
                      {{ s.delay_days === 0 ? __('Day 0') : '+' + s.delay_days + 'd' }}
                    </span>
                    <span class="text-[11px] text-ink-gray-5">{{ s.channel_note }}</span>
                  </div>
                  <blockquote class="mt-1 whitespace-pre-line rounded-lg bg-surface-gray-1 p-3 text-sm text-ink-gray-7">{{ s.body }}</blockquote>
                  <!-- linked task/draft -->
                  <div v-if="taskForStep(i)" class="mt-1 flex items-center gap-2 text-[11px] text-ink-gray-5">
                    <LucideListTodo class="h-3.5 w-3.5" />
                    {{ __('Task') }} #{{ taskForStep(i).name }} · {{ taskForStep(i).status }} ·
                    {{ __('due') }} {{ (taskForStep(i).due_date || '').slice(0, 10) }}
                    <span v-if="draftForTask(taskForStep(i).name)" class="text-ink-green-6">
                      · <LucideMail class="inline h-3 w-3" /> {{ __('draft in inbox') }}
                    </span>
                  </div>
                </li>
              </ol>
            </section>

            <!-- generated artifacts summary -->
            <section v-if="detail.data?.seeded" class="rounded-xl border border-surface-green-2 bg-surface-green-1 p-4">
              <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-green-7">{{ __('Pipeline artifacts') }}</h2>
              <div class="flex flex-wrap gap-3 text-sm text-ink-gray-7">
                <span><LucideListTodo class="mr-1 inline h-4 w-4" />{{ (detail.data.tasks || []).length }} {{ __('CRM tasks') }}</span>
                <span><LucideMail class="mr-1 inline h-4 w-4" />{{ (detail.data.drafts || []).length }} {{ __('inbox drafts') }}</span>
              </div>
            </section>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { createResource, toast } from 'frappe-ui'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const slug = computed(() => route.params.slug)

const detail = createResource({
  url: 'crm.api.industry.engagement_detail',
  makeParams: () => ({ slug: slug.value, option: 'A' }),
  auto: true,
})

const e = computed(() => detail.data?.engagement || null)
const fm = computed(() => e.value?.front_matter || {})
const fit = computed(() => e.value?.fit || {})
const gov = computed(() => e.value?.governance || {})
const contact = computed(() => e.value?.contacts || {})
const steps = computed(() => e.value?.message_options?.option_a?.steps || [])
const tasks = computed(() => detail.data?.tasks || [])
const drafts = computed(() => detail.data?.drafts || [])

const seed = createResource({
  url: 'crm.api.industry.seed_engagement_plan',
  onSuccess() {
    toast.success(__('Outreach plan generated'))
    detail.reload()
  },
  onError(err) {
    toast.error(__('Seeding failed') + ': ' + (err?.messages?.[0] || err))
  },
})
function onSeed() {
  seed.submit({ slug: slug.value, option: 'A' })
}

function taskForStep(i) {
  // tasks are ordered by due_date asc == step order
  return tasks.value[i] || null
}
function draftForTask(taskName) {
  return drafts.value.find((d) => String(d.reference_name) === String(taskName)) || null
}
function stepDotClass(s) {
  if (s.delay_days === 0) return 'bg-ink-blue-6 text-surface-white'
  return 'bg-ink-gray-7 text-surface-white'
}
function renderConstraint(c) {
  // bold the leading "**Label:**" pattern
  return (c || '').replace(/\*\*(.+?)\*\*/g, '<span class="font-medium text-ink-amber-7">$1</span>')
}
function goBack() {
  router.push({ name: 'Industry Dashboard' })
}
</script>
