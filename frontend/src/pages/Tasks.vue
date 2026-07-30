<template>
  <LayoutHeader>
    <template #left-header>
      <ViewBreadcrumbs v-model="viewControls" routeName="Tasks" />
    </template>
    <template #right-header>
      <CustomActions
        v-if="tasksListView?.customListActions"
        :actions="tasksListView.customListActions"
      />
      <Button
        variant="solid"
        :label="__('Create')"
        iconLeft="plus"
        @click="createTask"
      />
    </template>
  </LayoutHeader>

  <!-- Nyx suggestions strip: next-best actions from live pipeline state.
       Additive — sits above the stock CRM Task list/kanban and touches none of
       it. Recommendations WRITE NOTHING until the human clicks "Make a task". -->
  <div class="border-b border-ink-gray-2 bg-surface-gray-1 px-3 py-2 sm:px-5">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <button class="flex items-center gap-1.5 text-sm font-medium text-ink-gray-8" @click="nyxOpen = !nyxOpen">
        <LucideSparkles class="h-4 w-4 text-ink-blue-5" />
        {{ __('Nyx suggestions') }}
        <span v-if="suggestions.length" class="rounded-full bg-surface-blue-2 px-1.5 text-[10px] font-semibold text-ink-blue-6">{{ suggestions.length }}</span>
        <LucideChevronDown class="h-3.5 w-3.5 transition-transform" :class="nyxOpen ? 'rotate-180' : ''" />
      </button>
      <div v-if="nyxOpen" class="flex items-center gap-1.5">
        <span
          v-if="!nyxEnabled"
          class="rounded-full bg-surface-red-2 px-2 py-0.5 text-[10px] font-medium text-ink-red-7"
          :title="__('NYX execution is halted (kill switch on). You can still create tasks manually.')"
        >○ {{ __('NYX halted') }}</span>
        <button
          v-for="m in moods"
          :key="m.value"
          class="rounded-full px-2 py-0.5 text-[11px] font-medium"
          :class="mood === m.value ? 'bg-ink-gray-9 text-surface-white' : 'bg-surface-gray-3 text-ink-gray-7 hover:bg-surface-gray-4'"
          @click="setMood(m.value)"
        >{{ m.label }}</button>
        <Button variant="ghost" :loading="suggestRes.loading" @click="suggestRes.reload()">
          <template #prefix><LucideRefreshCw class="h-3.5 w-3.5" /></template>
        </Button>
      </div>
    </div>

    <div v-if="nyxOpen" class="mt-2">
      <div v-if="suggestRes.loading && !suggestions.length" class="py-2 text-xs text-ink-gray-5">{{ __('Nyx is reviewing your pipeline…') }}</div>
      <div v-else-if="!suggestions.length" class="py-2 text-xs text-ink-gray-4">{{ __('Nothing pressing right now — pipeline looks handled.') }}</div>
      <div v-else class="flex gap-2 overflow-x-auto pb-1">
        <div
          v-for="(s, i) in suggestions"
          :key="i"
          class="min-w-[260px] max-w-[320px] shrink-0 rounded-lg border border-ink-gray-2 bg-surface-white p-2.5"
        >
          <div class="flex items-start justify-between gap-2">
            <span class="rounded px-1.5 py-0.5 text-[10px] font-semibold" :class="prioClass(s.priority)">{{ s.priority }}</span>
            <span class="text-[10px] text-ink-gray-4">{{ kindLabel(s.kind) }}</span>
          </div>
          <div class="mt-1 text-xs font-medium text-ink-gray-9">{{ s.title }}</div>
          <div class="mt-0.5 line-clamp-2 text-[11px] text-ink-gray-5">{{ s.detail }}</div>
          <div class="mt-2 flex gap-1.5">
            <Button variant="solid" size="sm" :loading="makingIndex === i" @click="makeTask(s, i)">{{ __('Make a task') }}</Button>
            <Button variant="subtle" size="sm" @click="runSuggestion(s)">{{ actionVerb(s.action) }}</Button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <ViewControls
    ref="viewControls"
    v-model="tasks"
    v-model:loadMore="loadMore"
    v-model:resizeColumn="triggerResize"
    v-model:updatedPageCount="updatedPageCount"
    doctype="CRM Task"
    :options="{
      allowedViews: ['list', 'kanban'],
    }"
  />
  <KanbanView
    v-if="$route.params.viewType == 'kanban' && rows.length"
    v-model="tasks"
    :options="{
      onClick: (row) => showTask(row.name),
      onNewClick: (column) => createTask(column),
    }"
    @update="(data) => viewControls.updateKanbanSettings(data)"
    @loadMore="(columnName) => viewControls.loadMoreKanban(columnName)"
  >
    <template #title="{ titleField, itemName }">
      <div class="flex items-center gap-2">
        <div v-if="titleField === 'status'">
          <TaskStatusIcon :status="getRow(itemName, titleField).label" />
        </div>
        <div v-else-if="titleField === 'priority'">
          <TaskPriorityIcon :priority="getRow(itemName, titleField).label" />
        </div>
        <div v-else-if="titleField === 'assigned_to'">
          <Avatar
            v-if="getRow(itemName, titleField).full_name"
            class="flex items-center"
            :image="getRow(itemName, titleField).user_image"
            :label="getRow(itemName, titleField).full_name"
            size="sm"
          />
        </div>
        <div
          v-if="['modified', 'creation'].includes(titleField)"
          class="truncate text-base"
        >
          <Tooltip :text="getRow(itemName, titleField).label">
            <div>{{ getRow(itemName, titleField).timeAgo }}</div>
          </Tooltip>
        </div>
        <div
          v-else-if="getRow(itemName, titleField).label"
          class="truncate text-base"
        >
          {{ getRow(itemName, titleField).label }}
        </div>
        <div class="text-ink-gray-4" v-else>{{ __('No Title') }}</div>
      </div>
    </template>
    <template #fields="{ fieldName, itemName }">
      <div
        v-if="getRow(itemName, fieldName).label"
        class="truncate flex items-center gap-2"
      >
        <div v-if="fieldName === 'status'">
          <TaskStatusIcon
            class="size-3"
            :status="getRow(itemName, fieldName).label"
          />
        </div>
        <div v-else-if="fieldName === 'priority'">
          <TaskPriorityIcon :priority="getRow(itemName, fieldName).label" />
        </div>
        <div v-else-if="fieldName === 'assigned_to'">
          <Avatar
            v-if="getRow(itemName, fieldName).full_name"
            class="flex items-center"
            :image="getRow(itemName, fieldName).user_image"
            :label="getRow(itemName, fieldName).full_name"
            size="sm"
          />
        </div>
        <div
          v-if="['modified', 'creation'].includes(fieldName)"
          class="truncate text-base"
        >
          <Tooltip :text="getRow(itemName, fieldName).label">
            <div>{{ getRow(itemName, fieldName).timeAgo }}</div>
          </Tooltip>
        </div>
        <div
          v-else-if="fieldName == 'description'"
          class="truncate text-base max-h-44"
        >
          <TextEditor
            v-if="getRow(itemName, fieldName).label"
            :content="getRow(itemName, fieldName).label"
            :editable="false"
            editor-class="!prose-sm max-w-none focus:outline-none"
            class="flex-1 overflow-hidden"
          />
        </div>
        <div v-else class="truncate text-base">
          {{ getRow(itemName, fieldName).label }}
        </div>
      </div>
    </template>
    <template #actions="{ itemName }">
      <div class="flex gap-2 items-center justify-between">
        <div>
          <Button
            v-if="getRow(itemName, 'reference_docname').label"
            class="-ml-2"
            variant="ghost"
            size="sm"
            :label="refLabel(getRow(itemName, 'reference_doctype').label)"
            :iconRight="ArrowUpRightIcon"
            @click.stop="
              redirect(
                getRow(itemName, 'reference_doctype').label,
                getRow(itemName, 'reference_docname').label,
              )
            "
          />
        </div>
        <Dropdown
          class="flex items-center gap-2"
          :options="actions(itemName)"
          variant="ghost"
          @click.stop.prevent
        >
          <Button icon="more-horizontal" variant="ghost" />
        </Dropdown>
      </div>
    </template>
  </KanbanView>
  <TasksListView
    ref="tasksListView"
    v-else-if="tasks.data && rows.length"
    v-model="tasks.data.page_length_count"
    v-model:list="tasks"
    :rows="rows"
    :columns="tasks.data.columns"
    :options="{
      showTooltip: false,
      resizeColumn: true,
      rowCount: tasks.data.row_count,
      totalCount: tasks.data.total_count,
    }"
    @loadMore="() => loadMore++"
    @columnWidthUpdated="() => triggerResize++"
    @updatePageCount="(count) => (updatedPageCount = count)"
    @showTask="showTask"
    @applyFilter="(data) => viewControls.applyFilter(data)"
    @applyLikeFilter="(data) => viewControls.applyLikeFilter(data)"
    @likeDoc="(data) => viewControls.likeDoc(data)"
    @selectionsChanged="
      (selections) => viewControls.updateSelections(selections)
    "
  />
  <div v-else-if="tasks.data" class="flex h-full items-center justify-center">
    <div
      class="flex flex-col items-center gap-3 text-xl font-medium text-ink-gray-4"
    >
      <Email2Icon class="h-10 w-10" />
      <span>{{ __('No {0} Found', [__('Tasks')]) }}</span>
      <Button
        :label="__('Create')"
        iconLeft="plus"
        @click="showTaskModal = true"
      />
    </div>
  </div>
  <TaskModal
    v-if="showTaskModal"
    v-model="showTaskModal"
    v-model:reloadTasks="tasks"
    :task="task"
  />
</template>

<script setup>
import ViewBreadcrumbs from '@/components/ViewBreadcrumbs.vue'
import CustomActions from '@/components/CustomActions.vue'
import ArrowUpRightIcon from '@/components/Icons/ArrowUpRightIcon.vue'
import TaskStatusIcon from '@/components/Icons/TaskStatusIcon.vue'
import TaskPriorityIcon from '@/components/Icons/TaskPriorityIcon.vue'
import Email2Icon from '@/components/Icons/Email2Icon.vue'
import LayoutHeader from '@/components/LayoutHeader.vue'
import ViewControls from '@/components/ViewControls.vue'
import TasksListView from '@/components/ListViews/TasksListView.vue'
import KanbanView from '@/components/Kanban/KanbanView.vue'
import TaskModal from '@/components/Modals/TaskModal.vue'
import { getMeta } from '@/stores/meta'
import { usersStore } from '@/stores/users'
import { formatDate, timeAgo } from '@/utils'
import { Tooltip, Avatar, TextEditor, Dropdown, call, toast, createResource } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import LucideSparkles from '~icons/lucide/sparkles'
import LucideRefreshCw from '~icons/lucide/refresh-cw'
import LucideChevronDown from '~icons/lucide/chevron-down'

const { getFormattedPercent, getFormattedFloat, getFormattedCurrency } =
  getMeta('CRM Task')
const { getUser } = usersStore()

const router = useRouter()

// ---- Nyx suggestions strip -------------------------------------------------
const nyxOpen = ref(true)
const mood = ref('')
const moods = [
  { value: '', label: __('Balanced') },
  { value: 'aggressive', label: __('Hunt') },
  { value: 'cleanup', label: __('Cleanup') },
]
const suggestRes = createResource({
  url: 'crm.api.nyx_campaigns.suggest_tasks',
  auto: true,
  makeParams: () => ({ mood: mood.value || undefined, limit: 6 }),
})
const suggestions = computed(() => suggestRes.data?.suggestions || [])
function setMood(v) { mood.value = v; suggestRes.reload() }

// NYX execution (kill switch) state — surfaced so the suggestions strip reflects it.
const nyxStatus = createResource({ url: 'crm.api.nyx_agent.nyx_execution_status', auto: true })
const nyxEnabled = computed(() => nyxStatus.data?.enabled ?? true)

const makingIndex = ref(-1)
const createTaskRes = createResource({ url: 'crm.api.tasks.create_task' })
function makeTask(s, i) {
  // Turn a suggestion into a real CRM Task. If it references a campaign
  // (Outreach Sequence), link the task to it so it deep-links from the list.
  makingIndex.value = i
  const seq = s.action === 'open_campaign' ? s.action_params?.sequence : null
  createTaskRes.submit(
    {
      title: s.title,
      priority: s.priority || 'Medium',
      description: s.detail || '',
      reference_doctype: seq ? 'Outreach Sequence' : undefined,
      reference_docname: seq || undefined,
    },
    {
      onSuccess() {
        toast.success(__('Task created from Nyx suggestion.'))
        makingIndex.value = -1
        // Refresh the list so the new task appears. ViewControls binds its list
        // resource into the `tasks` model, so reloading it re-fetches the list.
        tasks.value?.reload?.()
      },
      onError() { makingIndex.value = -1; toast.error(__('Could not create the task.')) },
    },
  )
}
function runSuggestion(s) {
  // Secondary action: jump to the relevant surface instead of making a task.
  if (s.action === 'plan_campaign') {
    router.push({ name: 'Nyx', query: { plan_tier: s.action_params?.segment_tier || 'Tier 1' } })
  } else if (s.action === 'open_inbox') {
    router.push({ name: 'Human Inbox' })
  } else if (s.action === 'open_campaign') {
    router.push({ name: 'Nyx', query: { sequence: s.action_params?.sequence } })
  } else {
    router.push({ name: 'Nyx' })
  }
}
function actionVerb(a) {
  return {
    plan_campaign: __('Plan campaign'),
    open_inbox: __('Open inbox'),
    open_campaign: __('View campaign'),
  }[a] || __('Open Nyx')
}
function kindLabel(k) {
  return {
    outreach_hightier: __('Outreach'),
    approve_drafts: __('Drafts'),
    revive_campaign: __('Stalled'),
  }[k] || k
}
function prioClass(p) {
  if (p === 'High') return 'bg-surface-red-2 text-ink-red-4'
  if (p === 'Medium') return 'bg-surface-amber-2 text-ink-amber-3'
  return 'bg-surface-gray-2 text-ink-gray-6'
}

const tasksListView = ref(null)

// tasks data is loaded in the ViewControls component
const tasks = ref({})
const loadMore = ref(1)
const triggerResize = ref(1)
const updatedPageCount = ref(20)
const viewControls = ref(null)

function getRow(name, field) {
  function getValue(value) {
    if (value && typeof value === 'object') {
      return value
    }
    return { label: value }
  }
  return getValue(rows.value?.find((row) => row.name == name)[field])
}

const rows = computed(() => {
  if (!tasks.value?.data?.data) return []

  if (tasks.value.data.view_type === 'kanban') {
    return getKanbanRows(tasks.value.data.data, tasks.value.data.fields)
  }

  const parsed = parseRows(tasks.value?.data.data, tasks.value?.data.columns)
  openTaskFromURL(parsed)
  return parsed
})

function getKanbanRows(data, columns) {
  let _rows = []
  data.forEach((column) => {
    column.data?.forEach((row) => {
      _rows.push(row)
    })
  })
  return parseRows(_rows, columns)
}

function parseRows(rows, columns = []) {
  let view_type = tasks.value.data.view_type
  let key = view_type === 'kanban' ? 'fieldname' : 'key'
  let type = view_type === 'kanban' ? 'fieldtype' : 'type'

  return rows.map((task) => {
    let _rows = {}
    tasks.value?.data.rows.forEach((row) => {
      _rows[row] = task[row]

      let fieldType = columns?.find((col) => (col[key] || col.value) == row)?.[
        type
      ]

      if (
        fieldType &&
        ['Date', 'Datetime'].includes(fieldType) &&
        !['modified', 'creation', 'due_date'].includes(row)
      ) {
        _rows[row] = formatDate(task[row], '', true, fieldType == 'Datetime')
      }

      if (fieldType && fieldType == 'Currency') {
        _rows[row] = getFormattedCurrency(row, task)
      }

      if (fieldType && fieldType == 'Float') {
        _rows[row] = getFormattedFloat(row, task)
      }

      if (fieldType && fieldType == 'Percent') {
        _rows[row] = getFormattedPercent(row, task)
      }

      if (['modified', 'creation'].includes(row)) {
        _rows[row] = {
          label: formatDate(task[row]),
          timeAgo: __(timeAgo(task[row])),
        }
      } else if (row == 'assigned_to') {
        _rows[row] = {
          label: task.assigned_to && getUser(task.assigned_to).full_name,
          ...(task.assigned_to && getUser(task.assigned_to)),
        }
      }
    })
    return _rows
  })
}

const showTaskModal = ref(false)

const task = ref({
  name: '',
  title: '',
  description: '',
  assigned_to: '',
  due_date: '',
  status: 'Backlog',
  priority: 'Low',
  reference_doctype: 'CRM Lead',
  reference_docname: '',
})

function showTask(name) {
  let t = rows.value?.find((row) => row.name === name)
  task.value = {
    name: t.name,
    title: t.title,
    description: t.description,
    assigned_to: t.assigned_to?.email || '',
    due_date: t.due_date,
    status: t.status,
    priority: t.priority,
    reference_doctype: t.reference_doctype,
    reference_docname: t.reference_docname,
  }
  showTaskModal.value = true
}

function createTask(column) {
  task.value = {
    name: '',
    title: '',
    description: '',
    assigned_to: '',
    due_date: '',
    status: 'Backlog',
    priority: 'Low',
    reference_doctype: 'CRM Lead',
    reference_docname: '',
  }

  if (column.column?.name) {
    let column_field = tasks.value.params.column_field
    if (column_field) {
      task.value[column_field] = column.column.name
    }
  }

  showTaskModal.value = true
}

function actions(name) {
  return [
    {
      label: __('Delete'),
      icon: 'trash-2',
      onClick: () => {
        deletetask(name)
        tasks.value.reload()
      },
    },
  ]
}

async function deletetask(name) {
  await call('frappe.client.delete', {
    doctype: 'CRM Task',
    name,
  })
}

function refLabel(doctype) {
  if (doctype === 'CRM Deal') return __('Deal')
  if (doctype === 'Outreach Sequence') return __('Campaign')
  return __('Lead')
}
function redirect(doctype, docname) {
  if (!docname) return
  // Tasks can reference more than Leads/Deals (e.g. Outreach Sequence campaign
  // tasks are named OS-YYYY-NNNNN). Route by the ACTUAL reference doctype instead
  // of assuming everything non-Deal is a Lead — that produced "CRM Lead ... not
  // found" for campaign tasks.
  if (doctype === 'CRM Deal') {
    router.push({ name: 'Deal', params: { dealId: docname } })
  } else if (doctype === 'CRM Lead') {
    router.push({ name: 'Lead', params: { leadId: docname } })
  } else if (doctype === 'Outreach Sequence') {
    // Campaign tasks: open the Nyx hub focused on this sequence.
    router.push({ name: 'Nyx', query: { sequence: docname } })
  } else {
    toast.error(
      __('This task is linked to a {0} ({1}), which has no dedicated page.', [
        doctype || __('record'),
        docname,
      ]),
    )
  }
}

const openTaskFromURL = (parsed) => {
  const searchParams = new URLSearchParams(window.location.search)
  const taskName = searchParams.get('open')
  if (!taskName) return
  // Match against the FRESH parsed list (rows.value is stale mid-recompute) and
  // by exact string name — task.name is a string, so the old parseInt() never
  // strict-matched row.name and the link silently did nothing.
  const t = (parsed || []).find((r) => String(r.name) === String(taskName))
  if (!t) return
  searchParams.delete('open')
  window.history.replaceState(null, '', window.location.pathname)
  task.value = {
    name: t.name,
    title: t.title,
    description: t.description,
    assigned_to: t.assigned_to?.email || '',
    due_date: t.due_date,
    status: t.status,
    priority: t.priority,
    reference_doctype: t.reference_doctype,
    reference_docname: t.reference_docname,
  }
  showTaskModal.value = true
}
</script>
