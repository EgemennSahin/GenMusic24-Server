import torch
from transformers import MusicgenForConditionalGeneration, AutoProcessor
import scipy

print(torch.__version__)
print(torch.version.cuda)

device = "cuda:0" if torch.cuda.is_available() else "cpu"
print("Device: ", device)

model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
model.to(device)

processor = AutoProcessor.from_pretrained("facebook/musicgen-small")

text = "Drum and bass epic dramatic song futuristic with parts of 90's style"

inputs = processor(
    text=text,
    padding=True,
    return_tensors="pt",
)
inputs = {k: v.to(device) for k, v in inputs.items()}

audio_values = model.generate(**inputs, do_sample=True, guidance_scale=1, max_new_tokens=1536)

sampling_rate = model.config.audio_encoder.sampling_rate

audio_name = "musicgen_outputs/" + text.replace('/', '-') + ".wav"

scipy.io.wavfile.write(audio_name, rate=sampling_rate, data=audio_values[0, 0].cpu().numpy())