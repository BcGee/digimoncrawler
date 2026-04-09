import io
import json
import os
from concurrent.futures import ThreadPoolExecutor

import boto3
import requests
from botocore.exceptions import ClientError
from PIL import Image

s3 = boto3.client("s3")
BUCKET = os.environ.get("CARD_BUCKET", "ytlee-digimon")
BASE_IMG_URL = "https://digimon-cg-guide.com/wp-content/uploads"
CARD_SIZE_MM = (63, 88)
DPI = 300
CARD_SIZE_PX = (int(CARD_SIZE_MM[0] / 25.4 * DPI), int(CARD_SIZE_MM[1] / 25.4 * DPI))
CRAWL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://digimon-cg-guide.com/recipe-creater/",
}


def respond(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False),
    }


def parse_recipe(recipe_str):
    cards = []
    for entry in recipe_str.split("_"):
        # "bt14-0014" → card_id="BT14-001", qty=4 (last digit = quantity)
        qty = int(entry[-1])
        card_id = entry[:-1].upper()
        cards.append((card_id, qty))
    return cards


def s3_key_for_card(card_id):
    return f"cards/{card_id}.png"


def card_exists_in_s3(card_id):
    try:
        s3.head_object(Bucket=BUCKET, Key=s3_key_for_card(card_id))
        return True
    except ClientError:
        return False


def fetch_and_cache_card(card_id):
    url = f"{BASE_IMG_URL}/{card_id}.png"
    resp = requests.get(url, headers=CRAWL_HEADERS, timeout=15)
    if resp.status_code != 200:
        return False

    img = Image.open(io.BytesIO(resp.content))
    resized = img.resize(CARD_SIZE_PX, Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    resized.save(buf, format="PNG", dpi=(DPI, DPI))
    buf.seek(0)

    s3.put_object(
        Bucket=BUCKET,
        Key=s3_key_for_card(card_id),
        Body=buf.getvalue(),
        ContentType="image/png",
    )
    return True


def probe_alternates(card_id):
    """Probe for alternate art versions (P1, P2, ...) until failure."""
    alternates = []
    for i in range(1, 10):
        alt_id = f"{card_id}-P{i}"
        if card_exists_in_s3(alt_id):
            alternates.append(alt_id)
            continue
        url = f"{BASE_IMG_URL}/{alt_id}.png"
        try:
            resp = requests.head(url, headers=CRAWL_HEADERS, timeout=5)
            if resp.status_code == 200:
                if fetch_and_cache_card(alt_id):
                    alternates.append(alt_id)
                else:
                    break
            else:
                break
        except requests.RequestException:
            break
    return alternates


def handle_cards(params):
    recipe_str = params.get("recipe", [""])[0]
    if not recipe_str:
        return respond(400, {"error": "recipe parameter required"})

    cards = parse_recipe(recipe_str)
    unique_ids = list(dict.fromkeys(cid for cid, _ in cards))

    def process_card(card_id):
        cached = card_exists_in_s3(card_id)
        if not cached:
            cached = fetch_and_cache_card(card_id)
        alternates = probe_alternates(card_id)
        return {
            "card_id": card_id,
            "cached": cached,
            "key": s3_key_for_card(card_id),
            "alternates": alternates,
        }

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(process_card, unique_ids))

    return respond(
        200,
        {
            "cards": results,
            "deck": [{"card_id": cid, "qty": qty} for cid, qty in cards],
        },
    )


def handler(event, context):
    path = event.get("rawPath", event.get("path", ""))
    params = event.get("queryStringParameters") or {}
    multi_params = {}
    for k, v in params.items():
        multi_params[k] = [v] if isinstance(v, str) else v

    if path.endswith("/api/cards"):
        return handle_cards(multi_params)
    else:
        return respond(404, {"error": "not found"})
