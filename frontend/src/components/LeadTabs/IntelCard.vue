<template>
  <div v-if="text" class="rounded-lg border border-ink-gray-2 bg-surface-white px-4 py-3">
    <div class="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">{{ title }}</div>
    <p class="whitespace-pre-wrap text-sm leading-relaxed text-ink-gray-8">{{ text }}</p>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  text: { type: String, default: '' },
  wide: { type: Boolean, default: false },
})
</script>
