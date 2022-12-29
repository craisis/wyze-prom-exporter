import os
import logging
from prometheus_client import start_http_server, REGISTRY
from prometheus_client.core import GaugeMetricFamily
from wyze_sdk import Client
from apscheduler.schedulers.background import BackgroundScheduler
from time import sleep

logging.basicConfig(level=logging.DEBUG)

class WyzeHealthCollector(object):
    def __init__(self, wyze_client):
        self.wyze_client = wyze_client
        self.last_device_poll = dict()

    def collect(self):
        is_online = GaugeMetricFamily('is_online', 'Camera is Online', labels=['nickname', 'mac'])
        for _, device in self.last_device_poll.items():
            is_online.add_metric(labels=[device.nickname, device.mac], value=1 if device.is_online else 0)
        yield is_online

    def update_devices(self):
        self.last_device_poll = { device.mac:device for device in self.wyze_client.devices_list() }
        logging.info('Loaded {} devices'.format(len(self.last_device_poll)))
        logging.debug('Loaded the following devices {}'.format(','.join([ device.nickname for device in self.last_device_poll.values() ])))


# Web setup and main loop
if __name__ == '__main__':
    # Authenticate to Wyze
    login_response = Client().login(email=os.environ['WYZE_EMAIL'], password=os.environ['WYZE_PASSWORD'])
    client = Client(token=login_response['access_token'])

    # Setup metrics
    #is_online = Gauge('is_online', 'Camera is Online', ['nickname', 'mac'])
    # Register custom collector
    whc = WyzeHealthCollector(client)
    REGISTRY.register(whc)

    # Setup regular update job
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(whc.update_devices,'interval', minutes=1)
    sched.start()

    whc.update_devices()
    start_http_server(8000)
    while True:
        sleep(1000)
