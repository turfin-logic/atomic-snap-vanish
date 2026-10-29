import os, wave, math, struct

os.makedirs("assets", exist_ok=True)
sound_path = os.path.join("assets", "snap.wav")

sample_rate = 44100
duration = 1.6
num_samples = int(sample_rate * duration)

with wave.open(sound_path, 'w') as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(sample_rate)
    
    for i in range(num_samples):
        t = i / sample_rate
        val = 0.0
        # 1. High-impact snap / crack (0.0 to 0.06s)
        if t < 0.06:
            click = math.sin(2 * math.pi * 1800 * t) * math.exp(-t * 150)
            noise = (math.sin(t * 12000) * 0.6 + math.sin(t * 5400) * 0.4) * math.exp(-t * 90)
            val = click * 0.8 + noise * 0.5
        else:
            # 2. Cosmic Thanos / Atomic Disintegration shimmer & bass drop
            dt = t - 0.06
            # Sub-bass rumble
            bass = math.sin(2 * math.pi * 85 * dt) * math.exp(-dt * 2.0)
            # High-frequency crystalline dissolution shimmer
            shimmer1 = math.sin(2 * math.pi * (1600 - dt * 600) * dt) * math.exp(-dt * 2.2)
            shimmer2 = math.sin(2 * math.pi * (2400 + math.sin(dt * 40) * 300) * dt) * math.exp(-dt * 3.0)
            val = bass * 0.45 + shimmer1 * 0.35 + shimmer2 * 0.25
            
        sample = int(max(-1.0, min(1.0, val)) * 32767)
        f.writeframes(struct.pack('<h', sample))

print(f"Generated cinematic snap audio: {sound_path}")
