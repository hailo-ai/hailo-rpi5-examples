import lancedb
from db_handler import PersonRecord
import numpy as np
import json
import os
from datetime import datetime
import fiftyone as fo
import fiftyone.brain as fob
from fiftyone import ViewField as F
import subprocess
import shutil

def reset_fiftyone_db():
    """Reset the FiftyOne MongoDB database"""
    print("Attempting to reset FiftyOne database...")
    
    # Stop any running MongoDB instances
    try:
        subprocess.run(["pkill", "-f", "mongod"], check=False)
        print("Stopped any running MongoDB processes")
    except Exception as e:
        print(f"Warning: Could not stop MongoDB processes: {e}")
    
    # Check if the directory exists before trying to remove it
    mongo_dir = os.path.expanduser("~/.fiftyone/var/lib/mongo")
    if os.path.exists(mongo_dir):
        try:
            # Move the existing directory to a backup instead of deleting
            backup_dir = f"{mongo_dir}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.move(mongo_dir, backup_dir)
            print(f"Backed up MongoDB data to: {backup_dir}")
        except Exception as e:
            print(f"Warning: Could not back up MongoDB data: {e}")
    
    # Try a different visualization method
    print("Will use a simpler visualization approach that doesn't require MongoDB")
    
    return True

def visualize_face_embeddings(db_uri="/home/hailo/hailo-rpi5-examples/community_projects/face_recognition/resources/database/persons.db", table_name="persons"):
    """
    Visualize face embeddings from LanceDB using Voxel51's fiftyone.
    
    Args:
        db_uri: LanceDB database URI
        table_name: Name of the table containing PersonRecord instances
    """
    # Connect to LanceDB
    db = lancedb.connect(db_uri)
    table = db.open_table(table_name)
    
    # Query all records
    records = table.to_pandas()
    
    # Create a FiftyOne dataset
    dataset_name = f"face_embeddings_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    dataset = fo.Dataset(dataset_name)
    
    # Create dummy directory for placeholder files
    dummy_dir = "/tmp/dummy_face_images"
    os.makedirs(dummy_dir, exist_ok=True)
    
    # Add samples to dataset with embeddings
    for idx, record in records.iterrows():
        # Parse faces_json to get face images
        faces = json.loads(record['faces_json']) if record['faces_json'] else []
        
        # Safely handle tags - ensure they're strings
        tag_value = str(record['name']) if record['name'] is not None else "Unknown"
        
        # If there are face images, use them; otherwise, create dummy files
        if faces and len(faces) > 0:
            # Process each face for this person
            for face_idx, face in enumerate(faces):
                if "image" in face:
                    # Create a directory for this person
                    person_dir = os.path.join(dummy_dir, str(record['global_id']))
                    os.makedirs(person_dir, exist_ok=True)
                    
                    # Save the image from base64 string to file
                    image_path = os.path.join(person_dir, f"face_{face_idx}.jpg")
                    
                    # Check if image is base64 encoded
                    if isinstance(face["image"], str) and face["image"].startswith(("data:image", "base64")):
                        # Extract base64 data
                        import base64
                        if "base64," in face["image"]:
                            image_data = face["image"].split("base64,")[1]
                        else:
                            image_data = face["image"]
                        
                        # Write image file
                        with open(image_path, "wb") as f:
                            f.write(base64.b64decode(image_data))
                    else:
                        # If not base64, treat as a file path and copy the file
                        import shutil
                        try:
                            # Check if the path exists
                            if os.path.exists(face["image"]):
                                shutil.copy2(face["image"], image_path)
                            else:
                                # File doesn't exist, write the path as fallback
                                with open(image_path, "w") as f:
                                    f.write(str(face["image"]))
                        except (TypeError, ValueError):
                            # If there's any issue, write whatever we have
                            with open(image_path, "w") as f:
                                f.write(str(face["image"]))
                    
                    # Create sample with the actual face image
                    sample = fo.Sample(
                        filepath=image_path,
                        tags=[tag_value] if tag_value != "Unknown" else []
                    )
                    
                    # Add all person fields as metadata using safe access
                    sample["global_id"] = record['global_id']
                    sample["name"] = record['name']
                    
                    # Use the specific face embedding if available, otherwise fall back to average
                    if "embedding" in face and face["embedding"] is not None:
                        sample["embedding"] = np.array(face["embedding"])
                        sample["is_specific_embedding"] = True
                    else:
                        sample["embedding"] = np.array(record['avg_embedding']) 
                        sample["is_specific_embedding"] = False
                    
                    sample["confidence_threshold"] = record['classificaiton_confidence_threshold']
                    sample["last_image_time"] = record['last_image_recieved_time']
                    sample["face_id"] = face.get("id", f"face_{face_idx}")
                    
                    # Add to dataset
                    dataset.add_sample(sample)
        else:
            # Create a dummy filepath for cases with no face images
            dummy_filepath = os.path.join(dummy_dir, f"{idx}.jpg")
            
            # Create an empty file if it doesn't exist
            if not os.path.exists(dummy_filepath):
                with open(dummy_filepath, "w") as f:
                    pass
            
            sample = fo.Sample(
                filepath=dummy_filepath,
                tags=[tag_value] if tag_value != "Unknown" else []
            )
            
            # Add all person fields as metadata
            sample["global_id"] = record['global_id']
            sample["name"] = record['name']
            sample["embedding"] = np.array(record['avg_embedding'])
            sample["confidence_threshold"] = record['classificaiton_confidence_threshold']
            sample["last_image_time"] = record['last_image_recieved_time']
            
            # Add to dataset
            dataset.add_sample(sample)
    
    # Compute the embedding visualization with adjusted parameters
    # Get number of samples before visualization
    num_samples = len(dataset)
    print(f"Visualizing {num_samples} face embeddings")
    
    # For small datasets, always use PCA to avoid t-SNE issues
    if num_samples < 10:
        print(f"Dataset is small. Using PCA visualization.")
        results = fob.compute_visualization(
            dataset,
            embeddings="embedding",
            method="pca",  # Force PCA for small datasets
            brain_key="face_embeddings_viz",
            pca_dims=2  # Use 2D for visualization
        )
    else:
        # Only use t-SNE for larger datasets
        perplexity = min(num_samples // 3, 30)  # Very conservative perplexity
        print(f"Using t-SNE with perplexity={perplexity}")
        
        results = fob.compute_visualization(
            dataset,
            embeddings="embedding",
            method="tsne",
            brain_key="face_embeddings_viz",
            pca_dims=min(num_samples - 1, 10),
            tsne_perplexity=perplexity
        )
    
    # Launch the FiftyOne App to visualize
    try:
        session = fo.launch_app(dataset)
        print("\nFiftyOne App launched in your browser")
        print("\nYou can edit the following fields in the app:")
        print("1. Name (via adding/changing tags)")
        print("2. Confidence threshold (via metadata fields)")
        print("\nChanges will be saved back to the database when you close the app")
        
        # Wait for the user to finish
        session.wait()
    except Exception as e:
        print(f"Error launching FiftyOne: {e}")
        if reset_fiftyone_db():
            print("Skipping visualization. You can try again later after restarting your system.")
            # Provide an alternative simple visualization
            pass  # TODO
    
    # Save changes back to LanceDB
    save_fiftyone_changes_to_lancedb(dataset, db_uri, table_name)
    
    return dataset

def save_fiftyone_changes_to_lancedb(dataset, db_uri, table_name="persons"):
    """
    Save changes made in FiftyOne back to LanceDB, including handling deletions.
    
    Args:
        dataset: FiftyOne dataset with changes
        db_uri: LanceDB database URI
        table_name: Name of the table to update
    """
    print("Checking for changes in FiftyOne dataset...")
    
    # Connect to LanceDB
    db = lancedb.connect(db_uri)
    table = db.open_table(table_name)
    
    # Get current records from LanceDB
    original_records = table.to_pandas()
    
    # Track changes by global_id to ensure consistency
    name_changes = {}  # {global_id: set(new_names)}
    threshold_changes = {}  # {global_id: new_threshold}
    
    # Track which persons/faces still exist in FiftyOne
    existing_global_ids = set()
    existing_face_ids = set()
    
    # First pass: collect all changes and track existing IDs
    for sample in dataset:
        global_id = sample.get("global_id", None)
        face_id = sample.get("face_id", None)
        
        if global_id:
            existing_global_ids.add(global_id)
            
            if face_id:
                existing_face_ids.add(face_id)
            
            # Check for name changes (from tags or name field)
            if sample.tags and len(sample.tags) > 0:
                new_name = sample.tags[0]
                if new_name != sample.get("name", "Unknown"):
                    if global_id not in name_changes:
                        name_changes[global_id] = set()
                    name_changes[global_id].add(new_name)
            
            # Check for confidence threshold changes
            if "confidence_threshold" in sample and sample.has_field_changed("confidence_threshold"):
                threshold_changes[global_id] = sample["confidence_threshold"]
    
    # Resolve name conflicts
    for global_id, name_set in list(name_changes.items()):
        if len(name_set) > 1:
            print(f"\nCONFLICT: Person {global_id} has multiple different names: {', '.join(name_set)}")
            print("Please choose which name to use:")
            
            # Present options
            for i, name in enumerate(name_set):
                print(f"{i+1}. {name}")
            
            # Get user choice
            while True:
                try:
                    choice = int(input("Enter number of preferred name: "))
                    if 1 <= choice <= len(name_set):
                        chosen_name = list(name_set)[choice-1]
                        name_changes[global_id] = chosen_name
                        print(f"Selected '{chosen_name}' for person {global_id}")
                        break
                    else:
                        print("Invalid choice, please try again")
                except ValueError:
                    print("Please enter a number")
    
    # Apply changes to LanceDB
    changes_made = False
    
    # Apply name changes
    for global_id, new_name in name_changes.items():
        if isinstance(new_name, set):
            new_name = list(new_name)[0]  # Take first name if not resolved
        print(f"Updating name for person {global_id} to '{new_name}'")
        table.update().where(f"global_id = '{global_id}'").set("name", new_name).execute()
        changes_made = True
    
    # Apply threshold changes
    for global_id, new_threshold in threshold_changes.items():
        print(f"Updating confidence threshold for person {global_id} to {new_threshold}")
        table.update().where(f"global_id = '{global_id}'").set("classificaiton_confidence_threshold", new_threshold).execute()
        changes_made = True
    
    # Handle deletions
    # 1. Identify completely deleted persons
    deleted_persons = set()
    for record in original_records.itertuples():
        if record.global_id not in existing_global_ids:
            deleted_persons.add(record.global_id)
    
    # Delete persons that no longer exist
    if deleted_persons:
        for global_id in deleted_persons:
            print(f"Deleting person with ID {global_id} (all face images were removed)")
            table.delete().where(f"global_id = '{global_id}'").execute()
            changes_made = True
    
    # 2. Handle partial face deletions (for persons that still exist)
    # For each remaining person, update their faces_json to remove deleted faces
    for global_id in existing_global_ids:
        # Get the current record for this person
        person_record = original_records[original_records['global_id'] == global_id].iloc[0]
        
        # Parse faces_json
        faces = json.loads(person_record['faces_json']) if person_record['faces_json'] else []
        
        # Filter out deleted faces
        updated_faces = []
        for face in faces:
            if face.get("id") in existing_face_ids:
                updated_faces.append(face)
        
        # If faces changed, update the record
        if len(updated_faces) != len(faces):
            updated_faces_json = json.dumps(updated_faces)
            print(f"Updating faces for person {global_id}: removed {len(faces) - len(updated_faces)} faces")
            table.update().where(f"global_id = '{global_id}'").set("faces_json", updated_faces_json).execute()
            changes_made = True
            
            # If all faces removed but person record kept, consider updating other fields
            if not updated_faces:
                print(f"Warning: Person {global_id} has no remaining faces but was not deleted")
    
    if changes_made:
        print("All changes saved to LanceDB successfully!")
    else:
        print("No changes detected")

if __name__ == "__main__":
    visualize_face_embeddings()