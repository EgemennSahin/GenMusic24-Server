import json
import numpy as np
from scipy.stats import iqr
from scipy.signal import lombscargle


def calculate_hrv_metrics(rr_intervals):
    rr_intervals = np.array(rr_intervals)
    rr_diff = np.diff(rr_intervals)
    
    # Remove zero values
    rr_intervals = rr_intervals[rr_intervals != 0]
    rr_diff = rr_diff[rr_diff != 0]

    mean_rr = np.mean(rr_intervals)
    median_rr = np.median(rr_intervals)
    std_rr = np.std(rr_intervals)
    rmssd = np.sqrt(np.mean(rr_diff**2))
    iqr_rr = iqr(rr_intervals)
    
    try:
        # Convert RR intervals to time in seconds
        time = np.cumsum(rr_intervals)
        time -= time[0]  # Normalize to start at 0

        # Define frequency range for Lomb-Scargle
        freqs = np.linspace(0.01, 0.5, 1000)  # Frequency range from 0.01 to 0.5 Hz

        # Perform Lomb-Scargle periodogram
        angular_freqs = 2 * np.pi * freqs
        pgram = lombscargle(time, rr_intervals, angular_freqs)

        # Convert to Power Spectral Density (PSD)
        psd = np.sqrt(4 * (pgram / len(rr_intervals)))

        # Define LF and HF bands
        lf_band = (0.04, 0.15)
        hf_band = (0.15, 0.4)

        # Calculate power in LF and HF bands
        lf_power = np.trapz(psd[(freqs >= lf_band[0]) & (freqs < lf_band[1])], freqs[(freqs >= lf_band[0]) & (freqs < lf_band[1])])
        hf_power = np.trapz(psd[(freqs >= hf_band[0]) & (freqs < hf_band[1])], freqs[(freqs >= hf_band[0]) & (freqs < hf_band[1])])
    except:
        lf_power = None
        hf_power = None

    return {
        "mean": mean_rr,
        "median": median_rr,
        "std_dev": std_rr,
        "rmssd": rmssd,
        "iqr": iqr_rr,
        "lf_power": lf_power,
        "hf_power": hf_power
    }


import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd


if __name__ == "__main__":
    # Load RR intervals from JSON files
    with open('rr_intervals_5mincalm1_1715954816.json', 'r') as f:
        data = json.load(f)
        rr_intervals_calm_pre = data["pre_experiment"]
        rr_intervals_calm_post = data["post_experiment"]
    with open('rr_intervals_5minfocus1_1715955771.json', 'r') as f:
        data = json.load(f)
        rr_intervals_focus_pre = data["pre_experiment"]
        rr_intervals_focus_post = data["post_experiment"]

    # Calculate HRV metrics for each part of the experiment
    metrics_data = []
    for rr_intervals, label in [(rr_intervals_calm_pre, "Calm Pre"), (rr_intervals_calm_post, "Calm Post"), 
                                (rr_intervals_focus_pre, "Focus Pre"), (rr_intervals_focus_post, "Focus Post")]:
        metrics = calculate_hrv_metrics(rr_intervals)
        metrics["Condition"] = label
        metrics_data.append(metrics)

    # Convert to DataFrame for easier plotting
    df = pd.DataFrame(metrics_data)

    # Plot HRV metrics
    plt.figure(figsize=(15, 10))
    for i, metric in enumerate(["mean", "median", "std_dev", "rmssd", "iqr", "lf_power", "hf_power"], start=1):
        plt.subplot(2, 4, i)
        sns.boxplot(x="Condition", y=metric, data=df)
        plt.title(f"{metric} by Condition")
    plt.tight_layout()
    plt.savefig("hrv_metrics_by_condition.png")

    # Plot LF/HF ratio
    df["LF/HF Ratio"] = df["lf_power"] / df["hf_power"]
    plt.figure(figsize=(10, 5))
    sns.lineplot(x="Condition", y="LF/HF Ratio", data=df)
    plt.title("LF/HF Ratio by Condition")
    plt.savefig("lf_hf_ratio_by_condition.png")