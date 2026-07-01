import './index.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createDialog } from './utils/dialogs'
import { initSocket } from './socket'
import router from './router'
import translationPlugin from './translation'
import { posthogPlugin } from './telemetry'
import App from './App.vue'

import {
  FrappeUI,
  Button,
  Input,
  TextInput,
  FormControl,
  ErrorMessage,
  Dialog,
  Alert,
  Badge,
  setConfig,
  frappeRequest,
  FeatherIcon,
} from 'frappe-ui'

let globalComponents = {
  Button,
  TextInput,
  Input,
  FormControl,
  ErrorMessage,
  Dialog,
  Alert,
  Badge,
  FeatherIcon,
}

// create a pinia instance
let pinia = createPinia()

let app = createApp(App)

setConfig('resourceFetcher', frappeRequest)
app.use(FrappeUI)
app.use(pinia)
app.use(router)
app.use(translationPlugin)
app.use(posthogPlugin)
for (let key in globalComponents) {
  app.component(key, globalComponents[key])
}

app.config.globalProperties.$dialog = createDialog

function applyBoot(values) {
  if (!values || typeof values !== 'object') return
  for (let key in values) {
    window[key] = values[key]
  }
}

function needsSpaBoot() {
  return !window.csrf_token || window.csrf_token === '{{ csrf_token }}'
}

async function ensureSpaBoot() {
  if (!needsSpaBoot()) return
  try {
    applyBoot(
      await frappeRequest({
        url: 'crm.www.crm.get_spa_boot',
        method: 'GET',
      }),
    )
  } catch (error) {
    console.warn('[crm] SPA boot fetch failed:', error)
  }
}

async function startApp() {
  await ensureSpaBoot()
  const socket = initSocket()
  app.config.globalProperties.$socket = socket
  app.mount('#app')
}

if (import.meta.env.DEV) {
  frappeRequest({ url: '/api/method/crm.www.crm.get_context_for_dev' }).then(
    (values) => {
      applyBoot(values)
      startApp()
    },
  )
} else {
  startApp()
}

if (import.meta.env.DEV) {
  window.$dialog = createDialog
}
