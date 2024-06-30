from multiprocessing import Manager
import threading
import uuid
from flask import Flask, request, jsonify, json
from flask_cors import CORS
import time
import numpy as np
import scipy
from filters import process_audio
from generate import generate_music, generate_conditional_music
from plot import calculate_hrv_metrics
import sounddevice as sd
import os

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000'])

# List to store RR intervals
experiment_rr_intervals = {
    "pre_experiment": [],
    "post_experiment": [],
}

experiment_heart_rate = {
    "pre_experiment": [],
    "post_experiment": [],
}

song_rr_intervals = {
    "pre_song": [],
    "during_song": [],
    "post_song": []
}

song_heart_rate = {
    "pre_song": [],
    "during_song": [],
    "post_song": []
}


experiment_id = None

current_experiment_part = "pre_experiment"
current_song_part = "pre_song"
current_song_description = "Upbeat tune with catchy melodies, bright synths, and light percussion. Tempo: 100-120 BPM"

experiment_ongoing = False

@app.route('/api/heartRate', methods=['POST'])
def heart_rate():
    global current_experiment_part
    try:
        data = request.get_json()  # Parse JSON data from request body

        if 'rrIntervals' not in data or not isinstance(data['rrIntervals'], list):
            return jsonify({"message": "Invalid data format"}), 400

        rr_intervals = data['rrIntervals']
        heart_rate = data['heartRate']
        
        if not experiment_ongoing:
            return jsonify({"message": "Experiment not started."})

        # Store RR intervals in the appropriate list
        if current_experiment_part == "experiment":
            # Check if there exists a dictionary with the description as the current song description inside rr_intervals["experiment"]
            song_rr_intervals[current_song_part].extend(rr_intervals)
            song_heart_rate[current_song_part].append(heart_rate)
        else:
            experiment_rr_intervals[current_experiment_part].extend(rr_intervals)
            experiment_heart_rate[current_experiment_part].append(heart_rate)

        return jsonify({"message": "Data received successfully."})

    except Exception as e:
        print(f"Error processing heart rate data: {e}")
        return jsonify({"message": "Internal Server Error"}), 500

@app.route('/api/startExperiment', methods=['GET'])
def start_experiment():
    global experiment_ongoing, experiment_id
    experiment_ongoing = True
    experiment_id = str(uuid.uuid4())


    print("Experiment started.")
    return jsonify({"message": "Experiment started."})

@app.route('/api/stopExperiment', methods=['GET'])
def stop_experiment():
    global experiment_ongoing, experiment_rr_intervals, song_rr_intervals, experiment_heart_rate, song_heart_rate
    experiment_ongoing = False

    experiment_rr_intervals = {
        "pre_experiment": [],
        "songs": [],
        "post_experiment": []
    }

    experiment_heart_rate = {
        "pre_experiment": [],
        "songs": [],
        "post_experiment": []
    }

    song_rr_intervals = {
        "pre_song": [],
        "during_song": [],
        "post_song": []
    }

    song_heart_rate = {
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
    data = request.get_json()
    calming_description = data.get('calming_description')
    focus_description = data.get('focus_description')

    current_experiment_part = "pre_experiment"  # Start with pre_experiment

    if calming_description == "":
        calming_description = "A serene and soothing melody featuring gentle acoustic guitar, soft piano, and ambient synths. Perfect for relaxation, meditation, or unwinding after a long day."
    if focus_description == "":
        focus_description = "An immersive and steady instrumental piece with rhythmic beats, subtle bass lines, and light electronic elements. Ideal for enhancing concentration, productivity, and deep focus during work or study sessions."
    
    current_song_description = calming_description
        
    print("Calming description: ", calming_description)
    print("Focus description: ", focus_description)

    start_experiment()

    # Record HRV for 1 minute before playing the music
    print("...Recording HRV for 1 minute before experiment...")
    time.sleep(60)  # Wait for 1 minute

    current_experiment_part = "experiment"
    
    for i in range(5):
        print("Run number: ", i)
        # Get the previous song's pre and post metrics

        metrics_pre = calculate_hrv_metrics(song_rr_intervals.get("pre_song", []))
        metrics_post = calculate_hrv_metrics(song_rr_intervals.get("post_song", []))

        song_rr_intervals = {
            "pre_song": [],
            "during_song": [],
            "post_song": []
        }

        song_heart_rate = {
            "pre_song": [],
            "during_song": [],
            "post_song": []
        }

        # Record HRV for until the music is generated
        current_song_part = "pre_song"
        print("...Recording HRV before music is played...")

        # Create a Manager object and use it to create the list
        # This is necessary to share the list between threads
        manager = Manager()
        songs = manager.list()

        # Generate the base song
        song, sample_rate = generate_music(current_song_description)
        songs.append(song)
        
        # Generate the next 4 songs in separate threads while the current song is playing
        for _ in range(4):
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

        # Save all the songs by concatenating them.
        print("Saving songs...")
        songs_list = [song[0].cpu().numpy() for song in songs]
        all_songs = np.concatenate(songs_list, axis=1)
        all_songs = all_songs.flatten()

        
        if not os.path.exists(f'./experiment_data/{experiment_id}/songs'):
            os.makedirs(f'./experiment_data/{experiment_id}/songs')

        scipy.io.wavfile.write(f'./experiment_data/{experiment_id}/songs/{i}.wav', rate=sample_rate, data=all_songs)
        
        # Make a folder inside experiment_data to save the song RR intervals
        if not os.path.exists(f'./experiment_data/{experiment_id}/song_rr_intervals'):
            os.makedirs(f'./experiment_data/{experiment_id}/song_rr_intervals')

        # Save the song RR intervals to a json file with experiment_id and run number
        with open(f'./experiment_data/{experiment_id}/song_rr_intervals/{i}.json', 'w') as f:
            json.dump(song_rr_intervals, f)
        
        # Make a folder inside experiment_data to save the song heart rate intervals
        if not os.path.exists(f'./experiment_data/{experiment_id}/song_heart_rate'):
            os.makedirs(f'./experiment_data/{experiment_id}/song_heart_rate')

        # Save the heaert rate intervals
        with open(f'./experiment_data/{experiment_id}/song_heart_rate/{i}.json', 'w') as f:
            json.dump(song_heart_rate, f)

        print("Songs saved.")
        if not np.isnan(metrics_pre["mean"]) and not np.isnan(metrics_post["mean"]):
            pre_lf_hf_ratio = metrics_pre["lf_power"] / metrics_pre["hf_power"]
            post_lf_hf_ratio = metrics_post["lf_power"] / metrics_post["hf_power"]

            print("LF/HF ratio before song: ", pre_lf_hf_ratio)
            print("LF/HF ratio after song: ", post_lf_hf_ratio)
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

    with open(f'./experiment_data/{experiment_id}/experiment_rr_intervals.json', 'w') as f:
        json.dump(experiment_rr_intervals, f)

    with open(f'./experiment_data/{experiment_id}/experiment_heart_rate.json', 'w') as f:
        json.dump(experiment_heart_rate, f)

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