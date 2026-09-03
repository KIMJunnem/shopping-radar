#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "products.json"
HISTORY = ROOT / "data" / "history"
BASE = "https://kimjunnem.github.io/shopping-radar"
KST = timezone(timedelta(hours=9))
PUBLISHER = "ca-pub-4192319901350402"


def esc(value):
    return html.escape(str(value or ""), quote=True)


def money(value):
    try:
        price = float(value)
        return f"{int(price):,}원" if price > 0 else "가격 정보 없음"
    except (TypeError, ValueError):
        return "가격 정보 없음"


def trend(item):
    state = item.get("trend")
    change = item.get("rank_change")
    if state == "new":
        return "신규 진입"
    if state == "up":
        return f"{abs(int(change or 0))}계단 상승"
    if state == "down":
        return f"{abs(int(change or 0))}계단 하락"
    return "변동 없음"


def slug(value):
    result = re.sub(r"[^0-9A-Za-z가-힣]+", "-", str(value)).strip("-")
    return result or "category"


def enc(value):
    return quote(str(value), safe="/-._~")


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def valid_url(value):
    parsed = urlparse(str(value or ""))
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def normalize_item(item):
    if not isinstance(item, dict):
        return None
    product_id = str(item.get("product_id") or "").strip()
    name = str(item.get("name") or "").strip()
    category = str(item.get("category") or "").strip()
    try:
        rank = int(item.get("rank"))
    except (TypeError, ValueError):
        return None
    if not re.fullmatch(r"[0-9A-Za-z_-]+", product_id):
        return None
    if not name or not category or rank < 1 or not valid_url(item.get("url")):
        return None
    normalized = dict(item)
    normalized.update({"product_id": product_id, "name": name, "category": category, "rank": rank})
    if not valid_url(normalized.get("image")):
        normalized["image"] = ""
    return normalized


def head(title, description, canonical):
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(description)}"><link rel="canonical" href="{esc(canonical)}"><link rel="stylesheet" href="{BASE}/style.css"><meta name="google-adsense-account" content="{PUBLISHER}"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={PUBLISHER}" crossorigin="anonymous"></script></head><body><header class="top"><div class="wrap nav"><a class="brand" href="{BASE}/">쇼핑레이더</a><nav><a href="{BASE}/#ranking">인기상품</a><a href="{BASE}/#calculator">단위가격 비교</a><a href="{BASE}/about.html">사이트 안내</a></nav></div></header>'''


def foot():
    return f'''<footer><div class="wrap footer"><div><b>쇼핑레이더</b><p class="disclosure">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다.</p></div><div><a href="{BASE}/about.html">사이트 안내</a><a href="{BASE}/privacy.html">개인정보처리방침</a><a href="{BASE}/disclaimer.html">면책 안내</a></div></div></footer><script src="{BASE}/app.js?v=20260903-2"></script></body></html>'''


def history_counts(product_id, category_id):
    top10 = appearances = 0
    for path in sorted(HISTORY.glob("*.json"))[-30:]:
        payload = load(path, {})
        match = next(
            (
                item for item in payload.get("items", [])
                if str(item.get("product_id")) == str(product_id)
                and str(item.get("category_id")) == str(category_id)
            ),
            None,
        )
        if match:
            appearances += 1
            if isinstance(match.get("rank"), int) and match["rank"] <= 10:
                top10 += 1
    return top10, appearances


def product_snapshot(item):
    return {
        "product_id": item["product_id"],
        "name": item["name"],
        "category": item["category"],
        "price": item.get("price"),
        "url": item["url"],
        "image": item.get("image") or "",
        "detail_url": f"{BASE}/product/{enc(item['product_id'])}.html",
    }


def data_attribute(item):
    payload = json.dumps(product_snapshot(item), ensure_ascii=False, separators=(",", ":"))
    return quote(payload, safe="")


def card_html(item):
    detail = f"{BASE}/product/{enc(item['product_id'])}.html"
    image = (
        f'<img loading="lazy" width="512" height="512" src="{esc(item.get("image"))}" alt="{esc(item["name"])}">'
        if item.get("image") else ""
    )
    data = data_attribute(item)
    return f'''<article class="card" data-product="{data}"><button class="favorite-button" type="button" aria-label="{esc(item['name'])} 찜하기" aria-pressed="false">☆</button><a class="card-img product-detail-link" href="{detail}">{image}</a><div class="card-body"><div class="rank">{item['rank']}위 <small>{esc(trend(item))}</small></div><div class="category">{esc(item['category'])}</div><h3><a class="product-detail-link" href="{detail}">{esc(item['name'])}</a></h3><div class="price">{money(item.get('price'))}</div><a class="primary" target="_blank" rel="nofollow sponsored noopener" href="{esc(item['url'])}">쿠팡에서 보기</a></div></article>'''


def similar_card(item):
    detail = f"{BASE}/product/{enc(item['product_id'])}.html"
    image = (
        f'<img loading="lazy" width="512" height="512" src="{esc(item.get("image"))}" alt="{esc(item["name"])}">'
        if item.get("image") else ""
    )
    return f'''<article class="card"><a class="card-img" href="{detail}">{image}</a><div class="card-body"><div class="rank">{item['rank']}위 <small>{esc(trend(item))}</small></div><div class="category">{esc(item['category'])}</div><h3><a href="{detail}">{esc(item['name'])}</a></h3><div class="price">{money(item.get('price'))}</div><a class="secondary" href="{detail}">상품 정보 보기</a></div></article>'''


def price_history_rows(item):
    if int(item.get("price_history_days") or 0) < 2 or not item.get("lowest_price_30d"):
        return ""
    rows = [f'<div><span>최근 30일 기록 중 최저</span><b>{money(item.get("lowest_price_30d"))}</b></div>']
    if item.get("price_yesterday"):
        rows.append(f'<div><span>어제 기록 가격</span><b>{money(item.get("price_yesterday"))}</b></div>')
    if item.get("price_7_days_ago"):
        rows.append(f'<div><span>7일 전 기록 가격</span><b>{money(item.get("price_7_days_ago"))}</b></div>')
    return "".join(rows)


def current_product_script(item):
    payload = json.dumps(product_snapshot(item), ensure_ascii=False).replace("</", "<\\/")
    return f'<script id="currentProductData" type="application/json">{payload}</script>'


def main():
    payload = load(DATA, {"items": []})
    source_items = payload.get("items", []) if isinstance(payload, dict) else []
    items = [item for item in (normalize_item(value) for value in source_items) if item]
    if not items:
        print("No valid product data. Existing generated pages and indexes are preserved; root index preserved.")
        return 0

    for folder in (ROOT / "product", ROOT / "category"):
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)

    categories = {}
    for item in items:
        categories.setdefault(item["category"], []).append(item)
    for category_items in categories.values():
        category_items.sort(key=lambda item: item["rank"])

    for name, category_items in categories.items():
        cards = "".join(card_html(item) for item in category_items[:100])
        body = f'''<main class="wrap product-page"><div class="breadcrumb"><a href="{BASE}/">홈</a> &gt; 카테고리</div><p class="eyebrow">카테고리별 베스트</p><h1>{esc(name)} 인기상품</h1><p class="lead">쿠팡 파트너스 API가 제공한 해당 카테고리 베스트 순서입니다. 쿠팡 전체 상품의 판매량 순위가 아닙니다.</p><div class="grid">{cards}</div></main>'''
        page = head(
            f"{name} 인기상품 | 쇼핑레이더",
            f"{name} 카테고리 인기상품과 가격·순위 변화를 확인하세요.",
            f"{BASE}/category/{enc(slug(name))}.html",
        ) + body + foot()
        (ROOT / "category" / f"{slug(name)}.html").write_text(page, encoding="utf-8")

    for item in items:
        product_id = item["product_id"]
        top10, appearances = history_counts(product_id, item.get("category_id"))
        top10 = int(item.get("top10_count_30d") or top10)
        appearances = int(item.get("appearances_30d") or appearances)
        image = (
            f'<img loading="lazy" width="512" height="512" src="{esc(item.get("image"))}" alt="{esc(item["name"])}">'
            if item.get("image") else ""
        )
        delivery = "로켓배송" if item.get("is_rocket") else "상품 페이지 확인"
        if item.get("is_free_shipping"):
            delivery += " · 무료배송"
        related = [value for value in categories[item["category"]] if value["product_id"] != product_id][:4]
        related_html = ""
        if related:
            related_html = f'''<section class="similar-products"><h2>이 상품과 비슷한 인기상품</h2><p class="lead">같은 카테고리의 실제 인기상품입니다. 단위·용량 정보가 없어 자동 단위가격 비교는 하지 않습니다.</p><div class="grid">{''.join(similar_card(value) for value in related)}</div></section>'''
        data = data_attribute(item)
        facts = f'''<div class="facts"><div><span>현재 카테고리 순위</span><b>{item['rank']}위</b></div><div><span>전일 대비 순위</span><b>{esc(trend(item))}</b></div><div><span>최근 30일 TOP10 등장</span><b>{top10}회</b></div><div><span>최근 30일 등장 횟수</span><b>{appearances}회</b></div><div><span>배송 정보</span><b>{esc(delivery)}</b></div>{price_history_rows(item)}</div>'''
        body = f'''<main class="wrap product-page" data-product="{data}"><div class="breadcrumb"><a href="{BASE}/">홈</a> &gt; <a href="{BASE}/category/{enc(slug(item['category']))}.html">{esc(item['category'])}</a></div><section class="product-box"><div>{image}</div><div><p class="eyebrow">{esc(item['category'])} 카테고리 인기상품</p><h1>{esc(item['name'])}</h1><div class="price">{money(item.get('price'))}</div>{facts}<div class="product-actions"><button class="quiet-button favorite-button" type="button" aria-label="{esc(item['name'])} 찜하기" aria-pressed="false">☆ 찜하기</button><a class="secondary" href="{BASE}/#calculator">가격 비교 도구로 이동</a><a class="primary" target="_blank" rel="nofollow sponsored noopener" href="{esc(item['url'])}">쿠팡에서 상품·후기 보기</a></div><p class="disclosure">가격과 배송 조건은 바뀔 수 있습니다. 리뷰 원문은 복제하지 않으며 최신 정보와 후기는 쿠팡 상품 페이지에서 확인하세요.</p></div></section>{related_html}</main>{current_product_script(item)}'''
        page = head(
            f"{item['name']} 가격·인기순위 | 쇼핑레이더",
            f"{item['name']}의 현재 가격과 카테고리 인기순위·최근 기록을 확인하세요.",
            f"{BASE}/product/{enc(product_id)}.html",
        ) + body + foot()
        (ROOT / "product" / f"{product_id}.html").write_text(page, encoding="utf-8")

    updated = payload.get("updated_at") or datetime.now(KST).isoformat(timespec="seconds")
    ai_index = [
        {
            "name": item["name"],
            "category": item["category"],
            "category_rank": item["rank"],
            "rank_change": item.get("rank_change"),
            "price": item.get("price"),
            "page_url": f"{BASE}/product/{enc(item['product_id'])}.html",
            "merchant_url": item["url"],
            "updated_at": updated,
        }
        for item in items
    ]
    (ROOT / "data" / "ai-index.json").write_text(
        json.dumps(ai_index, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    today = datetime.now(KST).strftime("%Y-%m-%d")
    urls = [BASE + "/", BASE + "/about.html", BASE + "/privacy.html", BASE + "/disclaimer.html"]
    urls += [f"{BASE}/category/{enc(slug(name))}.html" for name in categories]
    urls += [f"{BASE}/product/{enc(item['product_id'])}.html" for item in items]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f"  <url><loc>{html.escape(url)}</loc><lastmod>{today}</lastmod></url>" for url in urls]
    xml.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\n".join(xml) + "\n", encoding="utf-8")
    (ROOT / "llms.txt").write_text(
        f"# 쇼핑레이더\n\n인기상품·단위가격 비교를 돕는 비공식 쇼핑 정보서비스입니다.\n"
        f"쿠팡 전체 판매량 순위가 아니며 리뷰 원문을 복제하지 않습니다.\n\n"
        f"Home: {BASE}/\nAI index: {BASE}/data/ai-index.json\nSitemap: {BASE}/sitemap.xml\n",
        encoding="utf-8",
    )
    print(f"generated {len(items)} products / {len(categories)} categories; root index preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
