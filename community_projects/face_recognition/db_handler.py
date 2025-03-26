import os
import json
from typing import Dict, Any, List, Tuple
import uuid
import numpy as np
from lancedb.pydantic import Vector, LanceModel
import lancedb
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
from matplotlib.patches import Ellipse
from matplotlib.offsetbox import OffsetImage, AnnotationBbox

DISTANCE_THRESHOLD = 0.7

# Define the LanceModel schema for the persons table
class PersonRecord(LanceModel):
    global_id: str = None  # unique id
    name: str = 'Unknown'  # unique (but same IRL person might have multiple e.g., "Bob", "Bob glasses" etc.) with default "None" value
    avg_embedding: Vector(512) # type: ignore the warning
    classificaiton_confidence_threshold: float = 1 - DISTANCE_THRESHOLD  # initial default value
    last_image_recieved_time: int = None  # epoch timestamp: In case the last image removed - not maintend to previous image time...
    faces_json: str = "[]"  # Store faces as a JSON string  # [{"embedding", "image", "id"}]

    @property
    def faces(self) -> List[Dict[str, Any]]:
        return json.loads(self.faces_json)
    
    @faces.setter
    def faces(self, value: List[Dict[str, Any]]):
        self.faces_json = json.dumps(value)

# Initialize the LanceDB database
def init_database():
    current_dir = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the current file
    resources_dir = os.path.join(current_dir, 'resources', 'database')
    os.makedirs(resources_dir, exist_ok=True)  # Create the directory if it doesn't exist
    db = lancedb.connect(uri=os.path.join(resources_dir, 'persons.db'))  # Connect to the database

    # Check if the table exists, if not create it and add indexes
    try:
        tbl_persons = db.open_table('persons')
    except:
        tbl_persons = db.create_table('persons', schema=PersonRecord)
        tbl_persons.create_scalar_index('global_id', index_type='BTREE')  # https://lancedb.github.io/lancedb/guides/scalar_index/#create-a-scalar-index
        tbl_persons.create_scalar_index('name', index_type='BTREE')
    return db, tbl_persons

db, tbl_persons = init_database() 

def create_person(embedding: np.ndarray, image: str, timestamp: int, name: str = 'Unknown') -> Dict[str, Any]:
    """
    Creates a person in the LanceDB table and generates a global ID.

    Args:
        embedding (np.ndarray) (required): The (first) face embedding vector.
        name (str) (optional): The name associated with the person.
        image (str) (required): The face image path.
        timestamp (int) (required): The timestamp of the image.

    Returns:
        record: The newly created person record as dict.

    Note: image file path id != iamge id

    In case after this insertion there are more than 256 records in the table, the table will be indexed by the embedding column.
    """
    record = PersonRecord(global_id=str(uuid.uuid4()),
                          name=name, 
                          avg_embedding=embedding.tolist(),
                          last_image_recieved_time=timestamp, 
                          faces_json = json.dumps([{"embedding": embedding.tolist(), 
                                                    "image": image, 
                                                    "id": str(uuid.uuid4())}]))
    tbl_persons.add([record])
    if len(tbl_persons.search().to_list()) > 256:
        tbl_persons.create_index(vector_column_name='embedding', metric="cosine", replace=True)
    return record.model_dump()

def insert_new_face(person: Dict[str, Any], embedding: np.ndarray, image: str, timestamp: int) -> None:
    """
    Adds a new face to a person, creates for the face id and recalculates the average embedding.

    Args:
        person (Dict[str, Any]): The person record to insert the face into.
        embedding (np.ndarray): The face embedding vector.
        image (str): The face image path.
        timestamp (int): The timestamp of the image.
    """
    faces = person['faces_json']
    faces.append({"embedding": embedding.tolist(), "image": image, "id": str(uuid.uuid4())})
    all_embeddings = [np.array(face["embedding"]) for face in faces]  # Recalculate the average embedding
    avg_embedding = np.mean(all_embeddings, axis=0)
    tbl_persons.update(where=f"global_id = '{person['global_id']}'", values={
        'avg_embedding': avg_embedding, 
        'faces_json': json.dumps(faces),
        'last_image_recieved_time': timestamp
    })

def remove_face_by_id(global_id: str, face_id: str) -> bool:
    """
    Removes a face from a person & recalculates the average embedding.

    Args:
        global_id (str): The global ID of the person to remove from.
        face_id (str): The ID of the face to remove.

    Returns:
        bool: True if the person was removed, False otherwise.
    """
    person = tbl_persons.search().where(f"global_id = '{global_id}'").to_list()[0]
    faces = json.loads(person['faces_json'])
    face_to_delete = [face for face in faces if face['id'] == face_id][0]
    delete_face_image(face_to_delete)
    new_faces = [face for face in faces if face['id'] != face_id]
    if not new_faces:  # If there are no more faces, remove the person from the database
        tbl_persons.delete(where=f"global_id = '{global_id}'")
        return True
    else:  # Update the person's record with the new list of faces and the recalculated average embedding
        tbl_persons.update(where=f"global_id = '{global_id}'", values={
            'avg_embedding': np.mean([np.array(face['embedding']) for face in new_faces], axis=0).tolist(), 
            'faces_json': json.dumps(new_faces)
        })
        return False

def search_person(embedding: np.ndarray, top_k: int = 1, metric_type: str = 'cosine') -> Dict[str, Any]:
    """
    Searches for a person in the LanceDB table by embedding vector similarity.

    Args:
        embedding (np.ndarray): The face embedding vector to search for.
        top_k (int): The number of top results to return.
        metric_type (str): The similarity metric to use (e.g., "cosine").

    Returns:
        Dict[str, Any]: The search result with classification confidence.
    """
    search_result = (
        tbl_persons.search(
            embedding.tolist(),
            vector_column_name='avg_embedding'
        )
        .metric(metric_type)
        .limit(top_k)
        .to_list()
    )
    if search_result:
        search_result[0]['faces_json'] = json.loads(search_result[0]['faces_json'])
        return search_result[0]
    return None

def update_person_name(global_id: str, name: str = 'Unknown') -> None:
    """
    Updates the name associated with a person in the LanceDB table.

    Args:
        global_id (str): The global ID of the person to update.
        name (str): The new name to associate with the person.
    """
    tbl_persons.update(where=f"global_id = '{global_id}'", values={'name': name})

def update_person_classificaiton_confidence_threshold(global_id: str, classificaiton_confidence_threshold: float) -> None:
    """
    Updates the classificaiton confidence threshold associated with a person in the LanceDB table.

    Args:
        global_id (str): The global ID of the person to update.
        classificaiton_confidence_threshold (str): The new classificaiton confidence threshold to associate with the person.
    """
    tbl_persons.update(where=f"global_id = '{global_id}'", values={'classificaiton_confidence_threshold': classificaiton_confidence_threshold})

def delete_person(global_id: str) -> None:
    """
    Deletes a person from the LanceDB table.

    Args:
        global_id (str): The global ID of the person to delete.
    """
    person = get_person_by_id(global_id)
    for face in person['faces_json']:
        delete_face_image(face)
    tbl_persons.delete('global_id = "' + global_id + '"')

def clear_table() -> None:
    """
    Deletes all records from the LanceDB table.
    """
    to_delete = ', '.join([f"'{record['global_id']}'" for record in tbl_persons.search().to_list()])  # Get all records
    tbl_persons.delete(f"global_id IN ({to_delete})")
    # Clear all files from the 'resources/faces' folder
    faces_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'faces')
    if os.path.exists(faces_dir):
        for filename in os.listdir(faces_dir):
            file_path = os.path.join(faces_dir, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)

def get_all_persons(only_unknowns=False) -> Dict[str, Any]:
    """
    Gets all persons from the LanceDB table.

    Args:
        only_unknowns (bool): If True, return only persons with the name 'Unknown'.

    Returns:
        List[Dict[str, Any]]: All the persons.
    """
    if only_unknowns:
        persons = tbl_persons.search().where("name = 'Unknown'").to_list()
    else:
        persons = tbl_persons.search().to_list()
    
    for person in persons:
        person['faces_json'] = json.loads(person['faces_json'])
    return persons

def get_person_by_id(global_id: str) -> Dict[str, Any]:
    """
    Gets a person record from the LanceDB table by global ID.

    Args:
        global_id (str): The global ID of the person to retrieve.

    Returns:
        Dict[str, Any]: The person record.
    """
    result = tbl_persons.search().where(f"global_id = '{global_id}'").to_list()[0]
    if result:
        result['faces_json'] = json.loads(result['faces_json'])
        return result
    return None

def get_person_by_name(name: str = "Unknown") -> Dict[str, Any]:
    """
    Gets a person record from the LanceDB table by name.

    Args:
        name (str): The name of the person to retrieve.

    Returns:
        Dict[str, Any]: The person record.
    """
    result = tbl_persons.search().where(f"name = '{name}'").to_list()[0]
    if result:
        result['faces_json'] = json.loads(result['faces_json'])
        return result
    return None

def get_persons_num_faces(global_id: str) -> int:
    """
    Gets the number of faces associated with a person.

    Args:
        global_id (str): The global ID of the person to retrieve.

    Returns:
        int: The number of faces.
    """
    return len(get_person_by_id(global_id)['faces_json'])
    #return len(json.loads(get_person_by_id(global_id)['faces_json']))

def get_persons_last_image_recieved_time(global_id: str) -> int:
    """
    Gets the last image recieved time associated with a person.

    Args:
        global_id (str): The global ID of the person to retrieve.

    Returns:
        int: The last image recieved time.
    """
    return get_person_by_id(global_id)['last_image_recieved_time']

def delete_face_image(face: Tuple[str, str, str]):
    """
    Deletes the face image file.

    Args:
        face (Dict[str, Any]): The face record containing the image file path.
    """
    image_path = face['image']
    if image_path and os.path.exists(image_path):
        os.remove(image_path)

def calibrate_classification_confidence_threshold():
    """
    Calibrates the classification confidence threshold based on confidence circles area.
    Smaller areas result in a smaller classification confidence threshold.
    """
    records = tbl_persons.search().to_list()
    areas = []

    for record in records:
        # Get embeddings for the person
        faces = json.loads(record['faces_json'])
        embeddings = [np.array(face['embedding']) for face in faces]

        if len(embeddings) < 2:
            # Skip calibration if there are not enough embeddings to calculate variance
            areas.append(0)
            continue

        # Perform PCA to reduce embeddings to 2D
        pca = PCA(n_components=2)
        reduced_embeddings = pca.fit_transform(embeddings)

        # Calculate standard deviations (semi-major and semi-minor axes)
        std_dev = np.std(reduced_embeddings, axis=0)
        semi_major_axis, semi_minor_axis = std_dev[0], std_dev[1]

        # Calculate the area of the confidence circle (ellipse)
        area = np.pi * semi_major_axis * semi_minor_axis
        areas.append(area)

    # Normalize areas for threshold calibration
    areas = np.array(areas)
    if len(areas) > 0 and np.max(areas) != np.min(areas):  # Avoid division by zero
        norm_areas = (areas - np.min(areas)) / (np.max(areas) - np.min(areas))
    else:
        norm_areas = np.zeros_like(areas)

    for i, record in enumerate(records):
        # Calculate the new threshold based on normalized area
        new_threshold = 1 - norm_areas[i] * DISTANCE_THRESHOLD
        update_person_classificaiton_confidence_threshold(record['global_id'], new_threshold)

def visualize_persons():
    """
    Creates a 2D visualization of persons with their embeddings, confidence circles, and their first picture near the point.
    """
    persons = tbl_persons.search().to_list()
    # Extract all embeddings and perform PCA for dimensionality reduction
    all_embeddings = []
    person_data = {}
    for person in persons:
        faces = json.loads(person['faces_json'])
        embeddings = [np.array(face['embedding']) for face in faces]
        all_embeddings.extend(embeddings)
        person_data[person['global_id']] = {
            'name': person['name'],
            'avg_embedding': np.array(person['avg_embedding']),
            'embeddings': embeddings,
            'image': faces[0]['image'] if faces else None
        }
    
    if not all_embeddings:
        print("No embeddings found.")
        return
    
    # Perform PCA to reduce embeddings to 2D
    pca = PCA(n_components=2)
    reduced_embeddings = pca.fit_transform(all_embeddings)
    
    # Create a mapping from original embeddings to reduced embeddings
    embedding_map = {tuple(embedding): reduced for embedding, reduced in zip(all_embeddings, reduced_embeddings)}
    
    # Create a 2D scatter plot
    fig, ax = plt.subplots(figsize=(10, 8))
    colors = ['blue', 'green', 'red', 'purple', 'orange', 'brown', 'pink', 'gray', 'cyan', 'magenta']
    
    for idx, (person_id, data) in enumerate(person_data.items()):
        avg_embedding = data['avg_embedding']
        reduced_avg_embedding = pca.transform([avg_embedding])[0]
        
        # Calculate the standard deviation for the confidence circle
        reduced_person_embeddings = np.array([embedding_map[tuple(embedding)] for embedding in data['embeddings']])
        std_dev = np.std(reduced_person_embeddings, axis=0)
        
        # Add the confidence circle
        ellipse = Ellipse(
            xy=reduced_avg_embedding,
            width=2 * std_dev[0],  # 2 standard deviations
            height=2 * std_dev[1],
            edgecolor=colors[idx % len(colors)],
            facecolor=colors[idx % len(colors)],
            alpha=0.2
        )
        ax.add_patch(ellipse)
        
        # Add the average embedding point
        ax.scatter(
            reduced_avg_embedding[0], reduced_avg_embedding[1],
            color=colors[idx % len(colors)], label=data['name'], s=100, edgecolor='black'
        )
        
        # Add the image near the point
        if data['image']:
            image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'faces', data['image'])
            if os.path.exists(image_path):
                # Open the image
                img = Image.open(image_path)
                img.thumbnail((50, 50))  # Resize the image to a small thumbnail

                # Create a circular mask
                mask = Image.new("L", img.size, 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0, img.size[0], img.size[1]), fill=255)
                img = Image.composite(img, Image.new("RGBA", img.size, (255, 255, 255, 0)), mask)

                # Offset the image to the side of the ellipse
                offset = 0.1  # Adjust this value to control the distance from the point
                image_position = (reduced_avg_embedding[0] + offset, reduced_avg_embedding[1] + offset)

                # Add the circular image to the plot
                imagebox = OffsetImage(img, zoom=0.5)
                ab = AnnotationBbox(imagebox, image_position, frameon=False)
                ax.add_artist(ab)

    # Add labels and legend
    ax.set_title("2D Visualization of Persons with Confidence Circles", fontsize=16)
    ax.set_xlabel("PCA Component 1", fontsize=12)
    ax.set_ylabel("PCA Component 2", fontsize=12)

    # Place the legend outside the main plotting area
    ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1), fontsize=10)

    plt.grid(True)
    plt.tight_layout()

    # Show the plot
    plt.show()

def main():
    visualize_persons()

if __name__ == "__main__":
    main()