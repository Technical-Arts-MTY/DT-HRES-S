<h1 align="center">DT-HRES-S</h1>

<p align="center">
Digital twin of a hybrid renewable energy system,<br>
built as an educational instrument for indigenous communities.
</p>

<p align="center">
<img src="https://img.shields.io/badge/EPICS%20in%20IEEE-2025--2026-1f6feb">
<img src="https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-lightgrey">
<img src="https://img.shields.io/badge/python-3.11-blue">
<img src="https://img.shields.io/badge/hardware-Raspberry%20Pi%205-c51a4a">
</p>

<table>
<tr>
<td align="center"><img src="docs/img/dthres1.png" width="100%"></td>
</tr>
<tr>
<td>

### Overview

Two enclosures wired at the back. In front, the control unit in a black 3D-printed shell: display behind an acrylic window, a rotary wheel and three buttons, green, yellow and red. Side hinges open to the internal components.

In the left, the observer instrument: an acrylic-walled box, with a circular opening on top and ventilation ducts at the bottom, housing the principles circuit built on a breadboard, with a solar panel and a battery lighting a bulb.

The circuit in the rear box is the physical system. The screen device is the digital twin of that same system.

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

**Control unit**

Raspberry Pi 5 with the display shielded by acrylic. The trained model runs here, with no internet connection.

</td>
<td valign="top">

**HRES-BOX**

Acrylic box with a circular opening on top and ventilation at the bottom. The wiring stays visible, connection by connection.

</td>
</tr>
</table>

<h2 align="center">Context</h2>

The instrument is aimed at indigenous communities that operate, or are evaluating whether to operate, a hybrid renewable energy system. 

Where an installation already exists, the rear box reproduces at scale what happens in it, and the front screen translates that behavior into numbers and charts: panel output through the day, battery state, demand covered.

Where there is no installation yet, the breadboard build is left exposed on purpose. Every connection can be traced by eye, measured, and reproduced with local material. The digital twin, trained on meteorological data, estimates the panel, turbine and battery size that fits the community's demand.

The project replaces closed-license commercial software, such as HOMER or PVsyst, with an open tool that any community member can open, read and modify.

<h2 align="center">Built</h2>

Aiming the system to be operable under outdoor conditions, the system is built with a closed architecture, putting the electronical components inside a 3D-Printed shell, and the Digital Twin screen behind an acrylic protection. 

The control unit houses a Raspberry Pi 5 inside a 3D-printed shell. The 7-inch display sits behind an acrylic window, no touch: interaction happens through a rotary wheel and three panel buttons. The wheel moves the selection and confirms on press; green advances, amber goes back, red restarts the entry. The hinges open the shell toward the components, accessible for maintenance or to show the interior during a workshop.

Dropping touch is deliberate. A capacitive screen does not respond to wet hands, forces the surface to stay exposed, and degrades in salty coastal climate. With a wheel and buttons, the screen stays sealed behind the acrylic and the instrument still works even when the screen is hard to see under direct sun.

The observer instrument sits apart and connects at the back. Its acrylic walls leave the full circuit visible. The circular opening on top lets light reach the solar panel, and the ducts at the base keep airflow over the components.

<h2 align="center">From Colab to the Raspberry Pi</h2>

Training lives in Google Colab and stays there. The dataset is generated with the repository's physics simulation, sweeping panel, turbine and battery sizes over the typical meteorological years of four cities. On that dataset, a decision tree, random forest, support vector machine and neural network are trained and compared, with leave-one-city-out validation, which measures how the model responds at a site it has never seen.

Only the result is copied to the Raspberry Pi: the winning model, serialized with joblib, and the preloaded meteorological data. The device does not train, it only runs inference, and that inference runs on the Pi's CPU in milliseconds. It carries no AI accelerator because the random forest does not need one; that decision is revisited only if a heavier model shows a measurable advantage in latency and accuracy on the actual hardware.

| Stage | Where it happens |
|---|---|
| Dataset generation | Colab |
| Training and comparison of the four algorithms | Colab |
| Leave-one-city-out validation | Colab |
| Serialization of the winning model | Colab |
| Inference on the community's demand | Raspberry Pi |
| Local sensor readings | Raspberry Pi |

<h2 align="center">Open in Colab</h2>

<p align="center">

| Notebook | Content | |
|---|---|---|
| 11 | Digital twin prototype, from physics simulation to trained model | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Technical-Arts-MTY/DT-HRES-S/blob/main/notebooks/11_digital_twin_prototype.ipynb) |
| 12 | Community interface, sizing with interactive sliders | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Technical-Arts-MTY/DT-HRES-S/blob/main/notebooks/12_community_interface.ipynb) |
| 13 | Walkthrough of the 4D methodology | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Technical-Arts-MTY/DT-HRES-S/blob/main/notebooks/13_4D_methodology_walkthrough.ipynb) |

</p>

The notebooks clone the repository and install dependencies in the first cell. No local install or license required.

<h2 align="center">4D Methodology</h2>

```
DT-HRES-S
│
├── 1D  Concept          theory and equations of the system
├── 2D  Body             optimization objectives and interface
├── 3D  Mind             sensors, data and uncertainty
└── 4D  Spirit           physical arrangement, blocks and losses
    │
    ├── HRES 1  theory and equations
    ├── HRES 2  optimization objectives
    ├── HRES 3  understanding the sensors
    ├── HRES 4  digital shadow on synthetic data
    ├── HRES 5  replacement with real data
    ├── HRES 6  model self-correction
    └── HRES 7  forecasting with machine learning
```

[Full 4D methodology](docs/4D_methodology/)

<h2 align="center">Instruments</h2>

### Control unit

| Component | Specification |
|---|---|
| Raspberry Pi 5 | 8 GB RAM |
| Storage | 64 GB industrial microSD, 256 GB USB SSD |
| Display | 7", 1024x600, IPS, behind acrylic window |
| Wheel | rotary encoder with push button, metal shaft |
| Buttons | 22 mm, IP67, green, amber, red |
| Shell | black 3D print, with hinges |
| Cooling | active heatsink with fan |
| Power | 20 W panel, 10 A PWM controller, 12 V 20 Ah LiFePO4 battery |

### Observer instrument

| Component | Specification |
|---|---|
| Solar panel | 20 W, 12 V |
| Battery | 12 V LiFePO4 |
| Charge controller | 10 A PWM |
| Load | light bulb |
| Mounting | breadboard, left exposed |
| Enclosure | acrylic, circular opening on top, ventilation ducts at the bottom |

### Meteorological sensors, optional

| Component | Specification |
|---|---|
| Pyranometer | global irradiance |
| BME280 | temperature, humidity, pressure |
| Anemometer | cup type, pulse output |

Without the sensors, the instrument runs on the preloaded meteorological years. The sensors allow that data to be checked against the site's own measurements.

<h2 align="center">Software</h2>

| Layer | Content |
|---|---|
| System | Raspberry Pi OS Lite |
| Computation | Python 3.11, scikit-learn, joblib, pandas, numpy |
| Interface | full screen, no desktop |
| Input | gpiozero for the wheel and buttons |
| Startup | systemd service on power-up |

<h2 align="center">Repository</h2>

```
DT-HRES-S
│
├── data/           typical meteorological years for four cities
├── src/            physical models, simulator and learning models
├── notebooks/      prototype, community interface and methodology walkthrough
├── docs/           4D methodology, research guide and images
├── tests/          module tests
└── requirements.txt
```

<h2 align="center">Documentation</h2>

[4D Methodology](docs/4D_methodology/)

[Research Guide](docs/RESEARCH_GUIDE.md)

<h2 align="center">License</h2>

<p align="center">CC BY-NC-SA 4.0</p>

---

### Note on the final form

The specifications on this page describe the reference design. The instrument's final form may vary with material availability: the shell can be built to other dimensions, components can be swapped for local equivalents, and the observer instrument can be assembled with whatever panel, battery and load are available in the region. What stays fixed is the separation between the two boxes, visual access to the circuit, and operation without touch or an internet connection.

---

<p align="center">
EPICS in IEEE 2025-2026 | Tecnológico de Monterrey | Technical Arts, ITESM Student Chapter<br>
Project lead | PhD Rasikh Tariq
</p>
