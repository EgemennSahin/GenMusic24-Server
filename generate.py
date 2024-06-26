from audiocraft.models import MusicGen

print("Loading MusicGen model...")
musicgen_model = MusicGen.get_pretrained("facebook/musicgen-small")

print("Setting generation parameters...")
musicgen_model.set_generation_params(duration=15)  # generate 15 seconds.

def generate_music(description):
    song = musicgen_model.generate([description])
    return song.cpu(), musicgen_model.sample_rate

def generate_conditional_music(song_prompt, sample_rate, description):
    overlap = 5
    last_sec = song_prompt[:, :, -overlap*sample_rate:]
    song = musicgen_model.generate_continuation(prompt=last_sec, prompt_sample_rate=sample_rate, descriptions=[description])
    song = song[:, :, overlap*sample_rate:]
    return song.cpu(), musicgen_model.sample_rate
