import json
from flask import Flask, request, jsonify
import time
import sounddevice as sd

from plot import calculate_hrv_metrics
print('here')

from generate import generate_music, get_opposite_effect_description

app = Flask(__name__)

# Directory to store audio files
audio_dir = 'test_audios'

# List to store RR intervals
rr_intervals = {
    "pre_experiment": [],
    "experiment": [],
    "post_experiment": []
}

current_experiment_part = "pre_experiment"
experiment_ongoing = False


@app.route('/api/heartRate', methods=['POST'])
def heart_rate():
    global current_experiment_part
    data = request.get_json()  # Parse JSON data from request body
    rr_interval = data['rrInterval']
    print("RR Interval Received: ", rr_interval)

    # Store RR intervals in the appropriate list
    rr_intervals[current_experiment_part].append(rr_interval)

    return jsonify({"message": "Data received successfully."})

@app.route('/api/startExperiment', methods=['GET'])
def start_experiment():
    global experiment_ongoing
    experiment_ongoing = True
    return jsonify({"message": "Experiment started."})

@app.route('/api/stopExperiment', methods=['GET'])
def stop_experiment():
    global experiment_ongoing
    experiment_ongoing = False
    return jsonify({"message": "Experiment stopped."})


@app.route('/api/playMusic', methods=['GET'])
def play_music():
    global current_experiment_part
    current_experiment_part = "pre_experiment"  # Start with pre_experiment
    rr_intervals = {
        "pre_experiment": [],
        "experiment": [],
        "post_experiment": []
    }

    # Record HRV for 1 minute before playing the music
    print("Recording HRV for 1 minute before playing the music...")
    time.sleep(60)  # Wait for 1 minute

    # Change to experiment part
    current_experiment_part = "experiment"

    while experiment_ongoing:
        # Generate and play music based on HRV data
        metrics_pre = calculate_hrv_metrics(rr_intervals.get("pre_experiment", []))
        metrics_post = calculate_hrv_metrics(rr_intervals.get("post_experiment", []))
        if metrics_pre and metrics_post:
            description = get_opposite_effect_description(metrics_pre["rmssd"], metrics_post["rmssd"])
            song, sample_rate = generate_music(description, metrics_pre["rmssd"], metrics_pre["sdnn"], metrics_pre["pnn50"])
            print(f"Playing music style: {description}")
            sd.play(song.numpy(), sample_rate)
            sd.wait()

        # Reset for the next iteration
        rr_intervals = {
            "pre_experiment": [],
            "experiment": [],
            "post_experiment": []
        }

    # Record HRV for 1 minute after the music
    print("Recording HRV for 1 minute after playing the music...")
    current_experiment_part = "post_experiment"
    time.sleep(60)  # Wait for 1 minute

    # Save the RR intervals to a JSON file with the name as the current timestamp
    timestamp = int(time.time())
    with open(f'rr_intervals_{timestamp}.json', 'w') as f:
        json.dump(rr_intervals, f)

    return jsonify({"message": "Music generation completed."})

if __name__ == "__main__":
    app.run(debug=True, port=5000)