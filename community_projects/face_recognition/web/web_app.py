from flask import Flask, render_template, request, redirect, url_for
import os
import base64
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db_handler import get_all_persons, delete_person, clear_table, remove_face_by_id, update_person_name, get_person_by_id, init_database as db_init

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
    return render_template('index.html', persons=persons, encode_image=encode_image)

@app.route('/update_person', methods=['POST'])
def update_person():
    # Handle updating or deleting a person
    global_id = request.form['global_id']
    face_id = request.form['face_id']
    action = request.form['action']
    if action.lower() == 'delete':
        if not remove_face_by_id(global_id, face_id):
            message = f"Image {face_id} deleted."
        else:
            message = f"This was the last image of this person - person removed from DB."
    else:
        update_person_name(global_id, action)
        message = f"Person name updated to {action}."
    return redirect(url_for('index'))

def encode_image(image_path):
    # Encode image as base64 for rendering in HTML
    try:
        full_path = os.path.join(os.path.dirname(__file__), "..", "resources", "faces", image_path)
        with open(full_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return ""

if __name__ == '__main__':
    # Initialize the database
    db, tbl_persons = db_init()
    app.run(debug=True, port=5001)