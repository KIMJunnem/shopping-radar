"use strict";

const units={
  g:{family:"weight",factor:1,basis:100,label:"100g"},
  kg:{family:"weight",factor:1000,basis:100,label:"100g"},
  ml:{family:"volume",factor:1,basis:100,label:"100ml"},
  L:{family:"volume",factor:1000,basis:100,label:"100ml"},
  "개":{family:"count",factor:1,basis:1,label:"1개"},
  "매":{family:"sheet",factor:1,basis:1,label:"1매"}
};

const examples={
  water:{a:{name:"생수 A",price:12900,quantity:12,unit:"L"},b:{name:"생수 B",price:10900,quantity:10,unit:"L"}},
  detergent:{a:{name:"세제 A",price:12900,quantity:2.1,unit:"L"},b:{name:"세제 B",price:15900,quantity:3,unit:"L"}},
  tissue:{a:{name:"휴지 A",price:16900,quantity:30,unit:"매"},b:{name:"휴지 B",price:19800,quantity:36,unit:"매"}},
  rice:{a:{name:"쌀 A",price:32900,quantity:10,unit:"kg"},b:{name:"쌀 B",price:18900,quantity:5,unit:"kg"}},
  coffee:{a:{name:"커피 A",price:14900,quantity:100,unit:"개"},b:{name:"커피 B",price:9900,quantity:60,unit:"개"}},
  petfood:{a:{name:"사료 A",price:36900,quantity:6,unit:"kg"},b:{name:"사료 B",price:52900,quantity:10,unit:"kg"}}
};

const slots=["a","b","c","d"];
const slotLabels={a:"상품 A",b:"상품 B",c:"상품 C",d:"상품 D"};
const storageKeys={comparisons:"shoppingRadarComparisonsV1",saved:"shoppingRadarSavedV1",recent:"shoppingRadarRecentV1"};
const esc=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[char]);

function parseNumber(value){
  const normalized=String(value??"").replace(/,/g,"").trim();
  if(!normalized)return NaN;
  const number=Number(normalized);
  return Number.isFinite(number)&&Math.abs(number)<=Number.MAX_SAFE_INTEGER?number:NaN;
}

function money(value,digits=0){
  return Number.isFinite(Number(value))&&Number(value)>0
    ?`${Number(value).toLocaleString("ko-KR",{maximumFractionDigits:digits})}원`
    :"가격 정보 없음";
}

function calculateUnitPrice(price,quantity,unitName){
  const unit=units[unitName];
  const parsedPrice=parseNumber(price);
  const parsedQuantity=parseNumber(quantity);
  if(!unit||!Number.isFinite(parsedPrice)||!Number.isFinite(parsedQuantity)||parsedPrice<=0||parsedQuantity<=0)return null;
  const value=parsedPrice/(parsedQuantity*unit.factor)*unit.basis;
  return Number.isFinite(value)&&value>0?{family:unit.family,label:unit.label,value}:null;
}

function compareUnitPrices(items){
  if(!Array.isArray(items)||items.length<2||items.some(item=>!item||!item.calculation))return {kind:"incomplete"};
  const families=new Set(items.map(item=>item.calculation.family));
  if(families.size!==1)return {kind:"incompatible"};
  const ranked=items.map((item,index)=>({...item,originalIndex:index})).sort((a,b)=>a.calculation.value-b.calculation.value||a.originalIndex-b.originalIndex);
  const allEqual=Math.abs(ranked[0].calculation.value-ranked.at(-1).calculation.value)<1e-9;
  return {kind:allEqual?"equal":"ranked",label:ranked[0].calculation.label,ranked};
}

function buildShareParams(items){
  const params=new URLSearchParams();
  items.slice(0,2).forEach((item,index)=>{
    const key=index===0?"a":"b";
    params.set(`${key}n`,item.name||slotLabels[key]);
    params.set(`${key}p`,String(item.price));
    params.set(`${key}q`,String(item.quantity));
    params.set(`${key}u`,item.unit);
  });
  return params.toString();
}

function parseShareParams(search){
  const params=new URLSearchParams(String(search||"").replace(/^\?/,""));
  const items=[];
  for(const key of ["a","b"]){
    const unit=params.get(`${key}u`);
    const price=parseNumber(params.get(`${key}p`));
    const quantity=parseNumber(params.get(`${key}q`));
    if(!units[unit]||price<=0||quantity<=0)return [];
    items.push({name:params.get(`${key}n`)||slotLabels[key],price,quantity,unit});
  }
  return items.length===2?items:[];
}

function formatIntegerString(value){
  const raw=String(value??"").trim();
  const negative=raw.startsWith("-");
  const digits=raw.replace(/\D/g,"").replace(/^0+(?=\d)/,"");
  if(!digits)return "";
  try{return `${negative?"-":""}${BigInt(digits).toLocaleString("ko-KR")}`;}catch{return `${negative?"-":""}${digits}`;}
}

function safeUrl(value){
  try{
    const text=String(value??"").trim();
    if(!text)return "#";
    const url=new URL(text,typeof location!=="undefined"?location.href:"https://example.com/");
    return ["http:","https:"].includes(url.protocol)?url.href:"#";
  }catch{return "#";}
}

function trendText(item){
  if(item.trend==="new")return "신규";
  if(item.trend==="up")return `▲ ${Math.abs(Number(item.rank_change)||0)}`;
  if(item.trend==="down")return `▼ ${Math.abs(Number(item.rank_change)||0)}`;
  return "변동 없음";
}

function storageGet(key){
  try{
    const value=JSON.parse(localStorage.getItem(key)||"[]");
    return Array.isArray(value)?value:[];
  }catch{return [];}
}

function storageSet(key,value){
  try{localStorage.setItem(key,JSON.stringify(value));return true;}catch{return false;}
}

function createComparisonCard(slot){
  const fieldset=document.createElement("fieldset");
  fieldset.className="calc-card";
  fieldset.dataset.slot=slot;
  fieldset.innerHTML=`<legend>${slotLabels[slot]}</legend><button class="remove-product" type="button" data-remove-slot="${slot}" aria-label="${slotLabels[slot]} 비교에서 제거">제거</button><label for="${slot}Name">상품 이름 <small>선택</small></label><input id="${slot}Name" class="name-input" autocomplete="off" placeholder="예: ${slotLabels[slot]}"><label for="${slot}Price">가격</label><div class="input-with-suffix"><input id="${slot}Price" class="price-input" inputmode="numeric" autocomplete="off" placeholder="12,900" aria-describedby="calcHelp"><span>원</span></div><label for="${slot}Qty">총 용량 또는 수량</label><div class="qty-row"><input id="${slot}Qty" class="quantity-input" inputmode="decimal" autocomplete="off" placeholder="1"><select id="${slot}Unit" class="unit-input" aria-label="${slotLabels[slot]} 단위">${Object.keys(units).map(unit=>`<option value="${unit}">${unit}</option>`).join("")}</select></div><output id="${slot}Result" class="item-result" for="${slot}Price ${slot}Qty ${slot}Unit">입력하면 단위가격을 계산합니다.</output>`;
  return fieldset;
}

function activeSlots(){
  return [...document.querySelectorAll("#comparisonItems [data-slot]")].map(card=>card.dataset.slot);
}

function readComparisonItem(slot){
  const priceValue=document.querySelector(`#${slot}Price`).value;
  const quantityValue=document.querySelector(`#${slot}Qty`).value;
  const unit=document.querySelector(`#${slot}Unit`).value;
  const name=document.querySelector(`#${slot}Name`).value.trim()||slotLabels[slot];
  return {slot,name,price:parseNumber(priceValue),quantity:parseNumber(quantityValue),unit,calculation:calculateUnitPrice(priceValue,quantityValue,unit)};
}

function updateItemResult(slot){
  const item=readComparisonItem(slot);
  const output=document.querySelector(`#${slot}Result`);
  output.textContent=item.calculation?`${item.calculation.label}당 ${money(item.calculation.value,2)}`:"입력하면 단위가격을 계산합니다.";
}

function showCalculatorMessage(text,error=false){
  const message=document.querySelector("#calcMessage");
  message.hidden=false;
  message.textContent=text;
  message.classList.toggle("is-error",error);
}

function conclusionFor(comparison){
  if(comparison.kind==="equal")return `모든 상품의 ${comparison.label}당 가격이 같습니다.`;
  const first=comparison.ranked[0];
  const second=comparison.ranked[1];
  const percent=(second.calculation.value-first.calculation.value)/second.calculation.value*100;
  const last=first.name.at(-1)||"";
  const code=last.charCodeAt(0);
  const particle=code>=0xac00&&code<=0xd7a3&&(code-0xac00)%28!==0?"이":"가";
  return `${first.name}${particle} ${second.name}보다 약 ${percent.toFixed(1)}% 저렴합니다.`;
}

function renderComparison(comparison){
  const result=document.querySelector("#comparisonResult");
  const list=document.querySelector("#rankingList");
  const lowest=comparison.ranked[0].calculation.value;
  document.querySelector("#resultBasis").textContent=`${comparison.label}당 가격 기준`;
  list.innerHTML=comparison.ranked.map((item,index)=>{
    const winnerDifference=index===0?"가장 저렴":`${((item.calculation.value-comparison.ranked[0].calculation.value)/item.calculation.value*100).toFixed(1)}% 차이`;
    const width=Math.max(8,lowest/item.calculation.value*100);
    return `<li class="ranking-item${index===0?" is-winner":""}"><span class="bar" style="width:${width.toFixed(2)}%" aria-hidden="true"></span><span class="ranking-number">${index+1}위</span><span class="ranking-name"><b>${esc(item.name)}</b><small>${esc(item.price.toLocaleString("ko-KR"))}원 / ${esc(item.quantity)}${esc(item.unit)} · ${winnerDifference}</small></span><span class="ranking-price">${money(item.calculation.value,2)}</span></li>`;
  }).join("");
  document.querySelector("#resultConclusion").textContent=conclusionFor(comparison);
  result.hidden=false;
  document.querySelector("#calcMessage").hidden=true;
}

function comparisonSnapshot(items,comparison){
  return {createdAt:new Date().toISOString(),items:items.map(({name,price,quantity,unit})=>({name,price,quantity,unit})),summary:conclusionFor(comparison)};
}

function saveComparison(items,comparison){
  const next=[comparisonSnapshot(items,comparison),...storageGet(storageKeys.comparisons)].slice(0,5);
  storageSet(storageKeys.comparisons,next);
  renderComparisonHistory();
}

function runComparison(save=false){
  const items=activeSlots().map(readComparisonItem);
  items.forEach(item=>updateItemResult(item.slot));
  const comparison=compareUnitPrices(items);
  document.querySelector("#comparisonResult").hidden=true;
  if(comparison.kind==="incomplete"){
    showCalculatorMessage("모든 상품의 가격과 용량을 0보다 크고 정확한 숫자로 입력해 주세요.",true);
    return null;
  }
  if(comparison.kind==="incompatible"){
    showCalculatorMessage("비교할 수 없는 단위입니다. g↔kg, ml↔L 또는 같은 수량 단위끼리 선택해 주세요.",true);
    return null;
  }
  renderComparison(comparison);
  if(save)saveComparison(items,comparison);
  return {items,comparison};
}

function resetCalculator(clearUrl=true){
  document.querySelectorAll("#comparisonItems [data-slot]").forEach(card=>{
    if(!["a","b"].includes(card.dataset.slot))card.remove();
  });
  document.querySelector("#comparisonForm").reset();
  for(const slot of ["a","b"])updateItemResult(slot);
  document.querySelector("#comparisonResult").hidden=true;
  showCalculatorMessage("두 상품의 가격과 용량을 입력한 뒤 비교해 주세요.");
  document.querySelector("#copyStatus").textContent="";
  document.querySelector("#addProduct").disabled=false;
  if(clearUrl&&typeof history!=="undefined"&&location.search){history.replaceState(null,"",location.pathname+location.hash);}
}

function fillItems(items){
  resetCalculator(false);
  while(activeSlots().length<Math.min(items.length,4))addProduct();
  items.slice(0,4).forEach((item,index)=>{
    const slot=activeSlots()[index];
    document.querySelector(`#${slot}Name`).value=item.name||slotLabels[slot];
    document.querySelector(`#${slot}Price`).value=formatIntegerString(item.price);
    document.querySelector(`#${slot}Qty`).value=String(item.quantity);
    document.querySelector(`#${slot}Unit`).value=item.unit;
    updateItemResult(slot);
  });
  return runComparison(false);
}

function addProduct(){
  const used=activeSlots();
  const slot=slots.find(value=>!used.includes(value));
  if(!slot)return;
  document.querySelector("#comparisonItems").append(createComparisonCard(slot));
  document.querySelector("#addProduct").disabled=activeSlots().length>=4;
  document.querySelector("#comparisonResult").hidden=true;
  showCalculatorMessage("추가한 상품의 가격과 용량도 입력해 주세요.");
  document.querySelector(`#${slot}Name`).focus();
}

function removeProduct(slot){
  document.querySelector(`#comparisonItems [data-slot="${slot}"]`)?.remove();
  document.querySelector("#addProduct").disabled=false;
  document.querySelector("#comparisonResult").hidden=true;
  showCalculatorMessage("변경된 상품 정보로 다시 비교해 주세요.");
}

function applyExample(name){
  const example=examples[name];
  if(!example)return;
  fillItems([example.a,example.b]);
  document.querySelector("#aName").focus();
}

function renderComparisonHistory(){
  const section=document.querySelector("#comparisonHistory");
  if(!section)return;
  const entries=storageGet(storageKeys.comparisons).slice(0,5);
  section.hidden=!entries.length;
  document.querySelector("#historyList").innerHTML=entries.map((entry,index)=>`<button class="history-entry" type="button" data-history-index="${index}"><span>${esc(entry.items.map(item=>item.name).join(" · "))}</span><small>${esc(entry.summary)}</small></button>`).join("");
}

async function copyText(value,status){
  try{
    await navigator.clipboard.writeText(value);
  }catch{
    const input=document.createElement("textarea");
    input.value=value;
    input.style.position="fixed";
    input.style.opacity="0";
    document.body.append(input);
    input.select();
    document.execCommand("copy");
    input.remove();
  }
  document.querySelector("#copyStatus").textContent=status;
}

function currentComparison(){return runComparison(false);}

function shareUrl(items){
  const base=`${location.origin}${location.pathname}`;
  return `${base}?${buildShareParams(items)}`;
}

function comparisonText(comparison){
  const lines=comparison.ranked.map((item,index)=>`${index+1}위 ${item.name} · ${item.calculation.label}당 ${money(item.calculation.value,2)}`);
  return [`쇼핑레이더 단위가격 비교`,...lines,conclusionFor(comparison)].join("\n");
}

function initCalculator(){
  const form=document.querySelector("#comparisonForm");
  if(!form)return;
  form.addEventListener("input",event=>{
    if(event.target.classList.contains("price-input"))event.target.value=formatIntegerString(event.target.value);
    const slot=event.target.closest("[data-slot]")?.dataset.slot;
    if(slot)updateItemResult(slot);
    document.querySelector("#comparisonResult").hidden=true;
    showCalculatorMessage("입력 내용을 확인한 뒤 단위가격 비교하기를 눌러 주세요.");
  });
  form.addEventListener("change",event=>{
    const slot=event.target.closest("[data-slot]")?.dataset.slot;
    if(slot)updateItemResult(slot);
  });
  form.addEventListener("click",event=>{
    const remove=event.target.closest("[data-remove-slot]");
    if(remove)removeProduct(remove.dataset.removeSlot);
  });
  form.addEventListener("submit",event=>{event.preventDefault();runComparison(true);});
  document.querySelector("#addProduct").addEventListener("click",addProduct);
  document.querySelector("#resetCalculator").addEventListener("click",()=>resetCalculator(true));
  document.querySelectorAll("[data-example]").forEach(button=>button.addEventListener("click",()=>applyExample(button.dataset.example)));
  document.querySelector("#clearHistory").addEventListener("click",()=>{storageSet(storageKeys.comparisons,[]);renderComparisonHistory();});
  document.querySelector("#historyList").addEventListener("click",event=>{
    const button=event.target.closest("[data-history-index]");
    if(!button)return;
    const entry=storageGet(storageKeys.comparisons)[Number(button.dataset.historyIndex)];
    if(entry)fillItems(entry.items);
  });
  document.querySelector("#copyResultLink").addEventListener("click",()=>{
    const result=currentComparison();
    if(result)copyText(shareUrl(result.items),"링크를 복사했습니다.");
  });
  document.querySelector("#copyResultText").addEventListener("click",()=>{
    const result=currentComparison();
    if(result)copyText(comparisonText(result.comparison),"결과를 복사했습니다.");
  });
  renderComparisonHistory();
  const shared=parseShareParams(location.search);
  if(shared.length===2)fillItems(shared);
}

function normalizeProduct(item){
  if(!item||typeof item!=="object")return null;
  const productId=String(item.product_id||"").trim();
  const name=String(item.name||"").trim();
  const category=String(item.category||"").trim();
  const rank=Number(item.rank);
  const url=safeUrl(item.url);
  if(!/^[0-9A-Za-z_-]+$/.test(productId)||!name||!category||!Number.isInteger(rank)||rank<1||url==="#")return null;
  const price=Number(item.price);
  return {product_id:productId,name,category,category_id:String(item.category_id||""),rank,url,image:safeUrl(item.image),price:Number.isFinite(price)&&price>0?price:null,trend:item.trend,rank_change:Number(item.rank_change)||0,top10_count_30d:Number(item.top10_count_30d)||0,appearances_30d:Number(item.appearances_30d)||0};
}

function productData(item){return encodeURIComponent(JSON.stringify({product_id:item.product_id,name:item.name,category:item.category,price:item.price,url:item.url,image:item.image,detail_url:`product/${encodeURIComponent(item.product_id)}.html`}));}

function productCard(item){
  const detail=`product/${encodeURIComponent(item.product_id)}.html`;
  const image=item.image!=="#"?`<img loading="lazy" width="512" height="512" src="${esc(item.image)}" alt="${esc(item.name)}">`:"";
  const data=productData(item);
  const saved=storageGet(storageKeys.saved).some(value=>value.product_id===item.product_id);
  return `<article class="card" data-product="${data}"><button class="favorite-button" type="button" aria-label="${esc(item.name)} 찜하기" aria-pressed="${saved}">${saved?"★":"☆"}</button><a class="card-img product-detail-link" href="${detail}">${image}</a><div class="card-body"><div class="rank">${esc(item.rank)}위 <small>${esc(trendText(item))}</small></div><div class="category">${esc(item.category)}</div><h3><a class="product-detail-link" href="${detail}">${esc(item.name)}</a></h3><div class="price">${money(item.price)}</div><a class="primary" target="_blank" rel="nofollow sponsored noopener" href="${esc(item.url)}">쿠팡에서 보기</a></div></article>`;
}

function productScore(item,query){
  if(!query)return 1;
  const name=item.name.toLocaleLowerCase("ko");
  const category=item.category.toLocaleLowerCase("ko");
  if(name===query)return 5;
  if(name.startsWith(query))return 4;
  if(name.includes(query))return 3;
  if(category===query)return 2;
  if(category.includes(query))return 1;
  return 0;
}

let allProducts=[];
let selectedCategory="all";

function renderProducts(){
  const search=document.querySelector("#productSearch");
  if(!search)return;
  const query=search.value.trim().toLocaleLowerCase("ko");
  const rows=allProducts.map(item=>({item,score:productScore(item,query)}))
    .filter(row=>row.score>0&&(selectedCategory==="all"||row.item.category===selectedCategory))
    .sort((a,b)=>b.score-a.score||a.item.rank-b.item.rank)
    .slice(0,100);
  document.querySelector("#productGrid").innerHTML=rows.map(row=>productCard(row.item)).join("");
  const summary=document.querySelector("#searchSummary");
  summary.hidden=!query&&!rows.length;
  summary.textContent=rows.length?`${rows.length}개 상품 표시 중`:"검색 조건에 맞는 상품이 없습니다.";
}

function renderCategoryChips(items){
  const counts={};
  items.forEach(item=>counts[item.category]=(counts[item.category]||0)+1);
  document.querySelector("#categoryChips").innerHTML=[`<button class="chip" type="button" data-category="all" aria-pressed="true">전체 ${items.length}</button>`,...Object.entries(counts).sort((a,b)=>a[0].localeCompare(b[0],"ko")).map(([name,count])=>`<button class="chip" type="button" data-category="${encodeURIComponent(name)}" aria-pressed="false">${esc(name)} ${count}</button>`)].join("");
}

function trendGroup(title,items,value){
  if(!items.length)return "";
  return `<section class="trend-group"><h3>${title}</h3>${items.slice(0,5).map(item=>`<a href="product/${encodeURIComponent(item.product_id)}.html">${esc(item.name)}<small>${esc(value(item))}</small></a>`).join("")}</section>`;
}

function renderTrends(items){
  const rises=items.filter(item=>item.trend==="up"&&item.rank_change>0).sort((a,b)=>b.rank_change-a.rank_change);
  const falls=items.filter(item=>item.trend==="down"&&item.rank_change<0).sort((a,b)=>a.rank_change-b.rank_change);
  const frequent=items.filter(item=>item.appearances_30d>=2&&item.top10_count_30d>0).sort((a,b)=>b.top10_count_30d-a.top10_count_30d);
  const html=[trendGroup("오늘 많이 오른 상품",rises,item=>`${item.rank_change}계단 상승`),trendGroup("오늘 많이 내려간 상품",falls,item=>`${Math.abs(item.rank_change)}계단 하락`),trendGroup("최근 30일 TOP10 단골",frequent,item=>`${item.top10_count_30d}회 등장`)].filter(Boolean).join("");
  const section=document.querySelector("#trendInsights");
  if(!section)return;
  section.hidden=!html;
  document.querySelector("#trendGroups").innerHTML=html;
}

async function loadProducts(){
  const emptyState=document.querySelector("#emptyState");
  try{
    const response=await fetch("data/products.json",{cache:"no-store"});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const data=await response.json();
    const sourceItems=Array.isArray(data.items)?data.items:[];
    allProducts=sourceItems.map(normalizeProduct).filter(Boolean);
    if(!allProducts.length)return;
    emptyState.hidden=true;
    document.querySelector("#productTools").hidden=false;
    document.querySelector("#rankingNote").textContent=`최근 갱신: ${String(data.updated_at||"").replace("T"," ").slice(0,16)} · 쿠팡 전체 판매량 순위가 아닙니다.`;
    renderCategoryChips(allProducts);
    renderProducts();
    renderTrends(allProducts);
  }catch(error){console.warn("상품 데이터를 불러오지 못했습니다.",error);}
}

function parseProductElement(element){
  try{return JSON.parse(decodeURIComponent(element.closest("[data-product]")?.dataset.product||""));}catch{return null;}
}

function storeProduct(kind,product){
  if(!product?.product_id)return;
  const key=storageKeys[kind];
  const next=[product,...storageGet(key).filter(item=>item.product_id!==product.product_id)].slice(0,8);
  storageSet(key,next);
  renderPersonalProducts();
}

function toggleSaved(product){
  const current=storageGet(storageKeys.saved);
  const exists=current.some(item=>item.product_id===product.product_id);
  storageSet(storageKeys.saved,exists?current.filter(item=>item.product_id!==product.product_id):[product,...current].slice(0,8));
  document.querySelectorAll("[data-product]").forEach(card=>{
    const value=parseProductElement(card);
    if(value?.product_id===product.product_id){
      const button=card.querySelector(".favorite-button");
      if(button){
        button.setAttribute("aria-pressed",String(!exists));
        button.textContent=button.closest(".product-actions")?(!exists?"★ 찜함":"☆ 찜하기"):(!exists?"★":"☆");
      }
    }
  });
  renderPersonalProducts();
}

function syncFavoriteButtons(){
  const savedIds=new Set(storageGet(storageKeys.saved).map(item=>item.product_id));
  document.querySelectorAll("[data-product]").forEach(card=>{
    const product=parseProductElement(card);
    const button=card.querySelector(".favorite-button");
    if(!product||!button)return;
    const saved=savedIds.has(product.product_id);
    button.setAttribute("aria-pressed",String(saved));
    button.textContent=button.closest(".product-actions")?(saved?"★ 찜함":"☆ 찜하기"):(saved?"★":"☆");
  });
}

function miniProduct(item){
  const image=safeUrl(item.image)!=="#"?`<img loading="lazy" width="42" height="42" src="${esc(item.image)}" alt="">`:`<span class="image-placeholder" aria-hidden="true"></span>`;
  const detail=safeUrl(item.detail_url);
  return `<article class="mini-product">${image}<div><b>${esc(item.name)}</b><small>${esc(item.category)} · ${money(item.price)}</small></div><a href="${esc(detail)}">보기</a></article>`;
}

function renderPersonalProducts(){
  const root=document.querySelector("#personalProducts");
  if(!root)return;
  const saved=storageGet(storageKeys.saved).slice(0,8);
  const recent=storageGet(storageKeys.recent).slice(0,8);
  root.hidden=!saved.length&&!recent.length;
  for(const [kind,items] of [["saved",saved],["recent",recent]]){
    const section=document.querySelector(`#${kind}Section`);
    section.hidden=!items.length;
    document.querySelector(`#${kind}Products`).innerHTML=items.map(miniProduct).join("");
  }
}

function initProductFeatures(){
  document.addEventListener("click",event=>{
    const favorite=event.target.closest(".favorite-button");
    if(favorite){const product=parseProductElement(favorite);if(product)toggleSaved(product);return;}
    const detail=event.target.closest(".product-detail-link");
    if(detail){const product=parseProductElement(detail);if(product)storeProduct("recent",product);}
  });
  document.querySelector("#productSearch")?.addEventListener("input",renderProducts);
  document.querySelector("#categoryChips")?.addEventListener("click",event=>{
    const button=event.target.closest("[data-category]");
    if(!button)return;
    selectedCategory=button.dataset.category==="all"?"all":decodeURIComponent(button.dataset.category);
    document.querySelectorAll("#categoryChips .chip").forEach(chip=>chip.setAttribute("aria-pressed",String(chip===button)));
    renderProducts();
  });
  document.querySelectorAll("[data-clear-products]").forEach(button=>button.addEventListener("click",()=>{storageSet(storageKeys[button.dataset.clearProducts],[]);renderPersonalProducts();renderProducts();}));
  const current=document.querySelector("#currentProductData");
  if(current){
    try{storeProduct("recent",JSON.parse(current.textContent));}catch{}
  }
  syncFavoriteButtons();
  renderPersonalProducts();
}

function init(){
  initCalculator();
  initProductFeatures();
  if(document.querySelector("#productGrid"))loadProducts();
}

const publicApi={parseNumber,calculateUnitPrice,compareUnitPrices,buildShareParams,parseShareParams,formatIntegerString,normalizeProduct};
if(typeof window!=="undefined")window.ShoppingRadar=publicApi;
if(typeof module!=="undefined"&&module.exports)module.exports=publicApi;
if(typeof document!=="undefined")init();
