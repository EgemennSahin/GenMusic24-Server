import json
import numpy as np
from scipy.stats import iqr

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

    return {
        "mean": mean_rr,
        "median": median_rr,
        "std_dev": std_rr,
        "rmssd": rmssd,
        "iqr": iqr_rr
    }

if __name__ == "__main__":
    # Load RR intervals from JSON file
    with open('rr_intervals.json', 'r') as f:
        rr_intervals = json.load(f)

    # Calculate HRV metrics for each part of the experiment
    for part in ["pre_experiment", "experiment", "post_experiment"]:
        print(f"{part} HRV metrics:")
        metrics = calculate_hrv_metrics(rr_intervals[part])
        for metric, value in metrics.items():
            print(f"{metric}: {value}")
        print()