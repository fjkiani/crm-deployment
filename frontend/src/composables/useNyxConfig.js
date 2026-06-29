export function useNyxConfig() {
    // Read EAIA URL from Frappe boot info (set by server-side hook or environment)
    const eaiaUrl = window.frappe?.boot?.eaia_url || 'http://127.0.0.1:8787'

    return {
        eaiaUrl
    }
}
