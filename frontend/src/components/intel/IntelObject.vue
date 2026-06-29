<template>
  <IntelEmpty v-if="isEmpty" :field-config="fieldConfig" />
  <div v-else class="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
    <template v-for="row in rows" :key="row.key">
      <div class="text-xs font-medium uppercase text-ink-gray-4">{{ row.label }}</div>
      <div class="text-ink-gray-8">
        <div v-if="row.isList" class="flex flex-wrap gap-1.5">
          <span
            v-for="(item, i) in row.value"
            :key="i"
            class="rounded-md bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-7"
          >
            {{ item }}
          </span>
        </div>
        <span v-else>{{ row.value }}</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import IntelEmpty from './IntelEmpty.vue'
import { isEmptyValue } from './registry'

const props = defineProps({
  value: { default: null },
  fieldConfig: { type: Object, default: () => ({}) },
})

const isEmpty = computed(() => isEmptyValue(props.value))

function humanize(key) {
  return String(key)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

// Render keys in fieldConfig.cols order when given (skipping absent keys), else all
// present keys. Each row carries its display label + value (lists become chips).
const rows = computed(() => {
  const obj = props.value
  if (!obj || typeof obj !== 'object') return []
  const cols = props.fieldConfig.cols
  const keys = cols && cols.length ? cols.map((c) => (typeof c === 'string' ? { key: c } : c)) : Object.keys(obj).map((k) => ({ key: k }))
  const out = []
  for (const c of keys) {
    let v = obj[c.key]
    if (v === null || v === undefined || v === '') continue
    if (typeof v === 'boolean') v = v ? __('Yes') : __('No')
    out.push({ key: c.key, label: c.label || humanize(c.key), value: v, isList: Array.isArray(v) })
  }
  return out
})
</script>
