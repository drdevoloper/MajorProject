from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np

# ---------------------------
# DEVICE SETUP
# ---------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("BERT using device:", device)


class FinBERT:

    def __init__(self):

        self.tokenizer = AutoTokenizer.from_pretrained(
            "ProsusAI/finbert"
        )

        self.model = AutoModelForSequenceClassification.from_pretrained(
            "ProsusAI/finbert"
        )

        self.model.to(device)   # 🔥 Move model to GPU
        self.model.eval()

    # ---------------------------
    # SENTIMENT FUNCTION
    # ---------------------------
    def sentiment(self, text):

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True
        )

        # Move inputs to GPU
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            with torch.cuda.amp.autocast():
                outputs = self.model(**inputs)

        probs = torch.nn.functional.softmax(
            outputs.logits,
            dim=1
        )

        return probs.cpu().numpy()[0]