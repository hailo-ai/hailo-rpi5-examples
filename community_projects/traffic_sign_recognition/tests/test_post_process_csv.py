import pytest
import os
import csv
import json
from post_process_csv import process_csv

def test_process_csv(tmp_path):
    input_csv_path = tmp_path / 'test_input.csv'
    output_csv_path = tmp_path / 'test_output.csv'
    output_geojson_path = tmp_path / 'test_output.geojson'

    with open(input_csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['id', 'latitude', 'longitude', 'altitude'])
        writer.writerow(['1', '12.34', '56.78', '90'])
        writer.writerow(['1', '12.35', '56.79', '91'])
        writer.writerow(['2', '22.34', '66.78', '100'])

    process_csv(input_csv_path, output_csv_path, output_geojson_path)

    with open(output_csv_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]['id'] == '1'
        assert rows[0]['latitude'] == '12.35'
        assert rows[0]['longitude'] == '56.79'
        assert rows[0]['altitude'] == '91'
        assert rows[1]['id'] == '2'
        assert rows[1]['latitude'] == '22.34'
        assert rows[1]['longitude'] == '66.78'
        assert rows[1]['altitude'] == '100'

    with open(output_geojson_path, 'r') as geojsonfile:
        geojson_data = json.load(geojsonfile)
        assert geojson_data['type'] == 'FeatureCollection'
        assert len(geojson_data['features']) == 2
        assert geojson_data['features'][0]['properties']['id'] == '1'
        assert geojson_data['features'][0]['geometry']['coordinates'] == [56.79, 12.35, 91]
        assert geojson_data['features'][1]['properties']['id'] == '2'
        assert geojson_data['features'][1]['geometry']['coordinates'] == [66.78, 22.34, 100]
