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
  water:{a:{price:12900,quantity:12,unit:"L"},b:{price:10900,quantity:10,unit:"L"}},
  detergent:{a:{price:12900,quantity:2.1,unit:"L"},b:{price:15900,quantity:3,unit:"L"}},
  tissue:{a:{price:16900,quantity:30,unit:"개"},b:{price:19800,quantity:36,unit:"개"}}
};

const esc=value=>String(value??"").replace(/[&<>"']/g,char=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"})[char]);

function parseNumber(value){
  const normalized=String(value??"").replace(/,/g,"").trim();
  if(!normalized)return NaN;
  const number=Number(normalized);
  return Number.isFinite(number)?number:NaN;
}

function money(value,digits=0){
  return Number.isFinite(Number(value))&&Number(value)>0
    ?`${Number(value).toLocaleString("ko-KR",{maximumFractionDigits:digits})}원`
    :"가격 확인";
}

function calculateUnitPrice(price,quantity,unitName){
  const unit=units[unitName];
  const parsedPrice=parseNumber(price);
  const parsedQuantity=parseNumber(quantity);
  if(!unit||!Number.isFinite(parsedPrice)||!Number.isFinite(parsedQuantity)||parsedPrice<=0||parsedQuantity<=0)return null;
  return {family:unit.family,label:unit.label,value:parsedPrice/(parsedQuantity*unit.factor)*unit.basis};
}

function compareUnitPrices(a,b){
  if(!a||!b)return {kind:"incomplete"};
  if(a.family!==b.family)return {kind:"incompatible"};
  if(Math.abs(a.value-b.value)<1e-9)return {kind:"equal",label:a.label,value:a.value};
  const cheaper=a.value<b.value?"상품 A":"상품 B";
  const low=Math.min(a.value,b.value);
  const high=Math.max(a.value,b.value);
  return {kind:"cheaper",cheaper,label:a.label,low,high,percent:(high-low)/high*100};
}

function safeUrl(value){
  try{
    const url=new URL(String(value),location.href);
    return ["http:","https:"].includes(url.protocol)?url.href:"#";
  }catch{return "#";}
}

function trend(item){
  if(item.trend==="new")return "신규";
  if(item.trend==="up")return `▲ ${item.rank_change||""}`.trim();
  if(item.trend==="down")return `▼ ${Math.abs(item.rank_change||0)}`;
  return "변동 없음";
}

function productCard(item){
  const id=encodeURIComponent(item.product_id);
  const imageUrl=safeUrl(item.image);
  const merchantUrl=safeUrl(item.url);
  const image=imageUrl!=="#"?`<img loading="lazy" src="${esc(imageUrl)}" alt="${esc(item.name)}">`:"";
  return `<article class="card"><a class="card-img" href="product/${id}.html">${image}</a><div class="card-body"><div class="rank">${esc(item.rank)}위 <small>${esc(trend(item))}</small></div><div class="category">${esc(item.category)}</div><h3><a href="product/${id}.html">${esc(item.name)}</a></h3><div class="price">${money(item.price)}</div><a class="primary" target="_blank" rel="nofollow sponsored noopener" href="${esc(merchantUrl)}">쿠팡에서 보기</a></div></article>`;
}

function composite(items){
  const groups={};
  items.forEach(item=>(groups[item.category_id]??=[]).push(item));
  Object.values(groups).forEach(group=>group.sort((a,b)=>(a.rank||999)-(b.rank||999)));
  const result=[];
  let row=0;
  while(result.length<100){
    let added=false;
    for(const key of Object.keys(groups).sort()){
      if(groups[key][row]){
        result.push(groups[key][row]);
        added=true;
        if(result.length>=100)break;
      }
    }
    if(!added)break;
    row+=1;
  }
  return result;
}

async function loadProducts(){
  const emptyState=document.querySelector("#emptyState");
  try{
    const response=await fetch("data/products.json",{cache:"no-store"});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const data=await response.json();
    const items=Array.isArray(data.items)?data.items:[];
    if(!items.length)return;
    emptyState.hidden=true;
    document.querySelector("#rankingNote").textContent=`최근 갱신: ${String(data.updated_at||"").replace("T"," ").slice(0,16)} · 쿠팡 전체 판매량 순위가 아닙니다.`;
    const counts={};
    items.forEach(item=>counts[item.category]=(counts[item.category]||0)+1);
    document.querySelector("#categoryChips").innerHTML=Object.entries(counts)
      .sort((a,b)=>a[0].localeCompare(b[0],"ko"))
      .map(([name,count])=>`<a class="chip" href="category/${encodeURIComponent(name)}.html">${esc(name)} ${count}</a>`)
      .join("");
    document.querySelector("#productGrid").innerHTML=composite(items).map(productCard).join("");
  }catch(error){
    console.warn("상품 데이터를 불러오지 못했습니다.",error);
  }
}

function readCalculatorItem(prefix){
  return calculateUnitPrice(
    document.querySelector(`#${prefix}Price`).value,
    document.querySelector(`#${prefix}Qty`).value,
    document.querySelector(`#${prefix}Unit`).value
  );
}

function hasCalculatorInput(prefix){
  return Boolean(document.querySelector(`#${prefix}Price`).value.trim()||document.querySelector(`#${prefix}Qty`).value.trim());
}

function renderCalculator(){
  const a=readCalculatorItem("a");
  const b=readCalculatorItem("b");
  const aOutput=document.querySelector("#aResult");
  const bOutput=document.querySelector("#bResult");
  const winner=document.querySelector("#calcWinner");
  aOutput.textContent=a?`${a.label}당 ${money(a.value,2)}`:"입력하면 단위가격을 계산합니다.";
  bOutput.textContent=b?`${b.label}당 ${money(b.value,2)}`:"입력하면 단위가격을 계산합니다.";
  const comparison=compareUnitPrices(a,b);
  winner.classList.remove("is-error");
  if(comparison.kind==="incomplete"){
    if(hasCalculatorInput("a")||hasCalculatorInput("b")){
      winner.textContent="두 상품 모두 가격과 용량을 0보다 큰 숫자로 입력해 주세요.";
      winner.classList.add("is-error");
    }else{
      winner.textContent="두 상품의 가격과 용량을 입력하면 어느 쪽이 얼마나 저렴한지 알려드립니다.";
    }
  }else if(comparison.kind==="incompatible"){
    winner.textContent="비교할 수 없는 단위입니다. g↔kg, ml↔L 또는 같은 수량 단위끼리 선택해 주세요.";
    winner.classList.add("is-error");
  }else if(comparison.kind==="equal"){
    winner.textContent=`두 상품의 ${comparison.label}당 가격이 ${money(comparison.value,2)}으로 같습니다.`;
  }else{
    winner.textContent=`${comparison.cheaper}가 ${comparison.label}당 가격 기준 약 ${comparison.percent.toFixed(1)}% 저렴합니다. (${money(comparison.low,2)} vs ${money(comparison.high,2)})`;
  }
}

function formatPriceInput(event){
  const digits=event.target.value.replace(/\D/g,"").replace(/^0+(?=\d)/,"");
  event.target.value=digits?Number(digits).toLocaleString("ko-KR"):"";
  renderCalculator();
}

function applyExample(name){
  const example=examples[name];
  if(!example)return;
  for(const prefix of ["a","b"]){
    const item=example[prefix];
    document.querySelector(`#${prefix}Price`).value=item.price.toLocaleString("ko-KR");
    document.querySelector(`#${prefix}Qty`).value=String(item.quantity);
    document.querySelector(`#${prefix}Unit`).value=item.unit;
  }
  renderCalculator();
  document.querySelector("#aPrice").focus();
}

function init(){
  document.querySelectorAll(".price-input").forEach(input=>input.addEventListener("input",formatPriceInput));
  ["#aQty","#bQty"].forEach(selector=>document.querySelector(selector).addEventListener("input",renderCalculator));
  ["#aUnit","#bUnit"].forEach(selector=>document.querySelector(selector).addEventListener("change",renderCalculator));
  document.querySelectorAll("[data-example]").forEach(button=>button.addEventListener("click",()=>applyExample(button.dataset.example)));
  loadProducts();
}

if(typeof window!=="undefined")window.ShoppingRadar={parseNumber,calculateUnitPrice,compareUnitPrices};
if(typeof module!=="undefined"&&module.exports)module.exports={parseNumber,calculateUnitPrice,compareUnitPrices};
if(typeof document!=="undefined")init();
