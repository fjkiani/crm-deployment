<template>
  <div v-if="visible" class="mx-4 sm:mx-10">
    <div class="flex flex-wrap items-center gap-4 rounded-xl p-4" :class="bandClass">
      <div class="flex flex-col items-center justify-center rounded-xl bg-white/90 px-4 py-2 shadow-sm">
        <span class="text-3xl font-bold" :class="scoreTextClass">{{ score !== null ? score : '—' }}</span>
        <span class="text-xs font-medium uppercase text-ink-gray-5">
          {{ __('Score') }}{{ scaleMax !== null ? ' / ' + scaleMax : '' }}
        </span>
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-sm font-semibold text-ink-gray-9">{{ tierLabel }}</span>
        <div class="flex flex-wrap items-center gap-2 text-sm text-ink-gray-6">
          <span v-if="tier" class="rounded-full px-2 py-0.5 text-xs font-medium" :class="tierBadgeClass">
            {{ tier }}
          </span>
          <template v-for="(m, i) in metaItems" :key="i">
            <span :class="{ 'text-ink-gray-5': i > 0 }">
              <template v-if="i > 0">· </template>{{ m.label }}: <span class="font-semibold text-ink-gray-8">{{ m.prefix || '' }}{{ m.value }}</span>
            </span>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  config: { type: Object, required: true }, // schema.score descriptor
  record: { type: Object, required: true },
})

const score = computed(() => {
  const v = props.record[props.config.field]
  return v === null || v === undefined || v === '' ? null : Number(v)
})

const scaleMax = computed(() => (props.config.scale ? props.config.scale[1] : null))
const tier = computed(() => (props.config.tierField ? props.record[props.config.tierField] : null))

const tierLabel = computed(() => {
  const fn = props.config.tierLabel
  return fn ? fn(tier.value, score.value) : tier.value || __('Unscored')
})

const tierBadgeClass = computed(() => {
  const fn = props.config.tierBadgeTheme
  return fn ? fn(tier.value, score.value) : 'bg-gray-100 text-gray-600'
})

const bandClass = computed(() => {
  const fn = props.config.bandClass
  return fn ? fn(tier.value, score.value) : 'bg-surface-gray-1 border border-surface-gray-3'
})

const scoreTextClass = computed(() => {
  const fn = props.config.scoreTextClass
  return fn ? fn(tier.value, score.value) : 'text-ink-gray-8'
})

// meta: [{label, field, prefix?}] -> resolve field values off the record, drop empties.
const metaItems = computed(() => {
  const meta = props.config.meta || []
  const out = []
  for (const m of meta) {
    const v = props.record[m.field]
    if (v === null || v === undefined || v === '') continue
    out.push({ label: m.label, value: v, prefix: m.prefix })
  }
  return out
})

const visible = computed(() => score.value !== null || !!tier.value || metaItems.value.length > 0)
</script>
