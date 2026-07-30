<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <!-- Header -->
    <header class="border-b px-6 py-4">
      <button class="mb-2 text-xs text-ink-gray-5 hover:text-ink-gray-8" @click="goBack">
        <LucideChevronLeft class="inline h-3.5 w-3.5" /> {{ __('All engagements') }}
      </button>
      <div v-if="e" class="flex items-start justify-between gap-4">
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-semibold text-ink-gray-9">{{ fm.company }}</h1>
            <span v-if="fm.outreach_priority_rank"
                  class="rounded-full bg-surface-gray-3 px-2 py-0.5 text-[11px] font-medium text-ink-gray-7">
              {{ __('Priority') }} #{{ fm.outreach_priority_rank }}
            </span>
          </div>
          <p class="mt-0.5 text-sm text-ink-gray-5">{{ fm.lead_drug }} · {{ fm.target }}</p>
        </div>
        <div class="flex shrink-0 items-center gap-2">
          <!-- kill-switch state -->
          <span
            class="rounded-lg px-2 py-1 text-[11px] font-medium"
            :class="nyxEnabled ? 'bg-surface-green-2 text-ink-green-7' : 'bg-surface-red-2 text-ink-red-7'"
            :title="nyxEnabled ? __('NYX execution enabled') : __('NYX execution disabled (kill switch on)')">
            <LucideShieldCheck v-if="nyxEnabled" class="mr-1 inline h-3.5 w-3.5" />
            <LucideShieldAlert v-else class="mr-1 inline h-3.5 w-3.5" />
            {{ nyxEnabled ? __('NYX live') : __('NYX halted') }}
          </span>
          <!-- enrich -->
          <button
            class="rounded-lg border border-surface-gray-4 bg-surface-white px-3 py-2 text-sm font-medium text-ink-gray-8 transition hover:bg-surface-gray-2 disabled:opacity-50"
            :disabled="enrich.loading"
            @click="onEnrich(false)">
            <LucideRadar class="mr-1 inline h-4 w-4" :class="enrich.loading ? 'animate-spin' : ''" />
            {{ enrich.loading ? __('Enriching…') : __('Enrich live intel') }}
          </button>
          <!-- seed -->
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
        <div class="grid grid-cols-1 gap-6 xl:grid-cols-12">
          <!-- ============ LEFT: strategy + fit + governance ============ -->
          <div class="space-y-6 xl:col-span-4">
            <!-- snapshot narrative -->
            <section class="rounded-xl border border-surface-gray-3 bg-surface-white p-4">
              <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-6">{{ __('Snapshot') }}</h2>
              <div class="prose-snapshot space-y-1 text-sm text-ink-gray-8" v-html="snapshotHtml"></div>
              <div class="mt-3 flex flex-wrap gap-1">
                <span v-for="t in (fm.tags || [])" :key="t"
                      class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] text-ink-gray-7">{{ t }}</span>
              </div>
            </section>

            <!-- fit score table + live corroboration -->
            <section class="rounded-xl border border-surface-gray-3 bg-surface-white p-4">
              <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-6">
                {{ __('CrisPRO Fit') }} <span class="text-ink-gray-4">({{ fit.composite }}/5)</span>
              </h2>
              <table class="w-full text-xs">
                <tbody>
                  <tr v-for="(r, i) in (fit.score_table || [])" :key="i" class="border-t border-surface-gray-2 first:border-0">
                    <td class="py-1 pr-2 text-ink-gray-7">
                      {{ r.dimension }}
                      <LucideCircleCheck v-if="dimCorroborated(r.dimension)"
                        class="ml-1 inline h-3 w-3 text-ink-green-6"
                        :title="__('Corroborated by live intel')" />
                    </td>
                    <td class="py-1 text-right font-medium text-ink-gray-9">{{ r.score }}</td>
                  </tr>
                </tbody>
              </table>
              <p v-if="fit.sharpest_hook" class="mt-2 rounded bg-surface-blue-1 p-2 text-xs text-ink-gray-7">
                <span class="font-medium text-ink-blue-7">{{ __('Hook') }}:</span> {{ fit.sharpest_hook }}
              </p>
            </section>

            <!-- governance: safe_to_say WITH evidence tags -->
            <section class="rounded-xl border border-surface-gray-3 bg-surface-white p-4">
              <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-6">
                {{ __('Governance — what you CAN say') }}
              </h2>
              <ul class="space-y-2">
                <li v-for="(s, i) in (gov.safe_to_say || [])" :key="i"
                    class="rounded-lg border border-surface-green-2 bg-surface-green-1 p-2 text-xs">
                  <div class="flex items-start justify-between gap-2">
                    <span class="text-ink-gray-8">{{ s.claim }}</span>
                    <span class="shrink-0 rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase"
                          :class="evidenceClass(s.evidence_status)">{{ s.evidence_status }}</span>
                  </div>
                  <div v-if="s.source" class="mt-1 text-[10px] text-ink-gray-5">{{ __('Source') }}: {{ s.source }}</div>
                  <div v-if="s.notes" class="mt-0.5 text-[10px] italic text-ink-gray-5">{{ s.notes }}</div>
                </li>
              </ul>
            </section>

            <!-- governance: not_safe_to_say + constraints -->
            <section class="rounded-xl border border-surface-amber-2 bg-surface-amber-1 p-4">
              <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-amber-7">{{ __('Guardrails') }}</h2>
              <div v-if="(gov.not_safe_to_say || []).length" class="mb-2">
                <div class="text-[11px] font-medium text-ink-amber-7">{{ __('Do NOT say') }}:</div>
                <ul class="mt-1 space-y-0.5 text-xs text-ink-gray-7">
                  <li v-for="(n, i) in gov.not_safe_to_say" :key="i" class="flex gap-1">
                    <LucideX class="mt-0.5 h-3 w-3 shrink-0 text-ink-red-5" /><span>{{ n.claim || n }}</span>
                  </li>
                </ul>
              </div>
              <div v-if="(gov.company_specific_constraints || []).length">
                <div class="text-[11px] font-medium text-ink-amber-7">{{ __('Constraints') }}:</div>
                <ul class="mt-1 space-y-1 text-xs text-ink-gray-7">
                  <li v-for="(c, i) in gov.company_specific_constraints" :key="i" v-html="renderConstraint(c)"></li>
                </ul>
              </div>
            </section>
          </div>

          <!-- ============ CENTER: contacts + full plan (A/B) ============ -->
          <div class="space-y-6 xl:col-span-4">
            <!-- contacts: primary + backup -->
            <section class="rounded-xl border border-surface-gray-3 bg-surface-white p-4">
              <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-6">{{ __('Contacts') }}</h2>
              <div class="space-y-3">
                <div v-for="c in contactList" :key="c.role"
                     class="rounded-lg border border-surface-gray-2 p-2">
                  <div class="flex items-center justify-between">
                    <span class="text-sm font-medium text-ink-gray-9">{{ c.who.name }}</span>
                    <span class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] uppercase text-ink-gray-6">{{ c.role }}</span>
                  </div>
                  <div class="text-xs text-ink-gray-6">{{ c.who.title }} · {{ c.who.institution }}</div>
                  <div class="mt-1 flex items-center gap-2 text-[11px]">
                    <a v-if="c.who.linkedin" :href="normalizeUrl(c.who.linkedin)" target="_blank"
                       class="text-ink-blue-6 hover:underline"><LucideLinkedin class="inline h-3 w-3" /> LinkedIn</a>
                    <span :class="c.who.public_email_verified === 'YES' ? 'text-ink-green-6' : 'text-ink-gray-5'">
                      {{ __('Email verified') }}: {{ c.who.public_email_verified || 'NO' }}
                    </span>
                  </div>
                  <div v-if="c.who.rationale" class="mt-1 text-[11px] italic text-ink-gray-5">{{ c.who.rationale }}</div>
                </div>
              </div>
              <div class="mt-2 text-[11px] text-ink-gray-5">
                {{ __('Preferred channel') }}: {{ contact.preferred_channel }}
              </div>
            </section>

            <!-- full outreach plan: BOTH options -->
            <section class="rounded-xl border border-surface-gray-3 bg-surface-white p-4">
              <div class="mb-3 flex items-center justify-between">
                <h2 class="text-xs font-semibold uppercase tracking-wide text-ink-gray-6">{{ __('Outreach Plan') }}</h2>
                <div class="flex rounded-lg border border-surface-gray-3 p-0.5 text-xs">
                  <button v-for="opt in ['A', 'B']" :key="opt"
                          class="rounded px-2.5 py-1 font-medium transition"
                          :class="activeOption === opt ? 'bg-ink-gray-9 text-surface-white' : 'text-ink-gray-6 hover:text-ink-gray-9'"
                          @click="activeOption = opt">
                    {{ __('Option') }} {{ opt }}
                  </button>
                </div>
              </div>

              <!-- timeline of steps for the active option -->
              <ol class="relative space-y-4 border-l border-surface-gray-3 pl-5">
                <li v-for="(s, i) in activeSteps" :key="i" class="relative">
                  <span class="absolute -left-[26px] flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold"
                        :class="stepDotClass(s)">{{ s.step_number }}</span>
                  <div class="flex flex-wrap items-center gap-2">
                    <span class="text-sm font-semibold text-ink-gray-9">{{ s.sender }}</span>
                    <span class="rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] text-ink-gray-6">
                      {{ s.delay_days === 0 ? __('Day 0') : '+' + s.delay_days + 'd' }}
                    </span>
                    <span class="text-[11px] text-ink-gray-5">{{ s.channel_note }}</span>
                  </div>
                  <blockquote class="mt-1 whitespace-pre-line rounded-lg bg-surface-gray-1 p-3 text-sm text-ink-gray-7">{{ s.body }}</blockquote>
                  <div v-if="activeOption === 'A' && taskForStep(i)" class="mt-1 flex items-center gap-2 text-[11px] text-ink-gray-5">
                    <LucideListTodo class="h-3.5 w-3.5" />
                    <button type="button" class="text-ink-blue-6 hover:underline"
                            @click="openTask(taskForStep(i).name)">{{ __('Task') }} #{{ taskForStep(i).name }}</button>
                    · {{ taskForStep(i).status }} ·
                    {{ __('due') }} {{ (taskForStep(i).due_date || '').slice(0, 10) }}
                    <button v-if="draftForTask(taskForStep(i).name)" type="button"
                            class="text-ink-green-6 hover:underline"
                            @click="openDraft(draftForTask(taskForStep(i).name))">
                      · <LucideMail class="inline h-3 w-3" /> {{ __('draft in inbox') }}
                    </button>
                  </div>
                </li>
              </ol>

              <!-- which_option decision matrix -->
              <div v-if="(whichOption || []).length" class="mt-4 rounded-lg bg-surface-gray-1 p-3">
                <div class="mb-1 text-[11px] font-semibold uppercase text-ink-gray-6">{{ __('Which option to use') }}</div>
                <ul class="space-y-1.5 text-xs">
                  <li v-for="(w, i) in whichOption" :key="i" class="flex gap-2">
                    <LucideCornerDownRight class="mt-0.5 h-3 w-3 shrink-0 text-ink-gray-4" />
                    <span class="text-ink-gray-7"><span class="text-ink-gray-5">{{ w.scenario }}</span> → <span class="font-medium text-ink-gray-9">{{ w.recommended_option }}</span></span>
                  </li>
                </ul>
              </div>
            </section>

            <!-- pipeline artifacts -->
            <section v-if="detail.data?.seeded" class="rounded-xl border border-surface-green-2 bg-surface-green-1 p-4">
              <h2 class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-green-7">{{ __('Pipeline artifacts') }}</h2>
              <div class="flex flex-wrap gap-3 text-sm text-ink-gray-7">
                <span><LucideListTodo class="mr-1 inline h-4 w-4" />{{ (detail.data.tasks || []).length }} {{ __('CRM tasks') }}</span>
                <span><LucideMail class="mr-1 inline h-4 w-4" />{{ (detail.data.drafts || []).length }} {{ __('inbox drafts') }}</span>
              </div>
            </section>
          </div>

          <!-- ============ RIGHT: live intel + NYX agent ============ -->
          <div class="space-y-6 xl:col-span-4">
            <!-- LIVE INTEL -->
            <section class="rounded-xl border border-surface-gray-3 bg-surface-white p-4">
              <div class="mb-2 flex items-center justify-between">
                <h2 class="text-xs font-semibold uppercase tracking-wide text-ink-gray-6">{{ __('Live Intel') }}</h2>
                <span v-if="intelData" class="flex items-center gap-1 text-[10px]"
                      :class="intelFresh ? 'text-ink-green-6' : 'text-ink-gray-5'">
                  <LucideDatabase class="h-3 w-3" />
                  {{ intelCached ? __('cached') : __('fresh') }} · {{ (intelData.fetched_at || '').slice(0, 16) }}
                </span>
              </div>

              <div v-if="!intelData" class="rounded-lg bg-surface-gray-1 p-3 text-xs text-ink-gray-5">
                {{ __('No live intel yet. Click "Enrich live intel" to pull PubMed, ClinicalTrials.gov, and firmographic signals.') }}
              </div>

              <template v-else>
                <!-- status + cost -->
                <div class="mb-2 flex items-center gap-2 text-[11px]">
                  <span class="rounded px-1.5 py-0.5 font-medium uppercase"
                        :class="intelStatusClass(intelData.status)">{{ intelData.status }}</span>
                  <span class="text-ink-gray-5">{{ intelData.cost_note }}</span>
                </div>

                <!-- distilled signals -->
                <ul v-if="(intelData.signals || []).length" class="space-y-1.5">
                  <li v-for="(sig, i) in intelData.signals" :key="i"
                      class="rounded-lg border border-surface-gray-2 p-2 text-xs">
                    <span class="mr-1 rounded bg-surface-gray-2 px-1 py-0.5 text-[9px] uppercase text-ink-gray-6">{{ sig.kind }}</span>
                    <span class="text-ink-gray-8">{{ sig.text }}</span>
                    <span v-if="sig.source" class="ml-1 text-[10px] text-ink-gray-4">— {{ sig.source }}</span>
                  </li>
                </ul>
                <div v-else class="rounded-lg bg-surface-amber-1 p-2 text-[11px] text-ink-amber-7">
                  {{ __('No citable signals extracted (quarantined). Set provider keys server-side for full coverage.') }}
                </div>

                <!-- source links -->
                <div v-if="(intelData.sources || []).length" class="mt-2">
                  <div class="text-[10px] font-medium uppercase text-ink-gray-5">{{ __('Sources') }}</div>
                  <div class="mt-1 flex flex-wrap gap-1">
                    <a v-for="(u, i) in intelData.sources.slice(0, 10)" :key="i" :href="u" target="_blank"
                       class="rounded bg-surface-blue-1 px-1.5 py-0.5 text-[10px] text-ink-blue-7 hover:underline">
                      {{ shortUrl(u) }}
                    </a>
                  </div>
                </div>
              </template>
            </section>

            <!-- NYX AGENT -->
            <section class="rounded-xl border border-surface-gray-3 bg-surface-white p-4">
              <div class="mb-2 flex items-center justify-between">
                <h2 class="text-xs font-semibold uppercase tracking-wide text-ink-gray-6">
                  <LucideBot class="mr-1 inline h-3.5 w-3.5" />{{ __('NYX Agent') }}
                </h2>
                <button
                  class="rounded-lg border border-surface-gray-4 px-2 py-1 text-[11px] font-medium text-ink-gray-8 hover:bg-surface-gray-2 disabled:opacity-50"
                  :disabled="plan.loading"
                  @click="onPlan">
                  <LucideWorkflow class="mr-1 inline h-3.5 w-3.5" />
                  {{ plan.loading ? __('Planning…') : __('Plan workflow') }}
                </button>
              </div>

              <div v-if="!planData" class="rounded-lg bg-surface-gray-1 p-3 text-xs text-ink-gray-5">
                {{ __('NYX proposes an ordered, human-gated workflow. Nothing runs until you click a step.') }}
              </div>

              <template v-else>
                <div class="mb-2 text-[10px] text-ink-gray-5">
                  {{ __('method') }}: {{ planData.method }} · {{ planData.steps.length }} {{ __('steps') }}
                </div>
                <ol class="space-y-2">
                  <li v-for="(st, i) in planData.steps" :key="i"
                      class="rounded-lg border border-surface-gray-2 p-2">
                    <div class="flex items-start justify-between gap-2">
                      <div class="min-w-0">
                        <div class="text-xs font-medium text-ink-gray-9">
                          {{ i + 1 }}. {{ st.label }}
                          <span v-if="st.writes" class="ml-1 rounded bg-surface-amber-2 px-1 text-[9px] uppercase text-ink-amber-7">{{ __('writes') }}</span>
                          <span v-if="st.requires_confirm" class="ml-1 rounded bg-surface-red-2 px-1 text-[9px] uppercase text-ink-red-7">{{ __('irreversible') }}</span>
                        </div>
                        <div v-if="st.rationale" class="text-[11px] text-ink-gray-5">{{ st.rationale }}</div>
                      </div>
                    </div>
                    <!-- per-step actions -->
                    <div class="mt-1.5 flex flex-wrap items-center gap-1.5">
                      <button v-if="st.dry_run_supported"
                        class="rounded border border-surface-gray-4 px-2 py-0.5 text-[10px] text-ink-gray-7 hover:bg-surface-gray-2 disabled:opacity-40"
                        :disabled="stepBusy === i"
                        @click="runStep(st, i, { dry_run: 1 })">
                        <LucideEye class="mr-0.5 inline h-3 w-3" />{{ __('Dry run') }}
                      </button>
                      <button
                        class="rounded px-2 py-0.5 text-[10px] font-medium text-surface-white disabled:opacity-40"
                        :class="st.requires_confirm ? 'bg-ink-red-6 hover:bg-ink-red-7' : 'bg-ink-gray-9 hover:bg-ink-gray-8'"
                        :disabled="stepBusy === i || !nyxEnabled"
                        @click="runStep(st, i, { execute: 1 })">
                        <LucidePlay class="mr-0.5 inline h-3 w-3" />
                        {{ st.requires_confirm ? __('Confirm & run') : __('Run') }}
                      </button>
                      <span v-if="stepResult[i]" class="text-[10px]"
                            :class="stepResultClass(stepResult[i].status)">
                        {{ stepResultLabel(stepResult[i]) }}
                      </span>
                    </div>
                    <!-- dry-run preview -->
                    <div v-if="stepResult[i]?.status === 'dry_run'" class="mt-1 rounded bg-surface-gray-1 p-1.5 text-[10px] text-ink-gray-6">
                      {{ stepResult[i].would_do?.action }}
                    </div>
                  </li>
                </ol>
              </template>

              <!-- action trail -->
              <div class="mt-4 border-t border-surface-gray-2 pt-3">
                <div class="mb-1 flex items-center justify-between">
                  <div class="text-[10px] font-semibold uppercase text-ink-gray-5">{{ __('Action trail') }}</div>
                  <button class="text-[10px] text-ink-blue-6 hover:underline" @click="trail.reload()">{{ __('Refresh') }}</button>
                </div>
                <div v-if="!(trail.data?.actions || []).length" class="text-[11px] text-ink-gray-4">{{ __('No actions logged yet.') }}</div>
                <ul v-else class="space-y-1">
                  <li v-for="a in trail.data.actions" :key="a.name"
                      class="flex items-center justify-between gap-2 text-[11px]">
                    <span class="min-w-0 truncate text-ink-gray-7">
                      <span class="rounded px-1 py-0.5 text-[9px] uppercase" :class="stepResultClass(a.status)">{{ a.status }}</span>
                      {{ a.tool }}
                      <span class="text-ink-gray-4">· {{ (a.timestamp || '').slice(5, 16) }}</span>
                    </span>
                    <button v-if="a.status === 'executed' && a.reversible"
                      class="shrink-0 rounded border border-surface-gray-4 px-1.5 py-0.5 text-[10px] text-ink-gray-7 hover:bg-surface-gray-2"
                      @click="onUndo(a.name)">
                      <LucideUndo2 class="inline h-3 w-3" /> {{ __('Undo') }}
                    </button>
                  </li>
                </ul>
              </div>
            </section>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, reactive } from 'vue'
import { createResource, toast } from 'frappe-ui'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()
const slug = computed(() => route.params.slug)

/* -------------------- engagement detail (existing endpoint) -------------------- */
const detail = createResource({
  url: 'crm.api.industry.engagement_detail',
  // WP4.3 -- forward subject params (set by the Lead "Generate outreach plan"
  // navigation) so a GENERATED slug resolves deterministically instead of
  // relying on slug-suffix reversal.
  makeParams: () => ({
    slug: slug.value,
    option: 'A',
    subject_type: route.query.subject_type || undefined,
    subject_key: route.query.subject_key || undefined,
  }),
  auto: true,
})

const e = computed(() => detail.data?.engagement || null)
const fm = computed(() => e.value?.front_matter || {})
const fit = computed(() => e.value?.fit || {})
const gov = computed(() => e.value?.governance || {})
const contact = computed(() => e.value?.contacts || {})
const contactList = computed(() => {
  const out = []
  if (contact.value?.primary) out.push({ role: 'primary', who: contact.value.primary })
  if (contact.value?.backup) out.push({ role: 'backup', who: contact.value.backup })
  return out
})
const whichOption = computed(() => e.value?.message_options?.which_option || [])
const tasks = computed(() => detail.data?.tasks || [])
const drafts = computed(() => detail.data?.drafts || [])

/* option A/B toggle */
const activeOption = ref('A')
const activeSteps = computed(() => {
  const mo = e.value?.message_options || {}
  return (activeOption.value === 'A' ? mo.option_a : mo.option_b)?.steps || []
})

/* snapshot markdown -> minimal html (bold + line breaks) */
const snapshotHtml = computed(() => {
  const raw = e.value?.snapshot || ''
  return raw
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<span class="font-semibold text-ink-gray-9">$1</span>')
    .replace(/\n/g, '<br>')
})

/* -------------------- seed (existing) -------------------- */
const seed = createResource({
  url: 'crm.api.industry.seed_engagement_plan',
  onSuccess() { toast.success(__('Outreach plan generated')); detail.reload() },
  onError(err) { toast.error(__('Seeding failed') + ': ' + (err?.messages?.[0] || err)) },
})
// WP4.3 -- a GENERATED (non-curated) card cannot seed via a curated slug; it
// seeds through the generator, which needs the subject.
const seedGenerated = createResource({
  url: 'crm.api.plan_generator.generate_and_seed_plan',
  onSuccess() { toast.success(__('Outreach plan generated')); detail.reload() },
  onError(err) { toast.error(__('Seeding failed') + ': ' + (err?.messages?.[0] || err)) },
})
function onSeed() {
  const gen = detail.data?.engagement?._generated
  if (detail.data?.generated && gen?.subject_key) {
    seedGenerated.submit({
      subject_type: gen.subject_type || 'Lead',
      subject_key: gen.subject_key,
      option: 'A',
      use_enrich: 1,
    })
  } else {
    seed.submit({ slug: slug.value, option: 'A' })
  }
}

/* -------------------- LIVE INTEL (new) -------------------- */
const enrich = createResource({
  url: 'crm.api.enrichment_api.enrich_engagement',
  onSuccess() { toast.success(__('Live intel updated')) },
  onError(err) { toast.error(__('Enrichment failed') + ': ' + (err?.messages?.[0] || err)) },
})
// cache-first read on load
const cachedIntel = createResource({
  url: 'crm.api.enrichment_api.get_enrichment',
  makeParams: () => ({ subject_type: 'Company', subject_key: slug.value }),
  auto: true,
})
const intelData = computed(() => {
  const live = enrich.data
  if (live && live.subject_key) return live
  const c = cachedIntel.data
  return c && c.status && c.status !== 'empty' ? c : null
})
const intelCached = computed(() => (enrich.data ? !!enrich.data.cached : true))
const intelFresh = computed(() => intelData.value?.status === 'ok')
function onEnrich(force) {
  enrich.submit({ slug: slug.value, force: force ? 1 : 0 })
}
function dimCorroborated(dimensionLabel) {
  const dims = intelData.value?.fit?.dimensions || {}
  const hit = Object.values(dims).find((d) => (d.label || '').toLowerCase() === (dimensionLabel || '').toLowerCase())
  return hit?.live_evidence || false
}

/* -------------------- NYX AGENT (new) -------------------- */
const plan = createResource({
  url: 'crm.api.nyx_agent.plan_workflow',
  onError(err) { toast.error(__('Planning failed') + ': ' + (err?.messages?.[0] || err)) },
})
const planData = computed(() => plan.data || null)
function onPlan() {
  plan.submit({ subject_type: 'Company', subject_key: slug.value, goal: 'advance outreach to next best action' })
}

const nyxStatus = createResource({
  url: 'crm.api.nyx_agent.nyx_execution_status',
  auto: true,
})
const nyxEnabled = computed(() => {
  // prefer freshest signal from any endpoint that reports it
  if (typeof plan.data?.execution_enabled === 'boolean') return plan.data.execution_enabled
  if (typeof trail.data?.execution_enabled === 'boolean') return trail.data.execution_enabled
  return nyxStatus.data?.enabled ?? true
})

const stepBusy = ref(-1)
const stepResult = reactive({})
const execStep = createResource({ url: 'crm.api.nyx_agent.execute_step' })
async function runStep(st, i, { dry_run = 0, execute = 0 }) {
  stepBusy.value = i
  const confirmGate = execute && st.requires_confirm
  if (confirmGate && !window.confirm(__('This is an IRREVERSIBLE action ({0}). Proceed?').replace('{0}', st.label))) {
    stepBusy.value = -1
    return
  }
  try {
    const res = await execStep.submit({
      subject_type: 'Company', subject_key: slug.value,
      tool: st.tool, params: JSON.stringify(st.params || {}),
      dry_run: dry_run ? 1 : 0, confirm: confirmGate ? 1 : 0,
      rationale: st.rationale || '',
    })
    stepResult[i] = res
    if (res.status === 'executed') { toast.success(__('Step executed')); trail.reload(); detail.reload() }
    else if (res.status === 'dry_run') toast.info(__('Dry run complete'))
    else if (res.status === 'blocked') toast.error(res.reason)
  } catch (err) {
    toast.error(__('Step failed') + ': ' + (err?.messages?.[0] || err))
  } finally {
    stepBusy.value = -1
  }
}

const trail = createResource({
  url: 'crm.api.nyx_agent.action_trail',
  makeParams: () => ({ subject_type: 'Company', subject_key: slug.value, limit: 20 }),
  auto: true,
})
const undo = createResource({ url: 'crm.api.nyx_agent.undo_action' })
async function onUndo(name) {
  try {
    const res = await undo.submit({ action_log_name: name })
    if (res.status === 'undone') { toast.success(__('Action undone')); trail.reload(); detail.reload() }
    else toast.info(res.reason || res.status)
  } catch (err) {
    toast.error(__('Undo failed') + ': ' + (err?.messages?.[0] || err))
  }
}

/* -------------------- helpers -------------------- */
function taskForStep(i) { return tasks.value[i] || null }
function draftForTask(taskName) { return drafts.value.find((d) => String(d.reference_name) === String(taskName)) || null }
// WP4.4 — every reference on the plan is a real step forward, not plain text.
function openTask(name) {
  if (name) router.push({ name: 'Tasks', query: { open: String(name) } })
}
function openDraft(d) {
  if (d && d.name) router.push({ name: 'Human Inbox', query: { comm: d.name } })
}
function normalizeUrl(u) {
  if (!u) return u
  return /^https?:\/\//i.test(u) ? u : 'https://' + u.replace(/^\/+/, '')
}
function stepDotClass(s) { return s.delay_days === 0 ? 'bg-ink-blue-6 text-surface-white' : 'bg-ink-gray-7 text-surface-white' }
function renderConstraint(c) { return (c || '').replace(/\*\*(.+?)\*\*/g, '<span class="font-medium text-ink-amber-7">$1</span>') }
function evidenceClass(status) {
  const s = (status || '').toUpperCase()
  if (s.includes('VERIFIED')) return 'bg-surface-green-2 text-ink-green-7'
  if (s.includes('CONFERENCE') || s.includes('ABSTRACT')) return 'bg-surface-amber-2 text-ink-amber-7'
  return 'bg-surface-gray-3 text-ink-gray-7'
}
function intelStatusClass(s) {
  if (s === 'ok') return 'bg-surface-green-2 text-ink-green-7'
  if (s === 'partial') return 'bg-surface-amber-2 text-ink-amber-7'
  if (s === 'quarantine') return 'bg-surface-amber-2 text-ink-amber-7'
  return 'bg-surface-red-2 text-ink-red-7'
}
function stepResultClass(s) {
  if (s === 'executed' || s === 'undone') return 'bg-surface-green-2 text-ink-green-7'
  if (s === 'dry_run' || s === 'proposed') return 'bg-surface-blue-1 text-ink-blue-7'
  if (s === 'blocked' || s === 'error') return 'bg-surface-red-2 text-ink-red-7'
  return 'text-ink-gray-5'
}
function stepResultLabel(r) {
  if (r.status === 'executed') return __('executed')
  if (r.status === 'dry_run') return __('dry run OK')
  if (r.status === 'blocked') return __('blocked')
  if (r.status === 'error') return __('error')
  return r.status
}
function shortUrl(u) {
  try { return new URL(u).hostname.replace('www.', '') } catch { return (u || '').slice(0, 22) }
}
function goBack() { router.push({ name: 'Industry Dashboard' }) }
</script>

<style scoped>
.prose-snapshot :deep(br) { content: ''; }
</style>
