from audiocraft.models import MusicGen
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


print("Loading AutoModelForCausalLM...")
llm_model = AutoModelForCausalLM.from_pretrained(
    "microsoft/Phi-3-mini-128k-instruct", 
    device_map="cuda", 
    torch_dtype="auto", 
    trust_remote_code=True, 
)
print("Model loaded successfully.")

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-128k-instruct")
print("Tokenizer loaded successfully.")

print("Initializing pipeline...")
pipe = pipeline(
    "text-generation",
    model=llm_model,
    tokenizer=tokenizer,
)
print("Pipeline ready.")

print("Loading MusicGen model...")
musicgen_model = MusicGen.get_pretrained("facebook/musicgen-small")
print("MusicGen model loaded.")

print("Setting generation parameters...")
musicgen_model.set_generation_params(duration=30)  # generate 15 seconds.
print("Generation parameters set.")




def get_opposite_effect_description(current_effect):
    llm_model.to('cuda')  # Move to GPU when needed

    # Define a concise prompt emphasizing direct response
    prompt = f"Describe the opposite emotional effect of a music style which had this effect'{current_effect}'. The aim is to create a music style that has the opposite effect on HRV. Focus only on naming the emotion or music style." 

    # Send the concise prompt to the model
    messages = [
        {"role": "system", "content": "Act like a professional in the music and hrv field. Please answer the following question with one or two words only:"},
        {"role": "user", "content": prompt},
    ]


    # Set generation arguments to limit the output
    generation_args = {
        "max_new_tokens": 500,  # reduced to focus on a brief answer
        "return_full_text": False,
        "do_sample": True,  # Use sampling to generate diverse outputs
        "temperature": 1.5,  # Increase the temperature for more diverse outputs
    }

    output = pipe(messages, **generation_args)[0]['generated_text']
    
    print("Generated text: ", output)
    
    llm_model.to('cpu')  # Move to CPU when not in use
    return output

def generate_music(description):
    song = musicgen_model.generate([description])
    return song.cpu(), musicgen_model.sample_rate

def generate_conditional_music(song_prompt, sample_rate, description):
    overlap = 5
    last_sec = song_prompt[:, :, -overlap*sample_rate:]
    song = musicgen_model.generate_continuation(prompt=last_sec, prompt_sample_rate=sample_rate, descriptions=[description])
    song = song[:, :, overlap*sample_rate:]
    return song.cpu(), musicgen_model.sample_rate