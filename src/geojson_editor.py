import json


def save_new_feature(geojson_path, feature):

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["features"].append(feature)

    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )
