#!/usr/bin/env python3
from __future__ import annotations
import html, json, re, shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"products.json"
HISTORY=ROOT/"data"/"history"
BASE="https://kimjunnem.github.io/shopping-radar"
KST=timezone(timedelta(hours=9))
PUBLISHER="ca-pub-4192319901350402"

def esc(v): return html.escape(str(v or ""),quote=True)
def money(v):
    try:return f"{int(float(v)):,}원"
    except:return "가격 확인"
def slug(v):
    s=re.sub(r"[^0-9A-Za-z가-힣]+","-",str(v)).strip("-")
    return s or "category"
def enc(s):return quote(str(s),safe="/-._~")
def load(p,d):
    try:return json.loads(p.read_text(encoding="utf-8"))
    except:return d
def head(title,desc,canonical):
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{esc(canonical)}"><link rel="stylesheet" href="{BASE}/style.css"><meta name="google-adsense-account" content="{PUBLISHER}"><script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={PUBLISHER}" crossorigin="anonymous"></script></head><body><header class="top"><div class="wrap nav"><a class="brand" href="{BASE}/">쇼핑레이더</a><nav><a href="{BASE}/#ranking">인기상품</a><a href="{BASE}/#calculator">단위가격 계산</a><a href="{BASE}/about.html">사이트 안내</a></nav></div></header>'''
def foot():
    return f'''<footer><div class="wrap footer"><div><b>쇼핑레이더</b><p class="disclosure">이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받을 수 있습니다.</p></div><div><a href="{BASE}/about.html">사이트 안내</a><a href="{BASE}/privacy.html">개인정보처리방침</a><a href="{BASE}/disclaimer.html">면책 안내</a></div></div></footer></body></html>'''
def history(pid,cid):
    top10=app=0
    for p in sorted(HISTORY.glob("*.json"))[-30:]:
        d=load(p,{})
        m=[x for x in d.get("items",[]) if str(x.get("product_id"))==str(pid) and str(x.get("category_id"))==str(cid)]
        if m:
            app+=1
            if (m[0].get("rank") or 999)<=10:top10+=1
    return top10,app

def main():
    d=load(DATA,{"items":[]})
    items=d.get("items",[])
    if not items:
        print("No product data. Existing generated pages and indexes are preserved; root index preserved.")
        return 0
    for folder in (ROOT/"product",ROOT/"category"):
        if folder.exists():shutil.rmtree(folder)
        folder.mkdir(parents=True,exist_ok=True)
    cats={}
    for x in items:cats.setdefault(x.get("category") or "기타",[]).append(x)
    for arr in cats.values():arr.sort(key=lambda x:x.get("rank") or 999)

    for name,arr in cats.items():
        cards=[]
        for x in arr[:100]:
            img=f'<img loading="lazy" src="{esc(x.get("image"))}" alt="{esc(x.get("name"))}">' if x.get("image") else ""
            cards.append(f'''<article class="card"><a class="card-img" href="{BASE}/product/{esc(x.get("product_id"))}.html">{img}</a><div class="card-body"><div class="rank">{esc(x.get("rank"))}위</div><h3><a href="{BASE}/product/{esc(x.get("product_id"))}.html">{esc(x.get("name"))}</a></h3><div class="price">{money(x.get("price"))}</div><a class="primary" target="_blank" rel="nofollow sponsored noopener" href="{esc(x.get("url"))}">쿠팡에서 확인</a></div></article>''')
        body=f'''<main class="wrap product-page"><div class="breadcrumb"><a href="{BASE}/">홈</a> &gt; 카테고리</div><p class="eyebrow">CATEGORY BEST</p><h1>{esc(name)} 인기상품</h1><p class="lead">해당 카테고리 API 베스트 목록의 순서이며 쿠팡 전체 판매량 순위는 아닙니다.</p><div class="grid">{''.join(cards)}</div></main>'''
        page=head(f"{name} 인기상품 | 쇼핑레이더",f"{name} 카테고리 인기상품과 가격을 확인하세요.",f"{BASE}/category/{enc(slug(name))}.html")+body+foot()
        (ROOT/"category"/f"{slug(name)}.html").write_text(page,encoding="utf-8")
        # app.js의 사람이 읽기 쉬운 카테고리 링크도 동일 페이지로 연결합니다.
        if str(name) != slug(name):
            (ROOT/"category"/f"{name}.html").write_text(page,encoding="utf-8")

    for x in items:
        pid=str(x.get("product_id") or "")
        if not pid:continue
        t10,app=history(pid,x.get("category_id"))
        img=f'<img src="{esc(x.get("image"))}" alt="{esc(x.get("name"))}">' if x.get("image") else ""
        body=f'''<main class="wrap product-page"><div class="breadcrumb"><a href="{BASE}/">홈</a> &gt; <a href="{BASE}/category/{enc(slug(x.get("category")))}.html">{esc(x.get("category"))}</a></div><section class="product-box"><div>{img}</div><div><p class="eyebrow">{esc(x.get("category"))} {esc(x.get("rank"))}위</p><h1>{esc(x.get("name"))}</h1><div class="price">{money(x.get("price"))}</div><div class="facts"><div><span>최근 30일 TOP10</span><b>{t10}일</b></div><div><span>최근 30일 등장</span><b>{app}일</b></div><div><span>배송</span><b>{"로켓배송" if x.get("is_rocket") else "상품 페이지 확인"}</b></div></div><a class="primary" target="_blank" rel="nofollow sponsored noopener" href="{esc(x.get("url"))}">쿠팡에서 상품·후기 보기</a><p class="disclosure">리뷰 원문은 복제하지 않습니다. 최신 후기는 쿠팡 상품 페이지에서 확인하세요.</p></div></section></main>'''
        page=head(f'{x.get("name")} 가격·인기순위 | 쇼핑레이더',f'{x.get("name")}의 현재 가격과 카테고리 인기순위를 확인하세요.',f'{BASE}/product/{pid}.html')+body+foot()
        (ROOT/"product"/f"{pid}.html").write_text(page,encoding="utf-8")

    updated=d.get("updated_at") or datetime.now(KST).isoformat(timespec="seconds")
    ai=[{"name":x.get("name"),"category":x.get("category"),"category_rank":x.get("rank"),"price":x.get("price"),"page_url":f'{BASE}/product/{x.get("product_id")}.html',"merchant_url":x.get("url"),"updated_at":updated} for x in items]
    (ROOT/"data"/"ai-index.json").write_text(json.dumps(ai,ensure_ascii=False,indent=2),encoding="utf-8")
    today=datetime.now(KST).strftime("%Y-%m-%d")
    urls=[BASE+"/",BASE+"/about.html",BASE+"/privacy.html",BASE+"/disclaimer.html"]
    urls += [f"{BASE}/category/{enc(slug(n))}.html" for n in cats]
    urls += [f"{BASE}/product/{x.get('product_id')}.html" for x in items if x.get("product_id")]
    xml=['<?xml version="1.0" encoding="UTF-8"?>','<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    xml += [f'  <url><loc>{html.escape(u)}</loc><lastmod>{today}</lastmod></url>' for u in urls]
    xml.append("</urlset>")
    (ROOT/"sitemap.xml").write_text("\n".join(xml)+"\n",encoding="utf-8")
    (ROOT/"llms.txt").write_text(f"# 쇼핑레이더\n\n인기상품·가격 비교를 돕는 비공식 쇼핑 정보서비스입니다.\n쿠팡 전체 판매량 순위가 아니며 리뷰 원문을 복제하지 않습니다.\n\nHome: {BASE}/\nAI index: {BASE}/data/ai-index.json\nSitemap: {BASE}/sitemap.xml\n",encoding="utf-8")
    print(f"generated {len(items)} products / {len(cats)} categories; root index preserved")
if __name__=="__main__":main()
