#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "products.json"
HISTORY = ROOT / "data" / "history"
BASE = "https://kimjunnem.github.io/shopping-radar"
KST = timezone(timedelta(hours=9))
PUBLISHER = "ca-pub-4192319901350402"


def esc(v): return html.escape(str(v or ""), quote=True)
def money(v):
    try: return f"{int(float(v)):,}원"
    except Exception: return "가격 확인"

def slug(v):
    s = re.sub(r"[^0-9A-Za-z가-힣]+", "-", str(v)).strip("-")
    return s or "category"

def encpath(s): return quote(s, safe="/-._~")

def load_json(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default


def head(title, description, canonical, extra=""):
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}"><link rel="stylesheet" href="{BASE}/style.css">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={PUBLISHER}" crossorigin="anonymous"></script>
{extra}</head><body><header class="top"><div class="wrap nav"><a class="brand" href="{BASE}/">쇼핑레이더</a><nav><a href="{BASE}/#popular">인기상품</a><a href="{BASE}/#categories">카테고리</a><a href="{BASE}/about.html">사이트 안내</a></nav></div></header>'''


def foot():
    return f'''<footer><div class="wrap"><p class="disclosure">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다.</p><p>상품 가격·배송 조건은 조회 시점 기준이며 실제 결제 화면과 다를 수 있습니다.</p><p><a href="{BASE}/about.html">사이트 안내</a> · <a href="{BASE}/privacy.html">개인정보처리방침</a> · <a href="{BASE}/disclaimer.html">면책 안내</a></p></div></footer></body></html>'''


def card(item, n=None):
    rank = n if n is not None else item.get("rank")
    trend = item.get("trend")
    change = item.get("rank_change")
    t = "신규" if trend == "new" else (f"▲ {change}" if trend == "up" else f"▼ {abs(change)}" if trend == "down" else "-")
    pid = esc(item.get("product_id"))
    img = f'<img loading="lazy" src="{esc(item.get("image"))}" alt="">' if item.get("image") else '<div class="noimg">이미지 없음</div>'
    badges = []
    if item.get("is_rocket"): badges.append("로켓")
    if item.get("is_free_shipping"): badges.append("무료배송")
    badge_html = ''.join(f'<span class="badge">{esc(x)}</span>' for x in badges)
    return f'''<article class="card"><a class="img" href="{BASE}/product/{pid}.html">{img}</a><div class="body"><div class="rank">{rank}위 <span>{esc(t)}</span></div><div class="cat">{esc(item.get("category"))}</div><h3><a href="{BASE}/product/{pid}.html">{esc(item.get("name"))}</a></h3><div class="price">{money(item.get("price"))}</div><div class="badges">{badge_html}</div><a class="btn" rel="nofollow sponsored" target="_blank" href="{esc(item.get("url"))}">쿠팡에서 상품·후기 보기</a></div></article>'''


def composite_top100(items):
    by_cat = {}
    for x in items:
        by_cat.setdefault(x.get("category_id"), []).append(x)
    for arr in by_cat.values(): arr.sort(key=lambda x: x.get("rank", 999))
    out=[]
    r=0
    while len(out)<100:
        added=False
        for cid in sorted(by_cat):
            arr=by_cat[cid]
            if r < len(arr):
                out.append(arr[r]); added=True
                if len(out)>=100: break
        if not added: break
        r+=1
    return out


def history_stats(pid, cid):
    days_top10=0
    appearances=0
    for p in sorted(HISTORY.glob("*.json"))[-30:]:
        d=load_json(p,{})
        matches=[x for x in d.get("items",[]) if str(x.get("product_id"))==str(pid) and str(x.get("category_id"))==str(cid)]
        if matches:
            appearances += 1
            if matches[0].get("rank",999) <= 10: days_top10 += 1
    return days_top10, appearances


def main():
    payload=load_json(DATA,{"items":[],"categories":[]})
    items=payload.get("items",[])
    for d in (ROOT/"product", ROOT/"category"):
        if d.exists(): shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    updated=payload.get("updated_at") or "아직 데이터 연결 전"

    cats={}
    for x in items: cats.setdefault(x.get("category","기타"),[]).append(x)
    for arr in cats.values(): arr.sort(key=lambda x:x.get("rank",999))

    popular=composite_top100(items)
    intro = '<section class="empty"><h2>쿠팡 파트너스 API 연결 전이에요</h2><p>API 키를 GitHub Secrets에 등록하면 매일 카테고리별 인기상품을 자동으로 가져옵니다.</p></section>' if not popular else ''
    popular_html=''.join(card(x,i+1) for i,x in enumerate(popular))
    cat_links=''.join(f'<a class="chip" href="{BASE}/category/{encpath(slug(name))}.html">{esc(name)} <b>{len(arr)}</b></a>' for name,arr in sorted(cats.items())) or '<span class="muted">API 연결 후 자동 생성됩니다.</span>'
    index = head("쇼핑레이더 | 오늘의 인기상품 100", "쿠팡 파트너스 카테고리별 베스트를 한곳에서 비교하고 상품과 후기를 확인하세요.", BASE+"/") + f'''<main class="wrap"><section class="hero"><p class="eyebrow">매일 자동 갱신</p><h1>오늘의 인기상품 100</h1><p>쿠팡 파트너스의 <strong>카테고리별 베스트</strong>를 모아 보기 쉽게 정리합니다. 전체 판매량 순위는 아닙니다.</p><p class="updated">최근 갱신: {esc(updated)}</p></section><section id="categories"><h2>카테고리</h2><div class="chips">{cat_links}</div></section>{intro}<section id="popular"><div class="section-title"><h2>카테고리 인기상품 100</h2><p>각 카테고리 상위 상품을 순서대로 섞어 최대 100개를 표시합니다.</p></div><div class="grid">{popular_html}</div></section></main>''' + foot()
    (ROOT/"index.html").write_text(index,encoding="utf-8")

    # 카테고리 페이지
    for name,arr in cats.items():
        s=slug(name)
        page=head(f"{name} 인기상품 순위 | 쇼핑레이더", f"{name} 카테고리의 쿠팡 인기상품을 순위·가격과 함께 확인하세요.", f"{BASE}/category/{encpath(s)}.html") + f'''<main class="wrap"><section class="hero small"><p class="eyebrow">카테고리 베스트</p><h1>{esc(name)} 인기상품</h1><p>카테고리 내 순위이며 실제 판매량·판매액은 공개되지 않습니다.</p></section><div class="grid">{''.join(card(x) for x in arr[:100])}</div></main>''' + foot()
        (ROOT/"category"/f"{s}.html").write_text(page,encoding="utf-8")

    # 상품 페이지
    for x in items:
        pid=str(x.get("product_id"))
        if not pid: continue
        d10,app=history_stats(pid,str(x.get("category_id")))
        extra=f'''<script type="application/ld+json">{json.dumps({"@context":"https://schema.org","@type":"Product","name":x.get("name"),"image":[x.get("image")] if x.get("image") else [],"offers":{"@type":"Offer","price":x.get("price") or "","priceCurrency":"KRW","url":x.get("url")}}, ensure_ascii=False)}</script>'''
        image=f'<img class="product-img" src="{esc(x.get("image"))}" alt="{esc(x.get("name"))}">' if x.get("image") else ''
        change=x.get("rank_change")
        trend="신규 진입" if x.get("trend")=="new" else (f"전일 대비 {change}계단 상승" if change and change>0 else f"전일 대비 {abs(change)}계단 하락" if change and change<0 else "전일과 같은 순위")
        page=head(f"{x.get('name')} 가격·인기순위 | 쇼핑레이더", f"{x.get('name')}의 현재 가격과 {x.get('category')} 인기순위를 확인하세요.", f"{BASE}/product/{pid}.html", extra) + f'''<main class="wrap"><div class="breadcrumb"><a href="{BASE}/">홈</a> › <a href="{BASE}/category/{encpath(slug(x.get('category')))}.html">{esc(x.get('category'))}</a></div><section class="product"><div>{image}</div><div><p class="eyebrow">{esc(x.get('category'))} {x.get('rank')}위</p><h1>{esc(x.get('name'))}</h1><div class="price big">{money(x.get('price'))}</div><p>{esc(trend)}</p><dl><div><dt>최근 30일 TOP10</dt><dd>{d10}일</dd></div><div><dt>최근 30일 등장</dt><dd>{app}일</dd></div><div><dt>배송</dt><dd>{'로켓배송' if x.get('is_rocket') else '상품 페이지 확인'}</dd></div></dl><a class="btn large" rel="nofollow sponsored" target="_blank" href="{esc(x.get('url'))}">쿠팡에서 상품·후기 보기</a><p class="fine">리뷰 원문은 쇼핑레이더가 복제하지 않습니다. 버튼을 누르면 쿠팡 상품 페이지에서 최신 후기를 직접 확인할 수 있습니다.</p></div></section><section class="info"><h2>순위 안내</h2><p>이 페이지의 순위는 쿠팡 파트너스 API가 제공하는 해당 카테고리 베스트 목록의 순서입니다. 쿠팡 전체 상품의 판매량 순위로 해석하면 안 됩니다.</p></section></main>''' + foot()
        (ROOT/"product"/f"{pid}.html").write_text(page,encoding="utf-8")

    # AI/search indexes
    ai=[{"name":x.get("name"),"category":x.get("category"),"category_rank":x.get("rank"),"price":x.get("price"),"url":f"{BASE}/product/{x.get('product_id')}.html","merchant_url":x.get("url"),"updated_at":updated} for x in items]
    (ROOT/"data"/"ai-index.json").write_text(json.dumps(ai,ensure_ascii=False,indent=2),encoding="utf-8")

    today=datetime.now(KST).strftime("%Y-%m-%d")
    urls=[BASE+"/", BASE+"/about.html", BASE+"/privacy.html", BASE+"/disclaimer.html"]
    urls += [f"{BASE}/category/{encpath(slug(n))}.html" for n in cats]
    urls += [f"{BASE}/product/{x.get('product_id')}.html" for x in items if x.get("product_id")]
    xml=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls: xml.append(f'  <url><loc>{esc(u)}</loc><lastmod>{today}</lastmod></url>')
    xml.append('</urlset>')
    (ROOT/"sitemap.xml").write_text('\n'.join(xml),encoding="utf-8")
    (ROOT/"llms.txt").write_text(f'''# 쇼핑레이더\n\n쇼핑레이더는 쿠팡 파트너스 API의 카테고리별 베스트 상품을 정리하는 비공식 정보 사이트입니다.\n쿠팡 전체 판매량 순위가 아닙니다. 리뷰 원문은 복제하지 않으며 상품 페이지로 연결합니다.\n\nHome: {BASE}/\nAI index: {BASE}/data/ai-index.json\nSitemap: {BASE}/sitemap.xml\n''',encoding="utf-8")
    print(f"generated: {len(items)} product pages, {len(cats)} category pages")

if __name__=="__main__": main()
