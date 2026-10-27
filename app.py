import json
import os
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

OMDB_URL = "https://www.omdbapi.com/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

PAGE = r"""
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CinéScore AI</title>
<style>
:root{color-scheme:dark;--bg:#10131b;--panel:#191e2a;--line:#30394b;--text:#f3f5fa;--muted:#a9b2c5;--accent:#f6c453}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:28px 16px 60px}h1{margin:0;font-size:clamp(28px,5vw,42px)}.sub{color:var(--muted);margin:5px 0 24px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;margin:16px 0}
label{display:block;font-weight:650;margin:12px 0 5px}input,textarea,button{font:inherit;border-radius:9px}
input,textarea{width:100%;background:#0f131c;color:var(--text);border:1px solid var(--line);padding:11px}
textarea{min-height:90px;resize:vertical}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
button{border:0;background:var(--accent);color:#211b0b;padding:12px 18px;font-weight:750;cursor:pointer;margin-top:15px}
button:disabled{opacity:.6;cursor:wait}.hint{color:var(--muted);font-size:13px}.status{margin:14px 0;color:var(--muted)}
.tablewrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:680px}th,td{text-align:left;padding:10px;border-bottom:1px solid var(--line)}th{color:var(--muted);cursor:pointer;white-space:nowrap}td.rating{font-weight:800;color:var(--accent)}a{color:var(--accent)}.poster{width:42px;height:60px;object-fit:cover;border-radius:4px;background:#282e3b}
@media(max-width:650px){.grid{grid-template-columns:1fr}.panel{padding:14px}}
</style>
</head>
<body><main>
<h1>🎬 CinéScore AI</h1>
<p class="sub">Récupère les films d’un catalogue et compare leurs notes IMDb.</p>
<section class="panel">
<form id="searchForm">
<label for="url">URL du catalogue de films</label>
<input id="url" type="url" placeholder="https://exemple.com/catalogue" value="https://danovli.com/e5b7668/c/danovli/12/0">
<div class="grid">
<div><label for="selector">Sélecteur CSS (facultatif)</label><input id="selector" placeholder="Ex. .movie-card"></div>
<div><label for="year">Année (facultative, pour tous les titres)</label><input id="year" type="number" min="1888" max="2100" placeholder="2026"></div>
</div>
<label for="titles">Titres à ajouter manuellement (facultatif)</label>
<textarea id="titles" placeholder="Un film par ligne"></textarea>
<label for="apikey">Clé API OMDb</label>
<input id="apikey" type="password" name="password" autocomplete="current-password" placeholder="Saisis la clé OMDb">
<p class="hint">La clé n’est pas enregistrée par cette page. Elle est utilisée pour la recherche envoyée au serveur.</p>
<button id="submit" type="submit">Analyser les films</button>
</form>
<div id="status" class="status" role="status"></div>
</section>
<section class="panel" id="resultsPanel" hidden>
<h2>Résultats <span id="count" class="hint"></span></h2>
<div class="tablewrap"><table><thead><tr>
<th data-sort="title">Film ↕</th><th data-sort="year">Année ↕</th><th data-sort="imdbRating">Note IMDb ↕</th><th data-sort="imdbVotes">Votes ↕</th><th>IMDb</th>
</tr></thead><tbody id="rows"></tbody></table></div>
</section>
</main>
<script>
const form=document.getElementById('searchForm'), statusEl=document.getElementById('status'), submit=document.getElementById('submit');
let results=[], sortKey='imdbRating', sortDesc=true;
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function render(){
 const sorted=[...results].sort((a,b)=>{
  let av=a[sortKey],bv=b[sortKey];
  if(sortKey==='imdbRating'||sortKey==='year') {av=parseFloat(av)||0;bv=parseFloat(bv)||0;}
  if(sortKey==='imdbVotes'){av=Number(String(av||'').replace(/,/g,''))||0;bv=Number(String(bv||'').replace(/,/g,''))||0;}
  const cmp=typeof av==='number'&&typeof bv==='number'?av-bv:String(av||'').localeCompare(String(bv||''),'fr');
  return sortDesc?-cmp:cmp;
 });
 document.getElementById('rows').innerHTML=sorted.map(m=>`<tr>
 <td>${m.Poster&&m.Poster!=='N/A'?`<img class="poster" src="${esc(m.Poster)}" alt=""> `:''}<strong>${esc(m.Title)}</strong><div class="hint">${esc(m.Type||'')}</div></td>
 <td>${esc(m.Year||'—')}</td><td class="rating">${esc(m.imdbRating||'N/A')}</td><td>${esc(m.imdbVotes||'—')}</td>
 <td>${m.imdbID?`<a href="https://www.imdb.com/title/${esc(m.imdbID)}/" target="_blank" rel="noopener">Ouvrir ↗</a>`:'—'}</td></tr>`).join('');
 document.getElementById('count').textContent=`(${results.length} film(s))`;
}
document.querySelectorAll('th[data-sort]').forEach(th=>th.addEventListener('click',()=>{const k=th.dataset.sort;if(sortKey===k)sortDesc=!sortDesc;else{sortKey=k;sortDesc=k==='imdbRating';}render();}));
form.addEventListener('submit',async e=>{
 e.preventDefault();submit.disabled=true;statusEl.textContent='Analyse en cours…';document.getElementById('resultsPanel').hidden=true;
 try{
  const payload={url:document.getElementById('url').value.trim(),selector:document.getElementById('selector').value.trim(),year:document.getElementById('year').value.trim(),titles:document.getElementById('titles').value,api_key:document.getElementById('apikey').value.trim()};
  const response=await fetch('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const data=await response.json();if(!response.ok)throw new Error(data.error||'Erreur lors de la recherche');
  results=data.results||[];render();document.getElementById('resultsPanel').hidden=false;
  statusEl.textContent=`${data.extracted_count||0} titre(s) détecté(s) automatiquement. ${data.message||''}`;
 }catch(err){statusEl.textContent='Erreur : '+err.message;}
 finally{submit.disabled=false;}
});
</script>
</body></html>
"""

def clean_title(value):
    """Normalise a possible movie title and removes obvious UI labels."""
    if not value:
        return ""
    value = re.sub(r"\s+", " ", str(value)).strip()
    value = re.sub(r"^(?:film|movie)\s*[:\-]\s*", "", value, flags=re.I)
    value = re.sub(r"\s*(?:[-|]\s*)?(?:regarder|watch online|streaming|bande annonce|trailer|play)\s*$", "", value, flags=re.I)
    value = value.strip(" \t\r\n|•–—-")
    if len(value) < 2 or len(value) > 140:
        return ""
    if value.lower() in {"accueil", "home", "films", "movies", "catalogue", "catalog", "menu", "recherche", "search", "connexion", "login", "play", "watch"}:
        return ""
    if not re.search(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]", value):
        return ""
    return value

def split_year(value):
    """Return (title, year) when a four-digit year is attached to a title."""
    value = clean_title(value)
    if not value:
        return "", ""
    match = re.match(r"^\s*((?:18|19|20)\d{2})\s*[-:|–—]?\s+(.+?)\s*$", value)
    if match:
        title = clean_title(match.group(2))
        return (title, match.group(1)) if title else ("", "")
    match = re.match(r"^\s*(.+?)\s*[\(\[]((?:18|19|20)\d{2})[\)\]]\s*$", value)
    if match:
        return clean_title(match.group(1)), match.group(2)
    match = re.match(r"^\s*(.+?)\s*[-–|]\s*((?:18|19|20)\d{2})\s*$", value)
    if match:
        return clean_title(match.group(1)), match.group(2)
    return value, ""

def values_from_jsonld(node, found):
    if isinstance(node, dict):
        typ = node.get("@type", "")
        name = node.get("name")
        if isinstance(name, str) and any(t in str(typ).lower() for t in ("movie", "creativework", "episode")):
            found.append(name)
        # Catalogs often wrap titles in ItemList -> itemListElement -> item.
        for key, val in node.items():
            if key in {"name", "description", "image", "url", "sameAs"}:
                continue
            values_from_jsonld(val, found)
    elif isinstance(node, list):
        for item in node:
            values_from_jsonld(item, found)

def extract_titles(url, selector=""):
    """Extract catalog titles from visible text, poster image attributes and page metadata."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("L’URL doit commencer par http:// ou https://.")
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    found = []

    # Read structured movie metadata before removing scripts.
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            values_from_jsonld(json.loads(script.string or script.get_text()), found)
        except (ValueError, TypeError, json.JSONDecodeError):
            pass

    # A custom CSS selector lets the user target a title/card area if needed.
    if selector:
        try:
            selected = soup.select(selector)
        except Exception as exc:
            raise ValueError("Le sélecteur CSS n’est pas valide.") from exc
        for node in selected:
            for attr in ("title", "aria-label", "alt", "data-title", "data-name"):
                val = node.get(attr) if hasattr(node, "get") else None
                if val:
                    found.append(val)
            if hasattr(node, "get_text"):
                found.append(node.get_text(" ", strip=True))

    # Main extraction: anchors and poster images, including enclosing card/link labels.
    for img in soup.find_all("img"):
        candidates = [img.get("alt"), img.get("title"), img.get("data-title"), img.get("data-name")]
        for attr, val in img.attrs.items():
            if attr.startswith("data-") and isinstance(val, str) and any(k in attr.lower() for k in ("title", "name", "movie", "film")):
                candidates.append(val)
        anchor = img.find_parent("a")
        if anchor:
            candidates.extend([anchor.get("title"), anchor.get("aria-label"), anchor.get_text(" ", strip=True)])
        # Add text/title from nearby card containers; keep this constrained to short values.
        parent = img.parent
        for _ in range(3):
            if not parent or getattr(parent, "name", None) in {"body", "html"}:
                break
            for attr in ("title", "aria-label", "data-title", "data-name"):
                val = parent.get(attr) if hasattr(parent, "get") else None
                if val:
                    candidates.append(val)
            text = parent.get_text(" ", strip=True) if hasattr(parent, "get_text") else ""
            if text and len(text) <= 140:
                candidates.append(text)
            parent = parent.parent
        found.extend(c for c in candidates if c)

    # Standard title headings and links.
    for node in soup.select('[itemprop="name"], [class*="movie-title"], [class*="film-title"], [class*="title"], article h2, article h3, .card h2, .card h3, h1, h2, h3, a[title], a[aria-label]'):
        for attr in ("content", "title", "aria-label", "data-title", "data-name"):
            val = node.get(attr)
            if val:
                found.append(val)
        text = node.get_text(" ", strip=True)
        if text:
            found.append(text)

    # Remove common non-content areas from any remaining broad heading/link extraction.
    for node in soup.select("nav, footer, header, script, style, noscript, svg"):
        node.decompose()

    titles = []
    seen = set()
    for raw in found:
        title, year = split_year(raw)
        if not title:
            continue
        # Ignore obvious URLs, asset filenames and very generic navigation labels.
        if title.startswith(("http://", "https://", "data:image")):
            continue
        if re.search(r"\.(?:jpg|jpeg|png|webp|gif|svg)$", title, re.I):
            continue
        key = (title.casefold(), year)
        if key not in seen:
            seen.add(key)
            titles.append({"title": title, "year": year})
    return titles

def lookup_omdb(title, api_key, year=""):
    params = {"apikey": api_key, "t": title, "type": "movie"}
    if year and str(year).isdigit():
        params["y"] = str(year)
    response = requests.get(OMDB_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=15)
    response.raise_for_status()
    data = response.json()
    if data.get("Response") == "True" and data.get("imdbID"):
        return data
    # Fallback search can rescue slightly different catalog naming.
    params = {"apikey": api_key, "s": title, "type": "movie"}
    if year and str(year).isdigit():
        params["y"] = str(year)
    response = requests.get(OMDB_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=15)
    response.raise_for_status()
    search_data = response.json()
    if search_data.get("Response") == "True" and search_data.get("Search"):
        first = search_data["Search"][0]
        detail_params = {"apikey": api_key, "i": first.get("imdbID"), "type": "movie"}
        response = requests.get(OMDB_URL, params=detail_params, headers={"User-Agent": USER_AGENT}, timeout=15)
        response.raise_for_status()
        detail = response.json()
        if detail.get("Response") == "True":
            return detail
    return {"Response": "False", "Error": data.get("Error", "Film introuvable")}

@app.get("/")
def home():
    return render_template_string(PAGE)

@app.post("/api/search")
def api_search():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    selector = (data.get("selector") or "").strip()
    manual_titles = (data.get("titles") or "").splitlines()
    api_key = (data.get("api_key") or os.environ.get("OMDB_API_KEY") or "").strip()
    default_year = str(data.get("year") or "").strip()

    if not api_key:
        return jsonify(error="Saisis ta clé API OMDb dans le champ prévu."), 400

    extracted = []
    if url:
        try:
            extracted = extract_titles(url, selector)
        except requests.RequestException as exc:
            return jsonify(error=f"Impossible de lire le catalogue : {exc}"), 400
        except ValueError as exc:
            return jsonify(error=str(exc)), 400

    for raw in manual_titles:
        title, year = split_year(raw)
        if title:
            extracted.append({"title": title, "year": year})

    # Deduplicate while preserving order; manual titles are still supported.
    unique = []
    seen = set()
    for item in extracted:
        title = clean_title(item.get("title", ""))
        year = str(item.get("year") or "").strip()
        key = (title.casefold(), year)
        if title and key not in seen:
            seen.add(key)
            unique.append({"title": title, "year": year})

    if not unique:
        return jsonify(error="Aucun titre détecté. Essaie un sélecteur CSS ou ajoute quelques titres manuellement."), 400

    results = []
    errors = []
    for item in unique[:100]:
        title = item["title"]
        year = item["year"] or default_year
        try:
            movie = lookup_omdb(title, api_key, year)
            if movie.get("Response") == "True":
                results.append(movie)
            else:
                errors.append(title)
        except (requests.RequestException, ValueError) as exc:
            errors.append(title)
    results.sort(key=lambda m: float(m.get("imdbRating", "0")) if m.get("imdbRating") not in (None, "", "N/A") else 0, reverse=True)
    message = f"{len(errors)} titre(s) sans résultat IMDb." if errors else "Recherche terminée."
    return jsonify(results=results, extracted_count=len(unique), message=message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
