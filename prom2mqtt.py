import asyncio
import logging
import signal
import time

import httpcore
from gmqtt import Client as MQTTClient, Message
from httpcore import ConnectError
from prometheus_client.parser import text_string_to_metric_families

from config import get_first_config

__version__ = '0.0.7'


class Prom2Mqtt:
    def __init__(self) -> None:
        self.config = get_first_config()

        if 'logging' in self.config:
            logging_level_name: str = self.config['logging'].upper()
            logging_level: int = logging.getLevelNamesMapping().get(logging_level_name, logging.NOTSET)
            if logging_level != logging.NOTSET:
                logging.getLogger().setLevel(logging_level)
            else:
                logging.warning(f'unknown logging level: %s.', logging_level)
        self.update_rate: int = self.config.get('update_rate', 60)

        will_message: Message = Message(f'{self.config["mqtt_topic"]}available', 'offline', will_delay_interval=5,
                                        retain=True)
        self.client: MQTTClient = MQTTClient(client_id=None, will_message=will_message)
        self.client.on_connect = self.on_connect
        self.client.set_auth_credentials(self.config['mqtt_username'], self.config['mqtt_password'])

    async def connect_mqtt(self) -> bool:
        if self.client.is_connected:
            return True
        try:
            await self.client.connect(self.config['mqtt_server'])
            return True
        except ConnectionRefusedError as e:
            logging.warning(f"{self.config['mqtt_server']=}, {e=}")
        except Exception as e:
            logging.error(f"{self.config['mqtt_server']=}, {e=}")
        return False

    async def loop_iteration(self) -> None:
        if not await self.connect_mqtt():
            return
        for scraper in self.config['scrapers']:
            for family in text_string_to_metric_families(await self.fetch(scraper['exporter_url'])):
                if family.name in scraper['filters']:
                    for sample in family.samples:
                        labels = '_'.join(f'{label}_{value}' for label, value in sample.labels.items())
                        logging.debug("Name: {0} Labels: {1} Value: {2}".format(*sample))
                        if self.client.is_connected or await self.connect_mqtt():
                            self.client.publish(f'{self.config["mqtt_topic"]}{sample.name}_{labels}', sample.value)

    async def loop(self) -> None:
        while True:
            start_time: float = time.perf_counter()
            await self.loop_iteration()
            time_taken: float = time.perf_counter() - start_time
            time_to_sleep: float = self.update_rate - time_taken
            logging.debug('looped in %.2fms, sleeping %.2fs.', time_taken * 1000, time_to_sleep)
            if time_to_sleep > 0:
                await asyncio.sleep(time_to_sleep)

    def on_connect(self, client, flags, rc, properties):
        client.publish(f'{self.config["mqtt_topic"]}available', 'online', retain=True)
        logging.info('mqtt connected.')

    async def exit(self):
        if self.client.is_connected:
            await self.client.disconnect(reason_code=4)
            logging.info('mqtt disconnected.')

    @staticmethod
    async def fetch(url: str) -> str:
        async with httpcore.AsyncConnectionPool() as http:
            try:
                response = await http.request("GET", url)
                return response.content.decode()
            except ConnectError as e:
                logging.warning(f'{e=}, {url=}')
            except Exception as e:
                logging.error(f'{e=}, {url=}')
            return ''


async def main():
    prom2mqtt = Prom2Mqtt()
    loop = asyncio.get_running_loop()
    main_task = asyncio.current_task()

    def shutdown_handler():
        if not main_task.done():
            main_task.cancel()

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, shutdown_handler)
    except NotImplementedError:
        pass
    try:
        await prom2mqtt.loop()
    except asyncio.CancelledError:
        logging.info('exiting.')
    finally:
        await prom2mqtt.exit()
        logging.info('exited.')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.getLogger('gmqtt').setLevel(logging.ERROR)
    logging.info(f'starting Prom2Mqtt v%s.', __version__)
    asyncio.run(main())
