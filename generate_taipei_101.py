#!/usr/bin/env python3
"""
Taipei 101 Procedural 3D Model Generator
Generates high-detail Taipei 101 architectural 3D models in GLB, OBJ/MTL, and STL formats.
Coordinate system: Y-up (glTF standard), 1 unit = 1 meter, total height = 508.2 m.
"""

import base64
import json
import math
import os
import struct
from typing import Dict, List, Tuple

Vec3 = Tuple[float, float, float]
Tri = Tuple[int, int, int]


def v_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def v_norm(v: Vec3) -> Vec3:
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length < 1e-12:
        return (0.0, 1.0, 0.0)
    return (v[0] / length, v[1] / length, v[2] / length)


class MeshGroup:
    """Stores flat-shaded or smooth-shaded triangles for a single material."""

    def __init__(self, name: str, material: str):
        self.name = name
        self.material = material
        self.positions: List[Vec3] = []
        self.normals: List[Vec3] = []
        self.indices: List[int] = []

    def add_tri(self, p0: Vec3, p1: Vec3, p2: Vec3, normal: Vec3 = None) -> None:
        if normal is None:
            n = v_norm(v_cross(v_sub(p1, p0), v_sub(p2, p0)))
        else:
            n = v_norm(normal)
        base = len(self.positions)
        self.positions.extend([p0, p1, p2])
        self.normals.extend([n, n, n])
        self.indices.extend([base, base + 1, base + 2])

    def add_quad(self, p0: Vec3, p1: Vec3, p2: Vec3, p3: Vec3) -> None:
        n = v_norm(v_cross(v_sub(p1, p0), v_sub(p2, p0)))
        self.add_tri(p0, p1, p2, n)
        self.add_tri(p0, p2, p3, n)

    def add_box(
        self,
        cx: float,
        cy: float,
        cz: float,
        sx: float,
        sy: float,
        sz: float,
        rot_y: float = 0.0,
    ) -> None:
        hx, hy, hz = sx * 0.5, sy * 0.5, sz * 0.5
        local_pts = [
            (-hx, -hy, -hz),
            (hx, -hy, -hz),
            (hx, -hy, hz),
            (-hx, -hy, hz),
            (-hx, hy, -hz),
            (hx, hy, -hz),
            (hx, hy, hz),
            (-hx, hy, hz),
        ]
        cos_r = math.cos(rot_y)
        sin_r = math.sin(rot_y)
        pts = []
        for x, y, z in local_pts:
            rx = x * cos_r - z * sin_r + cx
            rz = x * sin_r + z * cos_r + cz
            pts.append((rx, y + cy, rz))

        # Counter-clockwise outward faces
        faces = [
            (0, 1, 2, 3),  # bottom (-Y)
            (4, 7, 6, 5),  # top (+Y)
            (3, 2, 6, 7),  # front (+Z)
            (1, 0, 4, 5),  # back (-Z)
            (2, 1, 5, 6),  # right (+X)
            (0, 3, 7, 4),  # left (-X)
        ]
        for a, b, c, d in faces:
            self.add_quad(pts[a], pts[b], pts[c], pts[d])

    def add_loft(
        self,
        ring_bottom: List[Tuple[float, float]],
        y_bottom: float,
        ring_top: List[Tuple[float, float]],
        y_top: float,
        cap_bottom: bool = True,
        cap_top: bool = True,
    ) -> None:
        """
        Loft between two 2D CCW rings (in XZ plane, looking from +Y down means
        (x, z) ordered so that outward normal points away from origin).
        Note: In Y-up right-handed coords, CCW around +Y goes (+X -> -Z -> -X -> +Z),
        which means angle increases in (cos(a), -sin(a)).
        """
        n = len(ring_bottom)
        assert n == len(ring_top)

        for i in range(n):
            j = (i + 1) % n
            b0 = (ring_bottom[i][0], y_bottom, ring_bottom[i][1])
            b1 = (ring_bottom[j][0], y_bottom, ring_bottom[j][1])
            t1 = (ring_top[j][0], y_top, ring_top[j][1])
            t0 = (ring_top[i][0], y_top, ring_top[i][1])
            self.add_quad(b0, b1, t1, t0)

        if cap_bottom:
            center_b = (0.0, y_bottom, 0.0)
            for i in range(n):
                j = (i + 1) % n
                b0 = (ring_bottom[i][0], y_bottom, ring_bottom[i][1])
                b1 = (ring_bottom[j][0], y_bottom, ring_bottom[j][1])
                self.add_tri(center_b, b1, b0, (0.0, -1.0, 0.0))

        if cap_top:
            center_t = (0.0, y_top, 0.0)
            for i in range(n):
                j = (i + 1) % n
                t0 = (ring_top[i][0], y_top, ring_top[i][1])
                t1 = (ring_top[j][0], y_top, ring_top[j][1])
                self.add_tri(center_t, t0, t1, (0.0, 1.0, 0.0))

    def add_cylinder(
        self,
        cx: float,
        cz: float,
        y0: float,
        y1: float,
        r0: float,
        r1: float,
        segments: int = 16,
        cap_bottom: bool = True,
        cap_top: bool = True,
    ) -> None:
        ring0 = []
        ring1 = []
        for i in range(segments):
            ang = 2.0 * math.pi * i / segments
            dx = math.cos(ang)
            dz = -math.sin(ang)
            ring0.append((cx + dx * r0, cz + dz * r0))
            ring1.append((cx + dx * r1, cz + dz * r1))

        n = segments
        for i in range(n):
            j = (i + 1) % n
            b0 = (ring0[i][0], y0, ring0[i][1])
            b1 = (ring0[j][0], y0, ring0[j][1])
            t1 = (ring1[j][0], y1, ring1[j][1])
            t0 = (ring1[i][0], y1, ring1[i][1])
            self.add_quad(b0, b1, t1, t0)

        if cap_bottom and r0 > 1e-6:
            cb = (cx, y0, cz)
            for i in range(n):
                j = (i + 1) % n
                self.add_tri(
                    cb,
                    (ring0[j][0], y0, ring0[j][1]),
                    (ring0[i][0], y0, ring0[i][1]),
                    (0.0, -1.0, 0.0),
                )

        if cap_top and r1 > 1e-6:
            ct = (cx, y1, cz)
            for i in range(n):
                j = (i + 1) % n
                self.add_tri(
                    ct,
                    (ring1[i][0], y1, ring1[i][1]),
                    (ring1[j][0], y1, ring1[j][1]),
                    (0.0, 1.0, 0.0),
                )

    def add_sphere(
        self, cx: float, cy: float, cz: float, radius: float, stacks: int = 8, slices: int = 12
    ) -> None:
        for i in range(stacks):
            phi0 = math.pi * (-0.5 + i / stacks)
            phi1 = math.pi * (-0.5 + (i + 1) / stacks)
            y0 = cy + radius * math.sin(phi0)
            y1 = cy + radius * math.sin(phi1)
            r0 = radius * math.cos(phi0)
            r1 = radius * math.cos(phi1)
            for j in range(slices):
                th0 = 2.0 * math.pi * j / slices
                th1 = 2.0 * math.pi * (j + 1) / slices
                p00 = (cx + r0 * math.cos(th0), y0, cz - r0 * math.sin(th0))
                p10 = (cx + r0 * math.cos(th1), y0, cz - r0 * math.sin(th1))
                p11 = (cx + r1 * math.cos(th1), y1, cz - r1 * math.sin(th1))
                p01 = (cx + r1 * math.cos(th0), y1, cz - r1 * math.sin(th0))
                if i == 0:
                    self.add_tri(p00, p11, p01)
                elif i == stacks - 1:
                    self.add_tri(p00, p10, p01)
                else:
                    self.add_quad(p00, p10, p11, p01)

    def add_disc_face(
        self,
        center: Vec3,
        axis: str,
        sign: float,
        r_outer: float,
        r_inner: float,
        thickness: float,
        segments: int = 24,
    ) -> None:
        """
        Adds a circular ancient-coin (square-hole or ring) medallion mounted on a facade.
        axis: 'x' or 'z', sign: +1 or -1.
        """
        cx, cy, cz = center
        half_t = thickness * 0.5
        # Build ring with square inner hole (traditional Chinese coin)
        s_in = r_inner * 0.75
        outer_pts = []
        inner_pts = []
        for i in range(segments):
            ang = 2.0 * math.pi * i / segments
            u = math.cos(ang) * r_outer
            v = math.sin(ang) * r_outer
            outer_pts.append((u, v))
            # Project onto square of half-size s_in
            m = max(abs(math.cos(ang)), abs(math.sin(ang)))
            iu = (math.cos(ang) / m) * s_in
            iv = (math.sin(ang) / m) * s_in
            inner_pts.append((iu, iv))

        def to_3d(u: float, v: float, depth: float) -> Vec3:
            if axis == "z":
                return (cx + u * sign, cy + v, cz + depth * sign)
            else:
                return (cx + depth * sign, cy + v, cz - u * sign)

        for i in range(segments):
            j = (i + 1) % segments
            o0_f = to_3d(outer_pts[i][0], outer_pts[i][1], half_t)
            o1_f = to_3d(outer_pts[j][0], outer_pts[j][1], half_t)
            i1_f = to_3d(inner_pts[j][0], inner_pts[j][1], half_t)
            i0_f = to_3d(inner_pts[i][0], inner_pts[i][1], half_t)

            o0_b = to_3d(outer_pts[i][0], outer_pts[i][1], -half_t)
            o1_b = to_3d(outer_pts[j][0], outer_pts[j][1], -half_t)
            i1_b = to_3d(inner_pts[j][0], inner_pts[j][1], -half_t)
            i0_b = to_3d(inner_pts[i][0], inner_pts[i][1], -half_t)

            # Front face
            self.add_quad(i0_f, o0_f, o1_f, i1_f)
            # Back face
            self.add_quad(o0_b, i0_b, i1_b, o1_b)
            # Outer rim
            self.add_quad(o0_b, o1_b, o1_f, o0_f)
            # Inner square rim
            self.add_quad(i1_b, i0_b, i0_f, i1_f)


def taipei101_section_ring(half_w: float, notch: float = None) -> List[Tuple[float, float]]:
    """
    Generates the signature 20-vertex sawtooth / double-stepped corner cross-section
    of Taipei 101 in CCW order when viewed from +Y (using (x, z) with +X right, -Z up).
    Each corner has a W-shaped double setback notch.
    """
    h = half_w
    n1 = half_w * 0.14 if notch is None else notch
    n2 = n1 * 0.55

    # Define points in first quadrant (+X, -Z) and mirror/rotate 4 times in CCW order
    # Going around CCW around +Y: (+X, +Z) -> (+X, -Z) -> (-X, -Z) -> (-X, +Z)
    # Corner template for (+X, +Z) to (+X, -Z) side, then corner at (+X, -Z):
    pts: List[Tuple[float, float]] = []

    def rot90_ccw_y(x: float, z: float, k: int) -> Tuple[float, float]:
        # Rotation by +90 deg around +Y maps (x, z) -> (z, -x)
        for _ in range(k):
            x, z = z, -x
        return (x, z)

    # One side (+X face) from near +Z corner to near -Z corner, plus the (+X, -Z) sawtooth corner
    base_quadrant = [
        (h, h - n1),
        (h, -(h - n1)),
        (h - n2, -(h - n1)),
        (h - n2, -(h - n2)),
        (h - n1, -(h - n2)),
    ]

    for k in range(4):
        for x, z in base_quadrant:
            pts.append(rot90_ccw_y(x, z, k))

    return pts


def regular_polygon_ring(radius: float, sides: int, phase: float = 0.0) -> List[Tuple[float, float]]:
    ring = []
    for i in range(sides):
        ang = phase + 2.0 * math.pi * i / sides
        ring.append((radius * math.cos(ang), -radius * math.sin(ang)))
    return ring


def build_taipei_101() -> Tuple[Dict[str, MeshGroup], Dict[str, dict]]:
    """Constructs the full Taipei 101 architectural model."""

    materials = {
        "glass_curtain": {
            "baseColorFactor": [0.16, 0.36, 0.40, 1.0],
            "metallicFactor": 0.35,
            "roughnessFactor": 0.18,
            "emissiveFactor": [0.01, 0.03, 0.04],
        },
        "aluminum_frame": {
            "baseColorFactor": [0.28, 0.34, 0.36, 1.0],
            "metallicFactor": 0.72,
            "roughnessFactor": 0.35,
            "emissiveFactor": [0.0, 0.0, 0.0],
        },
        "mega_column": {
            "baseColorFactor": [0.58, 0.64, 0.66, 1.0],
            "metallicFactor": 0.65,
            "roughnessFactor": 0.30,
            "emissiveFactor": [0.0, 0.0, 0.0],
        },
        "ruyi_ornament": {
            "baseColorFactor": [0.66, 0.62, 0.48, 1.0],
            "metallicFactor": 0.75,
            "roughnessFactor": 0.28,
            "emissiveFactor": [0.02, 0.02, 0.01],
        },
        "podium_stone": {
            "baseColorFactor": [0.48, 0.49, 0.47, 1.0],
            "metallicFactor": 0.05,
            "roughnessFactor": 0.78,
            "emissiveFactor": [0.0, 0.0, 0.0],
        },
        "spire_metal": {
            "baseColorFactor": [0.76, 0.80, 0.82, 1.0],
            "metallicFactor": 0.88,
            "roughnessFactor": 0.22,
            "emissiveFactor": [0.0, 0.0, 0.0],
        },
        "beacon_red": {
            "baseColorFactor": [0.95, 0.12, 0.10, 1.0],
            "metallicFactor": 0.10,
            "roughnessFactor": 0.25,
            "emissiveFactor": [0.85, 0.08, 0.05],
        },
    }

    groups: Dict[str, MeshGroup] = {
        k: MeshGroup(name=k, material=k) for k in materials.keys()
    }

    glass = groups["glass_curtain"]
    frame = groups["aluminum_frame"]
    column = groups["mega_column"]
    ornament = groups["ruyi_ornament"]
    stone = groups["podium_stone"]
    spire = groups["spire_metal"]
    beacon = groups["beacon_red"]

    # -------------------------------------------------------------------------
    # 1. Plaza Base & Mall Podium (0 m -> 113 m)
    # -------------------------------------------------------------------------
    # Stepped granite plaza foundation
    stone.add_box(0.0, 1.0, 0.0, 96.0, 2.0, 96.0)
    stone.add_box(0.0, 3.0, 0.0, 82.0, 2.0, 82.0)

    # Adjacent Taipei 101 Mall podium wing (east/south-side low-rise massing)
    stone.add_box(42.0, 16.0, 0.0, 34.0, 24.0, 56.0)
    glass.add_box(42.0, 17.5, 0.0, 34.8, 17.0, 50.0)
    frame.add_box(42.0, 28.5, 0.0, 36.0, 1.5, 58.0)

    # Entrance glass canopies on the 4 faces of the tower base
    for rot in (0.0, math.pi * 0.5, math.pi, math.pi * 1.5):
        cos_r, sin_r = math.cos(rot), math.sin(rot)
        cx, cz = 31.5 * sin_r, 31.5 * cos_r
        frame.add_box(cx, 12.0, cz, 22.0, 1.2, 8.0, rot_y=rot)
        glass.add_box(cx, 12.7, cz, 20.5, 0.4, 7.2, rot_y=rot)

    # Main tapered base pedestal (1F-25F: y = 4 m -> 113 m)
    # Tapers inward from half_w = 29.0 m at bottom to 21.8 m at top
    base_y0 = 4.0
    base_y1 = 113.0
    base_hw0 = 29.0
    base_hw1 = 21.8

    ring_b0 = taipei101_section_ring(base_hw0)
    ring_b1 = taipei101_section_ring(base_hw1)
    glass.add_loft(ring_b0, base_y0, ring_b1, base_y1, cap_bottom=True, cap_top=True)

    # Base horizontal spandrel bands (25 floors)
    base_floors = 22
    for f in range(1, base_floors + 1):
        t = f / base_floors
        y = base_y0 + (base_y1 - base_y0) * t
        hw = base_hw0 + (base_hw1 - base_hw0) * t + 0.28
        r_lo = taipei101_section_ring(hw)
        r_hi = taipei101_section_ring(hw - 0.04)
        frame.add_loft(r_lo, y - 0.42, r_hi, y + 0.42, cap_bottom=True, cap_top=True)

    # Slanted corner buttress ribs & mega-columns on the base
    for side in range(4):
        rot = side * math.pi * 0.5
        cos_r, sin_r = math.cos(rot), math.sin(rot)
        for offset in (-8.2, 8.2):
            # Build slanted mega-column following base taper
            segs = 6
            for s in range(segs):
                t0 = s / segs
                t1 = (s + 1) / segs
                y_a = base_y0 + (base_y1 - base_y0) * t0
                y_b = base_y0 + (base_y1 - base_y0) * t1
                hw_a = base_hw0 + (base_hw1 - base_hw0) * t0 + 0.55
                hw_b = base_hw0 + (base_hw1 - base_hw0) * t1 + 0.55
                ym = 0.5 * (y_a + y_b)
                hwm = 0.5 * (hw_a + hw_b)
                px = offset * cos_r + hwm * sin_r
                pz = -offset * sin_r + hwm * cos_r
                column.add_box(px, ym, pz, 2.5, (y_b - y_a) + 0.4, 1.8, rot_y=rot)

    # Transition cornice cap at 25F/26F (y = 113 m)
    cap_r0 = taipei101_section_ring(22.8)
    cap_r1 = taipei101_section_ring(23.5)
    frame.add_loft(cap_r0, 112.0, cap_r1, 114.6, cap_bottom=True, cap_top=True)

    # Four giant traditional Chinese coin medallions at base crown (26F)
    coin_y = 109.5
    coin_r_out = 5.4
    coin_r_in = 2.0
    coin_z = base_hw1 + 1.0
    ornament.add_disc_face((0.0, coin_y, coin_z), "z", 1.0, coin_r_out, coin_r_in, 1.3)
    ornament.add_disc_face((0.0, coin_y, -coin_z), "z", -1.0, coin_r_out, coin_r_in, 1.3)
    ornament.add_disc_face((coin_z, coin_y, 0.0), "x", 1.0, coin_r_out, coin_r_in, 1.3)
    ornament.add_disc_face((-coin_z, coin_y, 0.0), "x", -1.0, coin_r_out, coin_r_in, 1.3)

    # -------------------------------------------------------------------------
    # 2. Eight Stacked Pagoda / Bamboo Modules (26F -> 90F, y = 113 m -> 385 m)
    # -------------------------------------------------------------------------
    num_modules = 8
    module_h = 34.0
    start_y = 113.0
    hw_bot = 18.2   # 36.4 m width at bottom of each module
    hw_top = 22.6   # 45.2 m width at top of each module (outward ~7.4 deg flare)

    for m in range(num_modules):
        y0 = start_y + m * module_h
        y1 = y0 + module_h

        # Main flared curtain-wall body
        r_bot = taipei101_section_ring(hw_bot)
        r_top = taipei101_section_ring(hw_top)
        glass.add_loft(r_bot, y0, r_top, y1, cap_bottom=True, cap_top=True)

        # 8 floor spandrel aluminum bands per module
        floors_per_mod = 8
        for f in range(1, floors_per_mod + 1):
            t = f / floors_per_mod
            fy = y0 + module_h * t
            fhw = hw_bot + (hw_top - hw_bot) * t + 0.25
            band_h = 0.72 if f == floors_per_mod else 0.36
            rb = taipei101_section_ring(fhw - 0.05)
            rt = taipei101_section_ring(fhw + 0.05)
            frame.add_loft(rb, fy - band_h, rt, fy + band_h, cap_bottom=True, cap_top=True)

        # Vertical mega-columns (2 per facade, flaring outward with the module)
        for side in range(4):
            rot = side * math.pi * 0.5
            cos_r, sin_r = math.cos(rot), math.sin(rot)
            for offset in (-6.8, 6.8):
                segs = 4
                for s in range(segs):
                    t0 = s / segs
                    t1 = (s + 1) / segs
                    ya = y0 + module_h * t0
                    yb = y0 + module_h * t1
                    hwa = hw_bot + (hw_top - hw_bot) * t0 + 0.45
                    hwb = hw_bot + (hw_top - hw_bot) * t1 + 0.45
                    ym = 0.5 * (ya + yb)
                    hwm = 0.5 * (hwa + hwb)
                    px = offset * cos_r + hwm * sin_r
                    pz = -offset * sin_r + hwm * cos_r
                    column.add_box(px, ym, pz, 2.2, (yb - ya) + 0.35, 1.5, rot_y=rot)

            # Central vertical mullion spine on each face
            segs = 4
            for s in range(segs):
                t0 = s / segs
                t1 = (s + 1) / segs
                ya = y0 + module_h * t0
                yb = y0 + module_h * t1
                hwm = hw_bot + (hw_top - hw_bot) * 0.5 * (t0 + t1) + 0.30
                ym = 0.5 * (ya + yb)
                px = hwm * sin_r
                pz = hwm * cos_r
                frame.add_box(px, ym, pz, 0.9, (yb - ya) + 0.2, 0.8, rot_y=rot)

        # Top eave lip & setback terrace parapet
        parapet_r0 = taipei101_section_ring(hw_top + 0.4)
        parapet_r1 = taipei101_section_ring(hw_top + 0.85)
        frame.add_loft(parapet_r0, y1 - 0.8, parapet_r1, y1 + 1.1, cap_bottom=True, cap_top=True)

        # Ruyi (cloud scroll) architectural ornaments at the 4 corners & facade centers
        ruyi_y = y1 + 1.6
        for corner in range(4):
            ang = math.pi * 0.25 + corner * math.pi * 0.5
            dist = (hw_top + 0.3) * 1.28
            rx = dist * math.cos(ang)
            rz = -dist * math.sin(ang)
            ornament.add_box(rx, ruyi_y, rz, 3.8, 3.6, 3.8, rot_y=ang)
            ornament.add_box(rx * 1.04, ruyi_y + 1.8, rz * 1.04, 2.4, 1.8, 2.4, rot_y=ang)

        # Center Ruyi scroll bracket on each facade
        for side in range(4):
            rot = side * math.pi * 0.5
            cos_r, sin_r = math.cos(rot), math.sin(rot)
            px = (hw_top + 0.9) * sin_r
            pz = (hw_top + 0.9) * cos_r
            ornament.add_box(px, y1 + 1.4, pz, 6.2, 2.8, 1.8, rot_y=rot)
            ornament.add_box(px, y1 + 3.2, pz, 3.4, 1.6, 1.4, rot_y=rot)

    # -------------------------------------------------------------------------
    # 3. Observatory & Crown Tiers (91F -> 101F, y = 385 m -> 448 m)
    # -------------------------------------------------------------------------
    # Tier 1: 91F Outdoor Observatory Deck & recessed core (385 -> 397 m)
    crown_tiers = [
        (385.0, 397.0, 16.0, 16.8),
        (397.0, 415.0, 13.8, 15.2),
        (415.0, 433.0, 10.6, 11.8),
        (433.0, 448.0, 7.6, 8.6),
    ]
    for y0, y1, w0, w1 in crown_tiers:
        r0 = taipei101_section_ring(w0)
        r1 = taipei101_section_ring(w1)
        glass.add_loft(r0, y0, r1, y1, cap_bottom=True, cap_top=True)

        # Horizontal crown framing rings
        for k in range(1, 4):
            t = k / 3.0
            fy = y0 + (y1 - y0) * t
            fw = w0 + (w1 - w0) * t + 0.28
            rb = taipei101_section_ring(fw)
            rt = taipei101_section_ring(fw + 0.08)
            frame.add_loft(rb, fy - 0.45, rt, fy + 0.45, cap_bottom=True, cap_top=True)

        # Corner fins on crown tiers
        for corner in range(4):
            ang = math.pi * 0.25 + corner * math.pi * 0.5
            dist = w1 * 1.24
            column.add_box(
                dist * math.cos(ang),
                0.5 * (y0 + y1),
                -dist * math.sin(ang),
                1.8,
                (y1 - y0) + 1.0,
                1.8,
                rot_y=ang,
            )

    # Crown top mechanical pedestal
    oct_base = regular_polygon_ring(6.8, 8, phase=math.pi / 8.0)
    oct_top = regular_polygon_ring(4.8, 8, phase=math.pi / 8.0)
    spire.add_loft(oct_base, 448.0, oct_top, 456.0, cap_bottom=True, cap_top=True)

    # -------------------------------------------------------------------------
    # 4. Pinnacle Spire (456 m -> 508.2 m)
    # -------------------------------------------------------------------------
    # Lower octagonal tapered spire section
    spire.add_cylinder(0.0, 0.0, 456.0, 474.0, 3.6, 2.0, segments=8)
    # Mid structural collar rings
    for ry, rad in [(462.0, 4.1), (470.0, 3.0), (478.0, 2.2), (488.0, 1.5), (498.0, 1.0)]:
        spire.add_cylinder(0.0, 0.0, ry - 0.45, ry + 0.45, rad, rad, segments=12)
    # Upper tapered mast
    spire.add_cylinder(0.0, 0.0, 474.0, 507.2, 1.8, 0.28, segments=12)

    # Aviation warning beacon at exact 508.2 m tip
    beacon.add_sphere(0.0, 507.7, 0.0, 0.55, stacks=8, slices=12)

    return groups, materials


def export_glb(path: str, groups: Dict[str, MeshGroup], materials: Dict[str, dict]) -> None:
    """Exports the model as a valid glTF 2.0 binary (.glb) file."""
    mat_names = list(materials.keys())
    mat_index_map = {name: idx for idx, name in enumerate(mat_names)}

    gltf_materials = []
    for name in mat_names:
        m = materials[name]
        gltf_materials.append(
            {
                "name": name,
                "pbrMetallicRoughness": {
                    "baseColorFactor": m["baseColorFactor"],
                    "metallicFactor": m["metallicFactor"],
                    "roughnessFactor": m["roughnessFactor"],
                },
                "emissiveFactor": m["emissiveFactor"],
            }
        )

    bin_chunks = bytearray()
    buffer_views = []
    accessors = []
    primitives = []

    def pad4(buf: bytearray) -> None:
        while len(buf) % 4 != 0:
            buf.append(0)

    for g in groups.values():
        if not g.indices:
            continue

        # Positions
        pad4(bin_chunks)
        pos_offset = len(bin_chunks)
        min_p = [float("inf")] * 3
        max_p = [float("-inf")] * 3
        for x, y, z in g.positions:
            min_p[0] = min(min_p[0], x)
            min_p[1] = min(min_p[1], y)
            min_p[2] = min(min_p[2], z)
            max_p[0] = max(max_p[0], x)
            max_p[1] = max(max_p[1], y)
            max_p[2] = max(max_p[2], z)
            bin_chunks.extend(struct.pack("<fff", x, y, z))
        pos_len = len(bin_chunks) - pos_offset

        pos_bv = len(buffer_views)
        buffer_views.append(
            {"buffer": 0, "byteOffset": pos_offset, "byteLength": pos_len, "target": 34962}
        )
        pos_acc = len(accessors)
        accessors.append(
            {
                "bufferView": pos_bv,
                "componentType": 5126,  # FLOAT
                "count": len(g.positions),
                "type": "VEC3",
                "min": min_p,
                "max": max_p,
            }
        )

        # Normals
        pad4(bin_chunks)
        norm_offset = len(bin_chunks)
        for nx, ny, nz in g.normals:
            bin_chunks.extend(struct.pack("<fff", nx, ny, nz))
        norm_len = len(bin_chunks) - norm_offset

        norm_bv = len(buffer_views)
        buffer_views.append(
            {"buffer": 0, "byteOffset": norm_offset, "byteLength": norm_len, "target": 34962}
        )
        norm_acc = len(accessors)
        accessors.append(
            {
                "bufferView": norm_bv,
                "componentType": 5126,  # FLOAT
                "count": len(g.normals),
                "type": "VEC3",
            }
        )

        # Indices (UNSIGNED_INT = 5125)
        pad4(bin_chunks)
        idx_offset = len(bin_chunks)
        for idx in g.indices:
            bin_chunks.extend(struct.pack("<I", idx))
        idx_len = len(bin_chunks) - idx_offset

        idx_bv = len(buffer_views)
        buffer_views.append(
            {"buffer": 0, "byteOffset": idx_offset, "byteLength": idx_len, "target": 34963}
        )
        idx_acc = len(accessors)
        accessors.append(
            {
                "bufferView": idx_bv,
                "componentType": 5125,  # UNSIGNED_INT
                "count": len(g.indices),
                "type": "SCALAR",
            }
        )

        primitives.append(
            {
                "attributes": {"POSITION": pos_acc, "NORMAL": norm_acc},
                "indices": idx_acc,
                "material": mat_index_map[g.material],
            }
        )

    pad4(bin_chunks)

    gltf = {
        "asset": {"version": "2.0", "generator": "Taipei101 Procedural Generator"},
        "scene": 0,
        "scenes": [{"name": "Taipei101Scene", "nodes": [0]}],
        "nodes": [{"name": "Taipei_101", "mesh": 0}],
        "meshes": [{"name": "Taipei_101_Mesh", "primitives": primitives}],
        "materials": gltf_materials,
        "buffers": [{"byteLength": len(bin_chunks)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_length = 12 + 8 + len(json_bytes) + 8 + len(bin_chunks)

    with open(path, "wb") as f:
        # GLB Header: magic, version, length
        f.write(struct.pack("<4sII", b"glTF", 2, total_length))
        # JSON chunk
        f.write(struct.pack("<I4s", len(json_bytes), b"JSON"))
        f.write(json_bytes)
        # BIN chunk
        f.write(struct.pack("<I4s", len(bin_chunks), b"BIN\x00"))
        f.write(bin_chunks)


def export_obj_mtl(
    obj_path: str, mtl_path: str, groups: Dict[str, MeshGroup], materials: Dict[str, dict]
) -> None:
    mtl_filename = os.path.basename(mtl_path)

    with open(mtl_path, "w", encoding="utf-8") as mf:
        mf.write("# Taipei 101 Material Library\n\n")
        for name, m in materials.items():
            r, g, b, _ = m["baseColorFactor"]
            er, eg, eb = m["emissiveFactor"]
            rough = m["roughnessFactor"]
            metal = m["metallicFactor"]
            ns = max(10.0, (1.0 - rough) * 200.0)
            mf.write(f"newmtl {name}\n")
            mf.write(f"Ka {r * 0.25:.4f} {g * 0.25:.4f} {b * 0.25:.4f}\n")
            mf.write(f"Kd {r:.4f} {g:.4f} {b:.4f}\n")
            mf.write(f"Ks {0.3 + metal * 0.6:.4f} {0.3 + metal * 0.6:.4f} {0.3 + metal * 0.6:.4f}\n")
            mf.write(f"Ke {er:.4f} {eg:.4f} {eb:.4f}\n")
            mf.write(f"Ns {ns:.2f}\n")
            mf.write("d 1.0\nillum 2\n\n")

    with open(obj_path, "w", encoding="utf-8") as of:
        of.write("# Taipei 101 3D Model (1 unit = 1 meter, Y-up)\n")
        of.write(f"mtllib {mtl_filename}\n\n")
        v_offset = 1
        for g in groups.values():
            if not g.indices:
                continue
            of.write(f"g {g.name}\n")
            of.write(f"usemtl {g.material}\n")
            for x, y, z in g.positions:
                of.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
            for nx, ny, nz in g.normals:
                of.write(f"vn {nx:.4f} {ny:.4f} {nz:.4f}\n")
            for i in range(0, len(g.indices), 3):
                a = g.indices[i] + v_offset
                b = g.indices[i + 1] + v_offset
                c = g.indices[i + 2] + v_offset
                of.write(f"f {a}//{a} {b}//{b} {c}//{c}\n")
            v_offset += len(g.positions)
            of.write("\n")


def export_stl(path: str, groups: Dict[str, MeshGroup]) -> None:
    """Exports binary STL (Z-up for 3D printing / CAD compatibility)."""
    triangles = []
    for g in groups.values():
        for i in range(0, len(g.indices), 3):
            p0 = g.positions[g.indices[i]]
            p1 = g.positions[g.indices[i + 1]]
            p2 = g.positions[g.indices[i + 2]]
            # Convert Y-up (x, y, z) -> Z-up (x, -z, y)
            q0 = (p0[0], -p0[2], p0[1])
            q1 = (p1[0], -p1[2], p1[1])
            q2 = (p2[0], -p2[2], p2[1])
            n = v_norm(v_cross(v_sub(q1, q0), v_sub(q2, q0)))
            triangles.append((n, q0, q1, q2))

    header = b"Taipei 101 3D Model - Z-up Binary STL (1 unit = 1 meter)"
    header = header.ljust(80, b"\x00")[:80]

    with open(path, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", len(triangles)))
        for n, q0, q1, q2 in triangles:
            f.write(
                struct.pack(
                    "<12fH",
                    n[0], n[1], n[2],
                    q0[0], q0[1], q0[2],
                    q1[0], q1[1], q1[2],
                    q2[0], q2[1], q2[2],
                    0,
                )
            )


def export_viewer_html(html_path: str, glb_path: str) -> None:
    """Exports a self-contained viewer.html with embedded GLB so file:// opens automatically."""
    with open(glb_path, "rb") as f:
        glb_b64 = base64.b64encode(f.read()).decode("ascii")

    html_content = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>台北 101 3D 模型檢視器</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: "Segoe UI", "Microsoft JhengHei", sans-serif;
      background: #0b1320;
      color: #e6edf3;
      overflow: hidden;
      height: 100vh;
      width: 100vw;
    }}
    #canvas-container {{ width: 100%; height: 100%; }}
    #hud {{
      position: fixed;
      top: 16px;
      left: 16px;
      background: rgba(15, 23, 36, 0.82);
      border: 1px solid rgba(148, 163, 184, 0.25);
      backdrop-filter: blur(8px);
      border-radius: 10px;
      padding: 14px 16px;
      width: 260px;
      font-size: 13px;
      line-height: 1.5;
    }}
    #hud h1 {{
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 6px;
      color: #f8fafc;
    }}
    #hud .meta {{
      color: #94a3b8;
      font-size: 12px;
      margin-bottom: 12px;
    }}
    .controls {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }}
    button {{
      background: #1e293b;
      color: #e2e8f0;
      border: 1px solid #334155;
      border-radius: 6px;
      padding: 7px 10px;
      font-size: 12px;
      cursor: pointer;
      text-align: center;
      transition: background 0.15s ease;
    }}
    button:hover {{ background: #334155; }}
    button.active {{
      background: #0f766e;
      border-color: #14b8a6;
      color: #ffffff;
    }}
    #status {{
      margin-top: 10px;
      font-size: 12px;
      color: #cbd5e1;
    }}
  </style>
  <script type="importmap">
    {{
      "imports": {{
        "three": "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js",
        "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"
      }}
    }}
  </script>
</head>
<body>
  <div id="canvas-container"></div>

  <div id="hud">
    <h1>台北 101 3D 模型</h1>
    <div class="meta">高度：508.2 m｜比例：1 單位 = 1 公尺<br />拖曳旋轉・滾輪縮放・右鍵平移</div>
    <div class="controls">
      <button id="btn-night" class="active">夜景模式</button>
      <button id="btn-day">日間模式</button>
      <button id="btn-rotate" class="active">自動旋轉</button>
      <button id="btn-wire">線框檢視</button>
      <button id="btn-reset" style="grid-column: span 2;">重設視角</button>
    </div>
    <div id="status">正在載入台北 101 模型 ...</div>
  </div>

  <script id="embedded-glb" type="application/octet-stream">{glb_b64}</script>

  <script type="module">
    import * as THREE from "three";
    import {{ OrbitControls }} from "three/addons/controls/OrbitControls.js";
    import {{ GLTFLoader }} from "three/addons/loaders/GLTFLoader.js";

    const container = document.getElementById("canvas-container");
    const statusEl = document.getElementById("status");

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1320);
    scene.fog = new THREE.FogExp2(0x0b1320, 0.00055);

    const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 1, 5000);
    camera.position.set(360, 290, 440);

    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 235, 0);
    controls.enableDamping = true;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.8;
    controls.maxDistance = 1600;
    controls.minDistance = 80;
    controls.update();

    const hemiLight = new THREE.HemisphereLight(0x8ec5fc, 0x1e293b, 0.75);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xfff4e0, 1.8);
    sunLight.position.set(320, 520, 280);
    scene.add(sunLight);

    const rimLight = new THREE.DirectionalLight(0x38bdf8, 0.9);
    rimLight.position.set(-280, 260, -240);
    scene.add(rimLight);

    const uplightGroup = new THREE.Group();
    const uplightPositions = [
      [0, 115, 36], [0, 115, -36], [36, 115, 0], [-36, 115, 0],
      [0, 388, 28], [0, 388, -28]
    ];
    for (const [x, y, z] of uplightPositions) {{
      const pLight = new THREE.PointLight(0x38e8c6, 900, 180, 1.6);
      pLight.position.set(x, y, z);
      uplightGroup.add(pLight);
    }}
    scene.add(uplightGroup);

    const grid = new THREE.GridHelper(600, 30, 0x1e3a5f, 0x132238);
    scene.add(grid);

    let loadedModel = null;
    let wireframe = false;
    const loader = new GLTFLoader();

    function base64ToArrayBuffer(b64) {{
      const binary = atob(b64);
      const len = binary.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {{
        bytes[i] = binary.charCodeAt(i);
      }}
      return bytes.buffer;
    }}

    try {{
      const b64 = document.getElementById("embedded-glb").textContent.trim();
      const buffer = base64ToArrayBuffer(b64);
      loader.parse(
        buffer,
        "",
        (gltf) => {{
          loadedModel = gltf.scene;
          scene.add(loadedModel);
          statusEl.textContent = "已自動載入 taipei_101.glb";
        }},
        (err) => {{
          statusEl.textContent = "模型解析失敗：" + err;
        }}
      );
    }} catch (err) {{
      statusEl.textContent = "載入發生錯誤：" + err.message;
    }}

    const btnNight = document.getElementById("btn-night");
    const btnDay = document.getElementById("btn-day");
    const btnRotate = document.getElementById("btn-rotate");
    const btnWire = document.getElementById("btn-wire");
    const btnReset = document.getElementById("btn-reset");

    btnNight.addEventListener("click", () => {{
      btnNight.classList.add("active");
      btnDay.classList.remove("active");
      scene.background.setHex(0x0b1320);
      scene.fog.color.setHex(0x0b1320);
      hemiLight.intensity = 0.75;
      sunLight.intensity = 1.6;
      uplightGroup.visible = true;
    }});

    btnDay.addEventListener("click", () => {{
      btnDay.classList.add("active");
      btnNight.classList.remove("active");
      scene.background.setHex(0xcfe4f7);
      scene.fog.color.setHex(0xcfe4f7);
      hemiLight.intensity = 1.25;
      sunLight.intensity = 2.6;
      uplightGroup.visible = false;
    }});

    btnRotate.addEventListener("click", () => {{
      controls.autoRotate = !controls.autoRotate;
      btnRotate.classList.toggle("active", controls.autoRotate);
    }});

    btnWire.addEventListener("click", () => {{
      wireframe = !wireframe;
      btnWire.classList.toggle("active", wireframe);
      if (loadedModel) {{
        loadedModel.traverse((obj) => {{
          if (obj.isMesh && obj.material) {{
            obj.material.wireframe = wireframe;
          }}
        }});
      }}
    }});

    btnReset.addEventListener("click", () => {{
      camera.position.set(360, 290, 440);
      controls.target.set(0, 235, 0);
      controls.update();
    }});

    window.addEventListener("resize", () => {{
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }});

    function animate() {{
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }}
    animate();
  </script>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def main() -> None:
    out_dir = os.path.dirname(os.path.abspath(__file__))
    groups, materials = build_taipei_101()

    total_verts = sum(len(g.positions) for g in groups.values())
    total_tris = sum(len(g.indices) // 3 for g in groups.values())

    glb_path = os.path.join(out_dir, "taipei_101.glb")
    obj_path = os.path.join(out_dir, "taipei_101.obj")
    mtl_path = os.path.join(out_dir, "taipei_101.mtl")
    stl_path = os.path.join(out_dir, "taipei_101.stl")
    html_path = os.path.join(out_dir, "viewer.html")

    export_glb(glb_path, groups, materials)
    export_obj_mtl(obj_path, mtl_path, groups, materials)
    export_stl(stl_path, groups)
    export_viewer_html(html_path, glb_path)

    print(f"Generated Taipei 101 3D model successfully:")
    print(f"  Vertices : {total_verts:,}")
    print(f"  Triangles: {total_tris:,}")
    for p in (glb_path, obj_path, mtl_path, stl_path, html_path):
        print(f"  {os.path.basename(p)}: {os.path.getsize(p):,} bytes")


if __name__ == "__main__":
    main()
