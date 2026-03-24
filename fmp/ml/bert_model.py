import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("FinBERT using device:", device)


class FinBERT:

    def __init__(self):

        self.tokenizer = AutoTokenizer.from_pretrained(
            "ProsusAI/finbert",
            local_files_only=True
        )

        self.model = AutoModelForSequenceClassification.from_pretrained(
            "ProsusAI/finbert",
            local_files_only=True
        )

        self.model.to(device)
        self.model.eval()

    def sentiment(self, texts):

        # convert single string → list
        if isinstance(texts, str):
            texts = [texts]

        inputs = self.tokenizer(
            texts,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512
        )

        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)

        probs = torch.nn.functional.softmax(outputs.logits, dim=1)

        probs = probs.cpu().numpy()

        return probs

    def sentiment_score(self, texts):

        probs = self.sentiment(texts)

        # FinBERT label order: positive, negative, neutral
        positive = probs[:, 0]
        negative = probs[:, 1]

        score = positive - negative

        return score