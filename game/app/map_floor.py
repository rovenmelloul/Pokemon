"""MapFloor - map using OpenStreetMap tiles with fast async loading."""

import math
import os
import urllib.request
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from panda3d.core import (
    Texture, PNMImage, CardMaker, Filename,
)
from direct.gui.OnscreenText import OnscreenText

TILE_STYLES = {
    "standard":          "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    "voyager":           "https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}@2x.png",
    "voyager_nolabels":  "https://basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}@2x.png",
    "dark":              "https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
    "dark_nolabels":     "https://basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}@2x.png",
    "light":             "https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png",
    "light_nolabels":    "https://basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}@2x.png",
}


def lat_lon_to_tile(lat, lon, zoom):
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


class MapFloor:
    """Async mega-tile map. Each mega = CHUNK x CHUNK stitched OSM tiles."""

    UA = "PokemonGoGame/1.0 (Panda3D; educational)"
    CHUNK = 3          # 3x3 = 9 tiles per mega (was 5x5=25)
    TILE_PX = 512

    def __init__(self, show_base, lat=48.8584, lon=2.2945, zoom=17,
                 style="voyager_nolabels", tile_size=25.0, **_kw):
        self.base = show_base
        self.zoom = zoom
        self.tile_size = tile_size
        self.mega_size = tile_size * self.CHUNK

        self.style = style if style in TILE_STYLES else "voyager_nolabels"
        self.tile_url = TILE_STYLES[self.style]

        self.root = show_base.render.attachNewNode("map_floor")

        self.origin_tx, self.origin_ty = lat_lon_to_tile(lat, lon, zoom)
        self._omx = self.origin_tx // self.CHUNK
        self._omy = self.origin_ty // self.CHUNK
        self._last_mega = (self._omx, self._omy)

        base_cache = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tile_cache')
        self._raw_dir = os.path.join(base_cache, self.style)
        self._mega_dir = os.path.join(base_cache, self.style + '_mega')
        os.makedirs(self._raw_dir, exist_ok=True)
        os.makedirs(self._mega_dir, exist_ok=True)

        self._megas = {}
        self._pending = set()
        self._ready = deque()
        self._executor = ThreadPoolExecutor(max_workers=8)

        # Loading screen
        self._loading_text = OnscreenText(
            text="Loading map...",
            pos=(0, 0), scale=0.08,
            fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
            mayChange=True,
        )

        # Load only the central mega-tile synchronously (~2-3s with 9 tiles)
        print("[Map] Loading central tile...")
        self._load_single_sync(self._omx, self._omy)
        print(f"[Map] Central mega loaded. Requesting neighbors async...")

        # Remove loading text
        if self._loading_text:
            self._loading_text.destroy()
            self._loading_text = None

        # Request the surrounding megas asynchronously
        self._request_async(self._omx, self._omy)

        show_base.taskMgr.add(self._tick, "map_floor_tick")

    def _download_tile(self, tx, ty):
        rp = os.path.join(self._raw_dir, f"{self.zoom}_{tx}_{ty}.png")
        if os.path.exists(rp):
            return rp
        url = self.tile_url.format(z=self.zoom, x=tx, y=ty)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': self.UA})
            data = urllib.request.urlopen(req, timeout=15).read()
            with open(rp, 'wb') as f:
                f.write(data)
            return rp
        except Exception as e:
            print(f"[Map] tile ({tx},{ty}) failed: {e}")
            return None

    def _mega_path(self, mx, my):
        return os.path.join(self._mega_dir, f"{self.zoom}_{mx}_{my}.jpg")

    def _build_mega(self, mx, my):
        mp = self._mega_path(mx, my)
        if os.path.exists(mp):
            return mp

        from PIL import Image
        C = self.CHUNK
        P = self.TILE_PX
        base_tx, base_ty = mx * C, my * C

        mega = Image.new('RGB', (C * P, C * P), (251, 248, 243))
        for dy in range(C):
            for dx in range(C):
                rp = self._download_tile(base_tx + dx, base_ty + dy)
                if rp:
                    try:
                        mega.paste(Image.open(rp).convert('RGB'), (dx * P, dy * P))
                    except Exception:
                        pass
        mega.save(mp, format='JPEG', quality=85)
        return mp

    def _make_mega_node(self, mx, my, cache_path):
        pnm = PNMImage()
        if not pnm.read(Filename.fromOsSpecific(cache_path)):
            return

        tex = Texture(f"mega_{mx}_{my}")
        tex.load(pnm)
        tex.setWrapU(Texture.WMClamp)
        tex.setWrapV(Texture.WMClamp)
        tex.setMinfilter(Texture.FTLinearMipmapLinear)
        tex.setMagfilter(Texture.FTLinear)

        cm = CardMaker(f"mega_{mx}_{my}")
        cm.setFrame(0, 1, 0, 1)

        node = self.root.attachNewNode(cm.generate())
        node.setTexture(tex)
        node.setP(-90)
        node.setScale(self.mega_size)

        C = self.CHUNK
        base_tx, base_ty = mx * C, my * C
        s = self.tile_size
        node.setPos(
            (base_tx - self.origin_tx) * s - s * 0.5,
            -(base_ty + C - 1 - self.origin_ty) * s - s * 0.5,
            0,
        )
        node.setLightOff()
        self._megas[(mx, my)] = node

    def _needed_megas(self, cmx, cmy):
        """5x5 grid of megas to compensate for smaller chunk size."""
        return {(cmx + dx, cmy + dy) for dx in range(-2, 3) for dy in range(-2, 3)}

    def _load_single_sync(self, mx, my):
        """Load a single mega-tile synchronously."""
        path = self._build_mega(mx, my)
        if path:
            self._make_mega_node(mx, my, path)

    def _request_async(self, cmx, cmy):
        needed = self._needed_megas(cmx, cmy)
        for k in [k for k in self._megas if k not in needed]:
            self._megas.pop(k).removeNode()
        for k in needed:
            if k not in self._megas and k not in self._pending:
                self._pending.add(k)
                self._executor.submit(self._bg_work, *k)

    def _bg_work(self, mx, my):
        path = self._build_mega(mx, my)
        self._pending.discard((mx, my))
        if path:
            self._ready.append((mx, my, path))

    def _world_to_mega(self, wx, wy):
        s = self.tile_size
        tx = self.origin_tx + int(math.floor(wx / s + 0.5))
        ty = self.origin_ty - int(math.floor(wy / s + 0.5))
        return tx // self.CHUNK, ty // self.CHUNK

    def _tick(self, task):
        for _ in range(4):
            if not self._ready:
                break
            mx, my, path = self._ready.popleft()
            if (mx, my) not in self._megas:
                self._make_mega_node(mx, my, path)

        cam = self.base.camera.getPos(self.base.render)
        c = self._world_to_mega(cam.getX(), cam.getY())
        if c != self._last_mega:
            self._last_mega = c
            self._request_async(*c)

        return task.cont

    def destroy(self):
        self.base.taskMgr.remove("map_floor_tick")
        self._executor.shutdown(wait=False)
        self.root.removeNode()
        self._megas.clear()
        if self._loading_text:
            self._loading_text.destroy()
            self._loading_text = None
