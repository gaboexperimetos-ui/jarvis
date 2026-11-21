import { Show, createSignal } from "solid-js"
import { Plugin } from "@opencode/plugin/tui"

// /loop — keeps an agent working until a completion condition is met.
// Port of Claude Code's /goal: after every finished turn a small judge model
// checks the condition and either starts another turn or resolves the goal.

type Status = "active" | "paused" | "achieved" | "failed"

type Goal = {
  sessionID: string
  condition: string
  startedAt: number
  turns: number
  status: Status
  reason: string
  /** assistant messages counted when the goal was set, for stall detection */
  baseline: number
}

type ModelRef = { providerID: string; id: string }

const DEFAULT_JUDGE: ModelRef = { providerID: "local", id: "qwen3.5-8b-abliterated:latest-gpu" }
const DEFAULT_MAX_TURNS = 40
const DEFAULT_STALL_TURNS = 3
const DEFAULT_TRANSCRIPT_MESSAGES = 12
const DEFAULT_TRANSCRIPT_CHARS = 24_000

const CLEAR_WORDS = new Set([
  "off",
  "clear",
  "stop",
  "cancel",
  "reset",
  "none",
  "quit",
  "exit",
  "apagar",
  "limpiar",
  "detener",
  "parar",
  "borra",
  "borrar",
])

const STATUS_LABEL: Record<Status, string> = {
  active: "activa",
  paused: "pausada",
  achieved: "cumplida",
  failed: " abandonada",
}

function directivePrompt(condition: string) {
  return `[loop] Completion condition:
${condition}

Keep working autonomously until that condition is satisfied. Take concrete steps with your tools and verify every step with real evidence (command output, test runs, file contents). End each turn with a short status: what is done and what is left. When you believe the condition is met, say so plainly and show the evidence that proves it.`
}

function continuePrompt(condition: string, reason: string) {
  return `[loop] The completion condition is still not met. Evaluator's reason: ${reason}

Condition:
${condition}

Do not restate the plan. Take the next concrete step, verify it, and keep going until the condition is met.`
}

const JUDGE_PROMPT = `You are a strict completion evaluator. You never do work, never call tools, and never propose changes.

Completion condition:
{{condition}}

Conversation transcript (oldest first):
{{transcript}}

Decide whether the completion condition is satisfied by evidence already present in the transcript.

Answer with exactly two lines and nothing else:
VERDICT: MET | NOT_MET | IMPOSSIBLE
REASON: <one short sentence>

Rules:
- MET only when the transcript contains direct evidence (command output, test results, file contents) that the condition holds right now.
- IMPOSSIBLE only when the transcript shows the condition can never be satisfied.
- Otherwise NOT_MET. Then REASON must name the single most useful next step, in the imperative.`

export default Plugin.define({
  id: "loop",
  setup(context) {
    const options = (context.options ?? {}) as Record<string, any>

    const maxTurns = numeric(options.maxTurns, DEFAULT_MAX_TURNS)
    const stallTurns = numeric(options.stallTurns, DEFAULT_STALL_TURNS)
    const transcriptMessages = numeric(options.transcriptMessages, DEFAULT_TRANSCRIPT_MESSAGES)
    const transcriptChars = numeric(options.transcriptChars, DEFAULT_TRANSCRIPT_CHARS)

    let judgeModel: ModelRef | null =
      options.judge?.providerID && options.judge?.id ? { ...options.judge } : { ...DEFAULT_JUDGE }

    const goals = new Map<string, Goal>()
    const [revision, setRevision] = createSignal(0)
    const touch = () => setRevision((value) => value + 1)

    function toast(message: string, variant: "info" | "success" | "warning" | "error" = "info") {
      context.ui.toast.show({ title: "loop", message, variant })
    }

    function routeSession(): string | undefined {
      const route = context.ui.router.current() as { type?: string; sessionID?: string } | undefined
      return route?.type === "session" ? route.sessionID : undefined
    }

    async function messages(sessionID: string): Promise<any[]> {
      const result = await context.client.session.context({ sessionID })
      return Array.isArray(result) ? result : []
    }

    function assistantCount(list: any[]) {
      return list.filter((message) => message?.type === "assistant").length
    }

    function toolOutput(state: any): string {
      if (!state) return ""
      const parts: string[] = []
      for (const item of state.content ?? []) if (item?.type === "text" && item.text) parts.push(item.text)
      if (state.error) parts.push(describeError(state.error))
      return parts.join("\n")
    }

    async function buildTranscript(sessionID: string): Promise<string> {
      const list = await messages(sessionID)
      const lines: string[] = []
      for (const message of list.slice(-transcriptMessages)) {
        if (message.type === "user") {
          lines.push(`USER: ${trim(message.text ?? "", 2_000)}`)
        } else if (message.type === "synthetic") {
          lines.push(`SYSTEM: ${trim(message.text ?? "", 1_000)}`)
        } else if (message.type !== "assistant") continue
        for (const item of message.content ?? []) {
          if (item.type === "text") {
            const text = trim(item.text ?? "", 3_000)
            if (text) lines.push(`ASSISTANT: ${text}`)
          } else if (item.type === "tool") {
            lines.push(`TOOL ${item.name} [${item.state?.status ?? "unknown"}]: ${trim(toolOutput(item.state), 1_500)}`)
          }
        }
      }
      const text = lines.join("\n")
      return text.length <= transcriptChars ? text : "...[recorte]...\n" + text.slice(text.length - transcriptChars)
    }

    function parseVerdict(raw: string): { verdict: string; reason: string } {
      const matched = raw.match(/VERDICT\s*[:=\-]?\s*(NOT[\s_-]?MET|MET|IMPOSSIBLE)/i)
      const reasonText = raw.match(/REASON\s*[:=\-]?\s*(.+)/i)
      const reason =
        trim((reasonText?.[1] ?? "").replace(/\s+/g, " "), 400) || "el judge no dio razón"
      const verdict = (matched?.[1] ?? "").toUpperCase().replace(/[\s_-]/g, "")
      if (verdict === "MET" || verdict === "NOTMET" || verdict === "IMPOSSIBLE") return { verdict, reason }
      return { verdict: "NOTMET", reason: `juerga ilegible del judge: ${trim(raw, 120)}` }
    }

    async function judge(goal: Goal): Promise<{ verdict: string; reason: string }> {
      const prompt = JUDGE_PROMPT.replace("{{condition}}", goal.condition).replace(
        "{{transcript}}",
        await buildTranscript(goal.sessionID),
      )

      let raw = ""
      if (judgeModel) {
        try {
          const result = await context.client.generate.text({ prompt, model: judgeModel })
          raw = result.text ?? ""
        } catch {
          judgeModel = null
          toast("Judge externo no disponible; evalúo con el modelo de la sesión", "warning")
        }
      }
      if (!raw) {
        const result = await context.client.session.generate({ sessionID: goal.sessionID, prompt })
        raw = result.text ?? ""
      }
      return parseVerdict(raw)
    }

    async function stalled(goal: Goal): Promise<boolean> {
      const list = await messages(goal.sessionID)
      const recent = assistantCount(list) - goal.baseline
      if (recent < stallTurns) return false
      const assistants = list.filter((message) => message?.type === "assistant").slice(goal.baseline)
      return assistants.every((message) => !(message.content ?? []).some((item: any) => item?.type === "tool"))
    }

    function pause(goal: Goal, reason: string) {
      goal.status = "paused"
      goal.reason = reason
      touch()
      toast(`Pausado: ${reason}. La meta sigue activa; escribe lo que quieras para seguir.`, "warning")
    }

    async function evaluate(goal: Goal) {
      goal.turns += 1
      goal.status = "active"
      touch()

      const limit = Math.min(maxTurns, turnLimit(goal.condition) ?? maxTurns)
      if (goal.turns >= limit) {
        pause(goal, `tope de turnos alcanzado (${limit})`)
        return
      }
      try {
        if (await stalled(goal)) {
          pause(goal, `${stallTurns} turnos seguidos sin usar herramientas`)
          return
        }
      } catch {
        // transcript unavailable: keep going, the judge still sees the session
      }

      let result: { verdict: string; reason: string }
      try {
        result = await judge(goal)
      } catch (error) {
        pause(goal, `el judge falló: ${describeError(error)}`)
        return
      }

      goal.reason = result.reason
      touch()

      if (result.verdict === "MET") {
        goal.status = "achieved"
        touch()
        await context.client.session.synthetic({
          sessionID: goal.sessionID,
          text: `◎ Meta cumplida: ${goal.condition}`,
          description: `loop · ${goal.turns} ${turnWord(goal.turns)} · ${formatDuration(Date.now() - goal.startedAt)} · ${result.reason}`,
        })
        toast(`Cumplida en ${goal.turns} ${turnWord(goal.turns)}: ${result.reason}`, "success")
        return
      }

      if (result.verdict === "IMPOSSIBLE") {
        goal.status = "failed"
        touch()
        await context.client.session.synthetic({
          sessionID: goal.sessionID,
          text: `✗ Meta abandonada (imposible): ${goal.condition}`,
          description: `loop · ${result.reason}`,
        })
        toast(`El judge dice que es imposible: ${result.reason}`, "error")
        return
      }

      toast(`Turno ${goal.turns}: aún no se cumple. ${result.reason}`, "info")
      await context.client.session.prompt({
        sessionID: goal.sessionID,
        text: continuePrompt(goal.condition, result.reason),
      })
    }

    async function setGoal(sessionID: string, condition: string) {
      const previous = goals.get(sessionID)
      if (previous && previous.status === "active") toast("Reemplazo la meta activa anterior", "warning")
      let baseline = 0
      try {
        baseline = assistantCount(await messages(sessionID))
      } catch {}
      goals.set(sessionID, {
        sessionID,
        condition,
        startedAt: Date.now(),
        turns: 0,
        status: "active",
        reason: "",
        baseline,
      })
      touch()
      toast(`Meta activa: ${condition}`, "info")
      await context.client.session.prompt({ sessionID, text: directivePrompt(condition) })
    }

    function clearGoal(sessionID: string) {
      const goal = goals.get(sessionID)
      if (!goal) {
        toast("No hay ninguna meta activa", "warning")
        return
      }
      goals.delete(sessionID)
      touch()
      toast(`Meta limpiada: ${goal.condition}`, "info")
    }

    async function showStatus(sessionID: string) {
      const goal = goals.get(sessionID)
      if (!goal) {
        await context.ui.dialog.alert({
          title: "loop",
          message: "No hay ninguna meta activa en esta sesión.\n\nUso: /loop <condición de finalización>\nCancelar: /loop off",
        })
        return
      }
      let spend = "—"
      try {
        const cost = context.data.session.cost(sessionID) as any
        const value = typeof cost === "number" ? cost : cost?.cost
        if (typeof value === "number") spend = `$${value.toFixed(4)}`
      } catch {}
      await context.ui.dialog.alert({
        title: "loop",
        message: [
          `Condición: ${goal.condition}`,
          `Estado: ${STATUS_LABEL[goal.status]} · ${goal.turns} ${turnWord(goal.turns)}`,
          `Duración: ${formatDuration(Date.now() - goal.startedAt)}`,
          `Gasto: ${spend}`,
          `Judge: ${judgeModel ? `${judgeModel.providerID}/${judgeModel.id}` : "modelo de la sesión"}`,
          `Último veredicto: ${goal.reason || "—"}`,
          "",
          "Cancelar: /loop off",
        ].join("\n"),
      })
    }

    const offSucceeded = context.data.on("session.execution.succeeded", (event: any) => {
      const goal = goals.get(event.data.sessionID)
      if (!goal || goal.status === "achieved" || goal.status === "failed") return
      void evaluate(goal)
    })

    const offFailed = context.data.on("session.execution.failed", (event: any) => {
      const goal = goals.get(event.data.sessionID)
      if (!goal || goal.status === "achieved" || goal.status === "failed") return
      pause(goal, `error del turno: ${describeError(event.data.error)}`)
    })

    const offInterrupted = context.data.on("session.execution.interrupted", (event: any) => {
      const goal = goals.get(event.data.sessionID)
      if (!goal || goal.status === "achieved" || goal.status === "failed") return
      pause(goal, `turno interrumpido (${event.data.reason ?? "user"})`)
    })

    const unregisterSlot = context.ui.slot({
      append: "prompt.footer.status",
      render: (props: any) => (
        <Show when={visibleGoal(props)}>
          {(goal) => (
            <box style={{ flexShrink: 0 }}>
              <text fg={goalColor(goal())}>◎ loop · {goal().turns} {turnWord(goal().turns)}</text>
            </box>
          )}
        </Show>
      ),
    })

    function visibleGoal(props: any): Goal | undefined {
      revision()
      const sessionID = props?.sessionID ?? routeSession()
      if (!sessionID) return undefined
      const goal = goals.get(sessionID)
      if (!goal || goal.status === "achieved" || goal.status === "failed") return undefined
      return goal
    }

    function goalColor(goal: Goal) {
      const theme = context.theme as any
      return goal.status === "paused" ? theme.text.muted : theme.hue.interactive[200]
    }

    // The keymap API needs a reactive owner, so the layer is registered from a
    // mounted slot (same as the bundled opencode.btw plugin) instead of setup.
    const unregisterApp = context.ui.slot({
      append: "app",
      render: () => {
        context.keymap.layer(() => ({
          mode: "global",
          priority: 10,
          commands: [
            {
              id: "loop.goal",
              title: "Trabajar hasta cumplir una condición",
              description: "El agente sigue trabajando hasta que un judge confirma que la condición se cumple",
              group: "Loop",
              palette: true,
              suggested: true,
              slash: { name: "loop", aliases: ["goal", "objetivo"], arguments: true },
              run: async (input?: string) => {
                const sessionID = routeSession()
                if (!sessionID) {
                  toast("Abre una sesión primero", "warning")
                  return
                }
                const argument = (input ?? "").trim()
                if (!argument) return void (await showStatus(sessionID))
                if (CLEAR_WORDS.has(argument.toLowerCase())) return clearGoal(sessionID)
                await setGoal(sessionID, argument)
              },
            },
          ],
        }))
        return null
      },
    })

    return () => {
      offSucceeded()
      offFailed()
      offInterrupted()
      unregisterSlot()
      unregisterApp()
    }
  },
})

function numeric(value: unknown, fallback: number) {
  const parsed = typeof value === "number" ? value : Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? Math.floor(parsed) : fallback
}

/** Reads an explicit turn budget from the condition, e.g. "or stop after 20 turns". */
function turnLimit(condition: string): number | undefined {
  const matched = condition.match(
    /(?:after|despu[eé]s|para(?:r)?|m[aá]x(?:imo)?|l[ií]mite de)\D{0,12}(\d{1,3})\s*(?:turnos?|turns?|pasos?|steps?)/i,
  )
  return matched ? Number(matched[1]) : undefined
}

function trim(text: string, max: number) {
  const value = text.trim()
  return value.length <= max ? value : value.slice(0, max) + "…"
}

function describeError(error: unknown): string {
  if (!error) return "error desconocido"
  if (typeof error === "string") return error
  const value = error as any
  if (typeof value.message === "string" && value.message) return value.message
  if (typeof value.data?.error?.message === "string") return value.data.error.message
  try {
    return trim(JSON.stringify(error), 200)
  } catch {
    return String(error)
  }
}

function turnWord(count: number) {
  return count === 1 ? "turno" : "turnos"
}

function formatDuration(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  if (hours) return `${hours}h ${minutes}m`
  if (minutes) return `${minutes}m ${seconds}s`
  return `${seconds}s`
}