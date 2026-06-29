<template>
  <span class="text-sm italic text-ink-gray-4">{{ fieldConfig?.emptyText || __('Not recorded') }}</span>
</template>

<script setup>
defineProps({
  fieldConfig: { type: Object, default: () => ({}) },
})
</script>
