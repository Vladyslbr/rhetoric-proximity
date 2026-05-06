import json
import argparse
from datetime import datetime


def convert_timestamp(ts: str) -> str:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt.isoformat()


def transform_axes(metrics: dict) -> dict:
    return {
        "militarism": metrics.get("militarism", 0),
        "national_identity": metrics.get("nationalism", 0),
        "traditionalism": metrics.get("traditionalism", 0),
        "statism": metrics.get("statism", 0),
        "populism": metrics.get("populism", 0),
    }


def transform_posts(input_data):
    grouped = {}

    for item in input_data:
        person = item["person"]

        post = {
            "id": item["id"],
            "posted_at": convert_timestamp(item["posted_at"]),
            "source": item["source"] + "_personal",
            "text": item["text"],
            "annotation": {
                "axes": transform_axes(item.get("metrics", {})),
                "quality": item.get("quality", {}),
                "confidence": item.get("confidence", None)
            }
        }

        if person not in grouped:
            grouped[person] = {
                "person": person,
                "posts": []
            }

        grouped[person]["posts"].append(post)

    return list(grouped.values())


def main():
    parser = argparse.ArgumentParser(description="Transform posts JSON structure")
    parser.add_argument("input_file", help="Path to input JSON file")
    parser.add_argument("output_file", help="Path to output JSON file")

    args = parser.parse_args()

    with open(args.input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    result = transform_posts(data)

    with open(args.output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Saved transformed data to {args.output_file}")


if __name__ == "__main__":
    main()