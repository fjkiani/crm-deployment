<template>
  <div class="flex flex-1 flex-col overflow-hidden">
    <header class="flex items-center justify-between border-b px-5 py-3">
      <div class="flex items-center gap-2">
        <h1 class="text-lg font-semibold text-ink-gray-9">{{ __('AACR Sessions') }}</h1>
        <span v-if="sessionsResource.data" class="text-sm text-ink-gray-5">
          {{ sessionsResource.data.total }} {{ __('sessions') }}
        </span>
      </div>
      <FormControl
        type="text"
        :placeholder="__('Search sessions…')"
        v-model="search"
        @input="debouncedFetch"
      >
        <template #prefix><LucideSearch class="h-4 w-4 text-ink-gray-5" /></template>
      </FormControl>
    </header>

    <div class="flex-1 overflow-y-auto px-5 py-4">
      <div v-if="sessionsResource.loading" class="py-10 text-center text-ink-gray-5">
        {{ __('Loading sessions…') }}
      </div>
      <div v-else-if="!rows.length" class="py-10 text-center text-ink-gray-5">
        {{ __('No sessions found.') }}
      </div>
      <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <button
          v-for="s in rows"
          :key="s.session_slug"
          class="rounded-lg border border-surface-gray-3 bg-surface-white p-4 text-left transition hover:border-surface-gray-5 hover:shadow-sm"
          @click="openSession(s.session_slug)"
        >
          <div class="truncate text-sm font-medium text-ink-gray-9" :title="s.session_slug">
            {{ prettySlug(s.session_slug) }}
          </div>
          <div class="mt-2 flex items-center gap-3 text-xs text-ink-gray-6">
            <span class="inline-flex items-center gap-1">
              <LucidePresentation class="h-3.5 w-3.5" /> {{ s.n_talks }} {{ __('talks') }}
            </span>
            <span class="inline-flex items-center gap-1">
              <LucideUsers class="h-3.5 w-3.5" /> {{ s.n_leads }} {{ __('leads') }}
            </span>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { createResource, FormControl } from 'frappe-ui'
import { useRouter } from 'vue-router'

const router = useRouter()
const search = ref('')

const sessionsResource = createResource({
  url: 'crm.api.session_nav.list_sessions',
  makeParams: () => ({ search: search.value || null }),
  auto: true,
})

const rows = computed(() => sessionsResource.data?.sessions || [])

let t = null
function debouncedFetch() {
  clearTimeout(t)
  t = setTimeout(() => sessionsResource.fetch(), 250)
}

function prettySlug(slug) {
  if (!slug) return '(unknown)'
  return slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function openSession(slug) {
  router.push({ name: 'AACR Session', params: { sessionSlug: slug } })
}
</script>
