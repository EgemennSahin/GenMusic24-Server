from audiocraft.data.audio import audio_write
from audiocraft.models import MusicGen
from transformers import pipeline


def get_opposite_effect_description(current_effect, rmssd, sdnn, pnn50):
    # Initialize the GPT-2 model
    gpt_model = pipeline('text-generation', model='gpt2')

    # Use the GPT-2 model to generate the opposite effect description
    prompt = f"Given that the current music effect is {current_effect} and the HRV metrics are RMSSD: {rmssd}, SDNN: {sdnn}, PNN50: {pnn50}, the opposite music effect should be"
    generated_text = gpt_model(prompt, max_length=100)[0]['generated_text']
    
    # Extract the opposite effect description from the generated text
    opposite_effect = generated_text.split("be")[1].strip()

    return opposite_effect

def generate_music(description, rmssd, sdnn, pnn50):
    # Initialize the MusicGen model
    musicgen_model = MusicGen.get_pretrained("small")
    musicgen_model.set_generation_params(duration=15)  # generate 15 seconds.

    opposite_description = get_opposite_effect_description(description, rmssd, sdnn, pnn50)
    wav = musicgen_model.generate([opposite_description])  # Generate a sample with the opposite effect

    for idx, one_wav in enumerate(wav):
        # Will save under {idx}.wav, with loudness normalization at -14 db LUFS.
        audio_write(f'{idx}', one_wav.cpu(), musicgen_model.sample_rate, strategy="loudness")

    return wav, musicgen_model.sample_rate