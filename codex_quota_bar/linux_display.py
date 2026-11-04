"""Linux preference storage and themeable vector quota icons."""

import json
import math
import os
from pathlib import Path
import tempfile
from xml.sax.saxutils import escape

from .track import outline
from .display import APPEARANCE, CONTROL_LABELS, WINDOWS, fraction
from .model import remaining_text


class Preferences:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else Path(
            os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
        ) / "codex-quota-bar/preferences.json"
        try:
            values = json.loads(self.path.read_text())
        except (OSError, ValueError):
            values = {}
        self.values = {key: value for key, value in values.items()
                       if self.valid(key, value)} if isinstance(values, dict) else {}

    @staticmethod
    def valid(key, value):
        return isinstance(value, str) and ((key in CONTROL_LABELS and value in WINDOWS)
                or (key == "interfaceLanguage" and value in ("system", "zh-Hans", "en"))
                or (key == "trackParts" and value in ("1", "2", "3"))
                or (key in APPEARANCE and value in APPEARANCE[key][1]))

    def get(self, key):
        return self.values.get(key)

    def set(self, key, choice):
        if not self.valid(key, choice):
            raise ValueError("Invalid display preference")
        values = dict(self.values, **{key: choice})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic replacement keeps both choices intact if a write fails.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                         prefix=".preferences-", delete=False) as file:
            temporary = Path(file.name)
            try:
                json.dump(values, file)
                file.flush()
                os.replace(temporary, self.path)
            finally:
                temporary.unlink(missing_ok=True)
        self.values = values


def status_svg(window, now, choice, render_text=None):
    """24px symbolic icon; host panel supplies its native foreground color."""
    value = fraction(window, now)
    gap = 54 if choice == "five_hour" else 68
    start = 90 + gap / 2
    arc = 360 - gap

    def point(angle, radius):
        radians = math.radians(angle)
        return f"{12 + radius * math.cos(radians):.3f},{12 + radius * math.sin(radians):.3f}"

    def path(angle, sweep, opacity):
        # GTK's symbolic loader overrides fill/stroke styles. Use an actual
        # filled outline with round caps, keeping the center transparent.
        outer, inner, cap = 11.9, 9.5, 1.2
        end = angle + sweep
        large = int(sweep > 180)
        return (f'<path d="M{point(angle, outer)} A{outer},{outer} 0 {large},1 {point(end, outer)} '
                f'A{cap},{cap} 0 0,1 {point(end, inner)} '
                f'A{inner},{inner} 0 {large},0 {point(angle, inner)} '
                f'A{cap},{cap} 0 0,1 {point(angle, outer)} Z" opacity="{opacity}"/>')

    if value is None:
        step = math.degrees(4 / 10.7)
        dash = math.degrees(1 / 10.7)
        shapes = '<g data-unknown="true">' + ''.join(
            path(start + offset, min(dash, arc - offset), 0.28)
            for offset in (index * step for index in range(math.ceil(arc / step)))
        ) + '</g>'
    else:
        shapes = path(start, arc, 0.28)
        if value > 0:
            shapes += path(start, arc * value, 1)
    text = remaining_text(window, now).removesuffix("%") if value is not None else "--"
    size = 9 if len(text) > 2 else 10.5
    marker = "H" if choice == "five_hour" else "W"
    def label(value, baseline, font_size):
        if render_text is not None:
            return render_text(value, 12, baseline, font_size)
        return f'<text x="12" y="{baseline}" font-size="{font_size}">{value}</text>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
            f'<title>{marker} {text}</title>'
            f'{shapes}<g fill="black" font-family="sans-serif" font-weight="bold" text-anchor="middle">'
            f'{label(text, 14, size)}{label(marker, 23.6, size)}</g></svg>')

def track_svg(reading, value, width, baseline=16):
    """Full-color wide image for GNOME's custom-image path (not symbolic).

    That path preserves width but does not apply the panel's symbolic tint.
    Use the stock Ubuntu dark panel's light foreground explicitly.
    """
    shapes = []
    for part, alpha in ((1, 0.28), (value or 0, 1)):
        points = outline(width, part)
        if points:
            coords = " ".join(f"{x:.2f},{y:.2f}" for x,y in points)
            shapes.append(f'<polygon points="{coords}" opacity="{alpha}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="24" viewBox="0 0 {width} 24">'
            f'<title>{escape(reading)}</title><g fill="#eeeeec">' + "".join(shapes)
            + f'<text x="{width / 2}" y="{baseline}" font-family="sans-serif" '
              f'font-size="11" font-weight="bold" text-anchor="middle">{escape(reading)}</text>'
            + '</g></svg>')
