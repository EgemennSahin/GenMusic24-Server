import numpy as np
import sounddevice as sd

# Example: Generate a 440 Hz sine wave
fs = 44100  # Sampling rate
duration = 5  # in seconds
t = np.linspace(0, duration, int(fs*duration), endpoint=False)  # Time vector
audio = 0.5 * np.sin(2 * np.pi * 440 * t)  # Generate sine wave

# Play audio
sd.play(audio, samplerate=fs)

# Wait for audio to finish playing
sd.wait()
