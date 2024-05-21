from generate import generate_music, get_opposite_effect_description
from plot import calculate_hrv_metrics
from flask import Flask, request, jsonify, json
from flask_cors import CORS
import time
import sounddevice as sd
import os
from scipy.io.wavfile import read


app = Flask(__name__)
CORS(app, origins=['http://localhost:3000'])

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
    data = request.get_json()  # Parse JSON data from request body
    rr_interval = data['rrInterval']
    if not experiment_ongoing:
        return jsonify({"message": "Experiment not started."})

    # Store RR intervals in the appropriate list
    if current_experiment_part == "experiment":
        # Check if there exists a dictionary with the description as the current song description inside rr_intervals["experiment"]
        song_rr_intervals[current_song_part].append(rr_interval)
    else:
        experiment_rr_intervals[current_experiment_part].append(rr_interval)

    return jsonify({"message": "Data received successfully."})

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
    global current_experiment_part, current_song_description, current_song_part, song_rr_intervals
    current_experiment_part = "pre_experiment"  # Start with pre_experiment

    start_experiment()

    # Record HRV for 1 minute before playing the music
    print("Recording HRV for 1 minute before experiment...")
    time.sleep(2)  # Wait for 1 minute

    current_experiment_part = "experiment"

    while experiment_ongoing:
        # Record HRV for until the music is generated
        current_song_part = "pre_song"
        print("Recording HRV before music is generated...")

        prev_song_description = current_song_description

        # Get the previous song's pre and post metrics
        metrics_pre = calculate_hrv_metrics(song_rr_intervals.get("pre_song", []))
        metrics_post = calculate_hrv_metrics(song_rr_intervals.get("post_song", []))

        song_rr_intervals = {
            "pre_song": [],
            "during_song": [],
            "post_song": []
        }
        
        print("Previous song pre metrics: ", metrics_pre)
        print("Previous song post metrics: ", metrics_post)

        if metrics_pre and metrics_post:
            change_percentage = (metrics_post["rmssd"] - metrics_pre["rmssd"]) / metrics_pre["rmssd"] * 100

            if abs(change_percentage) < 5:  # Change of less than 5% is considered stable
                current_effect = "HRV stable"
            elif change_percentage > 0:
                current_effect = "HRV increased"
            else:
                current_effect = "HRV decreased"

            print("Current effect: ", current_effect)
            print("prev rmsdd: ", metrics_pre["rmssd"])
            print("post rmsdd: ", metrics_post["rmssd"])
            print("Previous song description: ", prev_song_description)

            current_song_description = get_opposite_effect_description(current_effect)
        


        song, sample_rate = generate_music(current_song_description)
        # Play the generated music
        current_song_part = "during_song"
        print("Recording HRV while music is playing...")
        print(f"Playing music style: {current_song_description}")

        sd.play(song, sample_rate)
        sd.wait()
        

        # Record HRV for 15 seconds post_song
        current_song_part = "post_song"
        print("Recording HRV after music is generated...")
        time.sleep(15)


    # Record HRV for 1 minute after the music
    print("Recording HRV for 1 minute after playing the music...")
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