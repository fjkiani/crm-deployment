<template>
  <div class="flex flex-1 flex-col overflow-y-auto px-4 py-3 sm:px-10">
    <!-- Approach header -->
    <div class="mb-4 rounded-lg border border-ink-gray-2 bg-surface-white">
      <div class="flex items-center justify-between border-b border-ink-gray-2 px-4 py-2.5">
        <span class="text-sm font-semibold text-ink-gray-9">{{ __('Decision-maker approach') }}</span>
        <Button variant="subtle" :loading="loading" @click="load">
          <template #prefix><LucideRefreshCw class="h-3.5 w-3.5" /></template>
          {{ __('Refresh') }}
        </Button>
      </div>
      <div class="px-4 py-3">
        <p class="text-sm text-ink-gray-8">
          {{ __('Map the buying committee, then warm the highest-influence contact first.') }}
        </p>
        <div class="mt-3 flex gap-2">
          <Button size="sm" variant="solid" @click="showAdd = true">{{ __('Add decision maker') }}</Button>
          <Button size="sm" variant="outline" :loading="inferring" @click="infer">
            {{ __('Infer from intel') }}
          </Button>
        </div>
      </div>
    </div>

    <!-- Error state -->
    <div v-if="error" class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
      <Button class="ml-2" size="sm" variant="outline" @click="load">{{ __('Retry') }}</Button>
    </div>

    <!-- Infer review queue -->
    <div v-if="reviewQueue.length" class="mb-4 rounded-lg border border-amber-200 bg-amber-50">
      <div class="border-b border-amber-200 px-4 py-2 text-xs font-semibold text-amber-800">
        {{ __('Review inferred contacts') }} ({{ reviewQueue.length }})
      </div>
      <div v-for="(c, i) in reviewQueue" :key="i" class="flex items-center justify-between border-b border-amber-100 px-4 py-2 last:border-0">
        <div>
          <span class="text-sm font-medium text-ink-gray-9">{{ c.contact_name }}</span>
          <span class="ml-2 text-xs text-ink-gray-6">{{ c.title }} · {{ c.role }}</span>
        </div>
        <div class="flex gap-2">
          <Button size="sm" variant="solid" @click="approve(c, i)">{{ __('Approve') }}</Button>
          <Button size="sm" variant="subtle" @click="reviewQueue.splice(i, 1)">{{ __('Discard') }}</Button>
        </div>
      </div>
    </div>

    <!-- Hierarchy tree -->
    <div v-if="hierarchy.length" class="space-y-1">
      <DMNode v-for="node in hierarchy" :key="node.name" :node="node" :depth="0" />
    </div>
    <div v-else-if="!error" class="rounded-lg border border-dashed border-ink-gray-3 px-4 py-8 text-center">
      <p class="text-sm text-ink-gray-5">{{ __('No decision makers mapped yet.') }}</p>
      <Button class="mt-3" size="sm" variant="solid" @click="showAdd = true">{{ __('Add first contact') }}</Button>
    </div>

    <!-- Add modal -->
    <Dialog v-model="showAdd" :options="{ title: __('Add decision maker'), size: 'lg' }">
      <template #body-content>
        <div class="grid grid-cols-2 gap-3">
          <FormControl v-model="form.contact_name" :label="__('Name')" class="col-span-2" />
          <FormControl v-model="form.title" :label="__('Title')" />
          <FormControl v-model="form.role" :label="__('Role')" type="select"
            :options="['Economic Buyer','Champion','Influencer','Blocker','Gatekeeper','End User']" />
          <FormControl v-model="form.influence" :label="__('Influence (1-5)')" type="number" />
          <FormControl v-model="form.warmth" :label="__('Warmth')" type="select" :options="['cold','warm','hot']" />
          <FormControl v-model="form.email" :label="__('Email')" />
          <FormControl v-model="form.phone" :label="__('Phone')" />
          <FormControl v-model="form.reports_to" :label="__('Reports To (name)')" class="col-span-2" />
        </div>
      </template>
      <template #actions>
        <Button variant="solid" :loading="saving" @click="save">{{ __('Add') }}</Button>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Button, Dialog, FormControl, call, toast } from 'frappe-ui'
import DMNode from './DMNode.vue'

const props = defineProps({ leadId: { type: String, required: true } })
const loading = ref(false)
const error = ref('')
const inferring = ref(false)
const saving = ref(false)
const showAdd = ref(false)
const hierarchy = ref([])
const reviewQueue = ref([])
const form = ref({ contact_name: '', title: '', role: 'Influencer', influence: 3, warmth: 'cold', email: '', phone: '', reports_to: '' })

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await call('crm.api.decision_makers.get_hierarchy', { lead: props.leadId })
    hierarchy.value = res?.hierarchy || []
  } catch (e) {
    error.value = e?.messages?.[0] || e?.message || __('Failed to load decision makers')
    hierarchy.value = []
  } finally { loading.value = false }
}

async function save() {
  if (!form.value.contact_name) { toast.error(__('Name required')); return }
  saving.value = true
  try {
    await call('crm.api.decision_makers.add', { lead: props.leadId, ...form.value })
    toast.success(__('Added'))
    showAdd.value = false
    form.value = { contact_name: '', title: '', role: 'Influencer', influence: 3, warmth: 'cold', email: '', phone: '', reports_to: '' }
    load()
  } catch (e) { toast.error(e.messages?.[0] || __('Failed')) } finally { saving.value = false }
}

async function infer() {
  inferring.value = true
  try {
    const res = await call('crm.api.decision_makers.infer_from_intel', { lead: props.leadId })
    reviewQueue.value = res?.review_queue || []
    if (!reviewQueue.value.length) toast.info(__('No new contacts found in intel'))
  } catch (e) { toast.error(e.messages?.[0] || __('Infer failed')) } finally { inferring.value = false }
}

async function approve(c, i) {
  try {
    await call('crm.api.decision_makers.approve_inferred', {
      lead: props.leadId, contact_name: c.contact_name, title: c.title,
      role: c.role, influence: c.influence,
    })
    reviewQueue.value.splice(i, 1)
    toast.success(__('Approved'))
    load()
  } catch (e) { toast.error(e.messages?.[0] || __('Approve failed')) }
}
onMounted(load)
</script>
