<template>
  <div class="rounded-lg border border-ink-gray-2 bg-surface-white" :style="{ marginLeft: depth * 24 + 'px' }">
    <div class="flex items-center justify-between px-4 py-2.5">
      <div class="flex items-center gap-2">
        <span v-if="depth > 0" class="text-ink-gray-4">└</span>
        <div>
          <span class="text-sm font-medium text-ink-gray-9">{{ node.contact_name }}</span>
          <span class="ml-2 text-xs text-ink-gray-6">{{ node.title }}</span>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <span class="rounded px-1.5 py-0.5 text-[10px]" :class="warmthClass">{{ node.warmth }}</span>
        <span class="text-xs text-ink-gray-5">{{ node.role }} · {{ node.influence }}/5</span>
      </div>
    </div>
    <DMNode v-for="child in node.children || []" :key="child.name" :node="child" :depth="depth + 1" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ node: { type: Object, required: true }, depth: { type: Number, default: 0 } })
const warmthClass = computed(() => {
  const w = props.node.warmth
  if (w === 'hot') return 'bg-red-100 text-red-700'
  if (w === 'warm') return 'bg-yellow-100 text-yellow-700'
  return 'bg-blue-100 text-blue-700'
})
</script>
