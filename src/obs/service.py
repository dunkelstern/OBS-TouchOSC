from obswebsocket import requests, events, obsws

from osc.server import get_osc_server, start_osc_server


class OBSRemote:

    def __init__(self, osc_port, osc_client_host, osc_client_port, host, port, password=''):
        self.client = obsws(host, port, password)
        self.osc = get_osc_server()
        self.socket = None
        self.osc_client_host = osc_client_host
        self.osc_client_port = osc_client_port
        self.osc_port = osc_port

        self.scenes = []

    def start(self):
        self.client.connect()
        self.socket = start_osc_server(self.osc, self.osc_port)

        self._update_scenes()

        self.client.register(self.scene_changed, event=events.SwitchScenes)
        self.client.register(self.mute_changed, event=events.SourceMuteStateChanged)

        @self.osc.address('/scene/?/?', get_address=True)
        def scene_cb(address, values):
            if values < 1.0:
                return

            scene_id = int(address.split(b'/')[-1]) - 1
            if scene_id < len(self.scenes):
                print('Activate scene {}'.format(self.scenes[scene_id]))
                self.osc.answer(address, [1.0])
                self.client.call(requests.SetCurrentScene(self.scenes[scene_id]))

        @self.osc.address('/mic')
        def mic_cb(values):
            self.osc.answer('/mic', [values])
            self.client.call(requests.SetMute('Mic/Aux', values < 1.0))

        @self.osc.address('/audio')
        def audio_cb(values):
            self.osc.answer('/audio', [values])
            self.client.call(requests.SetMute('Desktop Audio', values < 1.0))

        @self.osc.address('/cam')
        def cam_cb(values):
            self.osc.answer('/cam', [values])
            self.client.call(requests.SetSceneItemProperties('Webcam', visible=values > 0.0))
            self.client.call(requests.SetSceneItemProperties('Overlay: Webcam', visible=values > 0.0))

        @self.osc.address('/rec')
        def rec_cb(values):
            self.osc.answer('/rec', [values])
            print('rec {}'.format(values))

        @self.osc.address('/stream')
        def stream_cb(values):
            self.osc.answer('/stream', [values])
            print('stream {}'.format(values))

    def stop(self):
        self.client.unregister(self.scene_changed, event=events.SwitchScenes)
        self.client.disconnect()
        self.osc.stop()
        self.socket = None

    def mute_changed(self, event):
        name = event.getSourceName()
        muted = event.getMuted()
        if name == 'Mic/Aux':
            self._send_osc('/mic', 1.0 if muted is False else 0.0)
        if name == 'Desktop Audio':
            self._send_osc('/audio', 1.0 if muted is False else 0.0)

    def scene_changed(self, event):
        name = event.getSceneName()
        for idx, scene_name in enumerate(self.scenes):
            if name == scene_name:
                print('Switching scene to idx {}'.format(idx))
                self._send_osc('/scene/1/{}'.format(idx + 1), 1.0)
        sources = event.getSources()
        webcam_found = False
        for source in sources:
            if source['name'] in ['Webcam', 'Overlay: Webcam']:
                webcam_found = True
                self._send_osc('/cam', 1.0 if source['render'] else 0.0)
        if not webcam_found:
            self._send_osc('/cam', 0.0)


    def _send_osc(self, address, value):
        self.osc.send_message(address, [value], self.osc_client_host, self.osc_client_port)

    def _update_scenes(self):
        self.scenes = [s['name'] for s in self.client.call(requests.GetSceneList()).getScenes() if not s['name'].lower().startswith('overlay:')]
        for idx in range(0, 8):
            try:
                name = self.scenes[idx]
            except IndexError:
                name = ''

            self._send_osc('/scene_label_{}'.format(idx), name)
