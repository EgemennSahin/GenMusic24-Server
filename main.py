from multiprocessing import Manager
import threading
from flask import Flask, request, jsonify, json
from flask_cors import CORS
import time
import logging

import numpy as np

from generate import generate_music, generate_conditional_music, get_opposite_effect_description
from plot import calculate_hrv_metrics


app = Flask(__name__)
CORS(app, origins=['http://localhost:3000'])

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# List to store RR intervals
experiment_rr_intervals = {
    "pre_experiment": [],
    "post_experiment": []
}

song_rr_intervals = {
    "pre_song": [],
    "during_song": [],
    "post_song": []
} 

current_experiment_part = "pre_experiment"
current_song_part = "pre_song"
current_song_description = "music"

experiment_ongoing = False

@app.route('/api/heartRate', methods=['POST'])
def heart_rate():
    global current_experiment_part
    try:
        data = request.get_json()  # Parse JSON data from request body
        logging.debug(f"Received data: {data}")  # Debugging line to print incoming data

        if 'rrIntervals' not in data or not isinstance(data['rrIntervals'], list):
            return jsonify({"message": "Invalid data format"}), 400

        rr_intervals = data['rrIntervals']
        if not experiment_ongoing:
            return jsonify({"message": "Experiment not started."})

        # Store RR intervals in the appropriate list
        if current_experiment_part == "experiment":
            # Check if there exists a dictionary with the description as the current song description inside rr_intervals["experiment"]
            song_rr_intervals[current_song_part].extend(rr_intervals)
        else:
            experiment_rr_intervals[current_experiment_part].extend(rr_intervals)

        return jsonify({"message": "Data received successfully."})

    except Exception as e:
        logging.error(f"Error processing heart rate data: {e}")
        return jsonify({"message": "Internal Server Error"}), 500

@app.route('/api/startExperiment', methods=['GET'])
def start_experiment():
    global experiment_ongoing
    experiment_ongoing = True

    print("Experiment started.")
    return jsonify({"message": "Experiment started."})

@app.route('/api/stopExperiment', methods=['GET'])
def stop_experiment():
    global experiment_ongoing, experiment_rr_intervals, song_rr_intervals
    experiment_ongoing = False

    experiment_rr_intervals = {
        "pre_experiment": [],
        "post_experiment": []
    }

    song_rr_intervals = {
        "pre_song": [],
        "during_song": [],
        "post_song": []
    }



    print("Experiment stopped.")
    return jsonify({"message": "Experiment stopped."})

@app.route('/api/getExperimentData', methods=['GET'])
def get_experiment_data():
    global experiment_rr_intervals, song_rr_intervals
    return jsonify({
        "experiment": experiment_rr_intervals,
        "song": song_rr_intervals
    })



@app.route('/api/playMusic', methods=['GET'])
def play_music():
    import sounddevice as sd

    global current_experiment_part, current_song_description, current_song_part, song_rr_intervals
    current_experiment_part = "pre_experiment"  # Start with pre_experiment

    start_experiment()

    # Record HRV for 1 minute before playing the music
    print("...Recording HRV for 1 minute before experiment...")
    time.sleep(2)  # Wait for 1 minute

    current_experiment_part = "experiment"

    while experiment_ongoing:
        # Get the previous song's pre and post metrics
        metrics_pre = calculate_hrv_metrics(song_rr_intervals.get("pre_song", []))
        metrics_post = calculate_hrv_metrics(song_rr_intervals.get("post_song", []))


        # Record HRV for until the music is generated
        current_song_part = "pre_song"
        print("...Recording HRV before music is played...")

        song_rr_intervals = {
            "pre_song": [],
            "during_song": [],
            "post_song": []
        }

        # Create a Manager object and use it to create the list
        manager = Manager()
        songs = manager.list()

        # Generate the base song
        song, sample_rate = generate_music(current_song_description)
        songs.append(song)

        # Generate the next 3 songs in separate threads while the current song is playing
        for _ in range(3):
            print("Generating next song...")
            # Start a new thread to generate the next song
            thread = threading.Thread(target=generate_next_song, args=(songs, sample_rate, current_song_description))
            thread.start()

            # Play the current song
            current_song_part = "during_song"
            print("...Recording HRV while music is playing...")
            sd.play(songs[-1][0].cpu()[0].numpy(), sample_rate)
            sd.wait()

            # Wait for the next song to be generated
            thread.join()
        

        if not np.isnan(metrics_pre["mean"]) and not np.isnan(metrics_post["mean"]):
            change_percentage_rmssd = (metrics_post["rmssd"] - metrics_pre["rmssd"]) / metrics_pre["rmssd"] * 100
            change_percentage_lf = (metrics_post["lf_power"] - metrics_pre["lf_power"]) / metrics_pre["lf_power"] * 100 if metrics_pre["lf_power"] else np.nan
            change_percentage_hf = (metrics_post["hf_power"] - metrics_pre["hf_power"]) / metrics_pre["hf_power"] * 100 if metrics_pre["hf_power"] else np.nan

            # Determine current effect based on HRV metrics
            if abs(change_percentage_rmssd) < 5 and abs(change_percentage_lf) < 5 and abs(change_percentage_hf) < 5:
                current_effect = "HRV stable"
            elif abs(change_percentage_hf) > abs(change_percentage_lf):
                current_effect = "Parasympathetic increase"
            elif abs(change_percentage_lf) > abs(change_percentage_hf):
                current_effect = "Sympathetic increase"
            else:
                current_effect = "Mixed response"

            current_song_description = get_opposite_effect_description(current_effect)
        else:
            print("Insufficient data to determine HRV metrics changes. Defaulting to previous description.")
            current_song_description = get_opposite_effect_description("HRV stable")
        

        # Record HRV for as long as the pre_song RR intervals
        current_song_part = "post_song"
        print("...Recording HRV after music is generated...")
        time.sleep(len(song_rr_intervals["pre_song"]))


    # Record HRV for 1 minute after the music
    print("...Recording HRV for 1 minute after playing the music...")
    current_experiment_part = "post_experiment"
    time.sleep(60)  # Wait for 1 minute

    # Save the RR intervals to a JSON file with the name as the current timestamp
    timestamp = int(time.time())
    with open(f'rr_intervals_{timestamp}.json', 'w') as f:
        json.dump(experiment_rr_intervals, f)

    # Find the difference in hrv metrics from before and after the experiment
    metrics_pre = calculate_hrv_metrics(experiment_rr_intervals["pre_experiment"])
    metrics_post = calculate_hrv_metrics(experiment_rr_intervals["post_experiment"])

    print("HRV metrics before experiment:")
    for metric, value in metrics_pre.items():
        print(f"{metric}: {value}")
    print()

    print("HRV metrics after experiment:")
    for metric, value in metrics_post.items():
        print(f"{metric}: {value}")

    stop_experiment()


    return jsonify({"message": "Music generation completed."})

def generate_next_song(songs, sample_rate, description):
    print("generate_next_song function called with songs length: ", len(songs))  # Add this line

    # Generate the next song based on the previous one
    try:
        song, _ = generate_conditional_music(songs[-1], sample_rate, description)
        songs.append(song)

        print("Next song generated.")

    except Exception as e:
        print(f"Error generating next song: {e}")



@app.route('/api/baselineTest/<session_name>', methods=['POST'])
def baseline_test(session_name):
    global current_experiment_part

    start_experiment()

    current_experiment_part = "pre_experiment"  # Start with pre_experiment

    # Record HRV for 1 minute before playing the music
    print("Recording HRV for 5 minutes before music is played...")
    time.sleep(300)      # Wait for 1 minute

    current_experiment_part = "experiment"

    print("Recording HRV while music is playing...")
    # print(f"Playing music file: {music_file_path}")

    time.sleep(300)

    current_experiment_part = "post_experiment"

    print("Recording HRV for 5 minutes after music is played...")
    time.sleep(300)

    # Save the RR intervals to a JSON file with the name as the current timestamp
    timestamp = int(time.time())
    with open(f'rr_intervals_{session_name}_{timestamp}.json', 'w') as f:
        json.dump(experiment_rr_intervals, f)

    # Find the difference in hrv metrics from before and after the experiment
    metrics_pre = calculate_hrv_metrics(experiment_rr_intervals["pre_experiment"])
    metrics_post = calculate_hrv_metrics(experiment_rr_intervals["post_experiment"])

    print("HRV metrics before experiment:")
    for metric, value in metrics_pre.items():
        print(f"{metric}: {value}")
    print()

    print("HRV metrics after experiment:")
    for metric, value in metrics_post.items():
        print(f"{metric}: {value}")

    stop_experiment()


    return jsonify({"message": "Baseline test completed."})

if __name__ == "__main__":
    app.run(debug=False, port=5000)