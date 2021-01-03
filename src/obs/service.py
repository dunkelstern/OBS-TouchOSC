from time import time_ns
from datetime import timedelta

from obswebsocket import requests, events, obsws
from oscpy.server import OSCThreadServer


class OBSRemote:

    def __init__(self, osc_port, osc_client_host, osc_client_port, host, port, password=''):
        self.client = obsws(host, port, password)
        self.register_callbacks()

        self.osc = OSCThreadServer(
            encoding='utf8',
            advanced_matching=True,
        )

        self.socket = None
        self.osc_client_host = osc_client_host
        self.osc_client_port = osc_client_port
        self.osc_port = osc_port
        self.volume_changed = False
        self.levels = [0, 0]

        self.scenes = []

    def start(self):
        self.client.connect()
        self.socket = self.osc.listen(address='0.0.0.0', port=self.osc_port, default=True)

        self.update_audio_sources()
        self.update_audio_levels()
        self.update_scenes()
        self.update_mute_status()
        self.register_osc_addresses()

        self.client.call(requests.SetHeartbeat(True))

    def stop(self):
        self.client.disconnect()
        self.osc.stop()
        self.socket = None

    def register_callbacks(self):
        self.client.register(self.scene_changed, event=events.SwitchScenes)
        self.client.register(self.mute_changed, event=events.SourceMuteStateChanged)
        self.client.register(self.update_scenes, event=events.ScenesChanged)
        self.client.register(self.update_scenes, event=events.SceneCollectionChanged)
        self.client.register(self.update_audio_sources, event=events.SourceRenamed)
        self.client.register(self.update_audio_levels, event=events.SourceVolumeChanged)
        self.client.register(self.status_update, event=events.Heartbeat)


    def register_osc_addresses(self):
        @self.osc.address('/scene/?/?', get_address=True)
        def scene_cb(address, values):
            if values < 1.0:
                return

            scene_id = int(address.split(b'/')[-1]) - 1
            if scene_id < len(self.scenes):
                self.osc.answer(address, [1.0])
                self.client.call(requests.SetCurrentScene(self.scenes[scene_id]))

        @self.osc.address('/mic')
        def mic_cb(values):
            self.osc.answer('/mic', [values])
            self.client.call(requests.SetMute(self.audio_sources['mic'], values < 1.0))

        @self.osc.address('/audio')
        def audio_cb(values):
            self.osc.answer('/audio', [values])
            self.client.call(requests.SetMute(self.audio_sources['desktop'], values < 1.0))

        @self.osc.address('/cam')
        def cam_cb(values):
            self.osc.answer('/cam', [values])
            self.client.call(requests.SetSceneItemProperties('Webcam', visible=values > 0.0))
            self.client.call(requests.SetSceneItemProperties('Overlay: Webcam', visible=values > 0.0))

        @self.osc.address('/audio_level/?', get_address=True)
        def audio_level_cb(address, values):
            slider_id = int(address.split(b'/')[-1]) - 1
            self.levels[slider_id] = values
            self.volume_changed = True

        @self.osc.address('/rec')
        def rec_cb(values):
            if values > 0.0:
                self.client.call(requests.StartRecording())
            else:
                self.client.call(requests.StopRecording())
            self.osc.answer('/rec', [values])

        @self.osc.address('/stream')
        def stream_cb(values):
            if values > 0.0:
                self.client.call(requests.StartStreaming())
            else:
                self.client.call(requests.StopStreaming())
            self.osc.answer('/stream', [values])

    def mute_changed(self, event):
        name = event.getSourceName()
        muted = event.getMuted()
        if name == self.audio_sources['mic']:
            self._send_osc('/mic', 1.0 if muted is False else 0.0)
        if name == self.audio_sources['desktop']:
            self._send_osc('/audio', 1.0 if muted is False else 0.0)

    def scene_changed(self, event):
        name = event.getSceneName()
        for idx, scene_name in enumerate(self.scenes):
            if name == scene_name:
                self._send_osc('/scene/1/{}'.format(idx + 1), 1.0)
        self.update_mute_status(sources=event.getSources())

    def status_update(self, event: events.Heartbeat):
        streaming = event.getStreaming()
        recording = event.getRecording()
        try:
            stream_time = timedelta(seconds=event.getTotalStreamTime())
        except KeyError:
            stream_time = 0
        try:
            rec_time = timedelta(seconds=event.getTotalRecordTime())
        except KeyError:
            rec_time = 0
        self._send_osc('/stream', 1.0 if streaming else 0.0)
        self._send_osc('/rec', 1.0 if recording else 0.0)
        self._send_osc('/stream_time', str(stream_time))
        self._send_osc('/rec_time', str(rec_time))

    def update_mute_status(self, sources=None):
        if sources is None:
            sources = self.client.call(requests.GetCurrentScene()).getSources()
        webcam_found = False
        for source in sources:
            if source['name'] in ['Webcam', 'Overlay: Webcam']:
                webcam_found = True
                self._send_osc('/cam', 1.0 if source['render'] else 0.0)
        if not webcam_found:
            self._send_osc('/cam', 0.0)

    def update_scenes(self, *args):
        if len(args) > 0:
            self.scenes = [s['name'] for s in args[0].getScenes() if not s['name'].lower().startswith('overlay:')]
        else:
            self.scenes = [s['name'] for s in self.client.call(requests.GetSceneList()).getScenes() if not s['name'].lower().startswith('overlay:')]

        for idx in range(0, 8):
            try:
                name = self.scenes[idx]
            except IndexError:
                name = ''

            self._send_osc('/scene_label_{}'.format(idx), name)
        self.update_mute_status()

    def update_audio_sources(self, *args):
        sources = self.client.call(requests.GetSpecialSources())
        self.audio_sources = {
            "mic": sources.getMic1(),
            "desktop": sources.getDesktop1()
        }

    def update_audio_levels(self, *args):
        if len(args) > 0:
            event = args[0]
            name = event.getSourceName()
            volume = None
            if isinstance(event, events.SourceVolumeChanged):
                volume = event.getVolume()
            muted = None
            if isinstance(event, events.SourceMuteStateChanged):
                muted = event.getMuted()

            if name == self.audio_sources['mic']:
                if volume is not None:
                    self._send_osc('/audio_level/1', volume)
                    self.levels[0] = volume
                if muted is not None:
                    self._send_osc('/mic', 1.0 if not muted else 0.0)
            elif name == self.audio_sources['desktop']:
                if volume is not None:
                    self._send_osc('/audio_level/2', volume)
                if muted is not None:
                    self._send_osc('/audio', 1.0 if not muted else 0.0)
        else:
            desktop = self.client.call(requests.GetVolume(self.audio_sources['desktop']))
            mic = self.client.call(requests.GetVolume(self.audio_sources['mic']))

            self._send_osc('/audio_level/2', desktop.getVolume())
            self.levels[1] = desktop.getVolume()
            self._send_osc('/audio', 1.0 if not desktop.getMuted() else 0.0)
            self._send_osc('/audio_level/1', mic.getVolume())
            self.levels[0] = mic.getVolume()
            self._send_osc('/mic', 1.0 if not mic.getMuted() else 0.0)

    def _send_osc(self, address, value):
        self.osc.send_message(address, [value], self.osc_client_host, self.osc_client_port)

    def tick(self):
        if self.volume_changed:
            self.volume_changed = False
            self.client.call(requests.SetVolume(list(self.audio_sources.values())[0], self.levels[0]))
            self.client.call(requests.SetVolume(list(self.audio_sources.values())[1], self.levels[1]))
