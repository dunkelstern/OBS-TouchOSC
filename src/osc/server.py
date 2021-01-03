from threading import current_thread
from oscpy.server import OSCThreadServer

def get_osc_server():
    def dump(address, *values):
        print(address, values)

    osc = OSCThreadServer(
        encoding='utf8',
        advanced_matching=True,
        # default_handler=dump
    )
    return osc


def start_osc_server(osc, port):
    sock = osc.listen(address='0.0.0.0', port=port, default=True)
    return sock
