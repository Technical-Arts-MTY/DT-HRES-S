<h1 align="center">DT-HRES-S</h1>

<p align="center">
Gemelo digital de un sistema híbrido de energía renovable,<br>
en formato de instrumento educativo para comunidades indígenas.
</p>

<p align="center">
<img src="https://img.shields.io/badge/EPICS%20in%20IEEE-2025--2026-1f6feb">
<img src="https://img.shields.io/badge/licencia-CC%20BY--NC--SA%204.0-lightgrey">
<img src="https://img.shields.io/badge/python-3.11-blue">
<img src="https://img.shields.io/badge/hardware-Raspberry%20Pi%205-c51a4a">
</p>

<table>
<tr>
<td align="center"><img src="docs/img/dthres1.png" width="100%"></td>
</tr>
<tr>
<td>

### El instrumento completo

Dos cajas acopladas por la parte trasera. Al frente, la unidad de control en coraza impresa en 3D negra: pantalla tras ventana de acrílico, rueda y tres botones, verde, ámbar y rojo. Las bisagras laterales abren hacia los componentes internos.

Detrás, el instrumento observador: caja de paredes de acrílico, con abertura circular en la parte superior y ductos de ventilación en la base, que aloja el circuito de principios armado en protoboard, con panel solar y batería encendiendo una bombilla.

El circuito de la caja trasera es el sistema físico. La pantalla del frente es el gemelo digital de ese mismo sistema.

</td>
</tr>
</table>

<table>
<tr>
<td width="50%" align="center"><img src="docs/img/dthres3.png" width="100%"></td>
<td width="50%" align="center"><img src="docs/img/dthres4.png" width="100%"></td>
</tr>
<tr>
<td valign="top">

**Unidad de control**

Raspberry Pi 5 con la pantalla protegida por acrílico. El modelo entrenado corre aquí, sin conexión a internet.

</td>
<td valign="top">

**Instrumento observador**

Caja de acrílico con abertura circular superior y ventilación inferior. El armado queda a la vista, conexión por conexión.

</td>
</tr>
</table>

<h2 align="center">Contexto</h2>

El instrumento está dirigido a comunidades indígenas que operan o evalúan operar un sistema híbrido de energía renovable.

Donde ya existe una instalación, la réplica de la caja trasera reproduce a escala lo que ocurre en ella, y la pantalla del frente traduce ese comportamiento a números y gráficas: producción del panel a lo largo del día, estado de la batería, consumo cubierto.

Donde todavía no hay instalación, el armado en protoboard queda expuesto a propósito. Cada conexión se sigue a simple vista, se mide y se reproduce con material local. El gemelo digital, entrenado con datos meteorológicos, estima el tamaño de panel, turbina y batería que corresponde al consumo de la comunidad.

El proyecto sustituye el uso de software comercial de licencia cerrada, como HOMER o PVsyst, por una herramienta abierta que cualquier miembro de la comunidad puede abrir, leer y modificar.

<h2 align="center">Cómo está armado</h2>

La unidad de control lleva una Raspberry Pi 5 dentro de una coraza impresa en 3D. La pantalla de 7 pulgadas va detrás de una ventana de acrílico, sin táctil: la interacción ocurre con una rueda giratoria y tres botones de panel. La rueda mueve la selección y confirma al presionarla; el verde avanza, el ámbar regresa, el rojo reinicia la captura. Las bisagras abren la coraza hacia los componentes, accesibles para mantenimiento o para mostrar el interior durante un taller.

El descarte del táctil es deliberado. Una pantalla capacitiva no responde con las manos mojadas, obliga a exponer la superficie y se degrada en clima costero salino. Con rueda y botones, la pantalla queda sellada detrás del acrílico y el instrumento se opera aunque no se alcance a ver bien la pantalla bajo el sol.

El instrumento observador va aparte y se conecta por la parte trasera. Sus paredes de acrílico dejan ver el circuito completo. La abertura circular superior deja pasar la luz hacia el panel solar, y los ductos de la base mantienen el flujo de aire sobre los componentes.

<h2 align="center">Del Colab a la Raspberry</h2>

El entrenamiento vive en Google Colab y no se mueve de ahí. El conjunto de datos se genera con la simulación física del repositorio, barriendo combinaciones de tamaño de panel, turbina y batería sobre los años meteorológicos típicos de cuatro ciudades. Sobre ese conjunto se entrenan y comparan árbol de decisión, bosque aleatorio, máquina de vectores de soporte y red neuronal, con validación dejando una ciudad fuera, que mide la respuesta del modelo en un sitio que nunca vio.

A la Raspberry se copia únicamente el resultado: el modelo ganador serializado con joblib y los datos meteorológicos precargados. El dispositivo no entrena, solo hace inferencia, y esa inferencia corre en la CPU de la Pi en milisegundos. No lleva acelerador de IA porque el bosque aleatorio no lo requiere; esa decisión se revisa solo si un modelo más pesado demuestra ventaja medible en latencia y precisión sobre el hardware real.

| Etapa | Dónde ocurre |
|---|---|
| Generación del conjunto de datos | Colab |
| Entrenamiento y comparación de los cuatro algoritmos | Colab |
| Validación dejando una ciudad fuera | Colab |
| Serialización del modelo ganador | Colab |
| Inferencia sobre el consumo de la comunidad | Raspberry Pi |
| Lectura de sensores locales | Raspberry Pi |

<h2 align="center">Open in Colab</h2>

<p align="center">

| Notebook | Contenido | |
|---|---|---|
| 11 | Prototipo del gemelo digital, de la simulación física al modelo entrenado | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Technical-Arts-MTY/DT-HRES-S/blob/main/notebooks/11_digital_twin_prototype.ipynb) |
| 12 | Interfaz comunitaria, dimensionamiento con controles deslizantes | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Technical-Arts-MTY/DT-HRES-S/blob/main/notebooks/12_community_interface.ipynb) |
| 13 | Recorrido por la metodología 4D | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Technical-Arts-MTY/DT-HRES-S/blob/main/notebooks/13_4D_methodology_walkthrough.ipynb) |

</p>

Los notebooks clonan el repositorio e instalan las dependencias en la primera celda. No requieren instalación local ni licencia.

<h2 align="center">Metodología 4D</h2>

```
DT-HRES-S
│
├── 1D  Concepto        teoría y ecuaciones del sistema
├── 2D  Cuerpo          objetivos de optimización e interfaz
├── 3D  Mente           sensores, datos e incertidumbre
└── 4D  Espíritu        arreglo físico, bloques y pérdidas
    │
    ├── HRES 1  teoría y ecuaciones
    ├── HRES 2  objetivos de optimización
    ├── HRES 3  comprensión de los sensores
    ├── HRES 4  sombra digital con datos sintéticos
    ├── HRES 5  reemplazo por datos reales
    ├── HRES 6  autocorrección del modelo
    └── HRES 7  pronóstico con aprendizaje automático
```

[Metodología 4D completa](docs/4D_methodology/)

<h2 align="center">Instrumentos</h2>

### Unidad de control

| Componente | Especificación |
|---|---|
| Raspberry Pi 5 | 8 GB RAM |
| Almacenamiento | microSD industrial 64 GB, SSD USB 256 GB |
| Pantalla | 7", 1024x600, IPS, tras ventana de acrílico |
| Rueda | encoder rotatorio con pulsador, eje metálico |
| Botones | 22 mm, IP67, verde, ámbar, rojo |
| Coraza | impresión 3D negra, con bisagras |
| Disipación | disipador activo con ventilador |
| Alimentación | panel 20 W, controlador PWM 10 A, batería LiFePO4 12 V 20 Ah |

### Instrumento observador

| Componente | Especificación |
|---|---|
| Panel solar | 20 W, 12 V |
| Batería | LiFePO4 12 V |
| Controlador de carga | PWM 10 A |
| Carga | bombilla |
| Montaje | protoboard a la vista |
| Caja | acrílico, abertura circular superior, ductos de ventilación inferiores |

### Sensores meteorológicos, opcionales

| Componente | Especificación |
|---|---|
| Piranómetro | irradiancia global |
| BME280 | temperatura, humedad, presión |
| Anemómetro | copas, salida de pulsos |

Sin los sensores el instrumento funciona con los años meteorológicos precargados. Los sensores permiten contrastar esos datos contra la medición del sitio.

<h2 align="center">Software</h2>

| Capa | Contenido |
|---|---|
| Sistema | Raspberry Pi OS Lite |
| Cálculo | Python 3.11, scikit-learn, joblib, pandas, numpy |
| Interfaz | pantalla completa, sin escritorio |
| Entrada | gpiozero para rueda y botones |
| Arranque | servicio systemd al encender |

<h2 align="center">Repositorio</h2>

```
DT-HRES-S
│
├── data/           años meteorológicos típicos de cuatro ciudades
├── src/            modelos físicos, simulador y modelos de aprendizaje
├── notebooks/      prototipo, interfaz comunitaria y recorrido de la metodología
├── docs/           metodología 4D, guía de investigación e imágenes
├── tests/          pruebas de los módulos
└── requirements.txt
```

<h2 align="center">Documentación</h2>

[Metodología 4D](docs/4D_methodology/)

[Guía de investigación](docs/RESEARCH_GUIDE.md)

<h2 align="center">Licencia</h2>

<p align="center">CC BY-NC-SA 4.0</p>

---

### Nota sobre la forma final

Las especificaciones de esta página describen el diseño de referencia. La forma final del instrumento puede variar según la disponibilidad de materiales: la coraza admite otras dimensiones, los componentes admiten equivalentes locales, y el instrumento observador puede armarse con el panel, la batería y la carga que se consigan en la región. Lo que se mantiene es la separación entre las dos cajas, el acceso visual al circuito y la operación sin táctil ni conexión a internet.

---

<p align="center">
EPICS in IEEE 2025-2026 | Tecnológico de Monterrey | Technical Arts, capítulo estudiantil ITESM<br>
Project lead | PhD Rasikh Tariq
</p>
