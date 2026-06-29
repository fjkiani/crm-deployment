<template>
  <Dialog v-model="show" :options="{ size: 'xl' }">
    <template #body-title>
      <h3 class="text-2xl font-semibold leading-6 text-ink-gray-9">
        {{ __('Upload Leads CSV') }}
      </h3>
    </template>
    <template #body-content>
      <div class="flex flex-col gap-4">
        <div class="flex items-center gap-3">
          <input
            ref="fileEl"
            type="file"
            accept=".csv,text/csv"
            @change="onFileChange"
          />
          <Button :label="__('Preview')" @click="onPreview" :disabled="!fileData" />
          <Button
            variant="subtle"
            :label="__('Import')"
            @click="onImport"
            :disabled="!fileData"
          />
        </div>
        <div v-if="preview" class="border rounded p-3 bg-surface-gray-2 max-h-64 overflow-auto text-sm">
          <div class="mb-2"><b>{{ __('Headers') }}:</b> {{ (preview.headers||[]).join(', ') }}</div>
          <div>
            <b>{{ __('Sample') }}:</b>
            <pre class="whitespace-pre-wrap">{{ JSON.stringify(preview.sample||[], null, 2) }}</pre>
          </div>
        </div>
        <div v-if="job" class="border rounded p-3 bg-surface-gray-2 text-sm">
          <div class="mb-1"><b>{{ __('Job') }}:</b> {{ job.job_id }}</div>
          <pre class="whitespace-pre-wrap">{{ JSON.stringify(job, null, 2) }}</pre>
        </div>
        <ErrorMessage v-if="error" :message="error" />
      </div>
    </template>
    <template #actions>
      <div class="flex justify-end">
        <Button :label="__('Close')" variant="subtle" @click="show = false" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref } from 'vue'
import { call } from 'frappe-ui'

const show = defineModel()

const fileEl = ref(null)
const fileData = ref('')
const preview = ref(null)
const job = ref(null)
const error = ref('')
const profileName = 'Leads Quick Import'

function onFileChange(e){
  error.value = ''
  const f = e?.target?.files?.[0]
  if (!f) { fileData.value = ''; return }
  const r = new FileReader()
  r.onload = () => { fileData.value = r.result }
  r.onerror = () => { error.value = 'Failed to read file' }
  r.readAsText(f)
}

async function onPreview(){
  try{
    error.value = ''
    if(!fileData.value) throw new Error('Choose a CSV file')
    preview.value = await call('crm.api.etl.preview', { filedata: fileData.value, max_rows: 20 })
  }catch(e){ error.value = e.message || String(e) }
}

async function onImport(){
  try{
    error.value = ''
    if(!fileData.value) throw new Error('Choose a CSV file')
    await call('crm.api.etl.autogenerate_mapping', { profile_name: profileName, source_type: 'CSV', filedata: fileData.value })
    const res = await call('crm.api.etl.import_rows', { payload: JSON.stringify({ title: 'Leads Upload', source_type: 'CSV', filedata: fileData.value, mapping_profile: profileName, dedupe: true, sync: true }) })
    job.value = { job_id: res.job_id, status: 'Queued' }
    poll(res.job_id)
  }catch(e){ error.value = e.message || String(e) }
}

async function poll(jobId){
  try{
    const s = await call('crm.api.etl.job_status', { job_id: jobId })
    job.value = s
    if(s.status && (s.status.startsWith('Completed') || s.status==='Failed')) return
    setTimeout(()=>poll(jobId), 2000)
  }catch(e){ error.value = e.message || String(e) }
}
</script>


