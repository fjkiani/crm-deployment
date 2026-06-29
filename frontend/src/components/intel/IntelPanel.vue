<template>
  <div class="flex flex-col">
    <!-- Header: title + optional source link -->
    <div class="mx-4 my-3 flex items-center justify-between sm:mx-10 sm:mb-4 sm:mt-6">
      <div class="flex h-8 items-center text-xl font-semibold text-ink-gray-8">{{ __(schema.title) }}</div>
      <a
        v-if="sourceHref"
        :href="sourceHref"
        target="_blank"
        class="text-xs font-medium text-ink-gray-5 underline hover:text-ink-gray-7"
      >
        {{ __(schema.sourceLink.label || 'Source') }}
      </a>
    </div>

    <!-- Optional score/tier band (GTM has it; AACR does not) -->
    <IntelScoreBand v-if="schema.score" :config="schema.score" :record="record" />

    <!-- Empty state: every declared field is empty -->
    <div
      v-if="recordEmpty"
      class="mx-4 my-6 flex flex-col items-center justify-center gap-2 text-ink-gray-4 sm:mx-10"
    >
      <FeatherIcon name="inbox" class="size-10 opacity-40" />
      <span class="text-sm">{{ emptyText || __('Nothing recorded yet') }}</span>
    </div>

    <!-- Grouped fields -->
    <template v-else>
      <div v-for="group in schema.groups" :key="group.label" class="mx-4 mt-2 sm:mx-10">
        <Section :label="__(group.label)" :opened="group.opened !== false">
          <div class="mt-2 grid gap-x-6 gap-y-3 sm:grid-cols-2">
            <div
              v-for="name in group.fields"
              :key="name"
              :class="{ 'sm:col-span-2': isWide(name) }"
            >
              <div class="text-xs font-medium uppercase text-ink-gray-4">{{ __(fieldLabel(name)) }}</div>
              <div class="mt-1">
                <component
                  :is="rendererFor(schema.fields[name].type)"
                  :value="record[name]"
                  :field-config="schema.fields[name]"
                />
              </div>
            </div>
          </div>
        </Section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { FeatherIcon } from 'frappe-ui'
import Section from '@/components/Section.vue'
import IntelScoreBand from './IntelScoreBand.vue'
import { rendererFor, isEmptyValue } from './registry'

const props = defineProps({
  schema: { type: Object, required: true },
  record: { type: Object, required: true },
  emptyText: { type: String, default: '' },
})

// Wide types span both grid columns for readability.
const WIDE_TYPES = ['paragraph', 'table_obj', 'object_of_lists']
function isWide(name) {
  const f = props.schema.fields[name]
  return f && (f.wide || WIDE_TYPES.includes(f.type))
}

function fieldLabel(name) {
  const f = props.schema.fields[name]
  return (f && f.label) || name
}

const sourceHref = computed(() => {
  const sl = props.schema.sourceLink
  return sl && typeof sl.href === 'function' ? sl.href(props.record) : null
})

// "Empty record" = every field declared in the schema is empty. The score band can
// still show independently (it reads score/tier/meta fields, not the grouped fields).
const recordEmpty = computed(() => {
  const fields = Object.keys(props.schema.fields || {})
  return fields.length > 0 && fields.every((name) => isEmptyValue(props.record[name]))
})
</script>
