"""
Post annotation via OpenAI API.

Input : JSON file with scraped posts (telegram_posts.json, etc.)
Output: JSON file with axes, quality flags and confidence for each post

Install:
  pip install openai
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from openai import OpenAI


# ─── Settings ────────────────────────────────────────────────────────────────
OPENAI_API_KEY = ""
MODEL          = "gpt-4o-mini"
INPUT_FILE     = "denys_smyhal.json"
OUTPUT_FILE    = "annotated_denys_smyhal.json"
WORKERS        = 10    # parallel threads (increase for higher-tier rate limits)
SAVE_EVERY     = 50    # save progress every N processed posts
# ─────────────────────────────────────────────────────────────────────────────

PROMPT_TEMPLATE = """You are an expert annotator of political texts.

Your task is to analyze a given text and assign numerical scores (from 0.0 to 1.0) for several rhetorical/ideological axes.

IMPORTANT:
* You are NOT evaluating the politician as a person.
* You are evaluating ONLY what is expressed in THIS specific text.
* Scores reflect how strongly each motif is expressed in the text.

---

AXES DEFINITIONS:

1. Militarism
   Degree to which the text frames problems in terms of force, threat, mobilization, or prioritizes military/force-based solutions.

2. Nationalism
   Degree to which the text emphasizes nation, sovereignty, language, culture, or "we as a nation".

3. Traditionalism
   Support for traditional values, moral order, family, religion, or criticism of changing norms.

4. Statism
   Support for strong state control, centralization, order, discipline as key solutions.

5. Populism
   Framing politics as "people vs elites", anti-elite rhetoric, moral polarization.

---

SCORING RULES:

Use the full scale [0.0 – 1.0]:
0.0  = completely absent
0.25 = weak signal
0.5  = mixed / unclear
0.75 = clear presence
1.0  = dominant theme

IMPORTANT:
* Do NOT default to 0.5.
* Use extreme values (0.0 or 1.0) when appropriate.
* Different axes are independent.

---

QUALITY FLAGS:

* is_quote   : text mainly quotes someone else's position
* is_irony   : text likely uses irony, sarcasm, or opposite meaning
* is_unclear : meaning or stance cannot be reliably determined

These flags DO NOT automatically reduce axis scores to 0.

---

CONFIDENCE:

1.0 = very confident
0.7 = mostly confident
0.4 = uncertain
0.1 = very unclear

Lower confidence if: irony, ambiguous meaning, lack of context.

---

OUTPUT FORMAT (STRICT JSON, no markdown):

{
  "axes": {
    "militarism": float,
    "nationalism": float,
    "traditionalism": float,
    "statism": float,
    "populism": float
  },
  "quality": {
    "is_quote": boolean,
    "is_irony": boolean,
    "is_unclear": boolean
  },
  "confidence": float
}

---

TEXT:
\"\"\"{TEXT}\"\"\"
"""


def annotate(client: OpenAI, text: str) -> dict:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": PROMPT_TEMPLATE.replace("{TEXT}", text)},
        ],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def load_json(path: str) -> list[dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(data: list[dict], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_output(post: dict, annotation: dict) -> dict:
    axes = annotation.get("axes", {})
    quality = annotation.get("quality", {})
    return {
        "id": post["id"],
        "posted_at": post["posted_at"],
        "source": post.get("source", "telegram"),
        "person": post.get("person", ""),
        "text": post["text"],
        "metrics": {
            "militarism":     axes.get("militarism", 0.0),
            "nationalism":    axes.get("nationalism", 0.0),
            "traditionalism": axes.get("traditionalism", 0.0),
            "statism":        axes.get("statism", 0.0),
            "populism":       axes.get("populism", 0.0),
        },
        "quality": {
            "is_quote":   quality.get("is_quote", False),
            "is_irony":   quality.get("is_irony", False),
            "is_unclear": quality.get("is_unclear", False),
        },
        "confidence": annotation.get("confidence", 0.0),
    }


def process_post(client: OpenAI, post: dict) -> dict | None:
    text = post.get("text", "").strip()
    if not text:
        return None
    try:
        annotation = annotate(client, text)
        return build_output(post, annotation)
    except Exception as e:
        print(f"  [ERROR] id={post['id']}: {e}")
        time.sleep(5)
        return None


def run(
    input_file: str = INPUT_FILE,
    output_file: str = OUTPUT_FILE,
) -> None:
    client = OpenAI(api_key=OPENAI_API_KEY)

    posts = load_json(input_file)
    print(f"Posts to process: {len(posts)}")

    out_path = Path(output_file)
    done: list[dict] = load_json(output_file) if out_path.exists() else []
    done_ids = {r["id"] for r in done}
    print(f"Already processed: {len(done_ids)}")
    print(f"Parallel workers: {WORKERS}")
    print("─" * 60)

    todo = [p for p in posts if p["id"] not in done_ids and p.get("text", "").strip()]

    results = list(done)
    lock = Lock()
    counter = [0]  # mutable counter for closure

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(process_post, client, post): post for post in todo}

        for future in as_completed(futures):
            post = futures[future]
            result = future.result()

            with lock:
                counter[0] += 1
                n = counter[0]
                if result:
                    results.append(result)
                print(f"  [{n}/{len(todo)}] id={post['id']} | {post['text'][:55]}...")
                if n % SAVE_EVERY == 0:
                    save_json(results, output_file)
                    print(f"  [saved {len(results)} records]")

    save_json(results, output_file)
    print(f"\nDone. Saved {len(results)} records → {output_file}")


if __name__ == "__main__":
    run(input_file=INPUT_FILE, output_file=OUTPUT_FILE)