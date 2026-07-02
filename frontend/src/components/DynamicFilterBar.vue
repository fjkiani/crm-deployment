<template>
  <div class="flex flex-wrap items-center gap-2 border-b bg-surface-gray-1 px-4 py-2">
    <span class="text-xs font-medium uppercase text-ink-gray-5">{{ __('Intel filters') }}</span>

    <!-- presets -->
    <Button
      v-for="p in manifest?.presets || []"
      :key="p.label"
      variant="subtle"
      :label="p.label"
      class="!text-xs"
      @click="applyPreset(p)"
    />

    <div class="mx-1 h-4 w-px bg-surface-gray-3" />

    <!-- dynamic filters -->
    <template v-for="f in manifest?.filters || []" :key="f.key">
      <!-- boolean toggle -->
      <Button
        v-if="f.type === 'boolean'"
        :variant="isActive(f) ? 'solid' : 'outline'"
        :label="f.label"
        class="!text-xs"
        @click="toggleBoolean(f)"
      />
      <!-- select -->
      <FormControl
        v-else-if="f.type === 'select'"
        type="select"
        class="!text-xs"
        :placeholder="f.label"
        :options="selectOptions(f)"
        :modelValue="selected[f.fieldname] ?? ''"
        @update:modelValue="(v) => setSelect(f, v)"
      />
    </template>

    <Button
      v-if="hasActive"
      variant="ghost"
      :label="__('Clear')"
      class="!text-xs"
      @click="clearAll"
    />
    <span class="ml-auto text-xs text-ink-gray-5" v-if="totalCount != null">
      {{ totalCount }} {{ __('leads') }}
    </span>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { createResource, Button, FormControl } from 'frappe-ui'

const props = defineProps({
  doctype: { type: String, default: 'CRM Lead' },
  totalCount: { type: Number, default: null },
})
const emit = defineEmits(['update:facetFilters'])

const manifestResource = createResource({
  url: 'crm.api.intel_facets.get_filter_manifest',
  makeParams: () => ({ doctype: props.doctype }),
  auto: true,
})
const manifest = computed(() => manifestResource.data || null)

// active facet filters, keyed by fieldname -> value or [op, value]
const selected = reactive({})

const hasActive = computed(() => Object.keys(selected).length > 0)

function isActive(f) {
  return f.fieldname in selected
}
function toggleBoolean(f) {
  if (f.fieldname in selected) delete selected[f.fieldname]
  else selected[f.fieldname] = f.operator && f.operator !== '=' ? [f.operator, f.value] : f.value
  push()
}
function setSelect(f, v) {
  if (v === '' || v == null) delete selected[f.fieldname]
  else selected[f.fieldname] = v
  push()
}
function selectOptions(f) {
  const opts = f.options || []
  return [{ label: f.label, value: '' }, ...opts.map((o) => ({ label: o, value: o }))]
}
function applyPreset(p) {
  for (const k of Object.keys(selected)) delete selected[k]
  Object.assign(selected, p.facet_filters || {})
  push()
}
function clearAll() {
  for (const k of Object.keys(selected)) delete selected[k]
  push()
}
function push() {
  emit('update:facetFilters', { ...selected })
}

watch(manifest, () => {}, { immediate: true })
</script>
