import csv
import os
import json

def process_csv(input_csv_path, output_csv_path, output_geojson_path):
    last_rows = {}

    # Read the input CSV file and store the last row for each id
    with open(input_csv_path, 'r') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            last_rows[row['id']] = row

    # Write the last rows to the output CSV file
    with open(output_csv_path, 'w', newline='') as outfile:
        fieldnames = ['id', 'latitude', 'longitude', 'altitude']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in last_rows.values():
            writer.writerow(row)

    # Write the last rows to the GeoJSON file
    features = []
    for row in last_rows.values():
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row['longitude']), float(row['latitude']), float(row['altitude'])]
            },
            "properties": {
                "id": row['id']
            }
        }
        features.append(feature)

    geojson_data = {
        "type": "FeatureCollection",
        "features": features
    }

    with open(output_geojson_path, 'w') as geojson_file:
        json.dump(geojson_data, geojson_file, indent=4)

if __name__ == "__main__":
    input_csv_path = os.path.join(os.path.dirname(__file__), 'tsr_mapping.csv')
    output_csv_path = os.path.join(os.path.dirname(__file__), 'tsr_mapping_processed.csv')
    output_geojson_path = os.path.join(os.path.dirname(__file__), 'tsr_mapping.geojson')
    process_csv(input_csv_path, output_csv_path, output_geojson_path)
    print(f"Processed CSV file saved to {output_csv_path}")
    print(f"GeoJSON file saved to {output_geojson_path}")
