import { createSignal } from "solid-js"
import { Plugin } from "@opencode/plugin/tui"
import { execFileSync } from "node:child_process"
import { readFileSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

// Cuotas de las APIs gratis en la barra lateral.
//
//   OpenRouter  remanente real de OpenRouter (lo dice su API /key)
//   OpenCode    mensajes gratis de OpenCode (Zen) usados hoy (el tope no es público)
//   Warp        mensajes del puente Unlimited (Warp) usados hoy (tampoco publica tope)
//   Kilo        mensajes de Kilo Code (kilofree) usados hoy (tampoco publica tope)
//
// OpenCode, Warp y Kilo no exponen "cuántos quedan": el servidor solo responde 429
// FreeUsageLimitError. Por eso se muestra el consumo de hoy y, cuando llega
// el límite, la hora a la que se reinicia.

const CONFIG_DIR = process.env.XDG_CONFIG_HOME
  ? join(process.env.XDG_CONFIG_HOME, "opencode")
  : join(homedir(), ".config", "opencode")
const DATA_DIR = process.env.XDG_DATA_HOME
  ? join(process.env.XDG_DATA_HOME, "opencode")
  : join(homedir(), ".local", "share", "opencode")
const DB_PATH = join(DATA_DIR, "opencode.db")
const SERVICE_FILE = join(CONFIG_DIR, "service.json")
const UNLIMITED_FILE = join(CONFIG_DIR, "unlimited.json")

// El reloj se repinta cada segundo; la BD y la red van por su cuenta para que
// ninguna petición lenta congele la cuenta atrás.
const TICK_MS = 1_000
const DB_EVERY_MS = 3_000
const OPENROUTER_EVERY_MS = 5 * 60_000
const OPENROUTER_TIMEOUT_MS = 8_000
const DAY_MS = 24 * 60 * 60 * 1000

type OrQuota = {
  remaining: number
  limit: number
  used: number
  credits?: number
  error?: string
}

type Bucket = {
  used: number
  resetAt?: number
}

type Quota = {
  at: number
  openrouter?: OrQuota
  zen: Bucket
  warp: Bucket
  kilo: Bucket
  warpNote?: string
}

let connection: any = undefined

// Conexión única de solo lectura, reutilizada en cada consulta.
async function sqlite(): Promise<any> {
  if (connection !== undefined) return connection
  try {
    const mod: any = await import("bun:sqlite")
    const Database = mod.Database
    connection = Database ? new Database(DB_PATH, { readonly: true }) : null
    // El TUI escribe en la misma BD: esperar el lock en vez de devolver vacío.
    if (connection) connection.run("pragma busy_timeout = 2000")
  } catch {
    connection = null
  }
  return connection
}

// Devuelve filas como objetos. Usa bun:sqlite y cae al CLI sqlite3.
// Los errores suben: quien llama conserva el último valor bueno.
async function rows(sql: string): Promise<any[]> {
  const db = await sqlite()
  if (db) {
    try {
      return db.query(sql).all()
    } catch {
      // conexión muerta (BD reemplazada, esquema cambiado): se reabre luego
      try {
        db.close()
      } catch {}
      connection = undefined
    }
  }
  const out = execFileSync("sqlite3", ["-json", DB_PATH, sql], {
    encoding: "utf8",
    timeout: 5_000,
    maxBuffer: 8 * 1024 * 1024,
  }).trim()
  return out ? JSON.parse(out) : []
}

function readJson(file: string): any {
  try {
    return JSON.parse(readFileSync(file, "utf8"))
  } catch {
    return null
  }
}

function openRouterKey(): string | undefined {
  if (process.env.OPENROUTER_API_KEY) return process.env.OPENROUTER_API_KEY
  const service = readJson(SERVICE_FILE)
  const key = service?.env?.OPENROUTER_API_KEY
  return typeof key === "string" ? key : undefined
}

// Cuenta solo las respuestas que el proveedor aceptó: un 429 o un error de red
// no consume cuota, y contarlos inflaba el número.
async function bucket(provider: string, resetAt: number | undefined, now: number): Promise<Bucket> {
  if (resetAt && resetAt > now) return { used: 0, resetAt }

  const floor = resetAt && resetAt <= now ? resetAt : now - DAY_MS
  const first = await rows(
    `select min(time_created) as t
       from session_message
      where type='assistant'
        and json_extract(data,'$.model.providerID') = '${provider}'
        and time_created > ${floor}
        and coalesce(json_extract(data,'$.finish'),'') <> 'error'`,
  )
  const start = Number(first?.[0]?.t)
  if (!Number.isFinite(start)) return { used: 0 }

  const counted = await rows(
    `select count(*) as n
       from session_message
      where type='assistant'
        and json_extract(data,'$.model.providerID') = '${provider}'
        and time_created >= ${start}
        and coalesce(json_extract(data,'$.finish'),'') <> 'error'`,
  )
  return { used: Number(counted?.[0]?.n) || 0 }
}

// Ultimo mensaje de un proveedor: `reset` cuando esta agotado (fue error) y
// `ok` cuando el ultimo fue correcto. Con `ok` no se puede pintar "limite"
// aunque un fichero viejo diga lo contrario.
async function lastMessage(
  provider: string,
  now: number,
): Promise<{ reset?: number; ok: boolean }> {
  const last = await rows(
    `select time_created as ts, data as raw
       from session_message
      where type='assistant'
        and json_extract(data,'$.model.providerID') = '${provider}'
      order by time_created desc
      limit 1`,
  )
  if (!last.length) return { ok: false }
  const row = last[0]
  let msg: any
  try {
    msg = JSON.parse(row.raw)
  } catch {
    return { ok: false }
  }
  if (msg?.finish !== "error") return { ok: true }
  const retry = Number(msg?.error?.retryAfterMs)
  const base = Number(msg?.time?.completed ?? msg?.time?.created ?? row.ts)
  if (!Number.isFinite(base)) return { ok: false }
  return { reset: retry > 0 ? base + retry : base + DAY_MS, ok: false }
}

async function readLocal(): Promise<Pick<Quota, "zen" | "warp" | "kilo" | "warpNote">> {
  const now = Date.now()
  let warpNote: string | undefined

  // Reinicio por agotamiento (último mensaje de error) de cada proveedor.
  const zenMsg = await lastMessage("opencode", now)
  const warpMsg = await lastMessage("unlimited", now)
  const kiloMsg = await lastMessage("kilofree", now)
  const zenReset = zenMsg.reset
  const warpLastOk = warpMsg.ok
  let warpReset = warpMsg.reset
  const kiloReset = kiloMsg.reset

  const state = readJson(UNLIMITED_FILE)
  const ip = typeof state?.lastIp === "string" ? state.lastIp : ""
  const flag = typeof state?.lastBucket === "string" ? state.lastBucket : ""
  // unlimited.json ya no es fiable: el escudo actual escribe "affinity", no
  // "lastBucket", asi que ese "exhausted" es de una version vieja y se queda
  // clavado. Manda el ultimo mensaje en la BD (arriba): si no fue error, no hay
  // limite. El fichero solo se cree cuando la BD no dice nada.
  if (flag === "exhausted" && !warpReset && !warpLastOk) {
    const at = Number(state?.updatedAt ? Date.parse(state.updatedAt) : 0)
    if (Number.isFinite(at) && at > 0) warpReset = at + DAY_MS
  }
  if (flag && flag !== "ok") warpNote = [flag, ip].filter(Boolean).join(" · ") || flag

  const [zen, warp, kilo] = await Promise.all([
    bucket("opencode", zenReset, now),
    bucket("unlimited", warpReset, now),
    bucket("kilofree", kiloReset, now),
  ])

  return { zen, warp, kilo, warpNote }
}

async function readOpenRouter(): Promise<OrQuota> {
  const key = openRouterKey()
  if (!key) return { remaining: 0, limit: 0, used: 0, error: "sin clave" }
  try {
    // Sin timeout, una petición colgada dejaba la barra congelada.
    const res = await fetch("https://openrouter.ai/api/v1/key", {
      headers: { Authorization: `Bearer ${key}` },
      signal: AbortSignal.timeout(OPENROUTER_TIMEOUT_MS),
    })
    if (!res.ok) return { remaining: 0, limit: 0, used: 0, error: `HTTP ${res.status}` }
    const body: any = await res.json()
    const data = body?.data ?? {}
    const free = data.free_model_daily_requests ?? {}
    return {
      remaining: Number(free.remaining ?? 0),
      limit: Number(free.limit ?? 0),
      used: Number(free.used ?? 0),
      credits: typeof data.limit_remaining === "number" ? data.limit_remaining : undefined,
    }
  } catch (error) {
    return { remaining: 0, limit: 0, used: 0, error: String((error as Error)?.message ?? error) }
  }
}

function clock(ts: number): string {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`
}

function countdown(ts: number): string {
  const ms = Math.max(0, ts - Date.now())
  const h = Math.floor(ms / 3_600_000)
  const m = Math.floor((ms % 3_600_000) / 60_000)
  if (h > 0) return `${h}h${String(m).padStart(2, "0")}`
  return `${m}m`
}

export default Plugin.define({
  id: "quota-bar",
  setup(context) {
    const theme = context.theme as any
    const ok = () => theme?.hue?.interactive?.[200] ?? theme?.text?.base
    const muted = () => theme?.text?.muted
    const warn = () => theme?.text?.feedback?.warning?.base
    const bad = () => theme?.text?.feedback?.error?.base

    const [quota, setQuota] = createSignal<Quota>({
      at: 0,
      zen: { used: 0 },
      warp: { used: 0 },
      kilo: { used: 0 },
    })
    // Pulso del reloj: cada segundo fuerza el repintado de la cuenta atrás.
    const [pulse, setPulse] = createSignal(0)

    let stopped = false
    let timer: any
    let dbBusy = false
    let netBusy = false
    let lastDb = 0
    let lastNet = 0

    async function refreshLocal(): Promise<void> {
      if (stopped || dbBusy) return
      dbBusy = true
      try {
        const local = await readLocal()
        if (!stopped) setQuota((current) => ({ ...current, ...local, at: Date.now() }))
      } catch {
        // se conserva el último valor bueno
      } finally {
        dbBusy = false
      }
    }

    async function refreshOpenRouter(): Promise<void> {
      if (stopped || netBusy) return
      netBusy = true
      try {
        const openrouter = await readOpenRouter()
        if (!stopped) setQuota((current) => ({ ...current, openrouter, at: Date.now() }))
      } finally {
        netBusy = false
      }
    }

    // El ciclo solo repinta y dispara trabajo en segundo plano: nunca espera
    // a la BD ni a la red, así el reloj no se congela.
    function tick() {
      if (stopped) return
      const now = Date.now()
      setPulse(now)
      if (now - lastDb >= DB_EVERY_MS) {
        lastDb = now
        void refreshLocal()
      }
      if (now - lastNet >= OPENROUTER_EVERY_MS) {
        lastNet = now
        void refreshOpenRouter()
      }
      timer = setTimeout(tick, TICK_MS)
    }

    tick()

    function bucketColor(bucket: Bucket) {
      return bucket.resetAt ? bad() : ok()
    }

    function bucketText(name: string, bucket: Bucket) {
      if (bucket.resetAt) return `${name} límite · ${countdown(bucket.resetAt)}`
      return `${name} ${bucket.used} hoy`
    }

    function openRouterText() {
      const value = quota().openrouter
      if (!value) return "OpenRouter …"
      if (value.error) return `OpenRouter ? (${value.error})`
      const credits =
        typeof value.credits === "number" && value.credits < 1
          ? ` · $${value.credits.toFixed(2)}`
          : ""
      return `OpenRouter ${value.remaining}/${value.limit}${credits}`
    }

    function openRouterColor() {
      const value = quota().openrouter
      if (!value || value.error) return muted()
      if (value.remaining <= 0) return bad()
      if (value.limit > 0 && value.remaining <= value.limit * 0.15) return warn()
      return ok()
    }

    const unregisterSidebar = context.ui.slot({
      prepend: "sidebar.content",
      render: () => {
        pulse() // dependencia: sin esto la cuenta atrás no avanza
        return (
          <box flexDirection="column" flexShrink={0}>
            <text fg={openRouterColor()}>{openRouterText()}</text>
            <text fg={bucketColor(quota().zen)}>{bucketText("OpenCode", quota().zen)}</text>
            <text fg={bucketColor(quota().warp)}>{bucketText("Warp", quota().warp)}</text>
            <text fg={bucketColor(quota().kilo)}>{bucketText("Kilo", quota().kilo)}</text>
          </box>
        )
      },
    })

    async function showDetail() {
      await Promise.all([refreshLocal(), refreshOpenRouter()])
      const value = quota()
      const lines = [
        `OpenRouter free: ${value.openrouter ? `${value.openrouter.remaining}/${value.openrouter.limit} (${value.openrouter.used} usadas)` : "sin datos"}`,
        value.openrouter?.error ? `  error: ${value.openrouter.error}` : "",
        typeof value.openrouter?.credits === "number"
          ? `OpenRouter saldo clave: $${value.openrouter.credits.toFixed(4)}`
          : "",
        "",
        `OpenCode (Zen) hoy: ${value.zen.used} mensajes${value.zen.resetAt ? ` · límite hasta ${clock(value.zen.resetAt)} (${countdown(value.zen.resetAt)})` : ""}`,
        `Warp (Unlimited) hoy: ${value.warp.used} mensajes${value.warp.resetAt ? ` · límite hasta ${clock(value.warp.resetAt)} (${countdown(value.warp.resetAt)})` : ""}`,
        `Kilo Code hoy: ${value.kilo.used} mensajes${value.kilo.resetAt ? ` · límite hasta ${clock(value.kilo.resetAt)} (${countdown(value.kilo.resetAt)})` : ""}`,
        value.warpNote ? `Warp estado: ${value.warpNote}` : "",
        "",
        "OpenCode, Warp y Kilo no publican el tope diario; solo avisan con 429 al llegar.",
        `Actualizado: ${value.at ? clock(value.at) : "—"}`,
      ].filter(Boolean)
      await context.ui.dialog.alert({ title: "Cuotas gratis", message: lines.join("\n") })
    }

    // El keymap necesita un owner reactivo: se registra desde un slot montado.
    const unregisterApp = context.ui.slot({
      append: "app",
      render: () => {
        context.keymap.layer(() => ({
          mode: "global",
          priority: 10,
          commands: [
            {
              id: "quota-bar.show",
              title: "Ver cuotas gratis (OpenRouter, OpenCode, Warp, Kilo)",
              description: "Detalle de los usos gratis restantes de hoy",
              group: "Cuotas",
              palette: true,
              slash: { name: "cuotas", aliases: ["quota", "cuota"] },
              run: () => showDetail(),
            },
          ],
        }))
        return null
      },
    })

    return () => {
      stopped = true
      if (timer) clearTimeout(timer)
      unregisterSidebar()
      unregisterApp()
    }
  },
})
