from flask import Flask, render_template, request, redirect, url_for
import os
import base64
import sys
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_handler import get_all_persons, delete_person, clear_table, remove_face_by_id, update_person_name, get_person_by_id, get_persons_classificaiton_confidence_threshold, update_person_classificaiton_confidence_threshold, init_database as db_init

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),  # Set template folder
)

@app.route('/')
def index():
    # Get all persons from the database
    persons = get_all_persons(only_unknowns=False)
    print(f"{len(persons)} persons found")
    
    # Debug: Print persons and their thresholds
    for person in persons:
        person['classification_confidence_threshold'] = get_persons_classificaiton_confidence_threshold(person['global_id'])
        print(f"Person ID: {person['global_id']}, Threshold: {person['classification_confidence_threshold']}")
    
    # Sort the persons list by global_id to maintain consistent order
    persons = sorted(persons, key=lambda x: x['global_id'])
    
    return render_template('index.html', persons=persons, encode_image=encode_image)

@app.route('/delete_image', methods=['POST'])
def delete_image():
    # Handle deleting an image
    global_id = request.form['global_id']
    face_id = request.form['face_id']
    
    try:
        # Remove the face by ID
        remove_face_by_id(global_id, face_id)
        
        try:
            # After removing the face, check if the person still exists/has faces
            person = get_person_by_id(global_id)
            if not person['faces_json']:  # Check if faces list is empty
                # Only delete the person if they have no faces left
                delete_person(global_id)
                print(f"Deleted person {global_id} because they have no more images")
        except IndexError:
            # Person was already deleted by remove_face_by_id
            print(f"Person {global_id} was already removed from database")
    except Exception as e:
        print(f"Error during image deletion: {e}")
    
    return redirect(url_for('index'))

@app.route('/update_person_name', methods=['POST'])
def update_person_name_route():
    # Handle updating a person's name
    global_id = request.form['global_id']
    new_name = request.form['new_name']
    update_person_name(global_id, new_name)
    return redirect(url_for('index'))

@app.route('/update_person_threshold', methods=['POST'])
def update_person_threshold():
    # Handle updating a person's classification confidence threshold
    global_id = request.form['global_id']
    new_threshold = request.form['new_threshold']
    try:
        new_threshold = float(new_threshold)
        update_person_classificaiton_confidence_threshold(global_id, new_threshold)
        print(f"Updated threshold for Person ID {global_id} to {new_threshold}")
    except ValueError:
        print("Invalid threshold value")
    return redirect(url_for('index'))

def encode_image(image_path):
    print(f"Encoding image: {image_path}")
    # Encode image as base64 for rendering in HTML
    try:
        if not image_path:
            raise ValueError("Invalid image path")
        
        full_path = os.path.join(os.path.dirname(__file__), "..", "resources", "faces", image_path)
        with open(full_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return ""  # Return an empty string if encoding fails

if __name__ == '__main__':
    # Initialize the database
    db, tbl_persons = db_init()
    app.run(debug=True, port=5002)