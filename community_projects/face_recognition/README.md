# Face Recognition System

This project is a face recognition system built using Python, Flask, and LanceDB. It provides a web interface for managing face recognition data, including adding, updating, and deleting persons and their associated images. The system also supports real-time face recognition using GStreamer pipelines.

---

## Features

- **Web Interface**: Manage persons, images, and thresholds via a user-friendly web interface.
- **Real-Time Face Recognition**: Detect and recognize faces in real-time using GStreamer pipelines.
- **Database Management**: Store and manage face embeddings and metadata using LanceDB.
- **Telegram Notifications**: Send alerts for detected faces via Telegram.
- **Visualization**: Visualize embeddings and confidence circles in a 2D plot.

---

## Prerequisites

- Python 3.8+
- Pipenv or virtualenv for dependency management
- Required Python libraries (see `requirements.txt`)
- GStreamer installed on the system
- LanceDB installed for database management

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/face-recognition.git
   cd face-recognition
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install GStreamer:
   ```bash
   sudo apt-get install gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly
   ```

4. Set up the database:
   ```bash
   python -c "from db_handler import init_database; init_database()"
   ```

5. Download resources:
   ```bash
   chmod +x download_resources.sh
   ./download_resources.sh --all
   ```

---

## Usage

### Run the Web Application

1. Start the Flask web server:
   ```bash
   python web/web_app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5002
   ```

### Run the Face Recognition Pipeline

1. Start the GStreamer pipeline:
   ```bash
   python app_db.py
   ```

2. Choose the mode:
   - `run`: Real-time face recognition
   - `run-save`: Save new faces detected
   - `train`: Train the system with new images
   - `delete`: Clear the database

---

## Web Interface

### Features

- **View Persons**: Displays all persons in the database with their images and metadata.
- **Update Name**: Modify the name of a person.
- **Delete Image**: Remove a specific image associated with a person.
- **Update Threshold**: Adjust the classification confidence threshold for a person.
- **Delete Person**: Remove a person and all their associated data.

---

## Telegram Notifications

- Configure the `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` in `app_db.py` to enable Telegram notifications.
- Notifications are sent when a face is detected, with an image and confidence score.

---

## File Structure

```
face-recognition/
├── web/
│   ├── templates/
│   │   └── index.html       # Web interface template
│   ├── web_app.py           # Flask web application
├── resources/
│   ├── train/               # Training images
│   ├── faces/               # Detected face images
│   ├── database/            # LanceDB database
├── db_handler.py            # Database management
├── app_db.py                # GStreamer pipeline and Telegram integration
├── face_recognition_pipeline_db.py # GStreamer face recognition pipeline
├── download_resources.sh    # Script to download resources
└── README.md                # Documentation
```

---

## API Endpoints

### `GET /`
- **Description**: Displays the web interface.
- **Response**: HTML page with persons and their data.

### `POST /delete_image`
- **Description**: Deletes a specific image of a person.
- **Parameters**:
  - `global_id`: The person's global ID.
  - `face_id`: The ID of the face to delete.

### `POST /update_person_name`
- **Description**: Updates the name of a person.
- **Parameters**:
  - `global_id`: The person's global ID.
  - `new_name`: The new name.

### `POST /update_person_threshold`
- **Description**: Updates the classification confidence threshold for a person.
- **Parameters**:
  - `global_id`: The person's global ID.
  - `new_threshold`: The new threshold value.

---

## Troubleshooting

- **Database Issues**: Ensure the database is initialized using `init_database()`.
- **GStreamer Errors**: Verify GStreamer is installed and configured correctly.
- **Telegram Notifications**: Check the `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` values.

---

## Acknowledgments

- [Flask](https://flask.palletsprojects.com/)
- [GStreamer](https://gstreamer.freedesktop.org/)
- [LanceDB](https://lancedb.github.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
```