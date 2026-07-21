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
    command: tuple[str, ...]
    stdout: str
    stderr: str


class HyperFramesRenderError(RuntimeError):
    """Raised with actionable CLI diagnostics when HyperFrames cannot render."""

    def __init__(
        self,
        message: str,
        *,
        command: list[str] | None = None,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        self.command = tuple(command or ())
        self.stdout = stdout.strip()
        self.stderr = stderr.strip()
        details = [message]
        if self.command:
            details.append(f"command={' '.join(self.command)}")
        if self.stderr:
            details.append(f"stderr={self.stderr[-2000:]}")
        elif self.stdout:
            details.append(f"stdout={self.stdout[-2000:]}")
        super().__init__(" | ".join(details))


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
        "machine_choice_cta",
        "consequence_map",
    }


_TEMPLATE_META: dict[str, tuple[str, str]] = {
    "behavior_prediction_engine": (
        "Your behavior becomes a forecast",
        "PAUSE · SKIP · REPLAY",
    ),
    "algorithm_chose_you": (
        "The system ranked this first",
        "ONE CHOICE · THOUSANDS SCORED",
    ),
    "attention_auction": (
        "Your next second is being auctioned",
        "BIDS ARRIVE IN MILLISECONDS",
    ),
    "machine_choice_explainer": (
        "Signals enter. A ranking comes out.",
        "INPUT · SCORE · SELECT",
    ),
    "machine_choice_cta": (
        "Who chooses what deserves your attention?",
        "YOU · OR THE SYSTEM",
    ),
    "consequence_map": (
        "One action changes the next recommendation",
        "EVERY SIGNAL MOVES THE PATH",
    ),
}


def _visual_markup(template_id: str) -> str:
    if template_id == "behavior_prediction_engine":
        return """
        <div class="visual prediction-system">
          <div class="signal-stack">
            <div class="signal-chip"><span>01</span><b>Pause</b><i>+0.18</i></div>
            <div class="signal-chip"><span>02</span><b>Replay</b><i>+0.32</i></div>
            <div class="signal-chip"><span>03</span><b>Skip</b><i>−0.24</i></div>
          </div>
          <div class="prediction-beam beam-a"></div>
          <div class="prediction-beam beam-b"></div>
          <div class="prediction-beam beam-c"></div>
          <div class="forecast-orb">
            <div class="orb-ring ring-one"></div>
            <div class="orb-ring ring-two"></div>
            <div class="forecast-value">87<span>%</span></div>
            <div class="forecast-label">NEXT ACTION</div>
          </div>
        </div>
        """
    if template_id == "algorithm_chose_you":
        return """
        <div class="visual ranking-system">
          <div class="rank-rail"></div>
          <div class="rank-card card-three"><span>03</span><div><b>Recommended</b><i>0.61</i></div></div>
          <div class="rank-card card-two"><span>02</span><div><b>Recommended</b><i>0.74</i></div></div>
          <div class="rank-card card-one selected"><span>01</span><div><b>Chosen for you</b><i>0.93</i></div><em>SELECTED</em></div>
          <div class="selection-line"></div>
          <div class="selection-dot"></div>
        </div>
        """
    if template_id == "attention_auction":
        return """
        <div class="visual auction-system">
          <div class="auction-ring"><div class="auction-time">0.08<span>s</span></div><small>DECISION WINDOW</small></div>
          <div class="bid bid-one"><span>VIDEO</span><b>72</b></div>
          <div class="bid bid-two"><span>AD</span><b>84</b></div>
          <div class="bid bid-three"><span>POST</span><b>66</b></div>
          <div class="bid-line line-one"></div><div class="bid-line line-two"></div><div class="bid-line line-three"></div>
          <div class="winning-bid">WINNING BID <strong>84</strong></div>
        </div>
        """
    if template_id == "machine_choice_explainer":
        return """
        <div class="visual scoring-system">
          <div class="input-column"><div>WATCH TIME</div><div>RECENCY</div><div>SIMILARITY</div></div>
          <div class="flow-line flow-one"></div><div class="flow-line flow-two"></div><div class="flow-line flow-three"></div>
          <div class="score-engine"><span>MODEL</span><b>RANK</b><i>3,240 candidates</i></div>
          <div class="output-arrow"></div>
          <div class="output-card"><small>NEXT</small><b>PLAY</b><span>0.91</span></div>
        </div>
        """
    if template_id == "machine_choice_cta":
        return """
        <div class="visual choice-system">
          <div class="choice-path human-path"><span>YOU</span><div class="path-line"></div><i>intent</i></div>
          <div class="phone-frame"><div class="phone-glow"></div><div class="screen-item"></div><div class="screen-item short"></div><div class="screen-item"></div></div>
          <div class="choice-path system-path"><span>SYSTEM</span><div class="path-line"></div><i>prediction</i></div>
          <div class="choice-divider"></div>
        </div>
        """
    return """
    <div class="visual consequence-system">
      <div class="origin-node"><span>ACTION</span><b>pause</b></div>
      <div class="branch branch-one"></div><div class="branch branch-two"></div><div class="branch branch-three"></div>
      <div class="outcome outcome-one"><span>MORE LIKE THIS</span><b>+18%</b></div>
      <div class="outcome outcome-two"><span>TOPIC WEIGHT</span><b>+11%</b></div>
      <div class="outcome outcome-three"><span>RETURN ODDS</span><b>+7%</b></div>
      <div class="next-node"><span>NEXT FEED</span><b>changed</b></div>
      <div class="consequence-arrow"></div>
    </div>
    """


def _animation_script(template_id: str, duration: float) -> str:
    repeats = max(0, int(duration / 2.4) - 1)
    scripts = {
        "behavior_prediction_engine": f"""
          tl.from('.signal-chip',{{opacity:0,x:-80,duration:.55,stagger:.14,ease:'power3.out'}},.35)
            .from('.prediction-beam',{{scaleX:0,opacity:0,duration:.65,stagger:.13,ease:'power2.inOut'}},.75)
            .from('.forecast-orb',{{scale:.55,opacity:0,duration:.9,ease:'back.out(1.5)'}},.85)
            .from('.forecast-value',{{textContent:0,roundProps:'textContent',duration:1.1,ease:'power2.out'}},1.05)
            .to('.orb-ring',{{rotation:180,duration:2.2,repeat:{repeats},ease:'none'}},1.1);
        """,
        "algorithm_chose_you": f"""
          tl.from('.rank-rail',{{scaleY:0,duration:.8,ease:'power2.out'}},.35)
            .from('.rank-card',{{opacity:0,x:110,duration:.6,stagger:.16,ease:'power3.out'}},.55)
            .from('.selection-line',{{scaleX:0,duration:.65,ease:'power2.inOut'}},1.25)
            .from('.selection-dot',{{scale:0,opacity:0,duration:.45,ease:'back.out(2)'}},1.65)
            .to('.selected',{{boxShadow:'0 0 80px rgba(93,205,255,.36)',duration:1.1,yoyo:true,repeat:{max(1, repeats)},ease:'sine.inOut'}},1.8);
        """,
        "attention_auction": f"""
          tl.from('.auction-ring',{{scale:.45,opacity:0,duration:.85,ease:'back.out(1.6)'}},.35)
            .from('.bid',{{opacity:0,scale:.7,duration:.5,stagger:.13,ease:'back.out(1.7)'}},.7)
            .from('.bid-line',{{scaleX:0,duration:.55,stagger:.12,ease:'power2.inOut'}},1.0)
            .from('.winning-bid',{{opacity:0,y:35,duration:.6,ease:'power3.out'}},1.55)
            .to('.auction-ring',{{rotation:90,duration:2.4,repeat:{repeats},ease:'none'}},1.65);
        """,
        "machine_choice_explainer": """
          tl.from('.input-column > div',{opacity:0,x:-70,duration:.5,stagger:.12,ease:'power3.out'},.35)
            .from('.flow-line',{scaleX:0,duration:.55,stagger:.12,ease:'power2.inOut'},.75)
            .from('.score-engine',{scale:.65,opacity:0,duration:.75,ease:'back.out(1.5)'},1.0)
            .from('.output-arrow',{scaleX:0,duration:.55,ease:'power2.inOut'},1.45)
            .from('.output-card',{opacity:0,x:80,duration:.65,ease:'power3.out'},1.65)
            .to('.score-engine',{filter:'brightness(1.35)',duration:.8,yoyo:true,repeat:2,ease:'sine.inOut'},1.85);
        """,
        "machine_choice_cta": f"""
          tl.from('.phone-frame',{{scale:.72,opacity:0,duration:.8,ease:'back.out(1.5)'}},.35)
            .from('.choice-path',{{opacity:0,y:50,duration:.65,stagger:.18,ease:'power3.out'}},.7)
            .from('.path-line',{{scaleX:0,duration:.7,stagger:.18,ease:'power2.inOut'}},1.05)
            .from('.choice-divider',{{scaleY:0,duration:.75,ease:'power2.out'}},1.25)
            .to('.phone-glow',{{opacity:.9,scale:1.18,duration:1.3,yoyo:true,repeat:{max(1, repeats)},ease:'sine.inOut'}},1.55);
        """,
        "consequence_map": """
          tl.from('.origin-node',{scale:.55,opacity:0,duration:.7,ease:'back.out(1.6)'},.35)
            .from('.branch',{scaleX:0,duration:.6,stagger:.12,ease:'power2.inOut'},.75)
            .from('.outcome',{opacity:0,y:45,duration:.55,stagger:.13,ease:'power3.out'},1.05)
            .from('.consequence-arrow',{scaleX:0,duration:.55,ease:'power2.inOut'},1.65)
            .from('.next-node',{scale:.65,opacity:0,duration:.7,ease:'back.out(1.6)'},1.85)
            .to('.next-node',{boxShadow:'0 0 80px rgba(111,224,255,.32)',duration:1.1,yoyo:true,repeat:2,ease:'sine.inOut'},2.1);
        """,
    }
    return scripts[template_id]


def _composition_html(scene, template_id: str, duration: float, width: int, height: int) -> str:
    title, kicker = _TEMPLATE_META.get(
        template_id,
        ("The system learns from every signal", "BEHAVIOR · MODEL · CHOICE"),
    )
    composition_id = "documentary-exact-visual"
    payload = json.dumps({"duration": duration, "template": template_id})
    visual = _visual_markup(template_id)
    animation = _animation_script(template_id, duration)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
:root{{--ink:#f4f7ff;--muted:#9eb0c9;--cyan:#6fe0ff;--blue:#567dff;--violet:#9d78ff;--panel:rgba(12,25,45,.78)}}
*{{box-sizing:border-box}}
html,body{{margin:0;width:100%;height:100%;overflow:hidden;background:#040812;color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,sans-serif}}
#stage{{position:relative;width:{width}px;height:{height}px;overflow:hidden;background:radial-gradient(circle at 73% 42%,#16305b 0,#09162a 34%,#040812 78%)}}
#stage:before{{content:"";position:absolute;inset:-18%;background:conic-gradient(from 220deg at 70% 45%,transparent 0 23%,rgba(74,126,255,.16) 29%,transparent 36% 100%);filter:blur(28px);opacity:.9}}
#stage:after{{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(3,7,15,.92) 0,rgba(3,7,15,.48) 45%,rgba(3,7,15,.08) 72%),repeating-linear-gradient(0deg,rgba(255,255,255,.018) 0 1px,transparent 1px 4px);pointer-events:none}}
.scene{{position:absolute;inset:0;overflow:hidden}}
.scene-content{{position:absolute;inset:0;padding:108px 112px;display:grid;grid-template-columns:44% 56%;align-items:center}}
.copy{{position:relative;z-index:6;align-self:center;max-width:760px}}
.kicker{{font-size:22px;letter-spacing:.19em;font-weight:750;color:#87c9ff;margin-bottom:28px}}
h1{{font-size:76px;line-height:1.01;letter-spacing:-.045em;margin:0;max-width:780px;text-wrap:balance}}
.copy-rule{{width:124px;height:5px;border-radius:999px;background:linear-gradient(90deg,var(--cyan),var(--blue));margin-top:40px;box-shadow:0 0 22px rgba(111,224,255,.38)}}
.visual{{position:relative;z-index:5;width:100%;height:760px}}
.visual:before{{content:"";position:absolute;inset:36px 0 10px 40px;border:1px solid rgba(130,175,255,.12);border-radius:42px;background:linear-gradient(145deg,rgba(14,29,53,.38),rgba(4,10,19,.1));box-shadow:inset 0 1px rgba(255,255,255,.05),0 30px 100px rgba(0,0,0,.25)}}
.signal-stack{{position:absolute;left:80px;top:150px;display:grid;gap:26px}}
.signal-chip{{width:330px;height:94px;border:1px solid rgba(122,184,255,.24);border-radius:24px;background:rgba(11,25,47,.88);display:grid;grid-template-columns:54px 1fr 68px;align-items:center;padding:0 24px;box-shadow:0 18px 45px rgba(0,0,0,.24)}}
.signal-chip span{{font-size:18px;color:#6fe0ff}}.signal-chip b{{font-size:28px}}.signal-chip i{{font-style:normal;color:#9fc0ff;font-size:20px;text-align:right}}
.prediction-beam{{position:absolute;left:410px;width:265px;height:3px;background:linear-gradient(90deg,#6fe0ff,rgba(111,224,255,.08));transform-origin:left center}}
.beam-a{{top:195px;transform:rotate(14deg)}}.beam-b{{top:318px;transform:rotate(0)}}.beam-c{{top:446px;transform:rotate(-14deg)}}
.forecast-orb{{position:absolute;right:60px;top:145px;width:410px;height:410px;border-radius:50%;display:grid;place-content:center;text-align:center;background:radial-gradient(circle at 38% 32%,#a0efff 0,#4c79ff 28%,#172f74 58%,#07101e 72%);box-shadow:0 0 110px rgba(70,116,255,.46)}}
.orb-ring{{position:absolute;inset:-28px;border:2px solid rgba(112,223,255,.28);border-radius:50%}}.ring-two{{inset:-62px;border-style:dashed;opacity:.55}}
.forecast-value{{font-size:112px;line-height:.9;font-weight:780;letter-spacing:-.07em}}.forecast-value span{{font-size:40px;color:#bfeeff}}.forecast-label{{font-size:17px;letter-spacing:.22em;margin-top:20px;color:#d7e7ff}}
.ranking-system{{perspective:1100px}}.rank-rail{{position:absolute;right:80px;top:112px;width:4px;height:510px;background:linear-gradient(#6fe0ff,#6075ff,transparent);transform-origin:top}}
.rank-card{{position:absolute;right:110px;width:620px;height:132px;border:1px solid rgba(130,178,255,.22);border-radius:28px;background:linear-gradient(130deg,rgba(18,35,62,.94),rgba(8,17,32,.82));display:grid;grid-template-columns:82px 1fr 118px;align-items:center;padding:0 30px;box-shadow:0 24px 60px rgba(0,0,0,.28);transform:rotateY(-7deg)}}
.rank-card>span{{font-size:34px;color:#7de5ff;font-weight:780}}.rank-card div{{display:flex;justify-content:space-between;align-items:center}}.rank-card b{{font-size:28px}}.rank-card i{{font-style:normal;font-size:24px;color:#9eb6d9}}.rank-card em{{font-style:normal;font-size:16px;letter-spacing:.16em;color:#8de8ff;text-align:right}}
.card-three{{top:120px;opacity:.66;transform:translateX(80px) rotateY(-7deg) scale(.9)}}.card-two{{top:292px;opacity:.82;transform:translateX(34px) rotateY(-7deg) scale(.95)}}.card-one{{top:474px}}.selected{{border-color:rgba(111,224,255,.72);background:linear-gradient(130deg,rgba(27,58,96,.98),rgba(12,25,48,.94))}}
.selection-line{{position:absolute;right:720px;top:540px;width:160px;height:3px;background:linear-gradient(90deg,transparent,#6fe0ff);transform-origin:right}}.selection-dot{{position:absolute;right:875px;top:530px;width:24px;height:24px;border-radius:50%;background:#6fe0ff;box-shadow:0 0 32px #6fe0ff}}
.auction-ring{{position:absolute;left:330px;top:150px;width:390px;height:390px;border:3px solid rgba(111,224,255,.66);border-radius:50%;display:grid;place-content:center;text-align:center;background:radial-gradient(circle,rgba(34,78,130,.86),rgba(7,16,29,.78) 64%);box-shadow:0 0 90px rgba(63,124,255,.35)}}
.auction-ring:before{{content:"";position:absolute;inset:-20px;border:2px dashed rgba(139,120,255,.46);border-radius:50%}}.auction-time{{font-size:98px;font-weight:780;letter-spacing:-.06em}}.auction-time span{{font-size:34px;color:#9edfff}}.auction-ring small{{font-size:15px;letter-spacing:.2em;color:#b6c9e6;margin-top:18px}}
.bid{{position:absolute;width:190px;height:104px;border-radius:24px;border:1px solid rgba(130,178,255,.3);background:rgba(11,25,47,.92);display:flex;justify-content:space-between;align-items:center;padding:0 24px;box-shadow:0 20px 50px rgba(0,0,0,.26)}}.bid span{{font-size:16px;letter-spacing:.14em;color:#a9bdd9}}.bid b{{font-size:38px;color:#8fe8ff}}.bid-one{{right:65px;top:95px}}.bid-two{{right:15px;top:300px;border-color:rgba(158,120,255,.65)}}.bid-three{{right:95px;top:510px}}
.bid-line{{position:absolute;left:680px;width:210px;height:3px;background:linear-gradient(90deg,#6fe0ff,transparent);transform-origin:left}}.line-one{{top:245px;transform:rotate(-24deg)}}.line-two{{top:340px}}.line-three{{top:445px;transform:rotate(24deg)}}
.winning-bid{{position:absolute;left:365px;bottom:76px;padding:16px 24px;border-radius:999px;background:rgba(100,75,210,.26);border:1px solid rgba(167,133,255,.44);font-size:16px;letter-spacing:.15em}}.winning-bid strong{{font-size:24px;color:#d5c7ff;margin-left:12px}}
.input-column{{position:absolute;left:72px;top:145px;display:grid;gap:24px}}.input-column>div{{width:260px;padding:22px 24px;border-radius:20px;border:1px solid rgba(125,181,255,.24);background:rgba(11,25,47,.9);font-size:17px;letter-spacing:.1em;color:#c4d5eb}}
.flow-line{{position:absolute;left:330px;width:160px;height:3px;background:linear-gradient(90deg,#6fe0ff,rgba(111,224,255,.12));transform-origin:left}}.flow-one{{top:194px;transform:rotate(12deg)}}.flow-two{{top:313px}}.flow-three{{top:432px;transform:rotate(-12deg)}}
.score-engine{{position:absolute;left:490px;top:190px;width:290px;height:290px;border-radius:34px;border:1px solid rgba(111,224,255,.52);background:radial-gradient(circle at 50% 35%,rgba(76,124,255,.75),rgba(10,23,43,.94) 68%);display:grid;place-content:center;text-align:center;box-shadow:0 0 90px rgba(57,113,255,.34)}}.score-engine span{{font-size:17px;letter-spacing:.22em;color:#a8dfff}}.score-engine b{{font-size:64px;margin:14px 0 10px}}.score-engine i{{font-style:normal;font-size:16px;color:#a7bad5}}
.output-arrow{{position:absolute;left:780px;top:332px;width:145px;height:3px;background:linear-gradient(90deg,#6fe0ff,#9b7cff);transform-origin:left}}.output-arrow:after{{content:"";position:absolute;right:-2px;top:-8px;border-left:16px solid #9b7cff;border-top:9px solid transparent;border-bottom:9px solid transparent}}
.output-card{{position:absolute;right:28px;top:230px;width:250px;height:210px;border-radius:30px;border:1px solid rgba(164,126,255,.64);background:linear-gradient(145deg,rgba(101,73,205,.72),rgba(15,29,52,.94));display:grid;place-content:center;text-align:center;box-shadow:0 25px 70px rgba(0,0,0,.3)}}.output-card small{{font-size:14px;letter-spacing:.22em;color:#d6cfff}}.output-card b{{font-size:54px;margin:12px 0}}.output-card span{{font-size:24px;color:#9deaff}}
.phone-frame{{position:absolute;left:435px;top:90px;width:280px;height:570px;border:6px solid #273a5b;border-radius:52px;background:#07101d;padding:72px 24px 28px;box-shadow:0 38px 90px rgba(0,0,0,.38);overflow:hidden}}.phone-frame:before{{content:"";position:absolute;top:22px;left:92px;width:96px;height:18px;border-radius:999px;background:#1c2d49}}.phone-glow{{position:absolute;left:38px;top:115px;width:205px;height:205px;border-radius:50%;background:radial-gradient(circle,#80e9ff,#4d6fff 40%,transparent 72%);opacity:.55;filter:blur(3px)}}.screen-item{{position:relative;height:70px;border-radius:16px;background:linear-gradient(90deg,rgba(111,224,255,.28),rgba(93,112,255,.14));margin-bottom:18px}}.screen-item.short{{width:72%}}
.choice-path{{position:absolute;top:260px;width:290px;text-align:center}}.human-path{{left:65px}}.system-path{{right:30px}}.choice-path span{{display:block;font-size:24px;letter-spacing:.19em;font-weight:800}}.choice-path i{{display:block;font-style:normal;font-size:17px;color:#9fb3d0;margin-top:22px}}.path-line{{height:4px;margin-top:24px;background:linear-gradient(90deg,transparent,#6fe0ff,transparent);transform-origin:center}}.system-path .path-line{{background:linear-gradient(90deg,transparent,#a47cff,transparent)}}.choice-divider{{position:absolute;left:570px;top:118px;width:2px;height:510px;background:linear-gradient(transparent,rgba(160,190,255,.4),transparent);transform-origin:top}}
.origin-node,.next-node{{position:absolute;width:220px;height:150px;border-radius:30px;border:1px solid rgba(111,224,255,.54);background:linear-gradient(145deg,rgba(37,78,126,.92),rgba(9,20,38,.94));display:grid;place-content:center;text-align:center}}.origin-node{{left:70px;top:275px}}.next-node{{right:30px;top:275px;border-color:rgba(161,124,255,.6)}}.origin-node span,.next-node span{{font-size:14px;letter-spacing:.2em;color:#aadcf7}}.origin-node b,.next-node b{{font-size:34px;margin-top:10px}}
.outcome{{position:absolute;left:415px;width:330px;height:112px;border-radius:24px;border:1px solid rgba(128,176,255,.22);background:rgba(11,25,47,.9);display:flex;justify-content:space-between;align-items:center;padding:0 28px}}.outcome span{{font-size:15px;letter-spacing:.12em;color:#aec2dd}}.outcome b{{font-size:28px;color:#8be6ff}}.outcome-one{{top:125px}}.outcome-two{{top:285px}}.outcome-three{{top:445px}}
.branch{{position:absolute;left:285px;width:150px;height:3px;background:linear-gradient(90deg,#6fe0ff,rgba(111,224,255,.08));transform-origin:left}}.branch-one{{top:342px;transform:rotate(-36deg)}}.branch-two{{top:350px}}.branch-three{{top:358px;transform:rotate(36deg)}}.consequence-arrow{{position:absolute;left:745px;top:350px;width:180px;height:3px;background:linear-gradient(90deg,#6fe0ff,#a47cff);transform-origin:left}}.consequence-arrow:after{{content:"";position:absolute;right:-2px;top:-8px;border-left:16px solid #a47cff;border-top:9px solid transparent;border-bottom:9px solid transparent}}
</style>
</head>
<body>
<div id="stage" data-template="{html.escape(template_id)}" data-composition-id="{composition_id}" data-start="0" data-duration="{duration}" data-width="{width}" data-height="{height}">
  <div class="scene clip" data-start="0" data-duration="{duration}" data-track-index="0">
    <div class="scene-content">
      <div class="copy"><div class="kicker">{html.escape(kicker)}</div><h1>{html.escape(title)}</h1><div class="copy-rule"></div></div>
      {visual}
    </div>
  </div>
</div>
<script>
window.__compositionData={payload};
const tl=gsap.timeline({{paused:true}});
tl.from('.copy > *',{{opacity:0,y:30,duration:.68,stagger:.12,ease:'power3.out'}},.18);
{animation}
window.__timelines=window.__timelines||{{}};
window.__timelines['{composition_id}']=tl;
</script>
</body>
</html>'''


def _run_hyperframes(command: list[str], *, cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "CI": "1", "NO_COLOR": "1"},
        )
    except subprocess.CalledProcessError as exc:
        raise HyperFramesRenderError(
            "HyperFrames render failed",
            command=command,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise HyperFramesRenderError(
            f"HyperFrames render timed out after {timeout}s",
            command=command,
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "",
        ) from exc


def render_scene(scene, family_id: str, template_id: str, *, width: int = 1920, height: int = 1080) -> HyperFramesRender:
    ready, reason = available()
    if not ready:
        raise HyperFramesRenderError(reason)
    if not supports(family_id, template_id):
        raise HyperFramesRenderError(
            f"Unsupported HyperFrames route: family={family_id}, template={template_id}"
        )

    duration = max(1.0, float(scene.duration_seconds))
    project_dir = MEDIA_ROOT / f"project-{scene.project_id:04d}"
    work_dir = project_dir / "hyperframes" / f"scene-{scene.scene_number:03d}-{template_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    index_path = work_dir / "index.html"
    index_path.write_text(
        _composition_html(scene, template_id, duration, width, height), encoding="utf-8"
    )

    output_path = work_dir / "render.mp4"
    output_path.unlink(missing_ok=True)
    command = [
        "npx",
        "--yes",
        "hyperframes",
        "render",
        "--output",
        str(output_path),
    ]
    completed = _run_hyperframes(
        command,
        cwd=work_dir,
        timeout=max(180, int(duration * 60)),
    )
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise HyperFramesRenderError(
            "HyperFrames completed without producing the requested MP4",
            command=command,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    destination = project_dir / "assets" / f"scene-{scene.scene_number:03d}-hyperframes-{template_id}.mp4"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_path, destination)
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
        command=tuple(command),
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )
