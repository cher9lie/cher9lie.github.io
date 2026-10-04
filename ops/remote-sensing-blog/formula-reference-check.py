"""Check newly cited primary sources and identify rendered math errors."""
import hashlib
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTICLE = ROOT / "src/content/blog/flaash-atmospheric-correction-concepts/index.md"
SOURCES = [
    "https://nvlpubs.nist.gov/nistpubs/Legacy/hb/nisthandbook152.pdf",
    "https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nbsspecialpublication250-1.pdf",
    "https://pages.nist.gov/ScatterMIST/docs/Introduction.htm",
    "https://pages.nist.gov/SCATMECH/docs/lambert.htm",
    "https://sentiwiki.copernicus.eu/__attachments/a_ece6183b6698587e7ecd9804974bece3d82e39e151aa5aeca9d8fd95e1f1558c/COPE-GSEG-EOPG-TN-15-0007%20-%20Sentinel-2%20Spectral%20Response%20Functions%202024%20-%204.0.xlsx",
    "https://gml.noaa.gov/grad/agasp2.html",
    "https://www.gml.noaa.gov/grad/surfrad/aod/",
    "https://www.usgs.gov/landsat-missions/landsat-normalized-difference-vegetation-index",
]


def check_source(url):
    request = urllib.request.Request(url, headers={"User-Agent": "RemoteSensingReferenceCheck/1.0"})
    with urllib.request.urlopen(request, timeout=50) as response:
        content = response.read()
        if url.endswith(".pdf"):
            assert content.startswith(b"%PDF"), url
        elif url.endswith(".xlsx"):
            assert content.startswith(b"PK"), url
        else:
            assert b"<html" in content.lower(), url
        return {"url": url, "status": response.status, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=4) as pool:
        checks = list(pool.map(check_source, SOURCES))
    output = {"date": "2026-10-05", "sources": checks}
    built_page = ROOT / "dist/blog/flaash-atmospheric-correction-concepts/index.html"
    if built_page.exists():
        rendered = built_page.read_text(encoding="utf-8")
        assert "katex-error" not in rendered
        assert "方向—半球反射率" in rendered
        assert "共同加性项" in rendered
        assert "波数间隔" in rendered
        equations = len(re.findall(r'class="katex-display"', rendered))
        expected = len(re.findall(r"^\$\$$", ARTICLE.read_text(encoding="utf-8"), flags=re.M)) // 2
        assert equations == expected, (equations, expected)
        for url in SOURCES:
            assert url in rendered, url
        output["rendered"] = {"display_equations": equations, "katex_errors": 0, "all_new_source_urls_present": True}
    target = Path(__file__).with_name("formula-reference-checks.json")
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
