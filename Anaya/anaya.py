import json

# Load configuration
with open("ananya_config.json", "r") as file:
    config = json.load(file)


def adjust_response(prompt, traits):
    tone = traits["tone"]
    humor = traits["humor"]
    return f"[{tone} | Humor: {humor}] {prompt}"


# from transformers import GPTNeoForCausalLM, GPT2Tokenizer
#
# model = GPTNeoForCausalLM.from_pretrained("EleutherAI/gpt-neo-1.3B")
# tokenizer = GPT2Tokenizer.from_pretrained("EleutherAI/gpt-neo-1.3B")
#
# prompt = (
#     "In a shocking finding, scientists discovered a herd of unicorns living in a remote, "
#     "previously unexplored valley, in the Andes Mountains. Even more surprising to the "
#     "researchers was the fact that the unicorns spoke perfect English."
# )
#
# input_ids = tokenizer(prompt, return_tensors="pt").input_ids
#
# gen_tokens = model.generate(
#     input_ids,
#     do_sample=True,
#     temperature=0.9,
#     max_length=100,
# )
# gen_text = tokenizer.batch_decode(gen_tokens)[0]

from transformers import GPTNeoXForCausalLM

model = GPTNeoXForCausalLM.from_pretrained("EleutherAI/gpt-neox-20b")
# This is generally not necessary, as the model is automatically unloaded when the variable goes out of scope

del model
