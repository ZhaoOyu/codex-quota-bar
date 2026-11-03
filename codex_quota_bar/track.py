"""Filled stadium outlines shared by AppKit and symbolic GTK icons (y down)."""
import math


def outline(width, portion):
    """Return the ribbon polygon; sample by arc length from the upper left tangent."""
    if portion <= 0:
        return []
    radius, cy, half_stroke = 9, 12, 1
    left, right = 11, width - 11
    straight, arc = right - left, math.pi * radius
    segments = [arc, straight, arc, straight]
    left_to_draw = min(1, portion) * sum(segments)
    outer, inner = [], []
    for segment, length in enumerate(segments):
        take = min(left_to_draw, length)
        steps = max(1, math.ceil(take / 1.2)) if segment in (0, 2) else 1
        for i in range(steps + 1):
            d = take * i / steps
            if segment in (0, 2):
                theta = (-math.pi / 2 if segment == 0 else math.pi / 2) - d / radius
                nx, ny = math.cos(theta), math.sin(theta)
                x, y = (left if segment == 0 else right) + radius * nx, cy + radius * ny
            else:
                x, y, nx, ny = ((left + d, cy + radius, 0, 1) if segment == 1
                                else (right - d, cy - radius, 0, -1))
            outer.append((x + nx * half_stroke, y + ny * half_stroke))
            inner.append((x - nx * half_stroke, y - ny * half_stroke))
        left_to_draw -= take
        if left_to_draw <= 0:
            break
    return outer + inner[::-1]
