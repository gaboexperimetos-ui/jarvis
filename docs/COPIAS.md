# Copias: PC, homelab y GitHub

GitHub no es el único respaldo. Hay **tres copias** de lo importante, y cada una cubre un
fallo distinto:

| # | Copia | Dónde | Qué protege |
|---|---|---|---|
| 1 | **PC** | `asus-tuf:~/backups/` | si GitHub cae o no hay red |
| 2 | **Homelab** | `gabo-Inspiron-5720:~/backups/` | si el PC muere o se pierde |
| 3 | **GitHub** (la "2.0") | `gaboexperimetos-ui/jarvis` | si se pierden las dos máquinas |

Las tres se actualizan solas. La 1 y la 2 cada día a las 04:00 (`backup-local.timer`); la 3
cada 5 minutos (`jarvis-sync.timer`).

---

## Qué guarda cada copia

`backup-local.sh` (en el PC) empaqueta con fecha y rota a **7 días**:

| Snapshot | Origen | Contenido |
|---|---|---|
| `jarvis-<fecha>.tar.gz` | `~/jarvis` | el espejo del home, sin `.git` ni cachés de Chromium del skill poki |
| `styp-<fecha>.tar.gz` | `~/proyectos/styp` | `data/` (SQLite `app.db` y sus backups) + `notes/` |
| `vault-<fecha>.tar.gz` | `~/SegundoCerebro` | la bóveda de Obsidian |
| `hermes-<fecha>.tar.gz` | **inspiron** `~/.hermes` | `config.yaml`, `.env`, `SOUL.md`, `memories/`, `skills/`, `plugins/`, `sessions/`, `state.db` |

El snapshot de Hermes es el más importante: **el `~/.hermes` del inspiron no está en GitHub**
(el repo espeja el del portátil). Sin esta copia, si el inspiron muere se pierde la memoria
del agente.

Del `~/.hermes` se excluye lo regenerable: `cache/` (1,6 G), `tools/` (1,1 G),
`hermes-agent/` (966 M), `installs/` (726 M), `logs/` y los `*.bak`. El snapshot queda en ~16 MB.

### Dónde acaba cada cosa

```
PC ~/backups/                          homelab ~/backups/
├── jarvis/         ──espejo──►        laptop/jarvis/
├── styp/           ──espejo──►        laptop/styp/
├── vault/          ──espejo──►        laptop/vault/
└── hermes-inspiron/ ──espejo──►       hermes/          (además de su copia propia)
```

Así el homelab tiene **su** copia y **la del PC**, y el PC tiene **la suya** y **la del
homelab**. Si una máquina se pierde, la otra conserva todo.

---

## Permisos

`umask 077`: directorios `700` y tarballs `600`. Los snapshots contienen el `.env` del agente,
así que solo los lee `gabo`.

---

## Uso

```bash
# forzar una copia ahora
systemctl --user start backup-local.service
systemctl --user list-timers backup-local.timer
cat ~/backups/backup.log | tail

# ver qué hay
ls -lh ~/backups/*/
ssh homelab 'ls -lh ~/backups/*/'
```

---

## Restaurar desde una copia local

```bash
# 1. el repo de configuración
tar xzf ~/backups/jarvis/jarvis-<fecha>.tar.gz -C /tmp
# comparar /tmp/jarvis con ~/jarvis, o copiar ficheros concretos

# 2. los datos del dashboard
tar xzf ~/backups/styp/styp-<fecha>.tar.gz -C /tmp
# /tmp/data/app.db es la base de verdad; parar study-platform antes de sustituirla:
systemctl --user stop study-platform
cp /tmp/data/app.db ~/proyectos/styp/data/app.db
systemctl --user start study-platform

# 3. la memoria del agente (en el inspiron)
scp ~/backups/hermes-inspiron/hermes-<fecha>.tar.gz homelab:/tmp/
ssh homelab 'tar xzf /tmp/hermes-<fecha>.tar.gz -C /tmp && \
  systemctl --user stop hermes-gateway && \
  cp -a /tmp/hermes/. ~/.hermes/ && \
  systemctl --user start hermes-gateway'
```

> Antes de sobrescribir, mover lo actual a un `.bak`. La copia no se toca: es de solo lectura.

---

## Por qué no se sube esto a GitHub

Los tarballs llevan el `.env` del agente (tokens de Telegram, claves de proveedores). Van solo
a los dos equipos de casa, con permisos `600`. GitHub sigue recibiendo únicamente lo que
`jarvis-sync.sh` considera no secreto.
