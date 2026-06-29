<template>
  <IntelEmpty v-if="isEmpty" :field-config="fieldConfig" />
  <div v-else class="flex flex-wrap gap-1.5">
    <span
      v-for="(item, i) in items"
      :key="i"
      class="rounded-md bg-surface-gray-2 px-2 py-0.5 text-xs text-ink-gray-7"
    >
      {{ item }}
    </span>
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

// Defensive: this renderer is for list[str]. If an object ever drifts in, show a
// stable label (fieldConfig.objLabel or the first string value) instead of [object Object].
const items = computed(() => {
  const v = props.value
  if (!Array.isArray(v)) return []
  return v.map((item) => {
    if (item && typeof item === 'object') {
      const key = props.fieldConfig.objLabel
      if (key && item[key] != null) return String(item[key])
      const firstStr = Object.values(item).find((x) => typeof x === 'string')
      return firstStr != null ? String(firstStr) : JSON.stringify(item)
    }
    return String(item)
  })
})
</script>
