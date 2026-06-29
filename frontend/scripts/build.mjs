#!/usr/bin/env node
/**
 * Frappe Cloud image builds run `bench build --app crm` on Node 16 benches.
 * frappe-ui's vite stack (@iconify/utils >=3) requires Node 20+ to load vite.config.js.
 * We ship prebuilt assets in crm/public/frontend — on Node < 20, reuse them and skip vite.
 */
import { spawnSync } from 'node:child_process'
import { copyFileSync, existsSync, readdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const frontendRoot = join(__dirname, '..')
const assetsDir = join(frontendRoot, '../crm/public/frontend/assets')
const indexHtml = join(frontendRoot, '../crm/public/frontend/index.html')
const crmHtml = join(frontendRoot, '../crm/www/crm.html')
const viteBin = join(frontendRoot, 'node_modules', '.bin', 'vite')

function run(cmd, args) {
  const result = spawnSync(cmd, args, {
    stdio: 'inherit',
    cwd: frontendRoot,
  })
  if (result.status !== 0) {
    process.exit(result.status ?? 1)
  }
}

function copyHtmlEntry() {
  copyFileSync(indexHtml, crmHtml)
}

function hasPrebuiltAssets() {
  if (!existsSync(indexHtml) || !existsSync(assetsDir)) {
    return false
  }
  return readdirSync(assetsDir).some(
    (file) => file.startsWith('index-') && file.endsWith('.js'),
  )
}

const nodeMajor = parseInt(process.versions.node.split('.')[0], 10)
const forceBuild =
  process.env.FORCE_VITE_BUILD === '1' || process.env.CRM_FORCE_VITE_BUILD === '1'

if (!forceBuild && nodeMajor < 20 && hasPrebuiltAssets()) {
  console.log(
    `[crm build] Node ${process.versions.node}: using committed assets (vite needs Node 20+)`,
  )
  copyHtmlEntry()
} else {
  run(viteBin, ['build', '--base=/assets/crm/frontend/'])
  copyHtmlEntry()
}
