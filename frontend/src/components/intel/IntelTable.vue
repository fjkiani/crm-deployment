<template>
  <IntelEmpty v-if="isEmpty" :field-config="fieldConfig" />
  <div v-else class="overflow-x-auto rounded-lg border border-surface-gray-3">
    <table class="w-full text-left text-sm">
      <thead>
        <tr class="border-b border-surface-gray-3 bg-surface-gray-1">
          <th
            v-for="col in columns"
            :key="col.key"
            class="px-3 py-1.5 text-xs font-medium uppercase text-ink-gray-5"
          >
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, i) in rows"
          :key="i"
          class="border-b border-surface-gray-2 last:border-0"
        >
          <td v-for="col in columns" :key="col.key" class="px-3 py-1.5 align-top text-ink-gray-8">
            {{ cell(row, col.key) }}
          </td>
        </tr>
      </tbody>
    </table>
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
const rows = computed(() => (Array.isArray(props.value) ? props.value.filter((r) => r && typeof r === 'object') : []))

function humanize(key) {
  return String(key)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

// Columns come from fieldConfig.cols (list of string keys or {key,label}); if absent,
// infer from the union of keys across all rows (stable first-seen order).
const columns = computed(() => {
  const cols = props.fieldConfig.cols
  if (cols && cols.length) {
    return cols.map((c) => (typeof c === 'string' ? { key: c, label: humanize(c) } : { key: c.key, label: c.label || humanize(c.key) }))
  }
  const seen = []
  for (const row of rows.value) for (const k of Object.keys(row)) if (!seen.includes(k)) seen.push(k)
  return seen.map((k) => ({ key: k, label: humanize(k) }))
})

function cell(row, key) {
  const v = row[key]
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'boolean') return v ? __('Yes') : __('No')
  if (Array.isArray(v)) return v.join(', ')
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
</script>
