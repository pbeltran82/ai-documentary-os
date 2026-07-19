from __future__ import annotations

"""Art Polish v62: source-level transport and habitat scene reconstruction.

This renderer removes decorative construction seams and treats moving doors as
real foreground masks. Characters are placed only in explicit safe zones, so a
door panel can never overlap or reveal a figure underneath it.
"""

import math

from PIL import Image, ImageDraw

from . import cartoon_documentary as cartoon
from . import cartoon_art_polish_v31 as v31
from . import cartoon_art_polish_v61 as v61


def _person(layer: Image.Image, x: int, y: int, scale: float, accent, pose: str = "stand") -> None:
    draw = ImageDraw.Draw(layer)
    cartoon._person(draw, x, y, scale, accent=accent, pose=pose)


def _transport(progress: float, variant: int) -> Image.Image:
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    image = Image.new("RGB", (width, height), (217, 235, 244))
    draw = ImageDraw.Draw(image)

    # Clean terminal shell: large silhouettes only, no full-height divider lines.
    draw.rounded_rectangle((90, 150, width - 90, height - 95), radius=58, fill=(181, 198, 210), outline=cartoon.INK, width=16)
    draw.rounded_rectangle((145, 205, width - 145, height - 155), radius=42, fill=(224, 234, 239), outline=(86, 101, 113), width=7)
    draw.rectangle((145, 765, width - 145, height - 155), fill=(107, 120, 132))
    draw.line((145, 765, width - 145, 765), fill=cartoon.INK, width=12)

    # Spacecraft nose and boarding ramp make the action unmistakable.
    draw.polygon(((1160, 275), (1685, 385), (1760, 540), (1685, 695), (1160, 805)), fill=(232, 239, 244), outline=cartoon.INK)
    draw.ellipse((1440, 430, 1610, 600), fill=cartoon.CYAN, outline=cartoon.INK, width=10)
    draw.polygon(((815, 770), (1165, 660), (1325, 770), (955, 865)), fill=(93, 106, 118), outline=cartoon.INK)

    # Door aperture is a reserved exclusion zone: x 760..1165, y 270..770.
    aperture = (760, 270, 1165, 770)
    draw.rounded_rectangle(aperture, radius=28, fill=(20, 32, 43), outline=cartoon.CYAN, width=9)

    # Characters are deliberately outside the aperture and moving-panel sweep.
    people = Image.new("RGBA", image.size, (0, 0, 0, 0))
    _person(people, 355, 655, 0.68, cartoon.AMBER, "carry")
    _person(people, 590, 690, 0.58, cartoon.BLUE, "stand")
    _person(people, 1395, 680, 0.62, cartoon.GREEN, "point")
    image.paste(people, (0, 0), people)

    # Two physical panels are composited last and therefore own occlusion.
    panels = Image.new("RGBA", image.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(panels)
    q = cartoon._ease(max(0.0, min(1.0, progress)))
    half_gap = round(24 + 165 * q)
    center = (aperture[0] + aperture[2]) // 2
    left_edge = center - half_gap
    right_edge = center + half_gap
    pd.rounded_rectangle((aperture[0] + 8, aperture[1] + 8, left_edge, aperture[3] - 8), radius=20, fill=(111, 128, 141), outline=cartoon.INK, width=8)
    pd.rounded_rectangle((right_edge, aperture[1] + 8, aperture[2] - 8, aperture[3] - 8), radius=20, fill=(111, 128, 141), outline=cartoon.INK, width=8)
    pd.rectangle((center - 8, aperture[1] + 35, center + 8, aperture[3] - 35), fill=cartoon.CYAN)
    image.paste(panels, (0, 0), panels)

    # A single operator console, placed away from the door sweep.
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1450, 660, 1695, 845), radius=24, fill=(35, 54, 67), outline=cartoon.GREEN, width=7)
    draw.ellipse((1515, 715, 1555, 755), fill=cartoon.GREEN)
    draw.ellipse((1590, 715, 1630, 755), fill=cartoon.AMBER)
    return image


def _habitat(progress: float, variant: int) -> Image.Image:
    width, height = cartoon.OUTPUT_WIDTH, cartoon.OUTPUT_HEIGHT
    image = Image.new("RGB", (width, height), (238, 218, 201))
    draw = ImageDraw.Draw(image)
    ground = 800
    draw.rectangle((0, ground, width, height), fill=(171, 91, 61))

    # One clean dome silhouette. No internal vertical supports or construction grid.
    dome_box = (260, 210, 1540, 955)
    draw.pieslice(dome_box, 180, 360, fill=(190, 224, 233), outline=cartoon.INK, width=17)
    draw.arc((330, 275, 1470, 900), 190, 350, fill=(121, 170, 189), width=5)
    draw.ellipse((430, 655, 690, 805), fill=(102, 157, 91), outline=cartoon.INK, width=8)
    draw.ellipse((735, 610, 1010, 805), fill=(92, 151, 85), outline=cartoon.INK, width=8)

    # Airlock module owns a rectangular mask independent from the dome artwork.
    module = (1260, 470, 1775, 900)
    draw.rounded_rectangle(module, radius=42, fill=(126, 145, 158), outline=cartoon.INK, width=15)
    aperture = (1385, 555, 1650, 870)
    draw.rounded_rectangle(aperture, radius=28, fill=(20, 32, 43), outline=cartoon.CYAN, width=8)

    # Operator and robot are outside the moving door region.
    people = Image.new("RGBA", image.size, (0, 0, 0, 0))
    _person(people, 1110, 690, 0.62, cartoon.AMBER, "point")
    pd = ImageDraw.Draw(people)
    pd.rounded_rectangle((930, 725, 1035, 815), radius=18, fill=cartoon.BLUE, outline=cartoon.INK, width=7)
    pd.ellipse((948, 804, 975, 831), fill=cartoon.INK)
    pd.ellipse((995, 804, 1022, 831), fill=cartoon.INK)
    image.paste(people, (0, 0), people)

    # Physical sliding airlock panels are always drawn last.
    panels = Image.new("RGBA", image.size, (0, 0, 0, 0))
    pd = ImageDraw.Draw(panels)
    q = cartoon._ease(max(0.0, min(1.0, progress)))
    center = (aperture[0] + aperture[2]) // 2
    half_gap = round(12 + 105 * q)
    pd.rounded_rectangle((aperture[0] + 7, aperture[1] + 7, center - half_gap, aperture[3] - 7), radius=18, fill=(96, 116, 130), outline=cartoon.INK, width=7)
    pd.rounded_rectangle((center + half_gap, aperture[1] + 7, aperture[2] - 7, aperture[3] - 7), radius=18, fill=(96, 116, 130), outline=cartoon.INK, width=7)
    image.paste(panels, (0, 0), panels)

    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((1635, 590, 1730, 745), radius=18, fill=(35, 54, 67), outline=cartoon.GREEN, width=6)
    draw.ellipse((1661, 620, 1704, 663), fill=cartoon.GREEN)
    draw.line((1682, 675, 1682, 716), fill=cartoon.AMBER, width=8)
    return image


def render_planned_frame(scene, template_id: str | None, duration_seconds: float, time_seconds: float, style_id: str | None = None) -> Image.Image:
    selected, progress, variant = v31._context(scene, template_id, duration_seconds, time_seconds)
    if selected.template_id == "transport_scene":
        return _transport(progress, variant)
    if selected.template_id == "habitat_build":
        return _habitat(progress, variant)
    return v61.render_planned_frame(scene, template_id, duration_seconds, time_seconds, style_id)


cartoon.render_planned_frame = render_planned_frame
