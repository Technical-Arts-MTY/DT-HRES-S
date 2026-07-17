# Technical Arts MTY · `notas`

Bitácora y documentación del capítulo, editable desde la terminal en cualquier
computadora del grupo. Una sola herramienta: `notas`. La idea es que sea rápido —
**escribes y se publica solo**.

---

## Proyectos activos

| Proyecto | Carpeta | Progreso |
|---|---|---|
| **DT-HRES** | `proyectos/DT-HRES/` | `PROGRESO.md` |
| **Michelson Interferometer** | `proyectos/Michelson_Interferometer/` | `PROGRESO.md` |

Estado rápido en la terminal:

```
notas proyectos
```

---

## Inicio rápido

```bash
gh repo clone Technical-Arts-MTY/notas     # clonar (solo la primera vez)
cd notas
python notas.py                            # abrir la interfaz
```

Firma tus notas con tu nombre (una vez por computadora):

```
Windows :  set TA_AUTOR=German
Unix    :  export TA_AUTOR=German
```

Para teclear solo `notas` (sin `python`): dentro de la carpeta ya funciona
`notas` (Windows, vía `notas.bat`) o `./notas` (Mac/Linux). Para usarlo desde
cualquier ruta, agrega esta carpeta a tu `PATH`.

---

## Flujo de todos los días

**Una nota rápida y se publica al instante:**

```bash
notas "arreglé el bug del display en Unity, queda pendiente el TMC2209"
```

**O por menú:** `notas` → `[1] Escribir nota` → escribe → Enter. Hace
`pull` + `commit` + `push` por ti.

---

## Cierre de sesión → wiki

Al terminar de trabajar (p. ej. en el interferómetro), documenta la sesión y
súbela al wiki, ya con estándar de física:

```bash
notas sesion
```

Pide proyecto, participantes, lo realizado, mediciones y pendientes; arma una
página bien estructurada y la sube al **wiki** del repo.

> La primera vez, abre el wiki una sola vez en GitHub (pestaña **Wiki →
> Create the first page**, guarda). Después `notas sesion` ya escribe solo.

---

## Citaciones (estándar de física)

```bash
notas citar
```

- **Medición:** registra magnitud, valor ± incertidumbre, **unidad SI**,
  instrumento, **estado de calibración**, condiciones y método. Queda en
  `proyectos/<proyecto>/mediciones.md`.
- **Referencia:** genera una entrada **BibTeX** para tus reportes en LaTeX y la
  agrega a `referencias.bib`.

---

## Estructura

```
notas/
├── notas.py                 # la herramienta
├── notas.bat / notas        # lanzadores (Windows / Unix)
├── README.md
├── proyectos/
│   ├── DT-HRES/             PROGRESO.md · mediciones.md
│   └── Michelson_Interferometer/   PROGRESO.md · mediciones.md
├── bitacora/               # notas diarias (YYYY-MM.md), se llenan solas
├── guias/github.md         # cheat sheet de git/GitHub
└── assets/
    ├── logos/              # pon aquí los .png del capítulo
    └── plantillas/         # plantilla-sesion.md · plantilla-medicion.md
```

---

## Roster

Alfred RS · Aaron Dir · German GH · Edgar Mth · — · — · —
