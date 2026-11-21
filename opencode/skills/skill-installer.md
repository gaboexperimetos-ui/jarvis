---
name: skill-installer
description: Instala skills de OpenCode desde repositorios GitHub o rutas locales usando skill-helper.sh. Usalo cuando el usuario pida instalar un skill, copiar uno de un repo, o traer skills de otra maquina.
---

# Skill Installer

La instalacion la hace `~/.config/opencode/skills/skill-helper.sh install`.
No existe un binario `skill-installer`: estas son las instrucciones que sigues
tu cuando el usuario pide instalar algo.

## Instalar

```bash
bash ~/.config/opencode/skills/skill-helper.sh install <url-o-ruta> [nombre]
```

Acepta:

- `https://github.com/usuario/repo` — clona en profundidad 1 y copia.
- `git@github.com:usuario/repo.git`
- Una ruta local: `bash ~/.config/opencode/skills/skill-helper.sh install ~/proyectos/mi-skill`

Si el repo trae varios skills, instala el `SKILL.md` mas superficial. Omite el
nombre para deducirlo del campo `name` del skill. El comando valida el resultado
y falla si el skill ya existe: no sobrescribe en silencio.

## Que hace, paso a paso

1. Clona a un directorio temporal (o usa la ruta local tal cual).
2. Busca todos los `SKILL.md` y elige el de ruta mas corta.
3. Copia el directorio completo, no solo el `SKILL.md` — asi se trae
   `scripts/`, `references/` y `templates/`.
4. Valida frontmatter, `name` y `description`.
5. Borra el temporal.

## Despues de instalar

```bash
bash ~/.config/opencode/skills/skill-helper.sh list
bash ~/.config/opencode/skills/skill-helper.sh validate all
```

OpenCode recarga los skills al cambiar los archivos. Si no aparece, revisa el
nombre (`SKILL.md` en mayusculas) y que la `description` no este vacia.

## Donde queda instalado

| Alcance | Ruta |
|---|---|
| Global (todos los proyectos) | `~/.config/opencode/skills/<nombre>/` |
| Solo este proyecto | `.opencode/skills/<nombre>/` en la raiz |

Para instalar en un proyecto en vez de globalmente, copia el directorio a mano:

```bash
cp -r ~/.config/opencode/skills/<nombre> <proyecto>/.opencode/skills/
```

## Desinstalar

No hay comando. Es un directorio:

```bash
mv ~/.config/opencode/skills/<nombre> ~/.config/opencode/skills/<nombre>.bak
```

Muevelo en vez de borrarlo: si el skill venia de un repo, el `.bak` es tu copia
de trabajo y no hay forma de reconstruir los cambios locales que le hayas hecho.

## Antes de instalar codigo de terceros

Un skill es texto que un agente va a leer y seguir, y puede traer `scripts/`.
Lee el `SKILL.md` y cualquier script antes de instalar si no conoces el repo.
Pasar el repo por `install` ejecuta `git clone` y `cp`, nada mas; los scripts
del skill no se ejecutan hasta que alguien los invoque.

## Fuentes conocidas

| Repo | Que trae |
|---|---|
| `swarmclawai/andrej-karpathy-skills` | `karpathy` (ya instalado) |
| `robzolkos/skill-karpathy-check` | revision de planes y de implementacion |

```bash
bash ~/.config/opencode/skills/skill-helper.sh install https://github.com/robzolkos/skill-karpathy-check
```