import sys
import os
import traceback

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, 'game')

    with open('game_output.log', 'w') as log:
        log.write("Starting game...\n")
        log.flush()

        import json
        import urllib.request
        from direct.showbase.ShowBase import ShowBase
        from panda3d.core import Filename, getModelPath
        from app.player.player_instance import Player
        from app.pokemon.pokemon import Pokemon
        from app.map_floor import MapFloor

        log.write("Imports OK\n")
        log.flush()

        PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

        def detect_gps():
            try:
                data = json.loads(urllib.request.urlopen(
                    'http://ip-api.com/json/', timeout=5).read())
                lat, lon = data['lat'], data['lon']
                city = data.get('city', '?')
                log.write(f"[GPS] Position: {city} ({lat}, {lon})\n")
                log.flush()
                return lat, lon
            except Exception as e:
                log.write(f"[GPS] Detection failed: {e}\n")
                log.flush()
                return 43.3104, 5.37335

        class MyApp(ShowBase):
            def __init__(self):
                ShowBase.__init__(self)
                getModelPath().prependDirectory(Filename.fromOsSpecific(PROJECT_ROOT))
                log.write("ShowBase initialized\n")
                log.flush()

                lat, lon = detect_gps()

                self.map_floor = MapFloor(
                    self, lat=lat, lon=lon, zoom=17,
                    style="voyager_nolabels",
                    cartoon=True,
                )
                log.write(f"MapFloor: {len(self.map_floor._tiles)} tiles\n")
                log.flush()

                player = Player(self)
                player.spawn_self()
                player.key_bindings()
                log.write("Player created\n")
                log.flush()

                for i in range(3):
                    pokemon = Pokemon(self)
                    pokemon.spawn_random_pokemon()
                    pokemon.draw_name_tag()
                log.write("Pokemon spawned - Game running!\n")
                log.flush()

        app = MyApp()
        app.run()

except Exception as e:
    with open('game_error.log', 'w') as f:
        traceback.print_exc(file=f)
    traceback.print_exc()
