import numpy as np
import scipy.signal as signal

def butter_bandpass(lowcut, highcut, fs, order=5):
        sos = signal.butter(order, [lowcut, highcut], analog=False, btype='band', output='sos', fs=fs)
        return sos

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
        sos = butter_bandpass(lowcut, highcut, fs, order=order)
        y = signal.sosfiltfilt(sos, data)
        return y

def process_audio(audio):
    # Filter the audio
    filtered_audio = butter_bandpass_filter(audio, 100, 13000, 32000)

    # Normalize the audio
    normalized_audio = filtered_audio / np.max(np.abs(filtered_audio))

    return normalized_audio
