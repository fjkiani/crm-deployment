<template>
  <div class="p-4 max-w-2xl mx-auto">
    <h1 class="text-xl font-semibold mb-4">Email Setup</h1>
    <div class="rounded-md border p-4 bg-white">
      <div class="mb-4 text-sm text-gray-700">
        <p class="mb-2">Connect Gmail using an App Password:</p>
        <ol class="list-decimal list-inside space-y-1">
          <li>Enable 2-Step Verification on your Google Account.</li>
          <li>Create an App Password for "Mail" on your device.</li>
          <li>Paste the 16-character App Password below.</li>
        </ol>
      </div>
      <form @submit.prevent="onSubmit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium mb-1">Gmail address</label>
          <input
            v-model="form.email_id"
            type="email"
            required
            class="w-full rounded border px-3 py-2"
            placeholder="you@company.com"
            @change="syncAccountName"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">App Password</label>
          <input
            v-model="form.password"
            type="password"
            required
            class="w-full rounded border px-3 py-2"
            placeholder="xxxx xxxx xxxx xxxx"
          />
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Account Name</label>
          <input
            v-model="form.email_account_name"
            type="text"
            required
            class="w-full rounded border px-3 py-2"
            placeholder="Gmail - you@company.com"
          />
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
          <label class="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" v-model="form.enable_incoming" />
            <span>Enable incoming</span>
          </label>
          <label class="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" v-model="form.enable_outgoing" />
            <span>Enable outgoing</span>
          </label>
          <label class="inline-flex items-center gap-2 text-sm">
            <input type="checkbox" v-model="form.default_outgoing" />
            <span>Default outgoing</span>
          </label>
        </div>
        <div class="flex items-center gap-3">
          <button
            type="submit"
            class="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
            :disabled="submitting"
          >
            {{ submitting ? 'Connecting…' : 'Connect Gmail' }}
          </button>
          <span v-if="success" class="text-green-700 text-sm">Connected! You can now send/receive emails.</span>
          <span v-if="error" class="text-red-600 text-sm">{{ error }}</span>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { call } from 'frappe-ui'
import router from '@/router'

const submitting = ref(false)
const success = ref(false)
const error = ref('')

const form = reactive({
  service: 'GMail',
  email_id: '',
  email_account_name: '',
  enable_incoming: true,
  enable_outgoing: true,
  default_outgoing: true,
  password: '',
})

function syncAccountName() {
  if (!form.email_account_name && form.email_id) {
    form.email_account_name = `Gmail - ${form.email_id}`
  }
}

async function onSubmit() {
  error.value = ''
  success.value = false
  submitting.value = true
  try {
    // frappe method expects payload under `data`
    await call('crm.api.settings.create_email_account', {
      data: {
        service: form.service,
        email_id: form.email_id,
        email_account_name: form.email_account_name,
        enable_incoming: form.enable_incoming ? 1 : 0,
        enable_outgoing: form.enable_outgoing ? 1 : 0,
        default_outgoing: form.default_outgoing ? 1 : 0,
        password: form.password,
      },
    })
    success.value = true
    // Optional: redirect to inbox after a short delay
    setTimeout(() => router.push({ name: 'Human Inbox' }), 800)
  } catch (e) {
    error.value = (e && (e.message || e)) || 'Failed to connect. Check App Password and IMAP.'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
</style>

