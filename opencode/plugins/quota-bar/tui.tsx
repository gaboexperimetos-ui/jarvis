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

const LOCAL_EVERY_MS = 5_000
const OPENROUTER_EVERY_MS = 5 * 60_000
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

let DatabaseCtor: any = undefined

async function sqlite(): Promise<any> {
  if (DatabaseCtor !== undefined) return DatabaseCtor
  try {
    const mod: any = await import("bun:sqlite")
    DatabaseCtor = mod.Database ?? null
  } catch {
    DatabaseCtor = null
  }
  return DatabaseCtor
}

// Devuelve filas como objetos. Usa bun:sqlite y cae al CLI sqlite3.
async function rows(sql: string): Promise<any[]> {
  const Database = await sqlite()
  if (Database) {
    try {
      const db = new Database(DB_PATH, { readonly: true })
      try {
        return db.query(sql).all()
      } finally {
        db.close()
      }
    } catch {
      // sigue con el CLI
    }
  }
  try {
    const out = execFileSync("sqlite3", ["-json", DB_PATH, sql], {
      encoding: "utf8",
      timeout: 5_000,
      maxBuffer: 8 * 1024 * 1024,
    }).trim()
    return out ? JSON.parse(out) : []
  } catch {
    return []
  }
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

// La ventana gratis de Zen dura 24 h desde la primera petición, así que no
// coincide con el día local. Se reconstruye desde el último reinicio conocido
// (los 429 traen retryAfterMs) y, si no hay ninguno, desde la primera petición
// de las últimas 24 h.
async function bucket(provider: string, resetAt: number | undefined, now: number): Promise<Bucket> {
  if (resetAt && resetAt > now) return { used: 0, resetAt }

  const floor = resetAt && resetAt <= now ? resetAt : now - DAY_MS
  const first = await rows(
    `select min(time_created) as t
       from session_message
      where type='assistant'
        and json_extract(data,'$.model.providerID') = '${provider}'
        and time_created > ${floor}`,
  )
  const start = Number(first?.[0]?.t)
  if (!Number.isFinite(start)) return { used: 0 }

  const counted = await rows(
    `select count(*) as n
       from session_message
      where type='assistant'
        and json_extract(data,'$.model.providerID') = '${provider}'
        and time_created >= ${start}`,
  )
  return { used: Number(counted?.[0]?.n) || 0 }
}

// Agotamiento real de un proveedor gratis: mira su ÚLTIMO mensaje. Si fue un
// error (finish='error'), está agotado. El reinicio es retryAfterMs si viene,
// o 24 h desde el error (ventana diaria) cuando no lo trae (Warp y Kilo no dan
// retryAfterMs). Si el último mensaje fue correcto, no está agotado.
async function exhaustedReset(provider: string, now: number): Promise<number | undefined> {
  const last = await rows(
    `select time_created as ts, data as raw
       from session_message
      where type='assistant'
        and json_extract(data,'$.model.providerID') = '${provider}'
      order by time_created desc
      limit 1`,
  )
  if (!last.length) return undefined
  const row = last[0]
  let msg: any
  try {
    msg = JSON.parse(row.raw)
  } catch {
    return undefined
  }
  if (msg?.finish !== "error") return undefined
  const retry = Number(msg?.error?.retryAfterMs)
  const base = Number(msg?.time?.completed ?? msg?.time?.created ?? row.ts)
  if (!Number.isFinite(base)) return undefined
  return retry > 0 ? base + retry : base + DAY_MS
}

async function readLocal(): Promise<Pick<Quota, "zen" | "warp" | "kilo" | "warpNote">> {
  const now = Date.now()
  let warpNote: string | undefined

  // Reinicio por agotamiento (último mensaje de error) de cada proveedor.
  const zenReset = await exhaustedReset("opencode", now)
  let warpReset = await exhaustedReset("unlimited", now)
  const kiloReset = await exhaustedReset("kilofree", now)

  const state = readJson(UNLIMITED_FILE)
  const ip = typeof state?.lastIp === "string" ? state.lastIp : ""
  const flag = typeof state?.lastBucket === "string" ? state.lastBucket : ""
  // Warp: unlimited.json es la señal fiable; si está agotado y no hay reset
  // por BD, usa la hora de la última rotación + 24 h.
  if (flag === "exhausted" && !warpReset) {
    const at = Number(state?.updatedAt ? Date.parse(state.updatedAt) : 0)
    if (Number.isFinite(at) && at > 0) warpReset = at + DAY_MS
  }
  if (flag && flag !== "ok") warpNote = [flag, ip].filter(Boolean).join(" · ") || flag

  const zen = await bucket("opencode", zenReset, now)
  const warp = await bucket("unlimited", warpReset, now)
  const kilo = await bucket("kilofree", kiloReset, now)

  return { zen, warp, kilo, warpNote }
}

async function readOpenRouter(): Promise<OrQuota> {
  const key = openRouterKey()
  if (!key) return { remaining: 0, limit: 0, used: 0, error: "sin clave" }
  try {
    const res = await fetch("https://openrouter.ai/api/v1/key", {
      headers: { Authorization: `Bearer ${key}` },
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

    let stopped = false
    let timer: any
    let lastOpenRouter = 0

    async function refresh() {
      if (stopped) return
      try {
        const local = await readLocal()
        setQuota((current) => ({ ...current, ...local, at: Date.now() }))
      } catch {
        // se conserva el último valor
      }
      if (Date.now() - lastOpenRouter > OPENROUTER_EVERY_MS) {
        lastOpenRouter = Date.now()
        const openrouter = await readOpenRouter()
        if (!stopped) setQuota((current) => ({ ...current, openrouter, at: Date.now() }))
      }
      if (!stopped) timer = setTimeout(refresh, LOCAL_EVERY_MS)
    }

    void refresh()

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
      render: () => (
        <box flexDirection="column" flexShrink={0}>
          <text fg={openRouterColor()}>{openRouterText()}</text>
          <text fg={bucketColor(quota().zen)}>{bucketText("OpenCode", quota().zen)}</text>
          <text fg={bucketColor(quota().warp)}>{bucketText("Warp", quota().warp)}</text>
          <text fg={bucketColor(quota().kilo)}>{bucketText("Kilo", quota().kilo)}</text>
        </box>
      ),
    })

    async function showDetail() {
      await refresh()
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