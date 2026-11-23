# Escalado al modelo local

El modelo principal (OpenRouter free) orquesta y responde lo normal. Cuando su
respuesta es una **negativa** ("I can't help with that", "No puedo ayudar con
eso", etc.), un plugin repite la misma petición al modelo local y entrega esa
respuesta en lugar de la negativa. Así el trabajo técnico legítimo (código
malicioso de un caso real, auditorías, pentesting autorizado) no se queda a
medias por el filtro del modelo gratuito.

## Cómo funciona

| Pieza | Qué hace |
|---|---|
| `~/.hermes/plugins/escalado-local/pre_llm_call` | Guarda el mensaje del usuario y el historial reciente por turno. |
| `~/.hermes/plugins/escalado-local/transform_llm_output` | Detecta la negativa; si la hay, pide la respuesta a `deepseek-v4pro` y la devuelve como respuesta del turno. |
| `~/.hermes/config.yaml` → `plugins.enabled` | Carga el plugin. |
| `plugins.hook_callback_timeout: 200` | Da margen a que el local conteste antes de abandonar el hook. |

El plugin no actúa si:

- la respuesta no parece una negativa,
- el turno ya venía del modelo local,
- el modelo local falla o devuelve vacío (se queda la respuesta original).

Registro de cada escalado: `~/.hermes/logs/escalado-local.log` (ese directorio
está excluido del sync).

## Verificación hecha (2026-11-22)

- `hermes plugins validate` → todo OK, seguridad incluida.
- `hermes plugins list` → `escalado-local` **enabled**, fuente `user`.
- Prueba real: se pidió al principal que respondiera con una negativa; el
  registro mostró `negativa escalada al local (modelo principal:
  nvidia/nemotron-3-ultra-550b-a55b:free)` y la respuesta la produjo
  `deepseek-v4pro`.
- Una respuesta normal no se toca (comprobado).

## Modelo local

- Endpoint: `http://127.0.0.1:8004/v1` (router llama.cpp, servicio `llama-router`).
- Modelo: `deepseek-v4pro`.
- **Contexto: 204800**, sin tocar. Desde el 2026-11-22 el KV q4_0 va en RAM
  (`no-kv-offload = true`) porque la app de GitHub (WebKit) retiene ~1,4 GB de
  VRAM y con el KV en GPU el modelo no cargaba. Coste medido: ~22 tok/s de
  generación y 75-169 tok/s de prefill (antes ~75 y ~1500 con el KV en GPU).
  Si se cierra esa app y se liberan ~2 GB de VRAM, se puede quitar
  `no-kv-offload` y vuelve la velocidad completa. Copias de la configuración:
  `router.ini.bak-20261122` y `router.ini.bak-ctx65536`.
- Es un modelo de 4B: responde rápido (≈1-2 s en preguntas cortas) pero puede
  inventar detalles. Para trabajo delicado conviene contrastar lo que diga.

## Alternativa manual

Para que una petición sensible vaya **directo** al local, sin pasar por el
modelo gratuito, se puede fijar el modelo del chat con el comando `/model`:

```text
/model deepseek-v4pro --once <pregunta>
```

`--once` aplica solo a ese turno; sin `--once`, el chat queda fijado al local.
