#!/usr/bin/env python3
"""ReadmeRocket local web GUI. Standard library only.
Run: python readmerocket_web.py   (opens in a desktop window or browser)
"""
import json
import os
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(ROOT, "rocket.json")
OUTDIR = os.path.join(ROOT, "profile_pack")

sys.path.insert(0, ROOT)
import readmerocket as rr

PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>ReadmeRocket</title>
<style>
:root{--bg:#07090e;--panel:#0d1117;--line:#1e2635;--txt:#e6edf3;--dim:#8b949e;--acc:#c4ff36}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:14px/1.5 "Segoe UI",Arial,sans-serif}
header{display:flex;justify-content:space-between;align-items:center;padding:14px 22px;border-bottom:1px solid var(--line)}
.logo{font-size:19px;font-weight:700}.logo span{color:var(--acc)}
.pill{border:1px solid var(--line);border-radius:20px;padding:4px 12px;color:var(--dim);font-size:12px}
main{display:grid;grid-template-columns:400px 1fr;gap:16px;padding:16px 22px;max-width:1440px;margin:0 auto}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}
h3{margin:0 0 12px;font-size:13px;letter-spacing:.08em;color:var(--dim);text-transform:uppercase}
label{display:block;font-size:12px;color:var(--dim);margin:10px 0 4px}
input,textarea,select{width:100%;background:#0a0e16;border:1px solid var(--line);border-radius:8px;color:var(--txt);padding:8px 10px;font:inherit;font-size:13px}
textarea{resize:vertical;min-height:56px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.gen{width:100%;margin-top:16px;background:var(--acc);color:#0a0f05;border:0;border-radius:10px;padding:12px;font-weight:700;font-size:15px;cursor:pointer}
.gen:hover{filter:brightness(1.08)}
#status{margin-top:10px;font-size:13px;color:var(--dim);min-height:20px}
a{color:var(--acc);cursor:pointer}
.prev{display:flex;flex-direction:column;gap:14px}
.prev img{width:100%;border-radius:14px;border:1px solid var(--line);background:#000}
.hint{color:var(--dim);font-size:12.5px}
</style></head><body>
<header><div class="logo">Readme<span>Rocket</span></div><div class="pill">Offline - Local Only</div></header>
<main>
<section class="panel">
<h3>01 - Your details (only the first three are needed)</h3>
<label>Your name</label><input id="name">
<label>GitHub username</label><input id="username">
<label>Role line</label><input id="role">
<details><summary style="cursor:pointer;color:var(--acc);margin:12px 0 4px">Optional details: tagline, about, skills, theme, numbers, links</summary>
<label>Tagline</label><input id="tagline">
<label>About (one or two lines)</label><textarea id="about"></textarea>
<label>Skills (comma separated)</label><input id="skills">
<label>Theme preset</label><select id="theme"><option value="lime">Lime on black</option><option value="ocean">Ocean blue</option><option value="amber">Amber</option></select>
<label>Template (structure)</label><select id="template"><option value="classic">Classic: about, projects, skills, stats</option><option value="showcase">Showcase: projects first, 3-wide skills</option><option value="compact">Compact: short hero, tight order</option></select>
<label>Typography</label><select id="font"><option value="modern">Modern (Segoe UI)</option><option value="mono">Mono (Consolas)</option><option value="serif">Serif (Georgia)</option><option value="impact">Impact (Arial Black)</option></select>
<div class="row"><div><label>Accent colour</label><input type="color" id="col_accent" style="height:38px;padding:2px"></div><div><label>Second colour</label><input type="color" id="col_accent2" style="height:38px;padding:2px"></div></div>
<div class="row"><div><label>Background</label><input type="color" id="col_bg" style="height:38px;padding:2px"></div><div><label>Hero alignment</label><select id="opt_align"><option value="left">Left</option><option value="center">Center</option></select></div></div>
<div class="row"><div><label>Corners</label><select id="opt_corners"><option value="round">Rounded</option><option value="sharp">Sharp</option></select></div><div><label>Animations</label><select id="opt_anim"><option value="on">On</option><option value="off">Off (static)</option></select></div></div>
<label style="display:flex;gap:8px;align-items:center;margin-top:10px"><input type="checkbox" id="opt_wave" checked style="width:auto"> Flowing divider line</label>
<div class="row"><div><label>Public repos</label><input id="st_repos"></div><div><label>Total stars</label><input id="st_stars"></div></div>
<div class="row"><div><label>Followers</label><input id="st_followers"></div><div><label>Contributions (1y)</label><input id="st_contrib"></div></div>
<label>GitHub link</label><input id="so_github">
<label>LinkedIn link</label><input id="so_linkedin">
<label>Instagram link</label><input id="so_instagram">
<label>Website link</label><input id="so_website">
<label>X link</label><input id="so_x">
<label>Email</label><input id="so_email">
<label>Projects (one per line: Name | link | stars | description)</label><textarea id="projects" placeholder="myapp | https://github.com/you/myapp | 12 | What the app does"></textarea>
</details>
<div class="row" style="margin-top:14px"><button id="blank" style="background:#131a26;color:var(--txt);border:1px solid var(--line);border-radius:10px;padding:10px;cursor:pointer">Start blank</button><button id="sample" style="background:#131a26;color:var(--txt);border:1px solid var(--line);border-radius:10px;padding:10px;cursor:pointer">Load sample</button></div>
<button class="gen" id="gen">GENERATE MY PROFILE</button>
<div id="status"></div>
</section>
<section class="panel prev">
<h3>02 - Live preview</h3>
<img id="p_hero" alt="Hero preview">
<img id="p_projects" alt="Projects preview">
<img id="p_skills" alt="Skills preview">
<img id="p_stats" alt="Stats preview">
<div class="hint">Minimum data is fine: name, username and role alone already build a complete profile. Panels with no data are simply left out. The pack is written to the profile_pack folder: README.md plus assets. Put it in a GitHub repo named exactly like your username and it becomes your profile. <a id="openlink">Open output folder</a></div>
</section>
</main>
<script>
const $=id=>document.getElementById(id);
const PRESETS={lime:{accent:'#c4ff36',accent2:'#7ee787',bg:'#07090e'},ocean:{accent:'#38bdf8',accent2:'#818cf8',bg:'#04121f'},amber:{accent:'#fbbf24',accent2:'#fb923c',bg:'#140d02'}};
function syncColors() {const p=PRESETS[$('theme').value]||PRESETS.lime;$('col_accent').value=p.accent;$('col_accent2').value=p.accent2;$('col_bg').value=p.bg;}
function collect(){return{name:$('name').value,username:$('username').value,role:$('role').value,tagline:$('tagline').value,about:$('about').value,
skills:$('skills').value.split(',').map(s=>s.trim()).filter(Boolean),theme:$('theme').value,template:$('template').value,font:$('font').value,
colors:{accent:$('col_accent').value,accent2:$('col_accent2').value,bg:$('col_bg').value},
options:{align:$('opt_align').value,corners:$('opt_corners').value,animate:$('opt_anim').value==='on',wave:$('opt_wave').checked},
stats:{repos:$('st_repos').value||'0',stars:$('st_stars').value||'0',followers:$('st_followers').value||'0',contributions:$('st_contrib').value||'0'},
socials:{github:$('so_github').value,linkedin:$('so_linkedin').value,instagram:$('so_instagram').value,website:$('so_website').value,x:$('so_x').value,email:$('so_email').value},
projects:parseProjects()};}
function parseProjects(){return $('projects').value.split('\n').map(l=>l.trim()).filter(Boolean).map(l=>{const p=l.split('|').map(x=>x.trim());return{name:p[0]||'',link:p[1]||'',stars:p[2]||'',desc:p.slice(3).join(' | ')};});}
function fill(c){if(!c)return;$('name').value=c.name||'';$('username').value=c.username||'';$('role').value=c.role||'';$('tagline').value=c.tagline||'';$('about').value=c.about||'';
$('skills').value=(c.skills||[]).join(', ');$('theme').value=c.theme||'lime';const st=c.stats||{};$('st_repos').value=st.repos||'';$('st_stars').value=st.stars||'';$('st_followers').value=st.followers||'';$('st_contrib').value=st.contributions||'';
$('template').value=c.template||'classic';$('font').value=c.font||'modern';const cc=c.colors||{};const oo=c.options||{};
$('opt_align').value=oo.align||'left';$('opt_corners').value=oo.corners||'round';$('opt_anim').value=(oo.animate===false?'off':'on');$('opt_wave').checked=oo.wave!==false;
if(cc.accent){$('col_accent').value=cc.accent;$('col_accent2').value=cc.accent2||'#7ee787';$('col_bg').value=cc.bg||'#07090e';}else{syncColors();}
const so=c.socials||{};$('so_github').value=so.github||'';$('so_linkedin').value=so.linkedin||'';$('so_instagram').value=so.instagram||'';$('so_website').value=so.website||'';$('so_x').value=so.x||'';$('so_email').value=so.email||'';
window._projects=c.projects||[];$('projects').value=(c.projects||[]).map(p=>[p.name||'',p.link||'',p.stars||'',p.desc||''].join(' | ')).join('\n');}
function refresh(){const t='?t='+Date.now();$('p_hero').src='/out/assets/hero.svg'+t;$('p_projects').src='/out/assets/projects.svg'+t;$('p_skills').src='/out/assets/skills.svg'+t;$('p_stats').src='/out/assets/stats.svg'+t;}
fetch('/api/config').then(r=>r.json()).then(d=>{fill(d.config);refresh();});
document.addEventListener('change',e=>{if(e.target.id==='theme'&&!window._ccTouched)syncColors();if(['col_accent','col_accent2','col_bg'].includes(e.target.id))window._ccTouched=true;});
$('gen').onclick=()=>{const cfg=collect();$('status').textContent='Generating...';
fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)})
.then(r=>r.json()).then(d=>{if(d.ok){$('status').textContent='Done: '+d.files.length+' files written to profile_pack.';refresh();}
else{$('status').textContent='Failed: '+d.error;}}).catch(e=>{$('status').textContent='Failed: '+e;});};
$('openlink').onclick=()=>fetch('/api/open',{method:'POST'});
$('blank').onclick=()=>{fill({name:'',username:'',role:'',tagline:'',about:'',skills:[],theme:'lime',template:'classic',font:'modern',stats:{},socials:{},projects:[]});window._ccTouched=false;syncColors();$('status').textContent='Blank form. Type your own details.';};
$('sample').onclick=()=>{fetch('/api/sample').then(r=>r.json()).then(d=>{fill(d.config);window._ccTouched=false;$('status').textContent='Sample loaded. Replace it with your own details.';});};
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except OSError:
            pass

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/":
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif u.path == "/api/sample":
            self._send(200, json.dumps({"ok": True, "config": rr.SAMPLE_CONFIG}))
        elif u.path == "/api/config":
            cfg = None
            if os.path.isfile(CONFIG):
                try:
                    with open(CONFIG, encoding="utf-8") as f:
                        cfg = json.load(f)
                except Exception:
                    cfg = None
            self._send(200, json.dumps({"ok": True, "config": cfg or rr.DEMO_CONFIG}))
        elif u.path.startswith("/out/"):
            rel = u.path[5:].replace("/", os.sep)
            path = os.path.normpath(os.path.join(OUTDIR, rel))
            if not path.startswith(os.path.normpath(OUTDIR) + os.sep):
                self._send(404, json.dumps({"ok": False}))
                return
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    data = f.read()
                ctype = "image/svg+xml" if path.endswith(".svg") else "text/plain; charset=utf-8"
                self._send(200, data, ctype)
            else:
                self._send(404, json.dumps({"ok": False}))
        else:
            self._send(404, json.dumps({"ok": False}))

    def do_POST(self):
        u = urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length else b""
        if u.path == "/api/generate":
            try:
                cfg = json.loads(raw or b"{}")
                with open(CONFIG, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
                files = rr.generate(cfg, OUTDIR)
                self._send(200, json.dumps({"ok": True, "files": files}))
            except Exception as e:
                self._send(200, json.dumps({"ok": False, "error": str(e)}))
        elif u.path == "/api/open":
            try:
                if sys.platform.startswith("win"):
                    os.startfile(OUTDIR)
                elif sys.platform == "darwin":
                    subprocess.run(["open", OUTDIR])
                else:
                    subprocess.run(["xdg-open", OUTDIR])
                self._send(200, json.dumps({"ok": True}))
            except Exception as e:
                self._send(200, json.dumps({"ok": False, "error": str(e)}))
        else:
            self._send(404, json.dumps({"ok": False}))


def main():
    port = None
    for cand in range(8820, 8840):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", cand), Handler)
            port = cand
            break
        except OSError:
            continue
    if port is None:
        print("No free port found.")
        return 1
    url = f"http://127.0.0.1:{port}/"
    print(f"ReadmeRocket UI running at {url}")
    try:
        import webview
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        webview.create_window("ReadmeRocket", url, width=1340, height=900)
        webview.start()
        return 0
    except Exception:
        pass
    webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
