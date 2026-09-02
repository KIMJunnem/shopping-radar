#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
HISTORY_DIR = DATA_DIR / "history"
PRODUCTS_FILE = DATA_DIR / "products.json"
DOMAIN = "https://api-gateway.coupang.com"
KST = timezone(timedelta(hours=9))

# 쿠팡 파트너스에서 널리 사용되는 카테고리 ID.
# API 계정에서 제공되는 최신 문서/카테고리 목록이 다르면 이 표만 수정하면 됩니다.
CATEGORIES = [
    ("1001", "여성패션"), ("1002", "남성패션"), ("1010", "뷰티"),
    ("1011", "출산·유아동"), ("1012", "식품"), ("1013", "주방용품"),
    ("1014", "생활용품"), ("1015", "홈인테리어"), ("1016", "가전디지털"),
    ("1017", "스포츠·레저"), ("1018", "자동차용품"), ("1019", "도서·음반"),
    ("1020", "완구·취미"), ("1021", "문구·오피스"), ("1024", "헬스·건강식품"),
    ("1025", "국내여행"), ("1026", "해외여행"), ("1029", "반려동물용품"),
    ("1030", "유아동패션"),
]


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def auth_header(method: str, path_with_query: str, access_key: str, secret_key: str) -> str:
    path, _, query = path_with_query.partition("?")
    signed_date = time.strftime("%y%m%dT%H%M%SZ", time.gmtime())
    message = signed_date + method + path + query
    signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return (
        "CEA algorithm=HmacSHA256, "
        f"access-key={access_key}, signed-date={signed_date}, signature={signature}"
    )


def fetch_category(category_id: str, access_key: str, secret_key: str, sub_id: str) -> list[dict]:
    params = [("limit", "100")]
    if sub_id:
        params.append(("subId", sub_id))
    params.append(("imageSize", "512x512"))
    query = urlencode(params)

    # 파트너스 API 문서/계정에 따라 v1 유무가 달랐던 사례가 있어 둘 다 안전하게 시도합니다.
    paths = [
        f"/v2/providers/affiliate_open_api/apis/openapi/v1/products/bestcategories/{category_id}?{query}",
        f"/v2/providers/affiliate_open_api/apis/openapi/products/bestcategories/{category_id}?{query}",
    ]
    last_error = None
    for path in paths:
        try:
            req = Request(
                DOMAIN + path,
                headers={
                    "Authorization": auth_header("GET", path, access_key, secret_key),
                    "Content-Type": "application/json",
                    "User-Agent": "ShoppingRadar/1.0",
                },
                method="GET",
            )
            with urlopen(req, timeout=25) as response:
                payload = json.loads(response.read().decode("utf-8"))
            rcode = str(payload.get("rCode", "0"))
            if rcode not in ("0", "SUCCESS"):
                raise RuntimeError(f"API rCode={rcode}: {payload.get('rMessage') or payload.get('message')}")
            data = payload.get("data", [])
            if isinstance(data, dict):
                for key in ("productData", "products", "items"):
                    if isinstance(data.get(key), list):
                        data = data[key]
                        break
            if not isinstance(data, list):
                raise RuntimeError("Unexpected API response shape")
            return data
        except (HTTPError, URLError, RuntimeError, json.JSONDecodeError) as exc:
            last_error = exc
    raise RuntimeError(f"category {category_id} failed: {last_error}")


def normalize(raw: dict, category_id: str, category_name: str, rank: int) -> dict:
    product_id = str(raw.get("productId") or raw.get("productID") or "").strip()
    return {
        "product_id": product_id,
        "category_id": category_id,
        "category": category_name,
        "rank": rank,
        "name": str(raw.get("productName") or raw.get("name") or "상품명 미제공").strip(),
        "price": raw.get("productPrice") if raw.get("productPrice") is not None else raw.get("price"),
        "image": str(raw.get("productImage") or raw.get("imageUrl") or "").strip(),
        "url": str(raw.get("productUrl") or raw.get("url") or "").strip(),
        "is_rocket": bool(raw.get("isRocket", False)),
        "is_free_shipping": bool(raw.get("isFreeShipping", False)),
    }


def previous_rank_map(previous: dict) -> dict[tuple[str, str], int]:
    out = {}
    for item in previous.get("items", []):
        pid = str(item.get("product_id") or "")
        cid = str(item.get("category_id") or "")
        if pid and cid and isinstance(item.get("rank"), int):
            out[(cid, pid)] = item["rank"]
    return out


def add_trend(items: list[dict], previous: dict) -> None:
    prev = previous_rank_map(previous)
    for item in items:
        old = prev.get((item["category_id"], item["product_id"]))
        if old is None:
            item["rank_change"] = None
            item["trend"] = "new"
        else:
            change = old - item["rank"]
            item["rank_change"] = change
            item["trend"] = "up" if change > 0 else "down" if change < 0 else "same"


def save_history(payload: dict) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(KST).strftime("%Y-%m-%d")
    (HISTORY_DIR / f"{today}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # 최근 30일만 유지
    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)
    for old in files[30:]:
        old.unlink(missing_ok=True)


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    previous = read_json(PRODUCTS_FILE, {"categories": [], "items": []})
    access_key = os.getenv("COUPANG_ACCESS_KEY", "").strip()
    secret_key = os.getenv("COUPANG_SECRET_KEY", "").strip()
    sub_id = os.getenv("COUPANG_SUB_ID", "").strip()

    if not access_key or not secret_key:
        print("Coupang API keys are not configured. Existing product data is preserved.")
        return 0

    old_by_category: dict[str, list[dict]] = {}
    for item in previous.get("items", []):
        old_by_category.setdefault(str(item.get("category_id", "")), []).append(item)

    all_items: list[dict] = []
    category_status = []
    for category_id, category_name in CATEGORIES:
        try:
            raw_items = fetch_category(category_id, access_key, secret_key, sub_id)
            normalized = [normalize(raw, category_id, category_name, i + 1) for i, raw in enumerate(raw_items)]
            normalized = [x for x in normalized if x["product_id"] and x["url"]]
            all_items.extend(normalized)
            category_status.append({"id": category_id, "name": category_name, "count": len(normalized), "ok": True})
            print(f"{category_name}: {len(normalized)}")
        except Exception as exc:
            fallback = old_by_category.get(category_id, [])
            all_items.extend(fallback)
            category_status.append({"id": category_id, "name": category_name, "count": len(fallback), "ok": False})
            print(f"WARN {category_name}: {exc}; preserved {len(fallback)} old items")
        time.sleep(0.12)

    add_trend(all_items, previous)
    now = datetime.now(KST).isoformat(timespec="seconds")
    payload = {
        "updated_at": now,
        "source": "Coupang Partners Open API",
        "notice": "카테고리별 베스트 상품을 모아 보여줍니다. 쿠팡 전체 판매량 순위가 아닙니다.",
        "categories": category_status,
        "items": all_items,
    }
    PRODUCTS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    save_history(payload)
    print(f"saved {len(all_items)} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
