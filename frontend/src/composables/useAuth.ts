import type { AuthError, Session } from '@supabase/supabase-js'
import { computed, shallowRef } from 'vue'

import { supabase } from '@/lib/supabase'

const INVALID_CREDENTIALS_CODE = 'invalid_credentials'
const INVALID_CREDENTIALS_MESSAGE = 'Correo o contraseña incorrectos.'
const SIGN_IN_FAILED_MESSAGE = 'No se pudo iniciar sesión. Inténtalo de nuevo en un momento.'

// Una sola sesión para toda la app: el guard, la cabecera y el cliente de la API leen la misma.
const session = shallowRef<Session | null>(null)
let loadingSession: Promise<Session | null> | null = null

function loadSession(): Promise<Session | null> {
  if (supabase === null) return Promise.resolve(null)
  const client = supabase
  loadingSession ??= (async () => {
    const { data } = await client.auth.getSession()
    session.value = data.session
    client.auth.onAuthStateChange((_event, next) => {
      session.value = next
    })
    return data.session
  })()
  return loadingSession
}

export async function hasSession(): Promise<boolean> {
  return (await loadSession()) !== null
}

function signInErrorMessage(error: AuthError): string {
  return error.code === INVALID_CREDENTIALS_CODE
    ? INVALID_CREDENTIALS_MESSAGE
    : SIGN_IN_FAILED_MESSAGE
}

// Devuelve el mensaje de error en español, o null si la sesión quedó iniciada.
async function signIn(email: string, password: string): Promise<string | null> {
  if (supabase === null) return SIGN_IN_FAILED_MESSAGE
  await loadSession()
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error !== null) return signInErrorMessage(error)
  session.value = data.session
  return null
}

async function signOut(): Promise<void> {
  if (supabase === null) return
  await supabase.auth.signOut()
  session.value = null
}

export function useAuth() {
  void loadSession()
  return {
    isConfigured: supabase !== null,
    email: computed(() => session.value?.user.email ?? null),
    isSignedIn: computed(() => session.value !== null),
    signIn,
    signOut,
  }
}
