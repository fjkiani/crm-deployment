<template>
  <div class="flex flex-1 items-center justify-center text-sm text-ink-gray-4">
    Reader loading… (composer pane provided by feat/inbox-composer)
  </div>
</template>
<script>
export default { name: 'InboxReader', props: { communication: { type: Object, default: null } } }
</script>
