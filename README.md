# ⚡ Atomic Snap Vanish

**Chutki bajao aur vanish ho jao.** Snap your fingers on camera and your body explodes into glowing particles, collapses into a blackhole vortex — then your own atoms spell out your excuse (`BRB...`, `GONE`, `MY INTERNET DIED`) before crumbling to dust. Built for leaving Zoom / Google Meet calls in style. 😎

> *"You were never there — only your message remained."*

Inspired by the viral introvert-meeting-exit idea ([Nicovic17/vanish_webcam](https://github.com/Nicovic17/vanish_webcam)) — rebuilt from scratch with snap-gesture detection and a cinematic 5-phase "Void Sequence".

## ✨ The Void Sequence

| Phase | What happens |
|---|---|
| 1. **DISSOLVE** | Shockwave! Your body bursts into 2,400 additive-glow particles (1 in 4 is an Infinity-Stone color) |
| 2. **VORTEX** | All particles spiral into a pulsing blackhole at the snap point |
| 3. **ASSEMBLE** | Your atoms fly out and assemble into a glowing message |
| 4. **THE MESSAGE** | The text shimmers like stardust for ~5 seconds |
| 5. **CRUMBLE** | The message dissolves top-down into falling dust → empty room |

Plus: **Magic Rebuild** (✌️ peace sign → sparks fly in from the screen edges and rebuild you, with a chime), **Ghost Echo** (a spectral replay of your last seconds haunts the vanished room), **Magic Wand Trail** (index finger leaves sparkles), **golden charge aura** while priming the snap, and floating **golden dust motes**.

## 🚀 Quick Start

```bash
git clone https://github.com/turfin-logic/atomic-snap-vanish.git
cd atomic-snap-vanish
pip install -r requirements.txt
python snap_vanish.py
```

Windows: double-click **`setup.bat`** once, then **`run.bat`** every time.

**How to play:** step out of frame for 3 seconds (it captures your empty room background) → pinch **thumb + middle finger** → a golden aura appears → **SNAP!** → show a **✌️ peace sign** to rebuild.

## ⌨️ Controls

| Key | Action |
|---|---|
| `[SPACE]` | Manual snap (trigger the Void Sequence) |
| `[T]` | Cycle the void message: `BRB... → GONE → AFK → MY INTERNET DIED → IN A MEETING` |
| `[R]` | Magic Rebuild |
| `[E]` | Ghost Echo ON/OFF |
| `[M]` | Magic Wand Trail ON/OFF |
| `[P]` | Save photo of the current frame (`saves/`) |
| `[B]` | Re-capture background |
| `[C]` | Switch camera (cycles **by device name**) |
| `[Q]` / `ESC` | Quit |

## 🎥 Using with Zoom / Google Meet / Teams

The app pipes its output into a **virtual camera** so you can select it in any meeting app:

1. **Install [OBS Studio](https://obsproject.com/)** (`winget install OBSProject.OBSStudio`). You don't need to stream or record — OBS just ships the *OBS Virtual Camera* driver.
2. Run `snap_vanish.py`. It detects the virtual camera automatically:
   ```
   [+] Virtual Camera active: OBS Virtual Camera
   ```
3. Start a Zoom / Meet / Teams call → open **video settings** → select **"OBS Virtual Camera"** as your camera.
4. Snap. Vanish. Leave the meeting like a legend.

*(Alternative: the [Unity Capture](https://github.com/schellingb/UnityCapture) driver also works — pyvirtualcam supports both.)*

## 🛠 Troubleshooting

- **Camera opens but shows black** — some laptops have an IR camera at index 0. Press `[C]` to cycle cameras, or wait: the app now auto-detects cameras **by name** and prefers your real laptop camera over phone/virtual ones (Iriun, DroidCam, OBS...).
- **Using Iriun (phone as webcam)** — open the Iriun app on your phone first; the app shows a *WAITING FOR CAMERA* screen until it starts streaming.
- **"Virtual Camera not active"** — install OBS Studio (see above), then restart the app.
- **Low FPS** — close other camera apps; MediaPipe runs on CPU.

## 🔒 Privacy

100% local. Nothing is recorded, stored, or uploaded — every frame dies in RAM.

## 📦 Tech

Python · OpenCV · MediaPipe (Hands + Selfie Segmentation) · NumPy · Pygame · PyVirtualCam · pygrabber

## 🙏 Credits

- Idea spark: [Nicovic17/vanish_webcam](https://github.com/Nicovic17/vanish_webcam) (the viral introvert meeting-exit)
- Effects, snap detection, Void Sequence, Ghost Echo & magic: built from scratch

MIT License — see [LICENSE](LICENSE).
