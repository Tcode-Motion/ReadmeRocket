#!/usr/bin/env python3
"""ReadmeRocket: one small config in, a full animated GitHub profile out.

Reads rocket.json (or flags) and generates a profile pack:
  README.md          the profile readme
  assets/hero.svg    animated hero banner (name, role, tagline)
  assets/skills.svg  animated skills panel
  assets/stats.svg   animated numbers panel
  assets/connect.svg animated connect panel

Offline, standard library only. Animations are SMIL, which GitHub
renders inside SVG images, the same technique used by hand-built
animated profiles.

Usage:
  python readmerocket.py                 (uses ./rocket.json)
  python readmerocket.py --config my.json --out pack_folder
  python readmerocket.py --demo          (writes a sample rocket.json)
"""
import argparse
import json
import os
import sys
from xml.sax.saxutils import escape

THEMES = {
    "lime":  {"bg": "#07090e", "panel": "#0d1117", "accent": "#c4ff36", "accent2": "#7ee787", "text": "#e6edf3", "dim": "#8b949e"},
    "ocean": {"bg": "#04121f", "panel": "#0a1c2e", "accent": "#38bdf8", "accent2": "#818cf8", "text": "#e6edf3", "dim": "#8b949e"},
    "amber": {"bg": "#140d02", "panel": "#1d1503", "accent": "#fbbf24", "accent2": "#fb923c", "text": "#f5efe0", "dim": "#a89f8d"},
}

FONT = "Segoe UI, Arial, sans-serif"
MONO = "Consolas, Menlo, monospace"

FONT_SETS = {
    "modern": {"head": "Segoe UI, Arial, sans-serif", "body": "Segoe UI, Arial, sans-serif", "mono": "Consolas, Menlo, monospace"},
    "mono": {"head": "Consolas, Menlo, monospace", "body": "Consolas, Menlo, monospace", "mono": "Consolas, Menlo, monospace"},
    "serif": {"head": "Georgia, 'Times New Roman', serif", "body": "Georgia, 'Times New Roman', serif", "mono": "Consolas, Menlo, monospace"},
    "impact": {"head": "'Arial Black', Arial, sans-serif", "body": "Arial, sans-serif", "mono": "Consolas, Menlo, monospace"},
}

TEMPLATES = ("classic", "showcase", "compact")


def _hex(v, fallback):
    v = str(v or "").strip()
    return v if len(v) == 7 and v.startswith("#") and all(ch in "0123456789abcdefABCDEF" for ch in v[1:]) else fallback


def resolve_theme(c):
    th = dict(THEMES.get(c.get("theme", "lime"), THEMES["lime"]))
    cc = c.get("colors", {}) if isinstance(c.get("colors", {}), dict) else {}
    th["accent"] = _hex(cc.get("accent"), th["accent"])
    th["accent2"] = _hex(cc.get("accent2"), th["accent2"])
    th["bg"] = _hex(cc.get("bg"), th["bg"])
    th["panel"] = _hex(cc.get("panel"), th["panel"])
    return th


def fonts_of(c):
    return FONT_SETS.get(c.get("font", "modern"), FONT_SETS["modern"])


def opts_of(c):
    o = c.get("options", {}) if isinstance(c.get("options", {}), dict) else {}
    return {
        "animate": o.get("animate", True) is not False,
        "wave": o.get("wave", True) is not False,
        "bars": o.get("bars", True) is not False,
        "align": "center" if o.get("align") == "center" else "left",
        "radius": 4 if o.get("corners") == "sharp" else 18,
    }


def esc(t):
    return escape(str(t), {'"': "&quot;"})


def fade_in(delay, dur=0.7, anim=True):
    if not anim:
        return ""
    return (f'<animate attributeName="opacity" from="0" to="1" '
            f'begin="{delay}s" dur="{dur}s" fill="freeze"/>')


def slide_up(delay, anim=True):
    if not anim:
        return ""
    return (f'<animateTransform attributeName="transform" type="translate" '
            f'from="0 14" to="0 0" begin="{delay}s" dur="0.6s" fill="freeze"/>')


def g_open(anim, extra=""):
    """Group wrapper that starts visible when animations are off."""
    return "<g opacity=\"1\">" if not anim else f'<g opacity="0"{extra}>' 


def _num(v):
    try:
        return int(str(v).replace(",", "").strip() or 0)
    except ValueError:
        return 0


def normalize(c):
    """Fill the gaps from the data that IS given, so a name and a
    username alone already produce a complete profile. Nothing is
    invented: every fill is derived from the user's own inputs."""
    c = dict(c)
    user = str(c.get("username", "")).strip()
    if not str(c.get("name", "")).strip():
        c["name"] = user or "Your Name"
    soc = dict(c.get("socials", {}))
    if user and not soc.get("github"):
        soc["github"] = f"https://github.com/{user}"
    c["socials"] = soc
    if not str(c.get("about", "")).strip():
        bits = []
        role = str(c.get("role", "")).strip()
        if role:
            bits.append(f"{c['name']} is a {role}.")
        skills = [str(x).strip() for x in c.get("skills", []) if str(x).strip()]
        if skills:
            bits.append("Works mostly with " + ", ".join(skills[:3]) + ".")
        projects = c.get("projects", [])
        if projects and projects[0].get("name"):
            bits.append(f"Currently building {projects[0]['name']}.")
        c["about"] = " ".join(bits) if bits else "Welcome to my GitHub profile."
    st = c.get("stats", {})
    c["_has_stats"] = any(_num(st.get(k)) > 0 for k in ("repos", "stars", "followers", "contributions"))
    c["_has_skills"] = bool([x for x in c.get("skills", []) if str(x).strip()])
    c["_has_socials"] = any(str(v).strip() for v in soc.values())
    c["_has_projects"] = bool(c.get("projects"))
    return c


def grp(anim, delay, slide=False):
    if not anim:
        return '<g opacity="1">'
    inner = fade_in(delay)
    tr = ' transform="translate(0 14)"' if slide else ''
    if slide:
        inner += slide_up(delay)
    return f'<g opacity="0"{tr}>{inner}'


def hero_svg(c, th, F, o, tpl):
    name = esc(c.get("name", "Your Name"))
    role_txt = str(c.get("role", "")).strip() or "Developer"
    role = esc(role_txt)
    tag = esc(c.get("tagline", ""))
    anim = o["animate"]
    center = o["align"] == "center"
    compact = tpl == "compact"
    w = 880
    h = 176 if compact else 240
    R = o["radius"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    parts.append(f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
                 f'<stop offset="0" stop-color="{th["accent"]}"/><stop offset="1" stop-color="{th["accent2"]}"/></linearGradient></defs>')
    parts.append(f'<rect width="{w}" height="{h}" rx="{R}" fill="{th["bg"]}"/>')
    parts.append(f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="{max(1, R-1)}" fill="none" stroke="{th["accent"]}" stroke-opacity="0.45" stroke-width="2"/>')
    pulse = '<animate attributeName="opacity" from="0.3" to="1" dur="2.4s" repeatCount="indefinite"/>' if anim else ''
    parts.append(f'<rect width="{w}" height="6" fill="url(#g)">{pulse}</rect>')
    full = "Hi, I am " + str(c.get("name", "Your Name"))
    fs = 38 if compact else 46
    est = len(full) * (fs * 0.576)
    if est > 780:
        fs = max(22, int(fs * 780 / est))
    nx = 440 if center else 48
    na = ' text-anchor="middle"' if center else ''
    ny = 74 if compact else 92
    parts.append(f'{grp(anim, 0.1)}<text x="{nx}" y="{ny}"{na} font-family="{F["head"]}" font-size="{fs}" font-weight="700" fill="{th["text"]}">Hi, I am <tspan fill="{th["accent"]}">{name}</tspan></text></g>')
    ry = 112 if compact else 138
    role_w = len(role_txt) * 14.6
    cx = (440 + role_w / 2 + 8) if center else (52 + role_w)
    blink = '<animate attributeName="opacity" values="1;0;1" dur="1.1s" repeatCount="indefinite"/>' if anim else ''
    parts.append(f'{grp(anim, 0.5)}<text x="{nx}" y="{ry}"{na} font-family="{F["mono"]}" font-size="24" fill="{th["accent2"]}">{role}</text>'
                 f'<rect x="{cx:.0f}" y="{ry - 20}" width="12" height="26" fill="{th["accent"]}">{blink}</rect></g>')
    if tag:
        ty = 148 if compact else 182
        chw = 11.5 if "Consolas" in F["body"] or "Menlo" in F["body"] else 9.6
        tw = min(830, 30 + len(str(c.get("tagline", ""))) * chw)
        clipw = f'<animate attributeName="width" from="0" to="{tw}" begin="0.9s" dur="{0.6 + len(str(c.get("tagline",""))) * 0.028:.2f}s" fill="freeze"/>' if anim else ''
        rectw = tw if not anim else 0
        clipx = (440 - tw / 2) if center else 44
        parts.append(f'<defs><clipPath id="tc"><rect x="{clipx:.0f}" y="{ty - 24}" width="{rectw}" height="34">{clipw}</rect></clipPath></defs>')
        parts.append(f'<g clip-path="url(#tc)"><text x="{nx}" y="{ty}"{na} font-family="{F["body"]}" font-size="19" fill="{th["dim"]}">{tag}</text></g>')
    if not compact:
        parts.append(f'{grp(anim, 1.2)}<text x="{nx}" y="216"{na} font-family="{F["mono"]}" font-size="14" fill="{th["dim"]}">readmerocket: profile online</text></g>')
    parts.append('</svg>')
    return "".join(parts)


def skills_svg(c, th, F, o, cols=4):
    skills = [str(x).strip() for x in c.get("skills", []) if str(x).strip()]
    rows = max(1, (len(skills) + cols - 1) // cols)
    cw = (880 - 80 - (cols - 1) * 12) // cols
    chh = 46
    w = 880
    h = 78 + rows * (chh + 12)
    anim = o["animate"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    parts.append(f'<rect width="{w}" height="{h}" rx="{o["radius"]}" fill="{th["panel"]}"/>')
    parts.append(f'<text x="40" y="46" font-family="{F["head"]}" font-size="22" font-weight="700" fill="{th["text"]}">Skills and tools</text>')
    for i, sk in enumerate(skills):
        r, col = divmod(i, cols)
        x = 40 + col * (cw + 12)
        y = 66 + r * (chh + 12)
        parts.append(f'{grp(anim, 0.15 + i * 0.09, slide=True)}'
                     f'<rect x="{x}" y="{y}" width="{cw}" height="{chh}" rx="10" fill="{th["bg"]}" stroke="{th["accent"]}" stroke-opacity="0.35"/>'
                     f'<circle cx="{x + 20}" cy="{y + chh // 2}" r="5" fill="{th["accent"]}"/>'
                     f'<text x="{x + 36}" y="{y + chh // 2 + 6}" font-family="{F["body"]}" font-size="16" fill="{th["text"]}">{esc(sk[:22])}</text></g>')
    parts.append('</svg>')
    return "".join(parts)


def stats_svg(c, th, F, o):
    st = c.get("stats", {})
    items = [(str(st.get("repos", "0")), "public repos"),
             (str(st.get("stars", "0")), "total stars"),
             (str(st.get("followers", "0")), "followers"),
             (str(st.get("contributions", "0")), "contributions (1y)")]
    w, h = 880, 150
    anim = o["animate"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    parts.append(f'<rect width="{w}" height="{h}" rx="{o["radius"]}" fill="{th["panel"]}"/>')
    vals = [_num(n) for n, _ in items]
    vmax = max(vals) if vals else 0
    for i, (num, label) in enumerate(items):
        x = 40 + i * 205
        bw = (12 + int(138 * vals[i] / vmax)) if (vmax and vals[i] > 0) else 0
        bar = ''
        if o["bars"]:
            grow = f'<animate attributeName="width" from="0" to="{bw}" begin="{0.35 + i * 0.18}s" dur="0.9s" fill="freeze"/>' if anim else ''
            startw = 0 if anim else bw
            bar = (f'<rect x="{x}" y="80" width="150" height="5" rx="2.5" fill="{th["bg"]}"/>'
                   f'<rect x="{x}" y="80" width="{startw}" height="5" rx="2.5" fill="{th["accent"]}">{grow}</rect>')
        parts.append(f'{grp(anim, 0.2 + i * 0.18)}'
                     f'<text x="{x}" y="66" font-family="{F["head"]}" font-size="40" font-weight="700" fill="{th["accent"]}">{esc(num)}</text>'
                     + bar +
                     f'<text x="{x}" y="112" font-family="{F["body"]}" font-size="15" fill="{th["dim"]}">{esc(label)}</text></g>')
    parts.append('</svg>')
    return "".join(parts)


def connect_svg(c, th, F, o):
    soc = c.get("socials", {})
    labels = [("github", "GitHub"), ("x", "X / Twitter"), ("linkedin", "LinkedIn"),
              ("instagram", "Instagram"), ("website", "Website"), ("email", "Email")]
    present = [(k, lbl) for k, lbl in labels if soc.get(k)]
    w, h = 880, 108
    anim = o["animate"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    parts.append(f'<rect width="{w}" height="{h}" rx="{o["radius"]}" fill="{th["panel"]}"/>')
    parts.append(f'<text x="40" y="44" font-family="{F["head"]}" font-size="20" font-weight="700" fill="{th["text"]}">Connect with me</text>')
    x = 40
    for i, (k, lbl) in enumerate(present):
        wid = 46 + len(lbl) * 9
        parts.append(f'{grp(anim, 0.2 + i * 0.12, slide=True)}'
                     f'<rect x="{x}" y="58" width="{wid}" height="34" rx="17" fill="{th["bg"]}" stroke="{th["accent"]}" stroke-opacity="0.4"/>'
                     f'<text x="{x + wid // 2}" y="80" text-anchor="middle" font-family="{F["body"]}" font-size="15" fill="{th["accent"]}">{lbl}</text></g>')
        x += wid + 12
    parts.append('</svg>')
    return "".join(parts)


def wave_svg(c, th, F, o):
    pulse = '<animate attributeName="opacity" values="0.25;0.7;0.25" dur="3.2s" repeatCount="indefinite"/>' if o["animate"] else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="880" height="14" viewBox="0 0 880 14">'
            f'<defs><linearGradient id="wg" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{th["accent"]}"/><stop offset="1" stop-color="{th["accent2"]}"/></linearGradient></defs>'
            f'<rect x="0" y="5" width="880" height="3" rx="1.5" fill="url(#wg)" opacity="0.55">{pulse}</rect></svg>')


def projects_svg(c, th, F, o):
    projects = c.get("projects", [])[:3]
    w = 880
    h = 78 + 96
    anim = o["animate"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    parts.append(f'<rect width="{w}" height="{h}" rx="{o["radius"]}" fill="{th["panel"]}"/>')
    parts.append(f'<text x="40" y="46" font-family="{F["head"]}" font-size="22" font-weight="700" fill="{th["text"]}">Featured projects</text>')
    cw = (880 - 80 - 24) // 3
    charw = 8.2 if ("Consolas" in F["body"] or "Menlo" in F["body"]) else 6.9
    budget = max(12, int((cw - 32) / charw))
    for i, p in enumerate(projects):
        x = 40 + i * (cw + 12)
        nm = esc(str(p.get("name", ""))[:24])
        desc = str(p.get("desc", ""))
        lines = []
        cur = ""
        for wd in desc.split():
            if len(cur) + len(wd) + 1 <= budget:
                cur = (cur + " " + wd).strip()
            else:
                lines.append(cur)
                cur = wd
            if len(lines) == 2:
                break
        if len(lines) < 2 and cur:
            lines.append(cur)
        line1 = lines[0] if lines else ""
        line2 = lines[1] if len(lines) > 1 else ""
        stars = esc(str(p.get("stars", "")))
        parts.append(f'{grp(anim, 0.2 + i * 0.16, slide=True)}'
                     f'<rect x="{x}" y="62" width="{cw}" height="96" rx="12" fill="{th["bg"]}" stroke="{th["accent"]}" stroke-opacity="0.35"/>'
                     f'<text x="{x + 16}" y="92" font-family="{F["head"]}" font-size="18" font-weight="700" fill="{th["accent"]}">{nm}</text>'
                     + (f'<text x="{x + cw - 16}" y="92" text-anchor="end" font-family="{F["body"]}" font-size="14" fill="{th["dim"]}">&#9733; {stars}</text>' if stars else '')
                     + f'<text x="{x + 16}" y="118" font-family="{F["body"]}" font-size="13.5" fill="{th["text"]}">{esc(line1)}</text>'
                     f'<text x="{x + 16}" y="138" font-family="{F["body"]}" font-size="13.5" fill="{th["text"]}">{esc(line2)}</text></g>')
    parts.append('</svg>')
    return "".join(parts)


def build_readme(c):
    tpl = c.get("template", "classic")
    o = opts_of(c)
    L = []
    L.append('<div align="center">')
    L.append('')
    L.append(f'<img src="assets/hero.svg" alt="{esc(c.get("name",""))}" width="880"/>')
    L.append('')
    if o["wave"]:
        L.append('<img src="assets/wave.svg" alt="" width="880"/>')
        L.append('')
    L.append('</div>')
    L.append('')

    def about_block():
        return ['## About me', '', c.get("about", ""), '']

    def projects_block():
        b = ['<div align="center">', '', '<img src="assets/projects.svg" alt="Featured projects" width="880"/>', '', '</div>', '',
             '| Project | What it is | Stars |', '|---|---|---|']
        for p in c.get("projects", []):
            nm = p.get("name", "")
            link = p.get("link", "")
            cell = f'[{nm}]({link})' if link else nm
            desc = str(p.get("desc", "")).replace("|", "/")
            b.append(f'| {cell} | {desc} | {p.get("stars","")} |')
        b.append('')
        return b

    def panel_block(fname, alt):
        return ['<div align="center">', '', f'<img src="assets/{fname}" alt="{alt}" width="880"/>', '', '</div>', '']

    blocks = {"about": about_block}
    if c.get("_has_projects"):
        blocks["projects"] = projects_block
    if c.get("_has_skills"):
        blocks["skills"] = lambda: panel_block("skills.svg", "Skills")
    if c.get("_has_stats"):
        blocks["stats"] = lambda: panel_block("stats.svg", "Stats")
    if c.get("_has_socials"):
        blocks["connect"] = lambda: panel_block("connect.svg", "Connect")
    orders = {
        "classic": ["about", "projects", "skills", "stats", "connect"],
        "showcase": ["projects", "about", "stats", "skills", "connect"],
        "compact": ["about", "skills", "stats", "projects", "connect"],
    }
    for key in orders.get(tpl, orders["classic"]):
        if key in blocks:
            L.extend(blocks[key]())
    soc = c.get("socials", {})
    links = []
    if soc.get("github"): links.append(f'[GitHub]({soc["github"]})')
    if soc.get("x"): links.append(f'[X]({soc["x"]})')
    if soc.get("linkedin"): links.append(f'[LinkedIn]({soc["linkedin"]})')
    if soc.get("instagram"): links.append(f'[Instagram]({soc["instagram"]})')
    if soc.get("website"): links.append(f'[Website]({soc["website"]})')
    if soc.get("email"): links.append(f'[Email](mailto:{soc["email"]})')
    if links:
        L.append('<div align="center">' + ' &nbsp;·&nbsp; '.join(links) + '</div>')
        L.append('')
    L.append('---')
    L.append('<div align="center"><sub>Profile generated with ReadmeRocket</sub></div>')
    return "\n".join(L)


def generate(config, outdir):
    config = normalize(config)
    th = resolve_theme(config)
    F = fonts_of(config)
    o = opts_of(config)
    tpl = config.get("template", "classic")
    if tpl not in TEMPLATES:
        tpl = "classic"
    assets = os.path.join(outdir, "assets")
    os.makedirs(assets, exist_ok=True)
    files = {
        os.path.join(assets, "hero.svg"): hero_svg(config, th, F, o, tpl),
        os.path.join(outdir, "README.md"): build_readme(config),
    }
    if o["wave"]:
        files[os.path.join(assets, "wave.svg")] = wave_svg(config, th, F, o)
    if config["_has_skills"]:
        files[os.path.join(assets, "skills.svg")] = skills_svg(config, th, F, o, cols=3 if tpl == "showcase" else 4)
    if config["_has_stats"]:
        files[os.path.join(assets, "stats.svg")] = stats_svg(config, th, F, o)
    if config["_has_socials"]:
        files[os.path.join(assets, "connect.svg")] = connect_svg(config, th, F, o)
    if config["_has_projects"]:
        files[os.path.join(assets, "projects.svg")] = projects_svg(config, th, F, o)
    for stale in ("skills.svg", "stats.svg", "connect.svg", "projects.svg", "wave.svg"):
        p = os.path.join(assets, stale)
        if p not in files and os.path.isfile(p):
            os.remove(p)
    for path, content in files.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    return sorted(files)


SAMPLE_CONFIG = {
    "name": "Alex Carter",
    "username": "alexcarter",
    "role": "Full-stack Developer",
    "tagline": "I build web apps and open source tools.",
    "about": "Full-stack developer who enjoys clean code, small tools and shipping in the open. Most of my work lives here on GitHub.",
    "theme": "lime",
    "template": "classic",
    "font": "modern",
    "skills": ["JavaScript", "TypeScript", "React", "Node.js", "Python", "Git", "Docker", "PostgreSQL"],
    "stats": {"repos": "18", "stars": "42", "followers": "9", "contributions": "640"},
    "projects": [
        {"name": "weathernow", "desc": "A tiny weather app with offline caching", "link": "https://github.com/alexcarter/weathernow", "stars": "12"},
        {"name": "mdnotes", "desc": "Markdown notes that sync as plain files", "link": "https://github.com/alexcarter/mdnotes", "stars": "8"},
    ],
    "socials": {
        "github": "https://github.com/alexcarter",
        "linkedin": "https://www.linkedin.com/in/alexcarter",
        "website": "https://alexcarter.dev",
        "email": "alex@example.com",
    },
}

# Backwards-compatible alias
DEMO_CONFIG = SAMPLE_CONFIG


def main(argv=None):
    ap = argparse.ArgumentParser(prog="readmerocket", description="One config in, a full animated GitHub profile out.")
    ap.add_argument("--config", default="rocket.json", help="Config JSON (default: rocket.json)")
    ap.add_argument("--out", default="profile_pack", help="Output folder (default: profile_pack)")
    ap.add_argument("--demo", action="store_true", help="Write a sample rocket.json and exit")
    ap.add_argument("--theme", default="", help="Override theme: lime, ocean, amber")
    ap.add_argument("--template", default="", help="Override template: classic, showcase, compact")
    ap.add_argument("--font", default="", help="Override font: modern, mono, serif, impact")
    ap.add_argument("--no-animate", action="store_true", help="Generate static panels (no animations)")
    args = ap.parse_args(argv)
    if args.demo:
        with open("rocket.json", "w", encoding="utf-8") as f:
            json.dump(SAMPLE_CONFIG, f, indent=2)
        print("Wrote rocket.json (neutral sample). Edit it with your own details, then run again.")
        return 0
    if not os.path.isfile(args.config):
        print(f"No config found at {args.config}. Run with --demo to create a sample.")
        return 2
    try:
        with open(args.config, encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Could not read {args.config}: {e}. Fix the file, or run with --demo for a fresh sample.")
        return 2
    if not isinstance(config, dict):
        print(f"{args.config} must contain a JSON object. Run with --demo for a sample.")
        return 2
    if args.theme:
        config["theme"] = args.theme
    if args.template:
        config["template"] = args.template
    if args.font:
        config["font"] = args.font
    if args.no_animate:
        config.setdefault("options", {})["animate"] = False
    files = generate(config, args.out)
    print(f"Profile pack ready in {args.out}/ ({len(files)} files):")
    for fp in files:
        print("  " + fp)
    print("Put the pack in a repo named exactly like your GitHub username, and it becomes your profile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
