<template>
  <IntelEmpty v-if="isEmpty" :field-config="fieldConfig" />
  <div v-else class="flex flex-col gap-2 text-sm">
    <div v-for="row in rows" :key="row.key" class="flex flex-col gap-1">
      <div class="text-xs font-medium uppercase text-ink-gray-4">{{ row.label }}</div>
      <div class="flex flex-wrap gap-1.5">
        <template v-for="(item, i) in row.value" :key="i">
          <a
            v-if="row.linkFor && row.linkFor(item)"
            :href="row.linkFor(item)"
            target="_blank"
            class="rounded-md bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-blue-600 underline hover:bg-surface-gray-3"
          >
            {{ item }}
          </a>
          <span v-else class="rounded-md bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-7">
            {{ item }}
          </span>
        </template>
      </div>
    </div>
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

// Object-of-lists is "empty" only when every sub-list is empty.
const isEmpty = computed(() => {
  const obj = props.value
  if (!obj || typeof obj !== 'object') return true
  return !Object.values(obj).some((v) => Array.isArray(v) && v.length > 0)
})

function humanize(key) {
  return String(key)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

// One row per non-empty list, in fieldConfig.order when given. linkFor(key,value)
// optionally turns a chip into a deep link (e.g. NCT -> ClinicalTrials.gov).
const rows = computed(() => {
  const obj = props.value
  if (!obj || typeof obj !== 'object') return []
  const order = props.fieldConfig.order && props.fieldConfig.order.length ? props.fieldConfig.order : Object.keys(obj)
  const lf = props.fieldConfig.linkFor
  const out = []
  for (const key of order) {
    const v = obj[key]
    if (!Array.isArray(v) || v.length === 0) continue
    out.push({
      key,
      label: humanize(key),
      value: v,
      linkFor: lf ? (item) => lf(key, item) : null,
    })
  }
  return out
})
</script>
