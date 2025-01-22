import os
import json
import re
from logger_config import logger

def get_named_direction(direction):
    """
    Get the named direction from a given angle.
    Args:
        direction (int): The angle in degrees.
    Returns:
        str: The named direction.
    """
    if direction >= 10 and direction < 70:
        return "OUT"
    if direction >= 190 and direction < 260:
        return "BACK"
    return "OTHER"

def relabel(filename):
    """
    Relabel the JSON file based on some criteria.
    Args:
        filename (str): The path to the JSON file.
    """
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
        
        data["named_direction"] = get_named_direction(data["direction"])
        
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)
        
        logger.info(f"Relabeled file: {filename}")
    except Exception as e:
        logger.error(f"Failed to relabel file {filename}: {e}")

def relabel_all(directory):
    """
    Go through all JSON files in the directory and call relabel(filename) for each file.
    Args:
        directory (str): The path to the directory.
    """
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.json'):
                filepath = os.path.join(root, file)
                relabel(filepath)

if __name__ == "__main__":
    base_directory = "output/"  # Replace with the actual base directory path
    date_pattern = re.compile(r'^\d{4}\d{2}\d{2}$')  # Pattern to match date folders (YYYY-MM-DD)

    for folder in os.listdir(base_directory):
        folder_path = os.path.join(base_directory, folder)
        if os.path.isdir(folder_path) and date_pattern.match(folder):
            relabel_all(folder_path)
