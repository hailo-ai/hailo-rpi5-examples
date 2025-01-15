import pandas as pd
import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler
import joblib

class Predictor:

    def __init__(self, model_filename='default.mdl'):
        self.model = self._create_model()
        self.model_filename = model_filename
        self.load_model()

    def _create_model(self):
        # Initialize the model
        self.scaler = StandardScaler()
        self.model = SGDClassifier(loss='log_loss')
        return self.model

    def learn(self, new_record, new_label):
        # Fit the scaler on the new record and transform it
        new_record = self.scaler.fit_transform([new_record])
        # Incrementally train the model
        self.model.partial_fit(new_record, [new_label], classes=np.unique([0, 1]))
        # Save the model after learning
        self.save_model()
  
    def predict_probability(self, new_record, label):
        # Transform the new record using the scaler
        new_record = self.scaler.transform([new_record])
        try:
            # Predict the probabilities
            probabilities = self.model.predict_proba(new_record)
            # Get the index of the label
            label_index = self.model.classes_.tolist().index(label)
            # Get the probability of the given label
            probability = probabilities[0][label_index]
        except NotImplementedError:
            raise ValueError("The model is not trained with a loss function that supports probability prediction.")
        return probability

    def save_model(self):
        # Save the model and scaler to disk
        joblib.dump((self.model, self.scaler), self.model_filename)

    def load_model(self):
        # Load the model and scaler from disk if the file exists
        try:
            self.model, self.scaler = joblib.load(self.model_filename)
        except FileNotFoundError:
            pass

if __name__ == "__main__":
    # Create an instance of the Predictor class
    predictor = Predictor()

    # Generate random data for testing
    np.random.seed(42)
    for _ in range(100):
        record = [
            np.random.randint(1, 8),  # daynum
            np.random.uniform(0, 24),  # time_of_day
            np.random.uniform(0, 360),  # direction
            np.random.uniform(0, 10),  # avg_instance_count
            np.random.uniform(0, 10)  # max_instance_count
        ]
        label = np.random.choice([0, 1])
        predictor.learn(record, label)

    # Example record for prediction
    test_record = [3, 12.5, 45.0, 3.2, 5]
    probability = predictor.predict_probability(test_record, 1)
    print(f"Probability of the record matching the label '1': {probability:.2f}")
