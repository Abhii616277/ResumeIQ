from transformers import AutoTokenizer, AutoModelForCausalLM

model_id = "microsoft/Phi-3-mini-4k-instruct"

tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=False)

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    device_map="auto"
)