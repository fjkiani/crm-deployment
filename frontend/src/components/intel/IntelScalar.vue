<template>
  <IntelEmpty v-if="isEmpty" :field-config="fieldConfig" />
  <Badge v-else-if="fieldConfig.badge" :theme="theme" :label="display" />
  <span v-else class="text-sm text-ink-gray-8">{{ display }}</span>
</template>

<script setup>
import { computed } from 'vue'
import { Badge } from 'frappe-ui'
import IntelEmpty from './IntelEmpty.vue'
import { isEmptyValue } from './registry'

const props = defineProps({
  value: { default: null },
  fieldConfig: { type: Object, default: () => ({}) },
})

const isEmpty = computed(() => isEmptyValue(props.value))

// Booleans render as Yes/No; everything else is shown as-is.
const display = computed(() => {
  const v = props.value
  if (typeof v === 'boolean') return v ? __('Yes') : __('No')
  return String(v)
})

// badgeTheme may be a function (value -> theme) or a plain {value: theme} map.
const theme = computed(() => {
  const bt = props.fieldConfig.badgeTheme
  if (!bt) return 'gray'
  if (typeof bt === 'function') return bt(props.value) || 'gray'
  return bt[props.value] || 'gray'
})
</script>
