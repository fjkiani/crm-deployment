<template>
  <div class="flex flex-1 flex-col overflow-y-auto px-4 py-3 sm:px-10">
    <!-- Generate panel -->
    <div class="mb-4 rounded-lg border border-ink-gray-2 bg-surface-white">
      <div class="flex items-center justify-between border-b border-ink-gray-2 px-4 py-2.5">
        <span class="text-sm font-semibold text-ink-gray-9">{{ __('Generate content') }}</span>
        <Button variant="subtle" :loading="loading" @click="load">
          <template #prefix><LucideRefreshCw class="h-3.5 w-3.5" /></template>
          {{ __('Refresh') }}
        </Button>
      </div>
      <div class="px-4 py-3">
        <p class="mb-2 text-sm text-ink-gray-8">
          {{ __('Generate stage-appropriate material from this lead\'s intel via NotebookLM, then attach it to a draft.') }}
        </p>
        <div class="mb-3 flex flex-wrap gap-1.5">
          <span v-for="(p, name) in providers" :key="name"
                class="rounded px-2 py-0.5 text-[11px]"
                :class="p.live ? 'bg-green-100 text-green-700' : 'bg-surface-gray-2 text-ink-gray-6'">
            {{ name }}: {{ p.live ? __('live') : (__('needs ') + (p.missing || []).join(', ')) }}
          </span>
        </div>

        <!-- Honest not-authenticated state: no provider is live -->
        <div v-if="!anyLive" class="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
          <p class="text-sm font-medium text-amber-800">{{ __('No content backend is authenticated.') }}</p>
          <p class="mt-1 text-xs text-amber-700">
            {{ __('Real NotebookLM artifacts require a live provider. Connect one, then refresh:') }}
          </p>
          <ul class="mt-1 list-disc pl-5 text-xs text-amber-700">
            <li>{{ __('Unofficial (literal NotebookLM): install the notebooklm CLI and run `notebooklm login` to create a Google session.') }}</li>
            <li>{{ __('Gemini: set GEMINI_API_KEY.') }}</li>
            <li>{{ __('Enterprise: set NOTEBOOKLM_OAUTH_TOKEN and NOTEBOOKLM_GCP_PROJECT.') }}</li>
          </ul>
          <p class="mt-1 text-xs text-amber-700">{{ __('Nothing is fabricated — generation stays disabled until a provider is live.') }}</p>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <FormControl v-model="gen.content_type" :label="__('Type')" type="select" :options="typeOptions" />
          <FormControl v-model="gen.provider" :label="__('Backend')" type="select"
            :options="['auto','unofficial','gemini','enterprise']" />
          <FormControl v-model="gen.funnel_stage" :label="__('Funnel stage')" type="select"
            :options="['first_touch','follow_up','deep_dive','proposal']" />
          <FormControl v-model="gen.point_of_discussion" :label="__('Point of discussion (optional)')" class="col-span-2" />
          <FormControl v-model="gen.crispro_value" :label="__('CrisPRO value (optional)')" class="col-span-2" />
        </div>
        <Button class="mt-3" size="sm" variant="solid" :loading="generating" :disabled="!anyLive" @click="generate">
          {{ anyLive ? __('Generate') : __('Generate (needs a live backend)') }}
        </Button>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
      <Button class="ml-2" size="sm" variant="outline" @click="load">{{ __('Retry') }}</Button>
    </div>

    <!-- Library -->
    <div class="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
      {{ __('Content library') }} ({{ files.length }})
    </div>
    <div v-if="files.length" class="space-y-2">
      <div v-for="f in files" :key="f.name"
           class="flex items-center justify-between rounded-lg border border-ink-gray-2 bg-surface-white px-4 py-3">
        <div>
          <span class="text-sm font-medium text-ink-gray-9">{{ f.file_name }}</span>
          <div class="text-xs text-ink-gray-5">
            {{ f.content_label || 'file' }} · {{ f.file_size }} bytes · {{ f.creation }}
          </div>
        </div>
        <div class="flex gap-2">
          <Button size="sm" variant="outline" @click="attach(f)">{{ __('Attach to draft') }}</Button>
          <Button size="sm" variant="subtle" @click="open(f)">{{ __('Open') }}</Button>
        </div>
      </div>
    </div>
    <div v-else class="rounded-lg border border-dashed border-ink-gray-3 px-4 py-8 text-center">
      <p class="text-sm text-ink-gray-5">
        {{ anyLive ? __('No content yet. Generate slides, audio, or video above.')
                   : __('No content yet. Authenticate a backend above to mint real material.') }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Button, FormControl, call, toast } from 'frappe-ui'

const props = defineProps({ leadId: { type: String, required: true } })
const loading = ref(false)
const generating = ref(false)
const error = ref('')
const files = ref([])
const providers = ref({})
const gen = ref({ content_type: 'slides', provider: 'auto', funnel_stage: 'first_touch', point_of_discussion: '', crispro_value: '' })

// Honest availability derived from real provider presence checks — never assumed.
const anyLive = computed(() => Object.values(providers.value || {}).some((p) => p && p.live))
const liveKinds = computed(() => {
  const s = new Set()
  for (const p of Object.values(providers.value || {})) {
    if (p && p.live) for (const k of p.kinds || []) s.add(k)
  }
  return [...s]
})
// Offer live kinds when a backend is up; otherwise show the full capability surface (disabled).
const typeOptions = computed(() => (liveKinds.value.length ? liveKinds.value : ['slides', 'audio', 'video']))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await call('crm.api.content_engine.list_content', { lead: props.leadId })
    files.value = res?.files || []
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || __('Failed to load content')
    files.value = []
  } finally {
    loading.value = false
  }
}

async function loadProviders() {
  try {
    const res = await call('crm.api.content_engine.content_providers')
    providers.value = res?.providers || {}
  } catch (e) {
    providers.value = {}
    error.value = e?.messages?.[0] || e?.message || __('Failed to read content providers')
  }
}

async function generate() {
  if (!anyLive.value) {
    toast.error(__('No content backend is authenticated. Connect a provider first.'))
    return
  }
  generating.value = true
  try {
    const res = await call('crm.api.content_engine.generate_content', {
      lead: props.leadId, ...gen.value,
    })
    toast.success(__('Generated ') + (res?.produced?.[0]?.type || gen.value.content_type))
    load()
  } catch (e) { toast.error(e.messages?.[0] || __('Generation failed')) } finally { generating.value = false }
}

async function attach(f) {
  try {
    await call('crm.api.content_engine.attach_to_email', { lead: props.leadId, file_name: f.name })
    toast.success(__('Attached to a draft'))
  } catch (e) { toast.error(e.messages?.[0] || __('Attach failed')) }
}

function open(f) { if (f.file_url) window.open(f.file_url, '_blank') }
onMounted(() => { load(); loadProviders() })
</script>
