from __future__ import annotations

import hashlib
import html
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .media_library import MEDIA_ROOT


@dataclass(frozen=True)
class HyperFramesRender:
    media_relative_path: str
    preview_relative_path: str
    width: int
    height: int
    duration_seconds: float
    size_bytes: int
    checksum_sha256: str
    composition_dir: str


def enabled() -> bool:
    return os.getenv("HYPERFRAMES_ENABLED", "").strip().lower() in {"1", "true", "yes"}


def _node_major() -> int | None:
    node = shutil.which("node")
    if not node:
        return None
    try:
        value = subprocess.run(
            [node, "--version"], check=True, capture_output=True, text=True, timeout=10
        ).stdout.strip().lstrip("v")
        return int(value.split(".", 1)[0])
    except Exception:
        return None


def available() -> tuple[bool, str]:
    major = _node_major()
    if major is None:
        return False, "Node.js is not installed"
    if major < 22:
        return False, f"HyperFrames requires Node.js 22+; found {major}"
    if not shutil.which("npx"):
        return False, "npx is not installed"
    if not shutil.which("ffmpeg"):
        return False, "FFmpeg is not installed"
    return True, "ready"


def supports(family_id: str, template_id: str | None) -> bool:
    return family_id == "tech_behavior_motion" and template_id in {
        "behavior_prediction_engine",
        "algorithm_chose_you",
        "attention_auction",
        "machine_choice_explainer",
        "consequence_map",
    }


def _composition_html(scene, template_id: str, duration: float, width: int, height: int) -> str:
    title_map = {
        "behavior_prediction_engine": "Your actions become predictions",
        "algorithm_chose_you": "The algorithm chose this",
        "attention_auction": "An auction for your attention",
        "machine_choice_explainer": "A machine ranks what comes next",
        "consequence_map": "Every signal changes the next choice",
    }
    title = title_map.get(template_id, "The system learns from every signal")
    subtitle = str(scene.visual_intent or scene.narration or "").strip()
    subtitle = subtitle[:180]
    payload = json.dumps({"duration": duration, "template": template_id})
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#07101d;color:#f6f8ff;font-family:Inter,ui-sans-serif,system-ui,sans-serif}}
#stage{{position:relative;width:{width}px;height:{height}px;background:radial-gradient(circle at 72% 30%,#183764 0,#0a1729 34%,#050a12 78%);overflow:hidden}}
.grid{{position:absolute;inset:0;background-image:linear-gradient(rgba(120,170,255,.08) 1px,transparent 1px),linear-gradient(90deg,rgba(120,170,255,.08) 1px,transparent 1px);background-size:72px 72px;mask-image:linear-gradient(to right,transparent,#000 20%,#000)}}
.copy{{position:absolute;left:110px;top:130px;width:760px;z-index:4}}
.eyebrow{{font-size:24px;letter-spacing:.18em;text-transform:uppercase;color:#8ebcff;margin-bottom:28px}}
h1{{font-size:78px;line-height:1.02;margin:0 0 32px;max-width:820px}}
p{{font-size:28px;line-height:1.45;color:#bdc9dc;max-width:720px}}
.orbit{{position:absolute;border:2px solid rgba(119,176,255,.35);border-radius:999px;right:120px;top:120px;width:700px;height:700px;transform:rotate(-12deg)}}
.core{{position:absolute;right:350px;top:350px;width:250px;height:250px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#91d9ff,#4968ff 45%,#182558 75%);box-shadow:0 0 90px rgba(75,120,255,.6)}}
.node{{position:absolute;width:26px;height:26px;border-radius:50%;background:#8de5ff;box-shadow:0 0 28px #58bfff}}
.n1{{right:205px;top:245px}}.n2{{right:680px;top:330px}}.n3{{right:250px;top:700px}}.n4{{right:720px;top:620px}}
.signal{{position:absolute;height:3px;background:linear-gradient(90deg,transparent,#8de5ff,transparent);transform-origin:left center;opacity:.75}}
.s1{{right:330px;top:420px;width:390px;transform:rotate(18deg)}}.s2{{right:360px;top:530px;width:360px;transform:rotate(-24deg)}}
.badge{{position:absolute;right:130px;bottom:95px;padding:18px 26px;border:1px solid rgba(139,205,255,.42);border-radius:999px;background:rgba(8,20,38,.72);font-size:22px;color:#bfe7ff}}
</style></head><body>
<div id="stage" data-composition-id="documentary-exact-visual" data-start="0" data-duration="{duration}" data-width="{width}" data-height="{height}">
<div class="grid"></div><div class="copy"><div class="eyebrow">Exact Visual · HyperFrames</div><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>
<div class="orbit"></div><div class="core"></div><div class="node n1"></div><div class="node n2"></div><div class="node n3"></div><div class="node n4"></div><div class="signal s1"></div><div class="signal s2"></div><div class="badge">deterministic HTML motion</div>
<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script><script>
window.__compositionData={payload};
const tl=gsap.timeline({{paused:true}});
tl.from('.copy > *',{{opacity:0,y:36,duration:.75,stagger:.12,ease:'power3.out'}},.2)
.from('.core',{{scale:.3,opacity:0,duration:1.1,ease:'power3.out'}},.35)
.from('.orbit',{{scale:.75,opacity:0,rotation:-35,duration:1.4,ease:'power2.out'}},.45)
.from('.node',{{scale:0,opacity:0,duration:.5,stagger:.16,ease:'back.out(1.8)'}},1.0)
.from('.signal',{{scaleX:0,duration:.8,stagger:.18,ease:'power2.inOut'}},1.4)
.to('.core',{{scale:1.08,duration:1.6,yoyo:true,repeat:2,ease:'sine.inOut'}},1.7);
window.__timelines=window.__timelines||{{}};window.__timelines['documentary-exact-visual']=tl;
</script></div></body></html>'''


def render_scene(scene, family_id: str, template_id: str, *, width: int = 1920, height: int = 1080) -> HyperFramesRender:
    ready, reason = available()
    if not ready:
        raise RuntimeError(reason)

    duration = max(1.0, float(scene.duration_seconds))
    project_dir = MEDIA_ROOT / f"project-{scene.project_id:04d}"
    work_dir = project_dir / "hyperframes" / f"scene-{scene.scene_number:03d}-{template_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    index_path = work_dir / "index.html"
    index_path.write_text(
        _composition_html(scene, template_id, duration, width, height), encoding="utf-8"
    )

    before = set(work_dir.rglob("*.mp4"))
    command = ["npx", "--yes", "hyperframes", "render", "index.html"]
    subprocess.run(
        command,
        cwd=work_dir,
        check=True,
        timeout=max(120, int(duration * 45)),
        env={**os.environ, "CI": "1", "NO_COLOR": "1"},
    )
    produced = sorted(
        (path for path in work_dir.rglob("*.mp4") if path not in before),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not produced:
        produced = sorted(work_dir.rglob("*.mp4"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not produced:
        raise RuntimeError("HyperFrames completed without producing an MP4")

    destination = project_dir / "assets" / f"scene-{scene.scene_number:03d}-hyperframes-{template_id}.mp4"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(produced[0], destination)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    relative = destination.relative_to(MEDIA_ROOT).as_posix()
    return HyperFramesRender(
        media_relative_path=relative,
        preview_relative_path=relative,
        width=width,
        height=height,
        duration_seconds=duration,
        size_bytes=destination.stat().st_size,
        checksum_sha256=digest,
        composition_dir=work_dir.relative_to(MEDIA_ROOT).as_posix(),
    )
