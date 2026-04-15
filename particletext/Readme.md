# ✨ Particle Text — 3D Interactive Particle Engine

A high-performance, real-time 3D particle system that morphs **10,000 particles** between an animated sphere and crisp text formations. Built with vanilla JavaScript and the HTML5 Canvas API — zero dependencies, single file, instant deploy.

---

## 🎬 Overview

Particle Text renders a dynamic, rotating 3D globe made of colorful particles. As you type into the input field, the particles smoothly transition from the sphere into the shape of your text — letter by letter, in real time. Move your cursor over the formed text to scatter the particles with a repulsion force, and double-click anywhere to return to the globe.

The entire engine runs at **60 FPS** using `Float32Array` typed arrays for all particle data, ensuring zero garbage collection pauses even with 10,000 active particles.

---

## 🚀 Features

| Feature | Description |
|---|---|
| **10,000 Particles** | Ultra-high density rendering for sharp, legible text formation |
| **True 3D Engine** | Full 3D coordinate system with perspective projection (FOV-based camera) |
| **Real-Time Typing** | Particles morph into text as you type — no submit button needed |
| **Fibonacci Sphere** | Default idle state uses golden-angle distribution for an organic, uniform globe |
| **Circular Motion** | Sphere particles rotate and float with orbital wobble for a living, breathing effect |
| **Cursor Repulsion** | Move your mouse over formed text to push particles away with physics-based force |
| **Multi-Line Wrapping** | Long phrases automatically wrap into multiple lines with adaptive font scaling |
| **Responsive Design** | Sphere and text scale dynamically based on screen dimensions |
| **Retina Support** | Full `devicePixelRatio` awareness for crisp rendering on HiDPI displays |
| **Zero Dependencies** | Single HTML file — no frameworks, no build tools, no npm |

---

## 📦 Getting Started

### Prerequisites

- A modern web browser (Chrome, Firefox, Safari, Edge)
- No server required — works with `file://` protocol

### Quick Start

1. **Open directly in your browser**

   ```bash
   open particletext/index.html
   ```

   Or serve it locally:

   ```bash
   npx serve ./particletext
   ```

2. **Start typing** in the input field at the bottom of the screen.

---

## 🎮 Usage & Controls

### Keyboard

| Action | Effect |
|---|---|
| **Type in the input field** | Particles morph into the text in real time |
| **Clear the input field** | Particles return to the 3D sphere |

### Mouse

| Action | Effect |
|---|---|
| **Move cursor over text** | Repels nearby particles away from the cursor |
| **Move cursor away** | Particles snap back to their text positions |
| **Double-click anywhere** | Resets everything back to the rotating sphere |

---

## 🏗️ Technical Architecture

### Rendering Pipeline

```
Input Text → Off-screen Canvas → Pixel Sampling → Target Positions → Physics Simulation → Perspective Projection → Canvas Draw
```

### Core Systems

#### Particle Data (Float32Array × 14)

| Array | Purpose |
|---|---|
| `px`, `py`, `pz` | Current 3D position |
| `vx`, `vy`, `vz` | Current velocity |
| `tx`, `ty`, `tz` | Target position (sphere or text) |
| `ox`, `oy`, `oz` | Original sphere-home position |
| `hue`, `phase` | Per-particle colour hue and wobble phase |

#### Physics Parameters

| Parameter | Sphere Mode | Text Mode |
|---|---|---|
| Spring constant | `0.02` | `0.022` |
| Friction | `0.82` | `0.82` |
| Rotation speed | `0.006 rad/frame` | `0` (static) |
| Orbital jitter | `1.8` | `0` |

#### 3D Projection

```
screenX = (worldX × FOV) / (worldZ + CAMERA_Z) + centerX
screenY = (worldY × FOV) / (worldZ + CAMERA_Z) + centerY
```

- **FOV**: `550`
- **CAMERA_Z**: `600`

#### Cursor Repulsion

- **Radius**: `100px`
- **Force**: `8`

---

## 📁 Project Structure

```
particletext/
├── index.html    # Complete application — HTML, CSS, and JS in one file
└── Readme.md     # This file
```

---

## 🌐 Browser Support

| Browser | Status |
|---|---|
| Chrome 90+ | ✅ Full support |
| Firefox 88+ | ✅ Full support |
| Safari 15+ | ✅ Full support |
| Edge 90+ | ✅ Full support |
| Mobile Chrome | ⚠️ Works, may lag at 10K particles |
| Mobile Safari | ⚠️ Works, may lag at 10K particles |
