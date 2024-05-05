from audiocraft.models import MusicGen
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, AutoProcessor, MusicgenForConditionalGeneration
from audiocraft.data.audio import audio_write


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
        {"role": "system", "content": "Provide only the name of the emotion or music style that would be the opposite effect. Use very unique and specific words, and avoid general terms."},
        {"role": "user", "content": prompt},
    ]


    # Set generation arguments to limit the output
    generation_args = {
        "max_new_tokens": 30,  # reduced to focus on a brief answer
        "return_full_text": False,
        "do_sample": True,  # Use sampling to generate diverse outputs
        "temperature": 1.5,  # Increase the temperature for more diverse outputs
    }

    output = pipe(messages, **generation_args)[0]['generated_text']
    
    print("Generated text: ", output)
    
    llm_model.to('cpu')  # Move to CPU when not in use
    return output

def generate_music(description):
    wav = musicgen_model.generate([description])
    song = wav[0].cpu()[0].numpy()
    return song, musicgen_model.sample_rate
