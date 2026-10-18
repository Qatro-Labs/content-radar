import { createClient, type SupabaseClient } from '@supabase/supabase-js'

// Sin URL o sin clave anónima no se crea cliente: la app funciona igual, sin login.
function createSupabaseClient(): SupabaseClient | null {
  const url = import.meta.env.VITE_SUPABASE_URL
  const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY
  if (!url || !anonKey) return null
  return createClient(url, anonKey)
}

export const supabase = createSupabaseClient()

// Por defecto el login es opcional: la demo funciona sin cuenta.
export const AUTH_REQUIRED = import.meta.env.VITE_AUTH_REQUIRED === 'true'

// Supabase renueva el token caducado dentro de `getSession`: por eso se pide en cada petición en
// lugar de guardar el de la sesión cargada.
async function currentAccessToken(): Promise<string | null> {
  if (supabase === null) return null
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

// Contrato con el backend: `Authorization: Bearer <access_token>` solo con sesión; sin sesión, la
// petición sale como siempre.
export async function authorizationHeaders(): Promise<Record<string, string>> {
  const token = await currentAccessToken()
  return token === null ? {} : { Authorization: `Bearer ${token}` }
}
