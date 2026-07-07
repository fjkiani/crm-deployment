import { createRouter, createWebHistory } from 'vue-router'
import { userResource } from '@/stores/user'
import { sessionStore } from '@/stores/session'
import { viewsStore } from '@/stores/views'

const routes = [
  {
    path: '/',
    name: 'Home',
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: () => import('@/pages/MobileNotification.vue'),
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('@/pages/Dashboard.vue'),
  },
  {
    path: '/ai',
    name: 'AI Copilot',
    component: () => import('@/pages/AiCopilot.vue'),
  },
  {
    path: '/voice',
    name: 'Voice Dashboard',
    component: () => import('@/pages/VoiceDashboard.vue'),
  },
  {
    path: '/leadgen',
    name: 'Lead Generation',
    component: () => import('@/pages/LeadGenDashboard.vue'),
  },
  {
    path: '/competitive-intel',
    name: 'Competitive Intel',
    component: () => import('@/pages/CompetitiveIntel.vue'),
  },
  {
    alias: '/leads',
    path: '/leads/view/:viewType?',
    name: 'Leads',
    component: () => import('@/pages/Leads.vue'),
  },
  {
    path: '/leads/:leadId',
    name: 'Lead',
    component: () => import(`@/pages/${handleMobileView('Lead')}.vue`),
    props: true,
  },
  {
    alias: '/deals',
    path: '/deals/view/:viewType?',
    name: 'Deals',
    component: () => import('@/pages/Deals.vue'),
  },
  {
    path: '/deals/:dealId',
    name: 'Deal',
    component: () => import(`@/pages/${handleMobileView('Deal')}.vue`),
    props: true,
  },
  {
    alias: '/notes',
    path: '/notes/view/:viewType?',
    name: 'Notes',
    component: () => import('@/pages/Notes.vue'),
  },
  {
    alias: '/tasks',
    path: '/tasks/view/:viewType?',
    name: 'Tasks',
    component: () => import('@/pages/Tasks.vue'),
  },
  {
    alias: '/contacts',
    path: '/contacts/view/:viewType?',
    name: 'Contacts',
    component: () => import('@/pages/Contacts.vue'),
  },
  {
    path: '/contacts/:contactId',
    name: 'Contact',
    component: () => import(`@/pages/${handleMobileView('Contact')}.vue`),
    props: true,
  },
  {
    alias: '/organizations',
    path: '/organizations/view/:viewType?',
    name: 'Organizations',
    component: () => import('@/pages/Organizations.vue'),
  },
  {
    path: '/organizations/:organizationId',
    name: 'Organization',
    component: () => import(`@/pages/${handleMobileView('Organization')}.vue`),
    props: true,
  },
  {
    alias: '/call-logs',
    path: '/call-logs/view/:viewType?',
    name: 'Call Logs',
    component: () => import('@/pages/CallLogs.vue'),
  },
  {
    path: '/welcome',
    name: 'Welcome',
    component: () => import('@/pages/Welcome.vue'),
  },
  {
    path: '/human_inbox',
    name: 'Human Inbox',
    component: () => import('@/pages/HumanInbox.vue'),
  },
  {
    path: '/nyx',
    name: 'Nyx',
    component: () => import('@/pages/NyxCockpit.vue'),
  },
  {
    path: '/imports',
    name: 'Imports',
    component: () => import('@/pages/Imports.vue'),
  },
  {
    path: '/email-setup',
    name: 'Email Setup',
    component: () => import('@/pages/EmailSetup.vue'),
  },
  {
    path: '/nyx-dashboard',
    name: 'Nyx Dashboard',
    component: () => import('@/pages/NyxDashboard.vue'),
  },
  {
    path: '/sessions',
    name: 'AACR Sessions',
    component: () => import('@/pages/AacrSessions.vue'),
  },
  {
    path: '/sessions/:sessionSlug',
    name: 'AACR Session',
    component: () => import('@/pages/AacrSession.vue'),
    props: true,
  },
  {
    path: '/aacr-intel',
    name: 'AACR Intelligence',
    component: () => import('@/pages/AacrDashboard.vue'),
  },
  {
    path: '/aacr-intel/axis/:axis',
    name: 'AACR Axis',
    component: () => import('@/pages/AacrAxis.vue'),
    props: true,
  },
  {
    path: '/industry',
    name: 'Industry Dashboard',
    component: () => import('@/pages/IndustryDashboard.vue'),
  },
  {
    path: '/industry/:slug',
    name: 'Industry Engagement',
    component: () => import('@/pages/IndustryEngagement.vue'),
    props: true,
  },
  {
    path: '/lead-search',
    name: 'Lead Search',
    component: () => import('@/pages/LeadSearch.vue'),
  },
  {
    path: '/:invalidpath',
    name: 'Invalid Page',
    component: () => import('@/pages/InvalidPage.vue'),
  },
]

const handleMobileView = (componentName) => {
  return window.innerWidth < 768 ? `Mobile${componentName}` : componentName
}

let router = createRouter({
  history: createWebHistory('/crm'),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const { isLoggedIn } = sessionStore()

  isLoggedIn && (await userResource.promise)

  if (to.name === 'Home' && isLoggedIn) {
    const { views, getDefaultView } = viewsStore()
    await views.promise

    let defaultView = getDefaultView()
    if (!defaultView) {
      next({ name: 'Leads' })
      return
    }

    let { route_name, type, name, is_standard } = defaultView
    route_name = route_name || 'Leads'

    if (name && !is_standard) {
      next({ name: route_name, params: { viewType: type }, query: { view: name } })
    } else {
      next({ name: route_name, params: { viewType: type } })
    }
  } else if (!isLoggedIn) {
    window.location.href = '/login?redirect-to=/crm'
  } else if (to.matched.length === 0) {
    next({ name: 'Invalid Page' })
  } else if (['Deal', 'Lead', 'Contact', 'Organization'].includes(to.name)) {
    const paramKey = to.name === 'Deal' ? 'dealId' : to.name === 'Lead' ? 'leadId' : to.name === 'Contact' ? 'contactId' : 'organizationId'
    const raw = to.params[paramKey]
    const clean = typeof raw === 'string' ? raw.trim().replace(/\s*\(.*$/, '') : raw
    if (clean && clean !== raw) {
      next({ ...to, params: { ...to.params, [paramKey]: clean }, replace: true })
      return
    }
    if (!to.hash) {
      let storageKey = to.name === 'Deal' ? 'lastDealTab' : 'lastLeadTab'
      const activeTab = localStorage.getItem(storageKey) || 'activity'
      const hash = '#' + activeTab
      next({ ...to, hash })
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
