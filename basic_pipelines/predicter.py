import pandas as pd
import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
import os
from datetime import datetime
import random

class Predictor:

    def __init__(self, model_filename='default.mdl'):
        self.model = self._create_model()
        self.model_filename = model_filename
        self.label_encoder = LabelEncoder()
        self.scaler = StandardScaler()
        self.load_model()

    def _create_model(self):
        # Initialize the model
        return SGDClassifier(loss='log_loss')

    def train(self, directory):
        records = []
        labels = []
        for filename in os.listdir(directory):
            if filename.endswith(".jpg"):
                try:
                    # Extract record information from the filename
                    parts = filename.split('_')
                    if len(parts) == 4:
                        date_str, time_str, milli_str, class_str = parts
                        date_obj = datetime.strptime(date_str, "%Y%m%d")
                        day_of_week = date_obj.weekday()  # Monday is 0 and Sunday is 6
                        hour = int(time_str[:2])
                        minute = int(time_str[2:4])
                        time_of_day = hour * 60 + minute
                        classname, counts = class_str.split('x')
                        maxcount, avgcount = counts.split('(')
                        avgcount, ext = avgcount.split(')')
                        direction = 90
                        record = [day_of_week, time_of_day, int(maxcount), float(avgcount), int(direction)]
                        label = classname
                        records.append(record)
                        labels.append(label)
                        print(f"Added file: {filename} ({record}, {label})")
                    else:
                        pass
                        # print(f"Ignored file: {filename} (incorrect format)")
                except Exception as e:
                    pass
                    # print(f"Error parsing file: {filename} ({e}), file ignored")
        
        # Encode labels
        encoded_labels = self.label_encoder.fit_transform(labels)
        
        # Convert records to DataFrame for easier manipulation
        df = pd.DataFrame(records, columns=['day_of_week', 'time_of_day', 'maxcount', 'avgcount', 'direction'])
        
        # Scale the features
        scaled_features = self.scaler.fit_transform(df)
        
        # Train the model
        self.model.partial_fit(scaled_features, encoded_labels, classes=np.unique(encoded_labels))
        
        # Save the model
        self.save_model()

    def predict(self, record, label):
        # Convert record to DataFrame
        df = pd.DataFrame([record], columns=['day_of_week', 'time_of_day', 'maxcount', 'avgcount', 'direction'])
        
        # Scale the features
        scaled_features = self.scaler.transform(df)
        
        # Encode the label
        encoded_label = self.label_encoder.transform([label])[0]
        
        # Predict the probability
        probabilities = self.model.predict_proba(scaled_features)
        label_index = np.where(self.model.classes_ == encoded_label)[0][0]
        probability = probabilities[0][label_index]
        
        return probability

    def save_model(self):
        # Save the model, scaler, and label encoder to disk
        joblib.dump((self.model, self.scaler, self.label_encoder), self.model_filename)

    def load_model(self):
        # Load the model, scaler, and label encoder from disk if the file exists
        try:
            self.model, self.scaler, self.label_encoder = joblib.load(self.model_filename)
        except FileNotFoundError:
            pass

if __name__ == "__main__":
    # Create an instance of the Predictor class
    predictor = Predictor()

    # Train the model with data from a directory
    predictor.train('images/dog')

    # Example record for prediction
    test_record = [2, 1145, 2, 1.18, 90]  # 0 is Monday, 870 minutes after midnight is 14:30
    label = 'dog'
    probability = predictor.predict(test_record, label)
    print(f"Probability of the record matching the label '{label}': {probability:.2f}")


