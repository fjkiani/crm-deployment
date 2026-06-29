<template>
  <IntelEmpty v-if="isEmpty" :field-config="fieldConfig" />
  <div v-else class="text-sm leading-relaxed text-ink-gray-8">
    <p class="whitespace-pre-wrap" :class="{ 'line-clamp-4': clamped }">{{ value }}</p>
    <button
      v-if="longText"
      class="mt-1 text-xs font-medium text-ink-gray-5 hover:text-ink-gray-7"
      @click="clamped = !clamped"
    >
      {{ clamped ? __('Show more') : __('Show less') }}
    </button>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import IntelEmpty from './IntelEmpty.vue'
import { isEmptyValue } from './registry'

const props = defineProps({
  value: { default: null },
  fieldConfig: { type: Object, default: () => ({}) },
})

const isEmpty = computed(() => isEmptyValue(props.value))
const longText = computed(() => typeof props.value === 'string' && props.value.length > 280)
const clamped = ref(true)
</script>
