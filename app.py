from flask import Flask, request, jsonify, render_template_string
import requests
from bs4 import BeautifulSoup
import re
import os
from urllib.parse import urlparse

app = Flask(__name__)

PAGE = r"""
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CinéScore AI — Notes IMDb</title>
<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#141c30;--line:#293550;--muted:#9aa8c2;--text:#f4f6fb;--accent:#f5c518;--blue:#8bb5ff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top,#172443 0%,var(--bg) 55%);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;color:var(--text)}
main{max-width:1100px;margin:0 auto;padding:34px 18px 60px}.brand{display:flex;align-items:center;gap:14px;margin-bottom:25px}.logo{background:var(--accent);color:#171717;font-weight:900;font-size:22px;border-radius:13px;padding:12px}.brand h1{font-size:26px;margin:0}.brand p{color:var(--muted);margin:2px 0 0}.panel{background:rgba(20,28,48,.94);border:1px solid var(--line);border-radius:18px;padding:22px;margin:16px 0;box-shadow:0 12px 35px #0002}.panel h2{font-size:17px;margin:0 0 14px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.field{display:flex;flex-direction:column;gap:7px}label{font-weight:650;font-size:13px;color:#dbe3f4}input,textarea{background:#0b1223;color:var(--text);border:1px solid #34415e;border-radius:10px;padding:12px;font:inherit;width:100%;outline:none}input:focus,textarea:focus{border-color:var(--blue)}textarea{min-height:110px;resize:vertical}.hint{color:var(--muted);font-size:12px}.actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}button{border:0;border-radius:10px;padding:11px 16px;font:inherit;font-weight:750;cursor:pointer;background:var(--accent);color:#171717}button.secondary{background:#25324d;color:var(--text);border:1px solid #394967}button:disabled{opacity:.55;cursor:wait}.status{margin-top:12px;color:var(--muted);white-space:pre-wrap}.stats{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}.stat{background:#0b1223;border:1px solid var(--line);padding:10px 14px;border-radius:12px;color:var(--muted)}.stat strong{color:var(--text);font-size:18px;margin-right:6px}.tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:650px}th,td{text-align:left;padding:13px 12px;border-bottom:1px solid var(--line)}th{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;cursor:pointer;white-space:nowrap}th:hover{color:var(--accent)}td a{color:#a9c8ff;text-decoration:none}td a:hover{text-decoration:underline}.rating{display:inline-block;background:#f5c518;color:#161616;font-weight:850;border-radius:7px;padding:3px 8px}.empty{text-align:center;color:var(--muted);padding:28px}.pill{font-size:11px;border:1px solid #394967;border-radius:20px;padding:3px 8px;color:var(--muted)}footer{color:var(--muted);font-size:12px;margin-top:20px}
@media(max-width:700px){.grid{grid-template-columns:1fr}.panel{padding:16px}.brand h1{font-size:22px}}
</style>
</head>
<body><main>
<header class="brand"><div class="logo">CS</div><div><h1>CinéScore AI</h1><p>Retrouve les notes IMDb et classe tes films.</p></div><span class="pill">Application web</span></header>
<section class="panel">
<h2>1. Source des films</h2>
<div class="grid">
<div class="field"><label for="siteUrl">URL de la page catalogue</label><input id="siteUrl" type="url" placeholder="https://exemple.com/films"><span class="hint">Le serveur tentera d'extraire les titres visibles et les liens de la page.</span></div>
<div class="field"><label for="selector">Sélecteur CSS des titres (facultatif)</label><input id="selector" placeholder="ex. .movie-card h2"><span class="hint">Si l'extraction automatique se trompe, indique le sélecteur HTML des titres.</span></div>
</div>
<div class="field" style="margin-top:14px"><label for="titles">Ou colle les titres manuellement (un par ligne)</label><textarea id="titles">Dune
Interstellar
Inception</textarea></div>
<div class="grid" style="margin-top:14px">
<div class="field"><label for="apiKey">Clé API OMDb</label><input id="apiKey" type="password" placeholder="Ta clé OMDb"><span class="hint">Nécessaire pour récupérer les notes IMDb. Obtiens une clé sur omdbapi.com.</span></div>
<div class="field"><label for="year">Année (facultatif)</label><input id="year" type="number" min="1888" max="2100" placeholder="Ex. 2021"><span class="hint">Aide à distinguer les films qui portent le même titre.</span></div>
</div>
<div class="actions"><button id="runBtn" onclick="runSearch()">Rechercher les notes IMDb</button><button class="secondary" onclick="loadDemo()">Charger l'exemple</button><button class="secondary" onclick="exportCsv()">Exporter CSV</button></div>
<div id="status" class="status" role="status">Prêt. Saisis une clé OMDb pour effectuer des recherches réelles.</div>
</section>
<section class="panel">
<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap"><h2 style="margin:0 0 14px">2. Résultats</h2><span class="pill">Clique sur un en-tête pour trier</span></div>
<div class="stats"><div class="stat"><strong id="count">0</strong> films</div><div class="stat"><strong id="avg">—</strong> note moyenne</div><div class="stat"><strong id="found">0</strong> notes trouvées</div></div>
<div class="tablewrap"><table><thead><tr><th data-key="title">Film ↕</th><th data-key="year">Année ↕</th><th data-key="rating">Note IMDb ↕</th><th data-key="votes">Votes ↕</th><th>Fiche</th></tr></thead><tbody id="results"><tr><td colspan="5" class="empty">Les résultats apparaîtront ici.</td></tr></tbody></table></div>
</section>
<footer>Les notes sont fournies par OMDb à partir des données IMDb. Ce prototype ne contourne pas les protections d'accès d'un site : certains catalogues peuvent bloquer l'extraction, exiger une connexion ou charger les films par JavaScript. N'utilise que des sites et des données auxquels tu es autorisé à accéder.</footer>
</main>
<script>
let rows=[]; let sortKey='rating'; let sortDir=-1;
document.querySelectorAll('th[data-key]').forEach(th=>th.addEventListener('click',()=>{const k=th.dataset.key;if(sortKey===k)sortDir*=-1;else{sortKey=k;sortDir=(k==='title'?-1:1)}render()}));
function loadDemo(){document.getElementById('titles').value='Dune\\nInterstellar\\nInception';document.getElementById('siteUrl').value='';document.getElementById('selector').value='';}
async function runSearch(){
 const key=document.getElementById('apiKey').value.trim(), url=document.getElementById('siteUrl').value.trim(), selector=document.getElementById('selector').value.trim(), manual=document.getElementById('titles').value;
 if(!key){setStatus('Ajoute ta clé API OMDb. Sans clé, les notes IMDb ne peuvent pas être récupérées automatiquement.');return}
 if(!url && !manual.trim()){setStatus('Saisis une URL de catalogue ou une liste de titres.');return}
 const btn=document.getElementById('runBtn');btn.disabled=true;rows=[];render();setStatus('Extraction des titres et recherche des notes IMDb…');
 try{
  const r=await fetch('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_key:key,url,selector,titles:manual,year:document.getElementById('year').value})});
  const data=await r.json(); if(!r.ok)throw new Error(data.error||'Erreur de recherche');
  rows=data.results||[];render();setStatus(data.message||`Terminé : ${rows.length} résultat(s).`);
 }catch(e){setStatus('Impossible de terminer la recherche : '+e.message+'\\nVérifie que le serveur tourne, que la clé OMDb est valide et que le site autorise l’accès.')}
 finally{btn.disabled=false}
}
function setStatus(s){document.getElementById('status').textContent=s}
function render(){
 const body=document.getElementById('results');
 const sorted=[...rows].sort((a,b)=>{let x=a[sortKey],y=b[sortKey];if(x==null)x=sortKey==='title'?'':-1;if(y==null)y=sortKey==='title'?'':-1;if(typeof x==='string')return x.localeCompare(y,'fr')*sortDir;return (x-y)*sortDir});
 body.innerHTML='';
 if(!sorted.length)body.innerHTML='<tr><td colspan="5" class="empty">Aucun résultat pour le moment.</td></tr>';
 sorted.forEach(r=>{const tr=document.createElement('tr');const rating=r.rating==null?'—':`<span class="rating">${Number(r.rating).toFixed(1)} / 10</span>`;tr.innerHTML=`<td>${esc(r.title||'Titre inconnu')}</td><td>${esc(r.year||'—')}</td><td>${rating}</td><td>${r.votes==null?'—':Number(r.votes).toLocaleString('fr-FR')}</td><td>${r.imdb_url?`<a href="${esc(r.imdb_url)}" target="_blank" rel="noopener">IMDb ↗</a>`:'—'}</td>`;body.appendChild(tr)});
 document.getElementById('count').textContent=rows.length;
 const rated=rows.filter(r=>typeof r.rating==='number');document.getElementById('found').textContent=rated.length;
 document.getElementById('avg').textContent=rated.length?(rated.reduce((s,r)=>s+r.rating,0)/rated.length).toFixed(1)+'/10':'—';
}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function exportCsv(){if(!rows.length){setStatus('Aucun résultat à exporter.');return}const q=v=>'"'+String(v??'').replace(/"/g,'""')+'"';const csv='Film,Année,Note IMDb,Votes,URL IMDb\\n'+rows.map(r=>[r.title,r.year,r.rating,r.votes,r.imdb_url].map(q).join(',')).join('\\n');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob(['\\ufeff'+csv],{type:'text/csv;charset=utf-8'}));a.download='cinescore-imdb.csv';a.click();URL.revokeObjectURL(a.href)}
</script></body></html>
"""

def valid_http_url(url):
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False

def clean_title(s):
    s = re.sub(r'\s+', ' ', s or '').strip()
    s = re.sub(r'\s*[\|\-–—]\s*(official trailer|trailer|watch online|streaming|netflix|prime video).*$', '', s, flags=re.I)
    s = re.sub(r'\s*\((?:19|20)\d{2}\)\s*$', '', s)
    return s.strip(' -|:·')

def extract_titles(url, selector=""):
    if not valid_http_url(url):
        raise ValueError("L’URL doit commencer par http:// ou https://.")
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CineScoreAI/1.0)"}
    resp = requests.get(url, headers=headers, timeout=18)
    resp.raise_for_status()
    if len(resp.content) > 8_000_000:
        raise ValueError("Page trop volumineuse (limite de 8 Mo).")
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
        tag.decompose()
    candidates = []
    if selector:
        try:
            nodes = soup.select(selector)
        except Exception as e:
            raise ValueError("Sélecteur CSS invalide : " + str(e))
        for node in nodes:
            val = node.get("title") or node.get("alt") or node.get_text(" ", strip=True)
            title = clean_title(val)
            if 1 < len(title) < 100:
                candidates.append(title)
    else:
        # Prefer common title headings and card links; fall back to headings.
        for node in soup.select('[itemprop="name"], [class*="movie-title"], [class*="film-title"], [class*="title"], article h2, article h3, .card h2, .card h3, h1, h2, h3'):
            val = node.get("content") or node.get("title") or node.get_text(" ", strip=True)
            title = clean_title(val)
            if 2 < len(title) < 85 and not re.search(r'^(home|accueil|films?|series?|menu|connexion|recherche|popular|latest)$', title, re.I):
                candidates.append(title)
        # Add meaningful linked titles if very few headings were found.
        if len(candidates) < 3:
            for a in soup.select('a[title], a'):
                val = a.get("title") or a.get_text(" ", strip=True)
                title = clean_title(val)
                if 2 < len(title) < 85 and not re.search(r'(login|sign up|cookie|privacy|terms|facebook|instagram|twitter)', title, re.I):
                    candidates.append(title)
    # Preserve order while removing duplicates.
    out, seen = [], set()
    for title in candidates:
        key = re.sub(r'[^a-z0-9]', '', title.lower())
        if key and key not in seen:
            seen.add(key); out.append(title)
    if not out:
        raise ValueError("Aucun titre détecté. Colle les titres manuellement ou précise un sélecteur CSS.")
    return out[:100]

def lookup_omdb(title, api_key, year=""):
    params = {"apikey": api_key, "t": title, "type": "movie"}
    if year:
        params["y"] = year
    resp = requests.get("https://www.omdbapi.com/", params=params, timeout=12)
    resp.raise_for_status()
    data = resp.json()
    if data.get("Response") != "True":
        # Fallback search results can help when exact title doesn't match.
        sr = requests.get("https://www.omdbapi.com/", params={"apikey": api_key, "s": title, "type": "movie", **({"y": year} if year else {})}, timeout=12)
        sr.raise_for_status()
        sd = sr.json()
        if sd.get("Response") == "True" and sd.get("Search"):
            imdb_id = sd["Search"][0].get("imdbID")
            if imdb_id:
                d2 = requests.get("https://www.omdbapi.com/", params={"apikey": api_key, "i": imdb_id}, timeout=12).json()
                if d2.get("Response") == "True":
                    data = d2
                else:
                    return {"title": title, "year": "", "rating": None, "votes": None, "imdb_url": None, "error": "Fiche non trouvée"}
            else:
                return {"title": title, "year": "", "rating": None, "votes": None, "imdb_url": None, "error": "Fiche non trouvée"}
        else:
            return {"title": title, "year": "", "rating": None, "votes": None, "imdb_url": None, "error": data.get("Error", "Fiche non trouvée")}
    rating = data.get("imdbRating")
    votes = data.get("imdbVotes")
    try: rating = float(rating) if rating and rating != "N/A" else None
    except ValueError: rating = None
    try: votes = int(votes.replace(",", "")) if votes and votes != "N/A" else None
    except ValueError: votes = None
    imdb_id = data.get("imdbID")
    return {"title": data.get("Title", title), "year": data.get("Year", ""), "rating": rating, "votes": votes,
            "imdb_url": f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else None,
            "error": None if rating is not None else "Note indisponible"}

@app.get("/")
def index():
    return render_template_string(PAGE)

@app.post("/api/search")
def api_search():
    data = request.get_json(silent=True) or {}
    api_key = (data.get("api_key") or "").strip()
    if not api_key:
        return jsonify(error="Clé API OMDb manquante."), 400
    titles = []
    url = (data.get("url") or "").strip()
    try:
        if url:
            titles.extend(extract_titles(url, (data.get("selector") or "").strip()))
        titles.extend(clean_title(t) for t in (data.get("titles") or "").splitlines() if clean_title(t))
        titles = list(dict.fromkeys(titles))[:100]
        if not titles:
            return jsonify(error="Aucun titre fourni ou détecté."), 400
    except requests.RequestException as e:
        return jsonify(error=f"Impossible de lire le site : {e}. Le site peut bloquer les requêtes ou nécessiter JavaScript."), 400
    except ValueError as e:
        return jsonify(error=str(e)), 400
    year = str(data.get("year") or "").strip()
    results, errors = [], []
    for title in titles:
        try:
            item = lookup_omdb(title, api_key, year)
            results.append(item)
        except Exception as e:
            results.append({"title": title, "year": "", "rating": None, "votes": None, "imdb_url": None, "error": str(e)})
            errors.append(title)
    message = f"{len(results)} film(s) traité(s), {sum(1 for x in results if x['rating'] is not None)} note(s) trouvée(s)."
    if errors: message += " Certaines recherches ont échoué (réseau/API)."
    return jsonify(results=results, message=message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
