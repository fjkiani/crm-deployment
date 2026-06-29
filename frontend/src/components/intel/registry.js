// Renderer registry: maps a value-type token (from a field-schema descriptor) to
// the leaf component that knows how to render that shape.
//
// This is the seam that keeps the Intel component layer domain-agnostic: a schema
// descriptor declares `type` per field, and the container looks the renderer up here.
// No domain (AACR, GTM, ...) literals live in any of these components.
//
// Supported type tokens (verified against the AACR-2026 862-record corpus):
//   scalar          - string / number / boolean (single value)
//   enum            - string from a small closed set -> rendered as a Badge
//   paragraph       - long free text (clamp + expand)
//   list_scalar     - list[str|number] -> chips / bullets
//   table_obj       - list[obj] -> compact table built from `cols`
//   object          - single {k: v} map -> key/value grid
//   object_of_lists - single {k: list} map -> key + chips per key
//
// A missing/empty value for any type falls back to IntelEmpty.

import IntelScalar from './IntelScalar.vue'
import IntelParagraph from './IntelParagraph.vue'
import IntelList from './IntelList.vue'
import IntelTable from './IntelTable.vue'
import IntelObject from './IntelObject.vue'
import IntelObjectOfLists from './IntelObjectOfLists.vue'

export const RENDERERS = {
  scalar: IntelScalar,
  enum: IntelScalar, // IntelScalar renders a Badge when fieldConfig.badge is set
  paragraph: IntelParagraph,
  list_scalar: IntelList,
  table_obj: IntelTable,
  object: IntelObject,
  object_of_lists: IntelObjectOfLists,
}

export function rendererFor(type) {
  return RENDERERS[type] || IntelScalar
}

// Shared emptiness test used by the container to decide between a renderer and
// the uniform empty state. Treats null/undefined/''/[]/{} as empty.
export function isEmptyValue(v) {
  if (v === null || v === undefined || v === '') return true
  if (Array.isArray(v)) return v.length === 0
  if (typeof v === 'object') return Object.keys(v).length === 0
  return false
}
