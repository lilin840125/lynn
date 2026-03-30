# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, session, redirect, url_for, Response
import requests as req
from bs4 import BeautifulSoup
import re, os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'yp-analyzer-2026')

# 登录密码，从环境变量读，默认 yp2026
LOGIN_PASSWORD = os.environ.get('LOGIN_PASSWORD', 'yp2026')

COOKIE = os.environ.get('YP_COOKIE', (
    "_ga_G7TMEY37GF=GS2.1.s1770822067$o1$g1$t1770822097$j30$l0$h0; "
    "_ga=GA1.1.825575630.1770822068; "
    "think_lang=zh-cn; "
    "PHPSESSID=cd351dab469e563331eed0eb3f11568e; "
    "user_name=Lynn%20Lee; "
    "user_id=2901; "
    "_ga_N6QD2QCJZV=GS2.1.s1774704622$o6$g1$t1774705221$j48$l0$h0; "
    "_ga_84WRH024M5=GS2.1.s1774704600$o97$g1$t1774707226$j22$l0$h0"
))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Cookie": COOKIE,
    "Referer": "https://www.yeahpromos.com/",
}

# ── 登录页 HTML ───────────────────────────────────────────────
LOGIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YP 分析器 — 登录</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f0f0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.box{background:#fff;border-radius:14px;padding:36px 32px;width:100%;max-width:360px;border:1px solid #e5e5e5}
h1{font-size:20px;font-weight:700;color:#111;margin-bottom:6px}
.sub{font-size:13px;color:#999;margin-bottom:24px}
label{font-size:11px;color:#999;font-weight:600;letter-spacing:.05em;text-transform:uppercase;display:block;margin-bottom:6px}
input[type=password]{width:100%;padding:10px 13px;border:1px solid #ddd;border-radius:8px;font-size:14px;outline:none;margin-bottom:14px}
input[type=password]:focus{border-color:#111}
.btn{width:100%;padding:11px;background:#111;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer}
.btn:hover{background:#333}
.err{background:#fee2e2;color:#991b1b;padding:9px 12px;border-radius:7px;font-size:13px;margin-bottom:14px;display:none}
.err.show{display:block}
</style>
</head>
<body>
<div class="box">
  <h1>YP Offer 分析器</h1>
  <p class="sub">请输入密码登录</p>
  <div class="err" id="err">密码错误，请重试</div>
  <label>密码</label>
  <input type="password" id="pw" placeholder="输入密码">
  <label style="margin-top:14px">你的 YP Cookie</label>
  <textarea id="ck" rows="3" placeholder="从浏览器 F12 → Network → Request Headers → Cookie 复制粘贴" style="width:100%;padding:9px 12px;border:1px solid #ddd;border-radius:8px;font-size:11px;font-family:monospace;resize:vertical;outline:none;margin-bottom:14px"></textarea>
  <div class="hint" style="font-size:11px;color:#bbb;margin-top:-10px;margin-bottom:14px;line-height:1.5">Cookie 只在你的浏览器里保存，不会被他人看到</div>
  <button class="btn" onclick="login()" onkeydown="if(event.key==='Enter')login()">登录</button>
</div>
<script>
async function login(){
  const pw = document.getElementById('pw').value;
  const ck = document.getElementById('ck').value.trim();
  if(!ck){alert('请填写你的 YP Cookie');return;}
  const r = await fetch('/login', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:pw,cookie:ck})});
  const d = await r.json();
  if(d.ok){
    sessionStorage.setItem('yp_cookie', ck);
    location.href='/';
  } else document.getElementById('err').classList.add('show');
}
</script>
</body>
</html>"""

# ── 主页面 HTML ───────────────────────────────────────────────
MAIN_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>YP Offer 分析器</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f0f0;min-height:100vh;padding:28px 16px}
.wrap{max-width:800px;margin:0 auto}
.top-bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:20px}
h1{font-size:22px;font-weight:700;color:#111}
.logout{font-size:12px;color:#999;cursor:pointer;text-decoration:underline}
.logout:hover{color:#333}
.card{background:#fff;border-radius:12px;padding:22px;margin-bottom:14px;border:1px solid #e5e5e5}
label{font-size:11px;color:#999;display:block;margin-bottom:5px;font-weight:600;letter-spacing:.05em;text-transform:uppercase}
textarea{width:100%;padding:10px 13px;border:1px solid #ddd;border-radius:8px;font-size:13px;font-family:monospace;resize:vertical;min-height:80px;outline:none;line-height:1.7}
textarea:focus{border-color:#333}
input[type=text]{width:100%;padding:9px 13px;border:1px solid #ddd;border-radius:8px;font-size:13px;outline:none}
input[type=text]:focus{border-color:#333}
select{width:100%;padding:9px 13px;border:1px solid #ddd;border-radius:8px;font-size:13px;outline:none;background:#fff}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.btn{width:100%;padding:11px;background:#111;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;margin-top:10px}
.btn:hover{background:#333}
.btn:disabled{opacity:.4;cursor:not-allowed}
.prog-bar{height:5px;background:#eee;border-radius:3px;margin-top:10px;overflow:hidden;display:none}
.prog-bar.show{display:block}
.prog-fill{height:100%;background:#111;border-radius:3px;transition:width .3s}
.prog-txt{font-size:12px;color:#999;margin-top:5px;text-align:center;display:none}
.prog-txt.show{display:block}
.cookie-toggle{font-size:12px;color:#bbb;cursor:pointer;margin-top:10px;display:inline-block}
.cookie-toggle:hover{color:#888}
.error{display:none;background:#fee2e2;color:#991b1b;padding:11px 14px;border-radius:8px;font-size:13px;margin-bottom:12px}
.error.show{display:block}
.tbl{width:100%;border-collapse:collapse;font-size:13px}
.tbl th{background:#f7f7f7;padding:8px 11px;text-align:left;font-size:11px;font-weight:600;color:#888;border-bottom:2px solid #eee;white-space:nowrap}
.tbl td{padding:8px 11px;border-bottom:1px solid #f0f0f0;vertical-align:middle}
.tbl tr:hover td{background:#fafafa}
.badge{display:inline-block;padding:2px 9px;border-radius:99px;font-size:11px;font-weight:600;white-space:nowrap}
.b-yes{background:#dcfce7;color:#166534}
.b-maybe{background:#fef9c3;color:#854d0e}
.b-no{background:#fee2e2;color:#991b1b}
.b-pass{background:#dcfce7;color:#166534}
.b-fail{background:#fee2e2;color:#991b1b}
.offer-card{background:#fff;border-radius:12px;border:1px solid #e5e5e5;margin-bottom:14px;overflow:hidden}
.offer-head{padding:14px 18px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.offer-name{font-size:15px;font-weight:700;color:#111}
.offer-meta{font-size:11px;color:#bbb;margin-top:3px;font-family:monospace}
.offer-body{padding:16px 18px}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px}
.metrics.three{grid-template-columns:repeat(3,1fr)}
.met{background:#f7f7f7;border-radius:8px;padding:11px;text-align:center}
.met-v{font-size:17px;font-weight:700;color:#111}
.met-l{font-size:10px;color:#aaa;margin-top:3px}
.chks{display:flex;flex-direction:column;gap:5px;margin-bottom:13px}
.chk{display:flex;justify-content:space-between;align-items:center;padding:8px 11px;border-radius:7px;font-size:13px;font-weight:500}
.c-pass{background:#f0fdf4;color:#166534}
.c-fail{background:#fef2f2;color:#991b1b}
.c-warn{background:#fffbeb;color:#92400e}
.chk-v{font-weight:400;font-size:12px;opacity:.75}
.cpc-row{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:13px}
.cpc-box{background:#eff6ff;border-radius:8px;padding:12px;text-align:center}
.cpc-v{font-size:17px;font-weight:700;color:#1e40af}
.cpc-l{font-size:10px;color:#93c5fd;margin-top:3px}
.sf-section{margin-bottom:12px}
.sf-link{display:block;font-size:12px;color:#1d4ed8;word-break:break-all;padding:3px 0;text-decoration:none}
.sf-link:hover{text-decoration:underline}
.sf-empty{font-size:12px;color:#bbb}
.prices{background:#f7f7f7;border-radius:8px;padding:10px;font-size:12px;line-height:2}
.p-ok{color:#166534;font-weight:500}
.p-na{color:#991b1b}
.sect-lbl{font-size:11px;color:#aaa;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin-bottom:6px}
</style>
</head>
<body>
<div class="wrap">
  <div class="top-bar">
    <h1>YP Offer 分析器</h1>
    <span class="logout" onclick="logout()">退出登录</span>
  </div>

  <div class="card">
    <label>Offer 链接（每行一个）</label>
    <textarea id="urls" placeholder="https://www.yeahpromos.com/index/offer/brand_detail?advert_id=369227&site_id=12052&#10;https://www.yeahpromos.com/index/offer/brand_detail?advert_id=380662&site_id=12052"></textarea>
    <div class="grid2">
      <div>
        <label style="margin-top:10px">最低预估佣金 ($)</label>
        <input type="text" id="min-comm" value="3.5">
      </div>
      <div>
        <label style="margin-top:10px">Storefront 检测</label>
        <select id="sf">
          <option value="auto">自动检测</option>
          <option value="yes">全部标记有</option>
          <option value="no">全部标记无</option>
        </select>
      </div>
    </div>
    <div style="font-size:12px;color:#bbb;margin-top:8px">Cookie 已从登录时自动载入。过期请<a href="#" style="color:#999;text-decoration:underline" onclick="logout();return false;">重新登录</a>更新。</div>
    <textarea id="cookie" style="display:none"></textarea>
    <button class="btn" id="btn" onclick="runAll()">开始分析</button>
    <div class="prog-bar" id="prog-bar"><div class="prog-fill" id="prog-fill" style="width:0"></div></div>
    <div class="prog-txt" id="prog-txt"></div>
  </div>

  <div class="error" id="err"></div>
  <div id="result"></div>

  <hr style="border:none;border-top:1px solid #e5e5e5;margin:8px 0 20px">

  <div class="card">
    <label>Top 10 产品筛选（按评论数，排除 Expired 和 N/Avail）</label>
    <textarea id="tp-url" style="min-height:52px" placeholder="粘贴商家详情页链接，每行一个"></textarea>
    <button class="btn" id="tp-btn" onclick="runTopProducts()" style="margin-top:10px">筛选 Top 10 产品</button>
    <div class="prog-bar" id="tp-prog-bar"><div class="prog-fill" id="tp-prog-fill" style="width:0"></div></div>
    <div class="prog-txt" id="tp-prog-txt"></div>
  </div>
  <div id="tp-result"></div>
</div>

<script>
function toggleCookie(){
  const a=document.getElementById('c-area'),show=a.style.display==='none';
  a.style.display=show?'block':'none';
  document.getElementById('c-arr').textContent=show?'▼':'▶';
}
async function logout(){
  await fetch('/logout',{method:'POST'});
  location.href='/login';
}
async function runAll(){
  const raw=document.getElementById('urls').value.trim();
  if(!raw){setErr('请输入链接');return;}
  const urls=raw.split('\\n').map(s=>s.trim()).filter(s=>s.includes('advert_id'));
  if(!urls.length){setErr('没有找到含 advert_id 的链接');return;}
  const minComm=parseFloat(document.getElementById('min-comm').value)||3.5;
  const sf=document.getElementById('sf').value;
  const cookie=sessionStorage.getItem('yp_cookie')||document.getElementById('cookie').value.trim();
  clearErr();
  document.getElementById('result').innerHTML='';
  document.getElementById('btn').disabled=true;
  document.getElementById('btn').textContent='分析中...';
  document.getElementById('prog-bar').classList.add('show');
  document.getElementById('prog-txt').classList.add('show');
  const results=[];
  for(let i=0;i<urls.length;i++){
    document.getElementById('prog-fill').style.width=Math.round(i/urls.length*100)+'%';
    document.getElementById('prog-txt').textContent=`${i+1} / ${urls.length}`;
    try{
      const r=await fetch('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({url:urls[i],sf,min_comm:minComm,cookie})});
      results.push(await r.json());
    }catch(e){results.push({url:urls[i],error:e.message});}
  }
  document.getElementById('prog-fill').style.width='100%';
  document.getElementById('prog-txt').textContent='完成';
  document.getElementById('btn').disabled=false;
  document.getElementById('btn').textContent='重新分析';
  render(results,minComm);
}
function verdict(d,minComm){
  const c2=d.est_commission>=minComm,c3=d.unavail_ratio<=0.1,
        c4=d.has_storefront,c5=(d.expired_count||0)===0;
  const n=[c2,c3,c4,c5].filter(Boolean).length;
  return{c2,c3,c4,c5,n,
    cls:n===4?'b-yes':n>=2?'b-maybe':'b-no',
    txt:n===4?'值得投放':n>=2?'谨慎投放':'不建议'};
}
function render(results,minComm){
  const ok=results.filter(r=>!r.error);
  let html='';
  if(ok.length>0){
    const rows=ok.map(d=>{
      const v=verdict(d,minComm);
      const cpcMin=(d.est_commission/50).toFixed(3),cpcMax=(d.est_commission/30).toFixed(3);
      return `<tr>
        <td><strong>${d.merchant_name}</strong></td>
        <td>${d.commission_rate}%</td>
        <td>$${d.avg_price.toFixed(2)}</td>
        <td>$${d.est_commission.toFixed(2)}</td>
        <td>${(d.unavail_ratio*100).toFixed(0)}%</td>
        <td><span style="color:#166534">${d.avail_count}</span> / <span style="color:#991b1b">${d.expired_count||0}过期</span></td>
        <td><span class="badge ${d.has_storefront?'b-pass':'b-fail'}">${d.has_storefront?'有':'无'}</span></td>
        <td style="font-family:monospace;font-size:12px">$${cpcMin}–$${cpcMax}</td>
        <td><span class="badge ${v.cls}">${v.txt}</span></td>
      </tr>`;
    }).join('');
    html+=`<div class="card"><div class="sect-lbl" style="margin-bottom:10px">汇总 — 共${results.length}个，成功${ok.length}个</div>
    <div style="overflow-x:auto"><table class="tbl">
      <thead><tr><th>商家名称</th><th>佣金率</th><th>均价</th><th>预估佣金</th><th>N/Avail</th><th>有效/过期</th><th>Storefront</th><th>CPC区间</th><th>建议</th></tr></thead>
      <tbody>${rows}</tbody>
    </table></div></div>`;
  }
  ok.forEach(d=>{
    const v=verdict(d,minComm);
    const cpcMin=(d.est_commission/50).toFixed(3),cpcMax=(d.est_commission/30).toFixed(3);
    const unavailPct=(d.unavail_ratio*100).toFixed(1);
    const pricesHtml=(d.prices||[]).slice(0,40).map(p=>
      p>0?`<span class="p-ok">$${p.toFixed(2)}</span>`:`<span class="p-na">N/A</span>`
    ).join(' ')+((d.prices||[]).length>40?` …共${d.prices.length}个`:'');
    const sfHtml=d.storefront_links&&d.storefront_links.length
      ?d.storefront_links.map(l=>`<a class="sf-link" href="${l}" target="_blank">${l}</a>`).join('')
      :'<span class="sf-empty">未找到 Storefront 链接</span>';
    html+=`<div class="offer-card">
      <div class="offer-head">
        <div>
          <div class="offer-name">${d.merchant_name}</div>
          <div class="offer-meta">advert_id: ${d.advert_id} · ${d.commission_range}</div>
        </div>
        <span class="badge ${v.cls}">${v.txt}</span>
      </div>
      <div class="offer-body">
        <div class="metrics">
          <div class="met"><div class="met-v">$${d.avg_price.toFixed(2)}</div><div class="met-l">平均售价</div></div>
          <div class="met"><div class="met-v">$${d.est_commission.toFixed(2)}</div><div class="met-l">预估单次佣金</div></div>
          <div class="met"><div class="met-v" style="color:${d.unavail_ratio<=0.1?'#166534':'#991b1b'}">${unavailPct}%</div><div class="met-l">N/Avail 占比</div></div>
          <div class="met"><div class="met-v">${d.commission_rate}%</div><div class="met-l">佣金率(均)</div></div>
        </div>
        <div class="metrics three">
          <div class="met"><div class="met-v" style="color:#166534">${d.avail_count}</div><div class="met-l">有效产品数</div></div>
          <div class="met"><div class="met-v" style="color:#991b1b">${d.expired_count||0}</div><div class="met-l">过期产品数</div></div>
          <div class="met"><div class="met-v" style="color:#92400e">${d.unavail_count}</div><div class="met-l">N/Avail 产品数</div></div>
        </div>
        <div class="chks">
          <div class="chk ${v.c2?'c-pass':'c-fail'}"><span>${v.c2?'✓':'✗'}  预估佣金 ≥ $${minComm}</span><span class="chk-v">$${d.est_commission.toFixed(2)}</span></div>
          <div class="chk ${v.c3?'c-pass':'c-warn'}"><span>${v.c3?'✓':'✗'}  N/Avail ≤ 10%</span><span class="chk-v">${unavailPct}% (${d.unavail_count}/${d.total_products})</span></div>
          <div class="chk ${v.c4?'c-pass':'c-fail'}"><span>${v.c4?'✓':'✗'}  有 Storefront Links</span><span class="chk-v">${d.has_storefront?'有':'无'}</span></div>
          <div class="chk ${v.c5?'c-pass':'c-fail'}"><span>${v.c5?'✓':'✗'}  无 Expired 产品</span><span class="chk-v">${d.expired_count||0}个已过期</span></div>
        </div>
        <div class="cpc-row">
          <div class="cpc-box"><div class="cpc-v">$${cpcMin}</div><div class="cpc-l">最低出价 (÷50)</div></div>
          <div class="cpc-box"><div class="cpc-v">$${cpcMax}</div><div class="cpc-l">最高出价 (÷30)</div></div>
        </div>
        <div class="sf-section">
          <div class="sect-lbl">Storefront Links</div>${sfHtml}
        </div>
        <div>
          <div class="sect-lbl">产品价格 (${d.avail_count}个有效 / ${d.expired_count||0}个过期 / ${d.unavail_count}个N/Avail)</div>
          <div class="prices">${pricesHtml}</div>
        </div>
      </div>
    </div>`;
  });
  results.filter(r=>r.error).forEach(r=>{
    html+=`<div class="offer-card"><div class="offer-head" style="color:#991b1b">
      <div><div class="offer-name">抓取失败</div><div class="offer-meta">${r.url||''}</div></div>
    </div><div class="offer-body" style="font-size:13px;color:#991b1b">${r.error}</div></div>`;
  });
  document.getElementById('result').innerHTML=html;
}
function setErr(msg){const e=document.getElementById('err');e.textContent=msg;e.classList.add('show');}
function clearErr(){document.getElementById('err').classList.remove('show');}

async function runTopProducts(){
  const raw=document.getElementById('tp-url').value.trim();
  if(!raw){alert('请输入链接');return;}
  const urls=raw.split('\\n').map(s=>s.trim()).filter(s=>s.includes('advert_id'));
  if(!urls.length){alert('没有找到含 advert_id 的链接');return;}
  const cookie=sessionStorage.getItem('yp_cookie')||'';
  document.getElementById('tp-btn').disabled=true;
  document.getElementById('tp-btn').textContent='筛选中...';
  document.getElementById('tp-prog-bar').classList.add('show');
  document.getElementById('tp-prog-txt').classList.add('show');
  document.getElementById('tp-result').innerHTML='';

  let html='';
  for(let i=0;i<urls.length;i++){
    document.getElementById('tp-prog-fill').style.width=Math.round((i+1)/urls.length*100)+'%';
    document.getElementById('tp-prog-txt').textContent=`${i+1} / ${urls.length}`;
    try{
      const r=await fetch('/top_products',{method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({url:urls[i],cookie,top_n:10})});
      const d=await r.json();
      if(d.error){html+=`<div class="offer-card"><div class="offer-body" style="color:#991b1b">${d.error}</div></div>`;continue;}
      html+=renderTopProducts(d);
    }catch(e){html+=`<div class="offer-card"><div class="offer-body" style="color:#991b1b">${e.message}</div></div>`;}
  }

  document.getElementById('tp-result').innerHTML=html;
  document.getElementById('tp-btn').disabled=false;
  document.getElementById('tp-btn').textContent='筛选 Top 10 产品';
  document.getElementById('tp-prog-txt').textContent='完成';
}

function renderTopProducts(d){
  const rows=d.top_products.map((p,i)=>`<tr>
    <td style="text-align:center;color:#999">${i+1}</td>
    <td><strong style="font-family:monospace;font-size:13px">${p.asin}</strong></td>
    <td style="font-size:12px;color:#555;max-width:200px">${p.name.slice(0,70)}${p.name.length>70?'…':''}</td>
    <td style="text-align:right">$${p.price.toFixed(2)}</td>
    <td style="text-align:right;font-weight:600;color:#166534">${p.review_count.toLocaleString()}</td>
    <td style="text-align:right;font-family:monospace;font-size:12px;color:#1e40af">$${p.cpc_min.toFixed(2)}–$${p.cpc_max.toFixed(2)}</td>
    <td style="font-size:11px;max-width:180px;word-break:break-all">${p.tracking_url?'<a href="'+p.tracking_url+'" target="_blank" style="color:#1d4ed8;text-decoration:none">'+p.tracking_url.slice(0,50)+'…</a>':'—'}</td>
  </tr>`).join('');

  const asins=d.top_products.map(p=>p.asin).join('\\n');
  const links=d.top_products.map(p=>p.tracking_url||'').join('\\n');

  return `<div class="offer-card">
    <div class="offer-head">
      <div>
        <div class="offer-name">${d.merchant_name} — Top ${d.top_products.length} 产品</div>
        <div class="offer-meta">共 ${d.total_valid} 个有效产品（已排除 Expired 和 N/Avail）</div>
      </div>
    </div>
    <div class="offer-body">
      <div style="overflow-x:auto;margin-bottom:16px">
        <table class="tbl">
          <thead><tr><th>#</th><th>ASIN</th><th>产品名称</th><th style="text-align:right">价格</th><th style="text-align:right">评论数</th><th style="text-align:right">CPC区间</th><th>追踪链接</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div>
          <div class="sect-lbl" style="margin-bottom:6px">ASIN 列表</div>
          <textarea style="width:100%;height:${d.top_products.length*22+16}px;font-family:monospace;font-size:12px;padding:8px;border:1px solid #ddd;border-radius:8px;resize:none;outline:none" readonly>${asins}</textarea>
        </div>
        <div>
          <div class="sect-lbl" style="margin-bottom:6px">追踪链接列表</div>
          <textarea style="width:100%;height:${d.top_products.length*22+16}px;font-family:monospace;font-size:11px;padding:8px;border:1px solid #ddd;border-radius:8px;resize:none;outline:none" readonly>${links}</textarea>
        </div>
      </div>
    </div>
  </div>`;
}
</script>
</body>
</html>"""

# ── 路由 ─────────────────────────────────────────────────────
@app.route('/login', methods=['GET'])
def login_page():
    return LOGIN_HTML

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    current_password = os.environ.get('LOGIN_PASSWORD', 'yp2026')
    if data.get('password') == current_password:
        session['logged_in'] = True
        return jsonify({'ok': True})
    return jsonify({'ok': False})

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))
    return MAIN_HTML

def scrape_offer(url, sf_pref, cookie_str):
    advert_m = re.search(r'advert_id=(\d+)', url)
    site_m   = re.search(r'site_id=(\d+)', url)
    if not advert_m:
        return {'error': '链接中未找到 advert_id'}
    advert_id = advert_m.group(1)
    site_id   = site_m.group(1) if site_m else '12052'
    fetch_url = f'https://www.yeahpromos.com/index/offer/brand_detail?advert_id={advert_id}&site_id={site_id}'
    headers   = {**HEADERS, 'Cookie': cookie_str or COOKIE}
    try:
        r = req.get(fetch_url, headers=headers, timeout=20)
        if r.status_code != 200:
            return {'error': f'HTTP {r.status_code}'}
        if 'login' in r.url:
            return {'error': 'Cookie 已过期，请展开更新 Cookie'}
        html = r.text
    except Exception as e:
        return {'error': str(e)}

    soup = BeautifulSoup(html, 'html.parser')

    # 商家名
    name = ''
    el = soup.find('div', class_='advert-title')
    if el:
        name = el.get_text(strip=True)
    if not name:
        name = f'商家 #{advert_id}'

    # 佣金范围文字
    commission_range = ''
    color_div = soup.find('div', class_=re.compile(r'^color-\d+$'))
    if color_div:
        commission_range = color_div.get_text(strip=True)

    # 产品行解析
    prices, comm_vals, unavail_count, expired_count = [], [], 0, 0
    for row in soup.find_all('div', class_='product-line'):
        adv_btn = row.find('p', class_='adv-btn')
        if adv_btn and 'Expired' in adv_btn.get_text():
            expired_count += 1
            continue
        cols = row.find_all('div', class_='col-xs-2')
        price_val, comm_val = None, None
        for col in cols:
            txt = col.get_text(strip=True)
            if txt.startswith('USD '):
                try:
                    price_val = float(txt.replace('USD', '').strip())
                except:
                    pass
            elif txt == 'N/Avail.':
                price_val = 0
            elif re.match(r'^\d+(\.\d+)?%$', txt):
                try:
                    v = float(txt.replace('%', ''))
                    if 1 <= v <= 80:
                        comm_val = v
                except:
                    pass
        if price_val is not None:
            prices.append(price_val)
            if price_val == 0:
                unavail_count += 1
        if comm_val is not None:
            comm_vals.append(comm_val)

    avail_prices = [p for p in prices if p > 0]
    avg_price = round(sum(avail_prices)/len(avail_prices), 2) if avail_prices else 0
    avg_comm  = round(sum(comm_vals)/len(comm_vals), 2) if comm_vals else 0
    est_comm  = round((avg_comm/100)*avg_price, 2)
    total     = len(prices)
    unavail_r = round(unavail_count/total, 4) if total > 0 else 0

    # Storefront Links
    has_sf, storefront_links = False, []
    if sf_pref == 'yes':
        has_sf = True
    elif sf_pref == 'no':
        has_sf = False
    else:
        brand_panel = soup.find('div', id='brand-panel')
        if brand_panel:
            for col in brand_panel.find_all('div', class_='col-xs-8'):
                txt = col.get_text(strip=True)
                if txt.startswith('http'):
                    storefront_links.append(txt)
                    has_sf = True
            for a in brand_panel.find_all('a', href=True):
                href = a['href']
                if href.startswith('http') and 'yeahpromos.com' not in href and href not in storefront_links:
                    storefront_links.append(href)
                    has_sf = True
            if not has_sf and brand_panel:
                has_sf = True

    return {
        'merchant_name':    name,
        'advert_id':        advert_id,
        'commission_rate':  avg_comm,
        'commission_range': commission_range,
        'avg_price':        avg_price,
        'est_commission':   est_comm,
        'has_storefront':   has_sf,
        'storefront_links': storefront_links,
        'total_products':   total,
        'avail_count':      len(avail_prices),
        'unavail_count':    unavail_count,
        'expired_count':    expired_count,
        'unavail_ratio':    unavail_r,
        'prices':           prices,
    }


def scrape_top_products(url, cookie_str, top_n=10):
    advert_m = re.search(r'advert_id=(\d+)', url)
    site_m   = re.search(r'site_id=(\d+)', url)
    if not advert_m:
        return {'error': '链接中未找到 advert_id'}
    advert_id = advert_m.group(1)
    site_id   = site_m.group(1) if site_m else '12052'
    fetch_url = f'https://www.yeahpromos.com/index/offer/brand_detail?advert_id={advert_id}&site_id={site_id}'
    headers   = {**HEADERS, 'Cookie': cookie_str or COOKIE}
    try:
        r = req.get(fetch_url, headers=headers, timeout=20)
        if r.status_code != 200:
            return {'error': f'HTTP {r.status_code}'}
        if 'login' in r.url:
            return {'error': 'Cookie 已过期'}
        html = r.text
    except Exception as e:
        return {'error': str(e)}

    soup = BeautifulSoup(html, 'html.parser')

    # 商家名
    name = ''
    el = soup.find('div', class_='advert-title')
    if el:
        name = el.get_text(strip=True)

    products = []
    for row in soup.find_all('div', class_='product-line'):
        # 过滤 Expired
        adv_btn = row.find('p', class_='adv-btn')
        if adv_btn and 'Expired' in adv_btn.get_text():
            continue

        # 产品名
        name_div = row.find('div', class_='product-name')
        if not name_div:
            continue
        prod_name = name_div.find('div')
        prod_name = prod_name.get_text(strip=True) if prod_name else ''

        # ASIN
        asin_div = name_div.find('div', class_='asin-code')
        asin = asin_div.get_text(strip=True) if asin_div else ''

        # 评论数（格式：(787) 或 (2,672)）
        review_count = 0
        star_div = name_div.find_all('div')
        for d in star_div:
            txt = d.get_text(strip=True)
            m = re.search(r'\(([\d,]+)\)', txt)
            if m:
                review_count = int(m.group(1).replace(',', ''))
                break

        # 价格和佣金率
        cols = row.find_all('div', class_='col-xs-2')
        price = None
        comm_rate = 0.0
        for col in cols:
            txt = col.get_text(strip=True)
            if txt.startswith('USD '):
                try:
                    price = float(txt.replace('USD', '').strip())
                except:
                    pass
            elif txt == 'N/Avail.':
                price = None
            elif re.match(r'^\d+(\.\d+)?%$', txt):
                try:
                    v = float(txt.replace('%', ''))
                    if 1 <= v <= 80:
                        comm_rate = v / 100
                except:
                    pass

        # 必须有价格
        if not asin or price is None:
            continue

        # 追踪链接：从 adv-btn 的 onclick 属性里提取
        tracking_url = ''
        if adv_btn:
            onclick = adv_btn.get('onclick', '')
            m = re.search(r"ClipboardJS\.copy\('([^']+)'\)", onclick)
            if m:
                tracking_url = m.group(1)

        cpc_max = round(price * comm_rate / 30, 3) if comm_rate else 0
        cpc_min = round(price * comm_rate / 50, 3) if comm_rate else 0

        products.append({
            'asin':         asin,
            'name':         prod_name,
            'price':        price,
            'review_count': review_count,
            'tracking_url': tracking_url,
            'cpc_min':      cpc_min,
            'cpc_max':      cpc_max,
        })

    # 按评论数降序，取前N
    products.sort(key=lambda x: x['review_count'], reverse=True)
    top = products[:top_n]

    return {
        'merchant_name': name,
        'advert_id':     advert_id,
        'total_valid':   len(products),
        'top_products':  top,
    }

@app.route('/top_products', methods=['POST'])
def top_products():
    if not session.get('logged_in'):
        return jsonify({'error': '请先登录'}), 401
    data   = request.json
    url    = data.get('url', '').strip()
    cookie = data.get('cookie', '').strip()
    top_n  = int(data.get('top_n', 10))
    if not url:
        return jsonify({'error': '请输入链接'})
    return jsonify(scrape_top_products(url, cookie, top_n))

@app.route('/analyze', methods=['POST'])
def analyze():
    if not session.get('logged_in'):
        return jsonify({'error': '请先登录'}), 401
    data   = request.json
    url    = data.get('url', '').strip()
    sf     = data.get('sf', 'auto')
    cookie = data.get('cookie', '').strip()
    if not url:
        return jsonify({'error': '请输入链接'})
    return jsonify(scrape_offer(url, sf, cookie))

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
