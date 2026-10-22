#!/usr/bin/env python3
"""Headless-browser smoke test of the interfaces on (a) the empty live data and (b) the v7 fixture.

Checks: no JavaScript errors, all 29 metrics always selectable, empty-state banner on empty data,
points/marks really drawn on the fixture, click -> provenance panel, and that missing values never plot as 0.
Leaflet is replaced by a tiny stub (the map logic, not the tiles, is what is tested). Needs: pip install playwright.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import PY, ROOT, Sandbox  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

STUB = """window.__markers=[];window.L={map:()=>({setView(){return this}}),tileLayer:()=>({addTo(){}}),
layerGroup:()=>({addTo(){return this},clearLayers(){window.__markers=[]}}),control:()=>({addTo(){this.onAdd();}}),
DomUtil:{create:(t,c)=>{const d=document.createElement(t);d.className=c;document.body.appendChild(d);return d}},
circleMarker:(ll,o)=>{const m={ll,o,tip:'',bindTooltip(t){this.tip=t},on(e,f){this.f=f},addTo(){window.__markers.push(this)}};return m}};"""
LOCAL_D3 = Path("/opt/npm-tools/node_modules/d3/dist/d3.min.js")
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)
        print("FAIL:", msg)


def run(site, label, empty):
    with sync_playwright() as p:
        b = p.chromium.launch(**({"executable_path": "/opt/pw-browsers/chromium"} if Path("/opt/pw-browsers/chromium").exists() else {}))
        pg = b.new_page(viewport={"width": 1300, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))

        def route(r):
            u = r.request.url
            if "leaflet.js" in u:
                r.fulfill(body=STUB, content_type="application/javascript")
            elif "leaflet.css" in u or "tile.openstreetmap" in u:
                r.abort()
            elif "d3" in u and u.endswith(".js") and LOCAL_D3.exists():
                r.fulfill(body=LOCAL_D3.read_text(), content_type="application/javascript")
            else:
                r.continue_()
        pg.route("**/*", route)
        ev = lambda js: pg.evaluate(js)  # noqa: E731
        for page in ("index", "map", "correlation", "comparison"):
            errs.clear()
            pg.goto(f"file://{site}/{page}.html")
            pg.wait_for_timeout(500)
            check(not errs, f"{label}/{page}: JS errors {errs}")
            banner = ev("(()=>{const b=document.getElementById('banner');return b&&!b.hidden})()")
            check(bool(banner) == empty, f"{label}/{page}: empty-state banner should be {'shown' if empty else 'hidden'}")
            if page == "map":
                check(ev("document.querySelectorAll('#metric option').length") == 29, f"{label}/map: 29 metrics")
                n, grey = ev("window.__markers.length"), ev("window.__markers.filter(m=>m.o.fillColor==='#9ca3af').length")
                check(n > 50, f"{label}/map: events drawn ({n})")
                if empty:
                    check(grey == n, f"{label}/map: all markers grey on empty data")
                else:
                    check(grey < n, f"{label}/map: some markers coloured")
                    ev("window.__markers.find(m=>m.o.fillColor!=='#9ca3af').f()")
                    check(ev("document.querySelectorAll('#values details').length") >= 1, f"{label}/map: click shows records")
            if page == "correlation":
                check(ev("document.querySelectorAll('#xm option').length") == 29, f"{label}/correlation: 29 metrics")
                dots = ev("document.querySelectorAll('.dot').length")
                check((dots == 0) == empty, f"{label}/correlation: dots={dots}")
            if page == "comparison":
                marks = ev("document.querySelectorAll('.mark').length")
                check((marks == 0) == empty, f"{label}/comparison: marks={marks}")
                if not empty:
                    ev("document.querySelector('.mark').nextElementSibling.dispatchEvent(new MouseEvent('click'))")
                    check("Study reference" in ev("document.getElementById('detail').textContent"), f"{label}/comparison: provenance panel")
        b.close()


def main():
    live, fix = Sandbox("live"), Sandbox("fixture")
    try:
        for sb in (live, fix):
            r = sb.run("build.py")
            check(r.returncode == 0, "build failed: " + r.stdout[-400:] + r.stderr[-400:])
        run(str(live.site), "live", True)
        run(str(fix.site), "fixture", False)
    finally:
        live.cleanup()
        fix.cleanup()
    print("UI smoke test:", "FAILED" if fails else "passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
