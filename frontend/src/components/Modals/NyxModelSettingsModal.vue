<template>
  <Dialog v-model="show" :options="{ size: 'lg' }">
    <template #body-title>
      <div class="flex items-center gap-3">
        <h3 class="text-2xl font-semibold leading-6 text-ink-gray-9">
          {{ __('Nyx Model Settings') }}
        </h3>
      </div>
    </template>
    <template #body-content>
      <div class="flex flex-col gap-4">
        <p class="text-sm text-ink-gray-6">
          {{
            __(
              'Choose which LLM the outreach brain uses to draft emails, and paste an API key. Keys are stored encrypted on the server and are never shown here.',
            )
          }}
        </p>

        <!-- Loading -->
        <div v-if="loading" class="flex items-center gap-2 text-ink-gray-5">
          <div class="h-4 w-4 animate-spin rounded-full border-2 border-ink-gray-4 border-t-transparent"></div>
          <span class="text-sm">{{ __('Loading current settings...') }}</span>
        </div>

        <template v-else>
          <!-- Provider -->
          <FormControl
            type="select"
            v-model="form.llm_provider"
            :label="__('Provider')"
            :options="providerOptions"
          />

          <!-- Model (OpenRouter only) -->
          <div v-if="form.llm_provider === 'openrouter'" class="flex flex-col gap-1">
            <FormControl
              type="select"
              v-model="form.openrouter_model"
              :label="__('Model')"
              :options="modelOptions"
            />
            <span class="text-xs text-ink-gray-5">
              {{ __('Gemma 3 27B is the recommended, reliable default. Any OpenRouter model id also works.') }}
            </span>
          </div>

          <!-- Model (Gemini) -->
          <div v-else-if="form.llm_provider === 'gemini'" class="flex flex-col gap-1">
            <FormControl
              type="select"
              v-model="form.gemini_model"
              :label="__('Model')"
              :options="modelOptions"
            />
          </div>

          <!-- API key (write-only) -->
          <div class="flex flex-col gap-1">
            <FormControl
              type="password"
              v-model="form.api_key"
              :label="keyLabel"
              :placeholder="keyPlaceholder"
            />
            <span class="text-xs text-ink-gray-5">
              {{
                keyIsSet
                  ? __('A key is already saved. Leave blank to keep it, or paste a new one to replace it.')
                  : __('No key saved yet. Paste one to enable drafting.')
              }}
            </span>
          </div>

          <!-- Grok note -->
          <div class="rounded-lg border border-ink-gray-2 bg-surface-gray-1 p-3">
            <span class="text-xs text-ink-gray-6">
              {{ __('xAI Grok (Llama) is a planned follow-up and requires a backend provider seam — not selectable yet.') }}
            </span>
          </div>

          <ErrorMessage v-if="error" :message="__(error)" />
        </template>
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button :label="__('Cancel')" @click="show = false" />
        <Button
          variant="solid"
          :label="saving ? __('Saving...') : __('Save')"
          :loading="saving"
          :disabled="loading || saving"
          @click="save"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { Dialog, FormControl, Button, ErrorMessage, toast, createResource } from 'frappe-ui'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const show = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const loading = ref(false)
const saving = ref(false)
const error = ref('')

const catalog = ref({}) // provider_catalog from the backend
const keyIsSet = ref(false) // whether a key already exists for the chosen provider

const form = reactive({
  llm_provider: 'openrouter',
  openrouter_model: 'google/gemma-3-27b-it',
  gemini_model: 'gemini-1.5-flash',
  api_key: '',
})

// Track has-key booleans per provider so switching provider updates the hint.
const hasKeys = reactive({ openrouter: false, gemini: false })

const providerOptions = computed(() => {
  const cat = catalog.value || {}
  const opts = []
  for (const key of ['openrouter', 'gemini']) {
    if (cat[key]) opts.push({ value: key, label: cat[key].label || key })
    else opts.push({ value: key, label: key })
  }
  return opts
})

const modelOptions = computed(() => {
  const cat = catalog.value || {}
  const entry = cat[form.llm_provider]
  const models = (entry && entry.models) || []
  const opts = models.map((m) => ({ value: m.id, label: m.label || m.id }))
  // Ensure the currently-saved model is present even if not in the catalog.
  const current = form.llm_provider === 'gemini' ? form.gemini_model : form.openrouter_model
  if (current && !opts.some((o) => o.value === current)) {
    opts.unshift({ value: current, label: current })
  }
  return opts
})

const keyLabel = computed(() =>
  form.llm_provider === 'gemini' ? __('Google / Gemini API Key') : __('OpenRouter API Key'),
)
const keyPlaceholder = computed(() => {
  const hint = (catalog.value?.[form.llm_provider] || {}).key_hint || ''
  return keyIsSet.value ? __('•••••••• (saved — leave blank to keep)') : hint
})

// Update keyIsSet when the provider changes.
watch(
  () => form.llm_provider,
  (p) => {
    keyIsSet.value = !!hasKeys[p]
    form.api_key = '' // never carry a typed key across providers
  },
)

const getResource = createResource({
  url: 'crm.api.nyx_email_brain.get_brain_settings',
  onSuccess: (data) => {
    if (!data) return
    catalog.value = data.provider_catalog || {}
    hasKeys.openrouter = !!data.has_openrouter_key
    hasKeys.gemini = !!data.has_google_key
    // Prefer the explicit configured provider, else the resolved active one.
    form.llm_provider =
      data.configured_provider || (data.active_provider !== 'none' ? data.active_provider : 'openrouter')
    if (data.openrouter_model) form.openrouter_model = data.openrouter_model
    keyIsSet.value = !!hasKeys[form.llm_provider]
  },
  onError: (err) => {
    error.value = err?.messages?.[0] || err?.message || 'Could not load settings.'
  },
})

const setResource = createResource({
  url: 'crm.api.nyx_email_brain.set_brain_settings',
})

async function load() {
  loading.value = true
  error.value = ''
  form.api_key = ''
  try {
    await getResource.reload()
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  error.value = ''
  try {
    const params = {
      llm_provider: form.llm_provider,
    }
    if (form.llm_provider === 'openrouter') {
      params.openrouter_model = form.openrouter_model
    }
    // Only send the key when the user actually typed one (blank = keep existing).
    if (form.api_key && form.api_key.trim()) {
      if (form.llm_provider === 'gemini') params.google_api_key = form.api_key.trim()
      else params.openrouter_api_key = form.api_key.trim()
    }
    const res = (await setResource.submit(params)) || {}
    // Reflect the new state.
    hasKeys.openrouter = !!res.has_openrouter_key
    hasKeys.gemini = !!res.has_google_key
    keyIsSet.value = !!hasKeys[form.llm_provider]
    form.api_key = ''
    toast({ variant: 'success', title: __('Model settings saved') })
    emit('saved', res)
    show.value = false
  } catch (err) {
    error.value = err?.messages?.[0] || err?.message || String(err)
    toast({ variant: 'error', title: __('Could not save settings'), text: error.value })
  } finally {
    saving.value = false
  }
}

// Load fresh settings each time the modal opens.
watch(
  () => props.modelValue,
  (open) => {
    if (open) load()
  },
)
</script>
