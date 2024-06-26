from multiprocessing import Manager
import threading
from flask import Flask, request, jsonify, json
from flask_cors import CORS
import time
import numpy as np
from filters import process_audio
from generate import generate_music, generate_conditional_music
from plot import calculate_hrv_metrics
import sounddevice as sd


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
current_song_description = "Upbeat, welcoming tune with catchy melodies, bright synths, and light percussion. Tempo: 100-120 BPM, evoking positivity and excitement"

experiment_ongoing = False

@app.route('/api/heartRate', methods=['POST'])
def heart_rate():
    global current_experiment_part
    try:
        data = request.get_json()  # Parse JSON data from request body

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
        print(f"Error processing heart rate data: {e}")
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



@app.route('/api/playMusic', methods=['POST'])
def play_music():
    global current_experiment_part, current_song_description, current_song_part, song_rr_intervals
    current_experiment_part = "pre_experiment"  # Start with pre_experiment
    data = request.get_json()
    calming_description = data.get('calming_description')
    focus_description = data.get('focus_description')
    

    if calming_description == "":
        calming_description = "Slow, calming music with gentle piano, acoustic guitar, and soft strings"
    if focus_description == "":
        focus_description = "Fast, energetic music with powerful drums, electric guitar, and intense synths"
    
    calming_description = calming_description + ". Tempo: 60-80 BPM, evoking peace and tranquility."
    focus_description = focus_description + ". Tempo: 120-140 BPM, evoking urgency and excitement."
        
    print("Calming description: ", calming_description)
    print("Focus description: ", focus_description)

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
        print('here 2')

        # Create a Manager object and use it to create the list
        # This is necessary to share the list between threads
        manager = Manager()
        songs = manager.list()

        print('here 3')
        # Generate the base song
        song, sample_rate = generate_music(current_song_description)
        print('here 4')

        songs.append(song)
        
        print('here 5')
        # Generate the next 3 songs in separate threads while the current song is playing
        for _ in range(3):
            print("Generating next song with prompt: ", current_song_description)
            # Start a new thread to generate the next song
            thread = threading.Thread(target=generate_next_song, args=(songs, sample_rate, current_song_description))
            thread.start()

            # Play the current song
            current_song_part = "during_song"
            print("...Recording HRV while music is playing...")
            
            song_to_play = process_audio(songs[-1][0].cpu()[0].numpy())
            sd.play(song_to_play, sample_rate)
            sd.wait()

            # Wait for the next song to be generated
            thread.join()
        

        # Record HRV for as long as the pre_song RR intervals
        current_song_part = "post_song"
        print("...Recording HRV after music is generated...")
        time.sleep(len(song_rr_intervals["pre_song"]))


        if not np.isnan(metrics_pre["mean"]) and not np.isnan(metrics_post["mean"]):
            pre_lf_hf_ratio = metrics_pre["lf_power"] / metrics_pre["hf_power"]
            post_lf_hf_ratio = metrics_post["lf_power"] / metrics_post["hf_power"]

            # Determine opposite effect based on the change in LF/HF ratio
            # If the LF/HF ratio increases, the previous song had a sympathetic effect, so the next song should calm the listener down
            if post_lf_hf_ratio > pre_lf_hf_ratio:
                current_song_description = calming_description

            # If the LF/HF ratio decreases, the previous song had a parasympathetic effect, so the next song should energize the listener
            else:
                current_song_description = focus_description


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
    # Generate the next song based on the previous one
    try:
        song, _ = generate_conditional_music(songs[-1], sample_rate, description)
        songs.append(song)


        print("Next song generated.")

    except Exception as e:
        print(f"Error generating next song: {e}")



if __name__ == "__main__":
    app.run(debug=False, port=5000)