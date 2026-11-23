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
- **Contexto: 65536** desde el 2026-11-22. Con 204800 el KV q4_0 (1,8 GB) no
  cabía porque WebKit retenía ~1,4 GB de VRAM; con 131072 fallaban los buffers
  de cómputo. Copia de la config anterior:
  `/home/gabo/models/router.ini.bak-20261122`. Si se libera VRAM, se puede
  volver a subir.
- Es un modelo de 4B: responde rápido (≈1-2 s en preguntas cortas) pero puede
  inventar detalles. Para trabajo delicado conviene contrastar lo que diga.

## Alternativa manual

Para que una petición sensible vaya **directo** al local, sin pasar por el
modelo gratuito, se puede fijar el modelo del chat con el comando `/model`:

```text
/model deepseek-v4pro --once <pregunta>
```

`--once` aplica solo a ese turno; sin `--once`, el chat queda fijado al local.
