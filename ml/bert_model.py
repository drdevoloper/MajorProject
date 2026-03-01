from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np


class FinBERT:

    def __init__(self):

        self.tokenizer = AutoTokenizer.from_pretrained(
            "ProsusAI/finbert"
        )

        self.model = AutoModelForSequenceClassification.from_pretrained(
            "ProsusAI/finbert"
        )

        self.model.eval()

    def sentiment(self, text):

        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True
        )

        with torch.no_grad():
            outputs = self.model(**inputs)

        probs = torch.nn.functional.softmax(outputs.logits, dim=1)

        return probs.numpy()[0]