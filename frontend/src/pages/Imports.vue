<template>
  <div class="p-4 h-full overflow-auto">
    <LayoutHeader>
      <template #left-header>
        <ViewBreadcrumbs routeName="Imports" />
      </template>
    </LayoutHeader>

    <div class="max-w-4xl space-y-4">
      <div class="text-lg font-medium">CSV Preview</div>
      <Textarea v-model="csvText" rows="8" placeholder="Paste CSV here or provide a URL below" />
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <Input v-model="fileUrl" placeholder="CSV URL (optional)" />
        <Input v-model="delimiter" placeholder=", (delimiter optional)" />
        <Button :loading="previewRes.loading" label="Preview" @click="onPreview" />
      </div>

      <div v-if="previewRes.data" class="rounded border p-3 bg-surface-white">
        <div class="text-base font-medium mb-2">Headers</div>
        <div class="text-sm mb-3">{{ previewRes.data.headers?.join(', ') }}</div>

        <div class="text-base font-medium mb-2">Sample</div>
        <div class="overflow-auto">
          <table class="min-w-full text-xs">
            <thead>
              <tr>
                <th v-for="(h, i) in previewRes.data.headers" :key="'h'+i" class="px-2 py-1 text-left border-b">{{ h }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, r) in previewRes.data.sample" :key="'r'+r">
                <td v-for="(cell, c) in row" :key="'c'+c" class="px-2 py-1 border-b">{{ cell }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="text-lg font-medium mt-6">Create Import Job</div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <Select :options="[{label:'CSV', value:'CSV'},{label:'Google Sheets', value:'GOOGLE_SHEETS'}]" v-model="sourceType" />
        <Input v-if="sourceType==='GOOGLE_SHEETS'" v-model="sheetId" placeholder="Google Sheet ID" />
        <Input v-if="sourceType==='GOOGLE_SHEETS'" v-model="sheetRange" placeholder="Range (e.g. Sheet1!A:Z)" />
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <Input v-model="mappingProfile" placeholder="Mapping Profile (optional)" />
        <Select :options="[{label:'Dry Run: Off', value:false},{label:'Dry Run: On', value:true}]" v-model="dryRun" />
        <Select :options="[{label:'Scheduled: Off', value:false},{label:'Scheduled: On', value:true}]" v-model="scheduled" />
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <Button variant="solid" :loading="importRes.loading" label="Create Job" @click="onImport" />
        <div v-if="importRes.data" class="text-sm">Job: {{ importRes.data.job_id }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import { Button, Textarea, Input, Select, createResource } from 'frappe-ui'
import { ref } from 'vue'

const csvText = ref('')
const fileUrl = ref('')
const delimiter = ref('')
const sourceType = ref('CSV')
const sheetId = ref('')
const sheetRange = ref('')
const mappingProfile = ref('')
const dryRun = ref(false)
const scheduled = ref(false)

const previewRes = createResource({
  url: 'crm.api.etl.preview',
  onError: (e) => console.error(e),
})

const importRes = createResource({
  url: 'crm.api.etl.import_rows',
  method: 'POST',
  onError: (e) => console.error(e),
})

function onPreview() {
  previewRes.submit({
    file_url: fileUrl.value || null,
    filedata: fileUrl.value ? null : csvText.value,
    delimiter: delimiter.value || null,
    max_rows: 50,
  })
}

function onImport() {
  const payload = {
    source_type: sourceType.value,
    file_url: sourceType.value === 'CSV' ? (fileUrl.value || null) : null,
    sheet_id: sourceType.value === 'GOOGLE_SHEETS' ? (sheetId.value || null) : null,
    sheet_range: sourceType.value === 'GOOGLE_SHEETS' ? (sheetRange.value || null) : null,
    dedupe: true,
    link_organization: true,
    mapping_profile: mappingProfile.value || null,
    dry_run: !!dryRun.value,
    scheduled: !!scheduled.value,
  }
  importRes.submit({ payload: JSON.stringify(payload) })
}
</script>


