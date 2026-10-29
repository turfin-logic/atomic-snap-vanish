"""
ATOMIC SNAP VANISH (Chutki Bajao aur Vanish!)
Real-time finger snap detection, Thanos/Atomic dust disintegration effect,
and virtual webcam streaming for Zoom / Teams / Google Meet.

THE VOID SEQUENCE (deep animation):
  1. DISSOLVE  - body explodes into glowing additive particles + Infinity Stones
  2. VORTEX    - particles spiral into a blackhole at the snap point
  3. ASSEMBLE  - your own atoms fly out and spell your message ("BRB...", "GONE"...)
  4. HOLD      - the message shimmers like stardust
  5. CRUMBLE   - it crumbles top-down into falling dust -> empty room

Also: golden charge aura, magic rebuild, wand trail, dust motes,
and GHOST ECHO - a spectral replay of your last seconds haunts the room.
"""

import cv2
import mediapipe as mp
import numpy as np
import pygame
import time
import os
import random
import math
import wave
import gc
from collections import deque

BASE_DIR = os.path.dirname(__file__)

# Initialize Pygame Mixer for instant, zero-latency audio
pygame.mixer.init()
SOUND_FILE = os.path.join(BASE_DIR, "assets", "snap.wav")
CHIME_FILE = os.path.join(BASE_DIR, "assets", "chime.wav")
snap_sound = None
chime_sound = None
if os.path.exists(SOUND_FILE):
    try:
        snap_sound = pygame.mixer.Sound(SOUND_FILE)
    except Exception as e:
        print(f"Warning: Could not load sound: {e}")

def ensure_chime():
    """Generates a soft ascending 'magic chime' if it doesn't exist yet."""
    if os.path.exists(CHIME_FILE):
        return CHIME_FILE
    try:
        sr = 22050
        dur = 1.3
        t = np.linspace(0, dur, int(sr * dur), False)
        freq = 523.25 * (2 ** (t / dur))  # C5 -> C6 ascending sweep
        data = np.sin(2 * np.pi * freq * t) * np.exp(-2.5 * t) * 0.55
        data += np.sin(2 * np.pi * freq * 1.5 * t) * np.exp(-3.5 * t) * 0.30
        audio = (data * 32767).astype(np.int16)
        with wave.open(CHIME_FILE, "w") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sr)
            f.writeframes(audio.tobytes())
        return CHIME_FILE
    except Exception as e:
        print(f"Warning: Could not create chime: {e}")
        return None

chime_path = ensure_chime()
if chime_path:
    try:
        chime_sound = pygame.mixer.Sound(chime_path)
    except Exception as e:
        print(f"Warning: Could not load chime: {e}")

# MediaPipe modules
mp_hands = mp.solutions.hands
mp_segmentation = mp.solutions.selfie_segmentation

hands = mp_hands.Hands(
    max_num_hands=2,
    min_detection_confidence=0.65,
    min_tracking_confidence=0.65
)
segmenter = mp_segmentation.SelfieSegmentation(model_selection=1)  # 1 = accurate landscape model

# App State
STATE_CALIBRATING = "CALIBRATING"
STATE_NORMAL = "NORMAL"
STATE_DISINTEGRATING = "VOID-SEQ"
STATE_VANISHED = "VANISHED"
STATE_REBUILDING = "REBUILDING"

current_state = STATE_CALIBRATING
calibration_start = time.time()
CALIBRATION_DURATION = 3.0  # seconds to step out of frame

background_frame = None
cached_bg_path = os.path.join(BASE_DIR, "assets", "background.jpg")
saves_dir = os.path.join(BASE_DIR, "saves")

# Snap detection state
snap_primed = False
prime_time = 0.0
last_snap_x, last_snap_y = 0, 0

# Magic config (BGR colors)
STONE_COLORS = [
    (255, 120, 0),    # Space - blue
    (0, 230, 255),    # Mind - yellow
    (60, 60, 255),    # Reality - red
    (200, 40, 160),   # Power - purple
    (80, 220, 0),     # Time - green
    (30, 130, 255),   # Soul - orange
]
GOLD = (0, 215, 255)
WAND_COLORS = [
    (0, 215, 255),    # gold
    (255, 255, 0),    # cyan
    (255, 0, 255),    # magenta
    (150, 250, 170),  # mint
]

# The Void Sequence timings (seconds since snap)
P1_DISSOLVE_END = 1.3
P2_VORTEX_END = 2.4
P3_ASSEMBLE_END = 3.8
P4_HOLD_END = 8.6      # message shimmers for ~4.8s
P5_CRUMBLE_END = 10.4

VOID_MESSAGES = ["BRB...", "GONE", "AFK", "MY INTERNET DIED", "IN A MEETING"]
void_message_idx = 0

class Particle:
    """One glowing spark. Optional (tx, ty) target + per-particle ease for the morph."""
    __slots__ = ("x", "y", "vx", "vy", "color", "life", "decay", "size", "tx", "ty", "ease", "twinkle")

    def __init__(self, x, y, color, vx=0.0, vy=0.0, decay=0.03, size=3, target=None,
                 ease=0.12, twinkle=0.0):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = 1.0
        self.decay = decay
        self.size = size
        if target is not None:
            self.tx, self.ty = float(target[0]), float(target[1])
        else:
            self.tx, self.ty = None, None
        self.ease = ease
        self.twinkle = twinkle  # phase offset for shimmer

particles = []          # void-sequence sparks
wand_particles = []     # fingertip sparkle trail / dust motes
rebuild_particles = []  # sparks converging back in
disintegrate_start_time = 0.0
rebuild_start_time = 0.0
REBUILD_DURATION = 1.1
shockwave_radius = 0
wand_mode = True
ghost_echo = True
void_bbox = None        # (x0, y0, x1, y1) of the assembled message
msg_assigned = False

# Ghost Echo ring buffer: downscaled silhouette replay while vanished
GHOST_W, GHOST_H = 320, 180
ghost_buffer = deque(maxlen=26)

VIRTUAL_CAM_HINTS = ("iriun", "obs", "droidcam", "epoccam", "e2esoft", "manycam", "xsplit", "virtual", "unity", "phone")

def get_camera_names():
    """Lists DirectShow camera names (index order == device order)."""
    try:
        from pygrabber.dshow_graph import FilterGraph
        return FilterGraph().get_input_devices()
    except Exception:
        return None

def warm_up(cap, tries=20):
    """Reads frames until one is non-black (HP/Iriun cameras can need seconds to start)."""
    best = None
    for _ in range(tries):
        ret, frame = cap.read()
        if ret and frame is not None:
            best = frame
            if frame.mean() > 5.0:
                return frame
        time.sleep(0.1)
    return best

def get_best_camera():
    """Auto-detects cameras by NAME - prefers the laptop's real camera over
    virtual/phone cams (Iriun, OBS, DroidCam...)."""
    names = get_camera_names()
    if names:
        print(f"[*] Cameras detected: {list(enumerate(names))}")
        real = [i for i, n in enumerate(names) if not any(h in n.lower() for h in VIRTUAL_CAM_HINTS)]
        virtual = [i for i, n in enumerate(names) if any(h in n.lower() for h in VIRTUAL_CAM_HINTS)]
        order = real + virtual
    else:
        print("[*] Camera names unavailable - probing indices 1, 0, 2...")
        order = [1, 0, 2]

    for idx in order:
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if cap.isOpened():
            frame = warm_up(cap)
            label = names[idx] if names else f"Camera {idx}"
            if frame is not None and frame.mean() > 5.0:
                print(f"[+] Connected to {label} (index {idx}, Resolution: {frame.shape[1]}x{frame.shape[0]})")
                return cap, idx, (names or [])
            print(f"[*] {label} (index {idx}) gives no image yet - trying next")
            cap.release()

    print("[*] No camera streaming yet - keeping fallback index 0 open (will wait)...")
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    warm_up(cap)
    return cap, 0, (names or [])

def check_snap_gesture(hand_landmarks, img_w, img_h):
    """
    Detects finger snap:
    1. Thumb tip (4) and Middle finger tip (12) touching (< 0.045 distance) -> primes snap.
    2. Rapid release/slide apart -> triggers snap!
    """
    global snap_primed, prime_time, last_snap_x, last_snap_y

    thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]

    dist = math.hypot(thumb_tip.x - middle_tip.x, thumb_tip.y - middle_tip.y)
    curr_time = time.time()

    # 1. Pinching thumb and middle finger together primes the snap
    if dist < 0.045:
        snap_primed = True
        prime_time = curr_time
        last_snap_x = int(thumb_tip.x * img_w)
        last_snap_y = int(thumb_tip.y * img_h)
        return False

    # 2. If primed recently and fingers snap apart
    if snap_primed and (curr_time - prime_time < 0.35):
        if dist > 0.085:
            snap_primed = False
            return True

    if curr_time - prime_time > 0.4:
        snap_primed = False

    return False

def check_peace_sign(hand_landmarks):
    """Peace sign (Index + Middle UP, Ring + Pinky DOWN) resets/reappears."""
    index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
    index_pip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_PIP]
    middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
    middle_pip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
    ring_tip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_TIP]
    ring_pip = hand_landmarks.landmark[mp_hands.HandLandmark.RING_FINGER_PIP]
    pinky_tip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_TIP]
    pinky_pip = hand_landmarks.landmark[mp_hands.HandLandmark.PINKY_PIP]

    index_up = index_tip.y < index_pip.y
    middle_up = middle_tip.y < middle_pip.y
    ring_down = ring_tip.y > ring_pip.y
    pinky_down = pinky_tip.y > pinky_pip.y

    return index_up and middle_up and ring_down and pinky_down

def sample_text_targets(message, w, h, max_points):
    """Renders the message on an offscreen canvas and samples its pixels as particle targets."""
    canvas = np.zeros((h, w), np.uint8)
    scale = 1.0
    while scale < 8.0:
        trial = scale + 0.25
        (tw, th), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_DUPLEX, trial, max(2, int(trial * 14)))
        if tw > w * 0.85 or th > h * 0.35:
            break
        scale = trial
    thickness = max(2, int(scale * 14))
    (tw, th), base = cv2.getTextSize(message, cv2.FONT_HERSHEY_DUPLEX, scale, thickness)
    org = ((w - tw) // 2, (h + th) // 2)
    cv2.putText(canvas, message, org, cv2.FONT_HERSHEY_DUPLEX, scale, 255, thickness, cv2.LINE_AA)

    ys, xs = np.where(canvas > 100)
    if len(xs) == 0:
        return None, None
    pts = np.column_stack((xs, ys)).astype(np.float64)
    if len(pts) > max_points:
        idx = np.random.choice(len(pts), max_points, replace=False)
        pts = pts[idx]
    else:
        need = min(max_points, len(pts) * 4)
        idx = np.random.choice(len(pts), need, replace=True)
        pts = pts[idx] + np.random.uniform(-2.5, 2.5, (need, 2))
    bbox = (int(org[0]), int(org[1] - th), int(org[0] + tw), int(org[1] + base))
    return pts, bbox

def trigger_disintegration(frame, person_mask, snap_pos, message):
    """THE VOID SEQUENCE: dissolve -> vortex -> assemble into text -> hold -> crumble."""
    global current_state, disintegrate_start_time, particles, shockwave_radius
    global void_bbox, msg_assigned
    current_state = STATE_DISINTEGRATING
    disintegrate_start_time = time.time()
    shockwave_radius = 5
    particles = []
    wand_particles.clear()
    void_bbox = None
    msg_assigned = False

    if snap_sound:
        snap_sound.play()

    ys, xs = np.where(person_mask > 0.5)
    if len(xs) > 0:
        sample_count = min(2400, len(xs))
        indices = np.random.choice(len(xs), size=sample_count, replace=False)
        for idx in indices:
            px, py = int(xs[idx]), int(ys[idx])
            b, g, r = frame[py, px]
            if random.random() < 0.25:
                color = random.choice(STONE_COLORS)
            else:
                color = (min(255, int(b * 0.4 + 20)), min(255, int(g * 0.8 + 120)), min(255, int(r * 1.2 + 180)))

            dx = px - snap_pos[0]
            angle = math.atan2(py - snap_pos[1], dx)
            speed = random.uniform(2.0, 7.0)
            vx = math.cos(angle) * speed + random.uniform(1.0, 5.0)  # wind to the right
            vy = math.sin(angle) * speed - random.uniform(2.0, 6.0)  # drift upward
            particles.append(Particle(px, py, color, vx=vx, vy=vy,
                                      decay=0.0,  # life is driven per-phase
                                      size=random.randint(2, 4),
                                      twinkle=random.uniform(0, math.tau)))

def trigger_rebuild(frame, person_mask):
    """Reverse of the vanish: sparks fly in from the screen edges and rebuild you."""
    global current_state, rebuild_start_time
    h, w = frame.shape[:2]
    current_state = STATE_REBUILDING
    rebuild_start_time = time.time()
    particles.clear()
    wand_particles.clear()
    rebuild_particles.clear()

    if chime_sound:
        chime_sound.play()

    ys, xs = np.where(person_mask > 0.5)
    if len(xs) > 0:
        sample_count = min(800, len(xs))
        indices = np.random.choice(len(xs), size=sample_count, replace=False)
        for idx in indices:
            tx, ty = float(xs[idx]), float(ys[idx])
            side = random.random()
            if side < 0.25:      # top
                sx, sy = random.uniform(-80, w + 80), -80.0
            elif side < 0.5:     # bottom
                sx, sy = random.uniform(-80, w + 80), h + 80.0
            elif side < 0.75:    # left
                sx, sy = -80.0, random.uniform(-80, h + 80)
            else:                # right
                sx, sy = w + 80.0, random.uniform(-80, h + 80)
            color = random.choice(STONE_COLORS + [GOLD])
            rebuild_particles.append(Particle(sx, sy, color, decay=0.0, size=2, target=(tx, ty)))

def assign_message_targets(message, w, h):
    """At vortex end: give every particle a pixel of the message (or let extras be dust)."""
    global void_bbox, msg_assigned
    pts, void_bbox = sample_text_targets(message, w, h, len(particles))
    msg_assigned = True
    if pts is None:
        return
    order = np.random.permutation(len(particles))
    for i, p_idx in enumerate(order):
        p = particles[p_idx]
        if i < len(pts):
            p.tx, p.ty = float(pts[i][0]), float(pts[i][1])
            p.ease = random.uniform(0.07, 0.15)
        # particles without a target stay as drifting dust

_glow_cache = {}  # (h, w) -> reusable additive layer (avoids per-frame allocation)

def draw_glow_layer(out_frame, spark_list, fade_with_life=True):
    """Renders sparks additively onto out_frame so overlaps bloom like real light."""
    if not spark_list:
        return out_frame
    key = out_frame.shape[:2]
    layer = _glow_cache.get(key)
    if layer is None:
        layer = np.zeros(key + (3,), np.uint8)
        _glow_cache[key] = layer
    else:
        layer[:] = 0
    for s in spark_list:
        a = s.life if fade_with_life else 1.0
        color = (min(255, int(s.color[0] * a)), min(255, int(s.color[1] * a)), min(255, int(s.color[2] * a)))
        if s.size > 1:
            glow_color = (color[0] // 4, color[1] // 4, color[2] // 4)
            cv2.circle(layer, (int(s.x), int(s.y)), s.size * 3, glow_color, -1)
        cv2.circle(layer, (int(s.x), int(s.y)), s.size, color, -1)
    cv2.add(out_frame, layer, dst=out_frame)
    return out_frame

def main():
    global current_state, background_frame, shockwave_radius, wand_mode
    global calibration_start, ghost_echo, void_message_idx

    cap, cam_idx, cam_names = get_best_camera()
    cam_label = cam_names[cam_idx] if cam_idx < len(cam_names) else f"Camera {cam_idx}"
    cam_switch_toast = 0.0
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print("\n========================================================")
    print("🔥 ATOMIC SNAP VANISH (Chutki Bajao aur Vanish!) ACTIVE")
    vcam = None
    try:
        import pyvirtualcam
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        vcam = pyvirtualcam.Camera(width=w, height=h, fps=30, fmt=pyvirtualcam.PixelFormat.BGR)
        print(f"[+] Virtual Camera active: {vcam.device}")
    except Exception as e:
        print(f"[*] Note: Virtual Camera not active ({e}). Live window running.")

    print("\n========================================================")
    print("🔥 ATOMIC SNAP VANISH (Chutki Bajao aur Vanish!) ACTIVE")
    print(f"📷 Active Camera Index: {cam_idx}")
    print("--------------------------------------------------------")
    print("👉 Snap fingers (Thumb + Middle) OR press [SPACE] to Vanish")
    print("   -> THE VOID SEQUENCE: dissolve > vortex > your atoms")
    print("      spell the message > shimmer > crumble to dust")
    print("👉 Show Peace Sign ✌️ OR press [R] to Rebuild")
    print("👉 [T]: Change Void Message  |  [E]: Ghost Echo ON/OFF")
    print("👉 [M]: Magic Wand Trail     |  [P]: Save Photo")
    print("👉 [B]: Re-capture background |  [C]: Switch Camera | [Q]: Quit")
    if cam_names:
        print(f"👉 [C] cycles: {' <-> '.join(cam_names)}")
    print("========================================================\n")

    window_name = "Atomic Snap Vanish"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 960, 540)

    # Wait for the camera to actually stream (Iriun needs its phone app open, HP warms up late)
    ret, frame = cap.read()
    cam_wait_start = time.time()
    while (not ret or frame is None) and time.time() - cam_wait_start < 20:
        blank = np.zeros((540, 960, 3), np.uint8)
        cv2.putText(blank, "WAITING FOR CAMERA...", (250, 240), cv2.FONT_HERSHEY_DUPLEX, 1.1, (0, 255, 255), 2)
        cv2.putText(blank, "Open the Iriun app on your phone, or press C after start to switch cams", (120, 300),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.imshow(window_name, blank)
        if (cv2.waitKey(1) & 0xFF) == ord('q'):
            print("Quitted while waiting for camera.")
            return
        time.sleep(0.2)
        ret, frame = cap.read()
    if not ret or frame is None:
        print("Fatal: No camera started streaming within 20s.")
        return

    fps_time = time.time()
    fps = 30.0
    ghost_tick = 0  # ring-buffer sampler clock (NORMAL state only)
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.01)
            continue

        frame = cv2.flip(frame, 1)  # Mirror for natural interaction
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        frame_count += 1
        if frame_count % 600 == 0:  # periodic native/heap pressure relief (~every 20s)
            gc.collect()

        # 1. State: Calibrating Background
        if current_state == STATE_CALIBRATING:
            elapsed = time.time() - calibration_start
            remaining = max(0.0, CALIBRATION_DURATION - elapsed)

            # Show countdown overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, 120), (20, 20, 20), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

            cv2.putText(frame, "STEP OUT OF FRAME TO CAPTURE BACKGROUND", (w // 2 - 380, 50),
                        cv2.FONT_HERSHEY_DUPLEX, 0.9, (0, 255, 255), 2)
            cv2.putText(frame, f"Capturing in: {remaining:.1f}s (or press B now)", (w // 2 - 220, 95),
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, (255, 255, 255), 2)

            if elapsed >= CALIBRATION_DURATION:
                background_frame = frame.copy()
                cv2.imwrite(cached_bg_path, background_frame)
                current_state = STATE_NORMAL
                print("[+] Background captured & saved!")

            out_frame = frame

        # 2. Normal / Active States
        else:
            if background_frame is None:
                background_frame = frame.copy()
            elif background_frame.shape != frame.shape:
                background_frame = cv2.resize(background_frame, (w, h))

            # Segment person
            seg_results = segmenter.process(rgb_frame)
            person_mask = seg_results.segmentation_mask

            # Hand tracking
            hand_results = hands.process(rgb_frame)
            snap_detected = False
            snap_pos = (w // 2, h // 2)

            if hand_results.multi_hand_landmarks:
                for hand_landmarks in hand_results.multi_hand_landmarks:
                    # Draw subtle hand skeleton
                    mp.solutions.drawing_utils.draw_landmarks(
                        frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp.solutions.drawing_utils.DrawingSpec(color=(0, 255, 200), thickness=2, circle_radius=2),
                        mp.solutions.drawing_utils.DrawingSpec(color=(0, 150, 255), thickness=2)
                    )

                    # Magic Wand Trail at index fingertip (only in NORMAL state)
                    if wand_mode and current_state == STATE_NORMAL:
                        tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                        wx, wy = int(tip.x * w), int(tip.y * h)
                        for _ in range(3):
                            wand_particles.append(Particle(
                                wx + random.randint(-4, 4), wy + random.randint(-4, 4),
                                random.choice(WAND_COLORS),
                                vx=random.uniform(-0.8, 0.8),
                                vy=random.uniform(-1.4, 0.2),
                                decay=random.uniform(0.05, 0.09),
                                size=random.randint(1, 3)))
                        if len(wand_particles) > 500:
                            del wand_particles[:len(wand_particles) - 500]

                    # Check Peace Sign (Rebuild / Reset)
                    if current_state in (STATE_VANISHED, STATE_DISINTEGRATING):
                        if check_peace_sign(hand_landmarks):
                            trigger_rebuild(frame, person_mask)

                    # Check Snap (Vanish)
                    elif current_state == STATE_NORMAL:
                        if check_snap_gesture(hand_landmarks, w, h):
                            snap_detected = True
                            snap_pos = (last_snap_x or w // 2, last_snap_y or h // 2)
                            break

            # Handle Snap Trigger
            if snap_detected and current_state == STATE_NORMAL:
                message = VOID_MESSAGES[void_message_idx % len(VOID_MESSAGES)]
                print(f"[✨] Void Sequence initiated: '{message}'")
                trigger_disintegration(frame, person_mask, snap_pos, message)

            # Ghost Echo recording (NORMAL state only): downscaled silhouette ring buffer
            if current_state == STATE_NORMAL:
                ghost_tick += 1
                if ghost_tick % 3 == 0:
                    ghost_buffer.append((
                        cv2.resize(frame, (GHOST_W, GHOST_H)),
                        cv2.resize(person_mask, (GHOST_W, GHOST_H)),
                    ))

            # RENDER: NORMAL STATE
            if current_state == STATE_NORMAL:
                out_frame = frame

                # Update + render wand trail additively (glowing sparkle)
                if wand_particles:
                    alive = []
                    for sp in wand_particles:
                        sp.x += sp.vx
                        sp.y += sp.vy
                        sp.life -= sp.decay
                        if sp.life > 0:
                            alive.append(sp)
                    wand_particles[:] = alive
                    draw_glow_layer(out_frame, wand_particles)

                # Snap charge-up golden aura (pulsing rings)
                if snap_primed:
                    pulse = math.sin(time.time() * 12)
                    r = 22 + int(5 * pulse)
                    cv2.circle(out_frame, (last_snap_x, last_snap_y), r + 9, (0, 90, 160), 2)
                    cv2.circle(out_frame, (last_snap_x, last_snap_y), r, (0, 200, 255), 2)
                    cv2.circle(out_frame, (last_snap_x, last_snap_y), 6, (0, 255, 255), -1)
                    cv2.putText(out_frame, "READY TO SNAP!", (last_snap_x - 70, last_snap_y - 40),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            # RENDER: THE VOID SEQUENCE
            elif current_state == STATE_DISINTEGRATING:
                dt = time.time() - disintegrate_start_time
                out_frame = background_frame.copy()

                # Phase 1: body dissolves (alpha fades, dissolve edge rises)
                if dt < P1_DISSOLVE_END:
                    progress = dt / P1_DISSOLVE_END
                    body_alpha = np.clip((1.0 - progress) * 1.5, 0.0, 1.0)
                    dissolve_threshold = 0.5 + progress * 0.5
                    mask_3d = np.repeat((person_mask > dissolve_threshold)[:, :, np.newaxis], 3, axis=2)
                    faded_body = (frame * body_alpha + background_frame * (1.0 - body_alpha)).astype(np.uint8)
                    out_frame = np.where(mask_3d, faded_body, background_frame)

                    shockwave_radius += int(25 * (1.0 - progress * 0.5))
                    if shockwave_radius < max(w, h):
                        cv2.circle(out_frame, snap_pos, shockwave_radius, (255, 220, 100), max(1, int(6 * (1.0 - progress))))
                        cv2.circle(out_frame, snap_pos, max(1, shockwave_radius - 12), (0, 180, 255), 2)

                    for p in particles:
                        p.x += p.vx
                        p.y += p.vy
                        p.vx *= 0.985
                        p.vy *= 0.985
                        p.life = 1.0
                    draw_glow_layer(out_frame, particles)

                # Phase 2: VORTEX - particles spiral into the snap blackhole
                elif dt < P2_VORTEX_END:
                    cx, cy = snap_pos
                    for p in particles:
                        dx, dy = cx - p.x, cy - p.y
                        d = max(1.0, math.hypot(dx, dy))
                        ux, uy = dx / d, dy / d
                        # pull inward + tangential swirl (clockwise)
                        p.vx = p.vx * 0.82 + ux * 4.2 - uy * 4.6
                        p.vy = p.vy * 0.82 + uy * 4.2 + ux * 4.6
                        p.x += p.vx
                        p.y += p.vy
                        p.life = 1.0
                    draw_glow_layer(out_frame, particles)
                    # blackhole core
                    core_r = 14 + int(4 * math.sin(dt * 18))
                    cv2.circle(out_frame, snap_pos, core_r + 8, (0, 60, 120), -1)
                    cv2.circle(out_frame, snap_pos, core_r, (0, 0, 0), -1)
                    cv2.circle(out_frame, snap_pos, core_r + 2, (0, 160, 255), 1)

                # Phase 3: ASSEMBLE - atoms fly to their message pixels
                elif dt < P3_ASSEMBLE_END:
                    if not msg_assigned:
                        message = VOID_MESSAGES[void_message_idx % len(VOID_MESSAGES)]
                        assign_message_targets(message, w, h)
                        if chime_sound:
                            chime_sound.play()
                    for p in particles:
                        if p.tx is not None:
                            p.x += (p.tx - p.x) * p.ease
                            p.y += (p.ty - p.y) * p.ease
                            p.life = 1.0
                        else:  # leftover dust drifts away
                            p.x += p.vx * 0.4
                            p.y += p.vy * 0.4 - 0.3
                            p.life = max(0.0, p.life - 0.012)
                    draw_glow_layer(out_frame, particles)

                # Phase 4: HOLD - the message shimmers like stardust
                elif dt < P4_HOLD_END:
                    now = time.time()
                    for p in particles:
                        if p.tx is not None:
                            jitter = 1.2
                            p.x = p.tx + math.sin(now * 2.0 + p.twinkle) * jitter
                            p.y = p.ty + math.cos(now * 1.6 + p.twinkle) * jitter
                            p.life = 0.72 + 0.28 * math.sin(now * 6.0 + p.twinkle)
                        else:
                            p.x += p.vx * 0.2
                            p.y += p.vy * 0.2 - 0.2
                            p.life = max(0.0, p.life - 0.010)
                    draw_glow_layer(out_frame, particles)

                # Phase 5: CRUMBLE - message dissolves top-down into falling dust
                elif dt < P5_CRUMBLE_END:
                    if void_bbox is not None:
                        x0, y0, x1, y1 = void_bbox
                        crumble_progress = (dt - P4_HOLD_END) / (P5_CRUMBLE_END - P4_HOLD_END)
                        line_y = y0 - 30 + (y1 - y0 + 60) * crumble_progress
                    else:
                        line_y = 0
                    for p in particles:
                        if p.tx is not None and p.ty <= line_y:
                            p.tx = p.ty = None
                            p.vx = random.uniform(-1.0, 1.0)
                            p.vy = random.uniform(-1.5, 0.0)
                        if p.tx is None:
                            p.vy += 0.35  # gravity on the dust
                            p.x += p.vx
                            p.y += p.vy
                            p.life = max(0.0, p.life - 0.016)
                        else:
                            now = time.time()
                            p.x = p.tx + math.sin(now * 2.0 + p.twinkle) * 1.2
                            p.y = p.ty + math.cos(now * 1.6 + p.twinkle) * 1.2
                            p.life = 0.72 + 0.28 * math.sin(now * 6.0 + p.twinkle)
                    draw_glow_layer(out_frame, particles)

                else:
                    particles.clear()
                    current_state = STATE_VANISHED

                # Live phase label
                if dt < P1_DISSOLVE_END:
                    phase_label = "DISSOLVE"
                elif dt < P2_VORTEX_END:
                    phase_label = "VORTEX"
                elif dt < P3_ASSEMBLE_END:
                    phase_label = "ASSEMBLE"
                elif dt < P4_HOLD_END:
                    phase_label = "THE MESSAGE"
                elif dt < P5_CRUMBLE_END:
                    phase_label = "CRUMBLE"
                else:
                    phase_label = "..."
                cv2.putText(out_frame, f"[VOID SEQUENCE: {phase_label}]", (30, 45),
                            cv2.FONT_HERSHEY_DUPLEX, 0.8, GOLD, 2)

            # RENDER: REBUILDING (sparks converge and rebuild the body)
            elif current_state == STATE_REBUILDING:
                dt = time.time() - rebuild_start_time
                progress = min(1.0, dt / REBUILD_DURATION)
                ease = 1.0 - (1.0 - progress) ** 3  # ease-out cubic

                out_frame = background_frame.copy()
                mask_3d = np.repeat((person_mask > 0.5)[:, :, np.newaxis], 3, axis=2)
                body = (frame * ease + background_frame * (1.0 - ease)).astype(np.uint8)
                out_frame = np.where(mask_3d, body, background_frame)

                # Sparks chase their silhouette targets
                follow = min(1.0, ease + 0.15)
                for sp in rebuild_particles:
                    sp.x += (sp.tx - sp.x) * follow
                    sp.y += (sp.ty - sp.y) * follow
                    sp.life = 1.0 - progress * 0.6
                draw_glow_layer(out_frame, rebuild_particles)

                cv2.putText(out_frame, "[MAGIC REBUILD IN PROGRESS...]", (30, 45),
                            cv2.FONT_HERSHEY_DUPLEX, 0.8, GOLD, 2)

                if progress >= 1.0:
                    rebuild_particles.clear()
                    current_state = STATE_NORMAL
                    print("[+] Rebuild complete - welcome back!")

            # RENDER: FULLY VANISHED (empty room + golden dust + ghost echo)
            elif current_state == STATE_VANISHED:
                out_frame = background_frame.copy()

                # GHOST ECHO: spectral replay of your last seconds flickers in the room
                if ghost_echo and len(ghost_buffer) > 4:
                    g_idx = int(time.time() * 10) % len(ghost_buffer)
                    g_small, gm_small = ghost_buffer[g_idx]
                    g_up = cv2.resize(g_small, (w, h), interpolation=cv2.INTER_LINEAR)
                    gm_up = cv2.resize(gm_small, (w, h), interpolation=cv2.INTER_LINEAR)
                    flicker = 0.16 + 0.07 * math.sin(time.time() * 7.0)
                    if random.random() < 0.05:  # occasional glitch jump
                        shift = random.randint(6, 18) * random.choice((-1, 1))
                        g_up = np.roll(g_up, shift, axis=1)
                    ghost_layer = (g_up.astype(np.float32) * flicker).astype(np.uint8)
                    out_frame = np.where(gm_up[:, :, np.newaxis] > 0.5,
                                         cv2.add(out_frame, ghost_layer), out_frame)
                    cv2.putText(out_frame, "[GHOST ECHO ACTIVE]", (w - 320, 45),
                                cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 80, 255), 1)

                # Ambient golden dust motes drift through the empty room
                for _ in range(2):
                    wand_particles.append(Particle(
                        random.uniform(0, w), random.uniform(h * 0.3, h),
                        GOLD,
                        vx=random.uniform(-0.3, 0.3),
                        vy=random.uniform(-0.8, -0.2),
                        decay=random.uniform(0.008, 0.016),
                        size=random.randint(1, 2)))
                if len(wand_particles) > 400:
                    del wand_particles[:len(wand_particles) - 400]
                alive = []
                for sp in wand_particles:
                    sp.x += sp.vx
                    sp.y += sp.vy
                    sp.life -= sp.decay
                    if sp.life > 0:
                        alive.append(sp)
                wand_particles[:] = alive
                draw_glow_layer(out_frame, wand_particles)

                cv2.putText(out_frame, "[YOU ARE VANISHED - Empty Room]", (30, 45),
                            cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 255), 2)
                cv2.putText(out_frame, "Show ✌️ Peace Sign or Press [R] to Rebuild", (30, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        # HUD Overlay
        curr_fps_time = time.time()
        instant_fps = 1.0 / max(0.001, curr_fps_time - fps_time)
        fps = fps * 0.85 + instant_fps * 0.15  # smoothed
        fps_time = curr_fps_time

        wand_status = "ON" if wand_mode else "OFF"
        echo_status = "ON" if ghost_echo else "OFF"
        hud_text = f"FPS: {int(fps)} | {current_state} | CAM: {cam_label} [C] | Msg [T] | Echo [E]: {echo_status} | Wand [M]: {wand_status} | [SPACE]: Snap | [R]: Rebuild | [Q]: Quit"
        cv2.putText(out_frame, hud_text, (20, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        # Camera-switch toast (big label, 2s)
        if time.time() < cam_switch_toast:
            label = f"CAM: {cam_label}"
            (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 1.0, 2)
            x0 = w // 2 - tw // 2 - 20
            cv2.rectangle(out_frame, (x0, 96), (x0 + tw + 40, 156), (20, 20, 20), -1)
            cv2.putText(out_frame, label, (x0 + 20, 136),
                        cv2.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 255), 2)

        if vcam:
            vcam.send(out_frame)

        cv2.imshow(window_name, out_frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord(' '):  # SPACE triggers snap
            if current_state == STATE_NORMAL:
                seg_results = segmenter.process(rgb_frame)
                message = VOID_MESSAGES[void_message_idx % len(VOID_MESSAGES)]
                print(f"[✨] Void Sequence initiated: '{message}'")
                trigger_disintegration(frame, seg_results.segmentation_mask, (w // 2, h // 2), message)
        elif key == ord('r'):  # R rebuilds
            if current_state in (STATE_VANISHED, STATE_DISINTEGRATING):
                trigger_rebuild(frame, person_mask if current_state != STATE_VANISHED else np.ones((h, w), dtype=np.float32))
            else:
                current_state = STATE_NORMAL
                particles.clear()
        elif key == ord('t'):  # T cycles the void message
            void_message_idx = (void_message_idx + 1) % len(VOID_MESSAGES)
            print(f"[*] Void Message: '{VOID_MESSAGES[void_message_idx]}'")
        elif key == ord('e'):  # E toggles ghost echo
            ghost_echo = not ghost_echo
            print(f"[*] Ghost Echo: {'ON' if ghost_echo else 'OFF'}")
        elif key == ord('m'):  # M toggles magic wand trail
            wand_mode = not wand_mode
            wand_particles.clear()
            print(f"[*] Magic Wand Trail: {'ON' if wand_mode else 'OFF'}")
        elif key == ord('p'):  # P saves a photo
            os.makedirs(saves_dir, exist_ok=True)
            photo_path = os.path.join(saves_dir, f"snap_{time.strftime('%Y%m%d_%H%M%S')}.png")
            cv2.imwrite(photo_path, out_frame)
            print(f"[📸] Photo saved: {photo_path}")
        elif key == ord('b'):  # B re-calibrates background
            current_state = STATE_CALIBRATING
            calibration_start = time.time()
        elif key == ord('c'):  # C cycles through ALL detected cameras by name
            if len(cam_names) > 1:
                cam_idx = (cam_idx + 1) % len(cam_names)
            else:
                cam_idx = 0 if cam_idx == 1 else 1
            cam_label = cam_names[cam_idx] if cam_idx < len(cam_names) else f"Camera {cam_idx}"
            print(f"[*] Switching to: {cam_label} (index {cam_idx})...")
            cap.release()
            cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            warm_up(cap)
            cam_switch_toast = time.time() + 2.0
            current_state = STATE_CALIBRATING  # new camera -> new background needed
            calibration_start = time.time()
            particles.clear()
            wand_particles.clear()
            rebuild_particles.clear()

    cap.release()
    cv2.destroyAllWindows()
    if vcam:
        vcam.close()

if __name__ == "__main__":
    main()
