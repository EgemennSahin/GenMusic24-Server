from flask import Flask, request, jsonify
import os
import time
import sounddevice as sd
from scipy.io.wavfile import read
import json

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


@app.route('/api/heartRate', methods=['POST'])
def heart_rate():
    global current_experiment_part
    data = request.get_json()  # Parse JSON data from request body
    rr_interval = data['rrInterval']
    print("RR Interval Received: ", rr_interval)

    # Store RR intervals in the appropriate list
    rr_intervals[current_experiment_part].append(rr_interval)

    return jsonify({"message": "Data received successfully."})


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

    # Play each song in the directory
    for filename in os.listdir(audio_dir):
        if filename.endswith(".wav"):  # Check if the file is an audio file
            print("Playing song: ", filename)
            # Play the song
            fs, data = read(os.path.join(audio_dir, filename))
            sd.play(data, fs)
            sd.wait()  # Wait until song is finished

            # Record HRV for 1 minute after the music
            print("Recording HRV for 1 minute after playing the music...")
                # Change to post_experiment part
            current_experiment_part = "post_experiment"

            time.sleep(60)  # Wait for 1 minute


    # Save RR intervals to a file
    with open('rr_intervals.json', 'w') as f:
        json.dump(rr_intervals, f)

    return jsonify({"message": "HRV data recorded successfully."})

if __name__ == "__main__":
    app.run(debug=True, port=5000)