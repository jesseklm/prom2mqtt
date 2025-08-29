import asyncio
import logging
import signal
import time

import httpcore
from httpcore import ConnectError
from prometheus_client.parser import text_string_to_metric_families

from config import get_first_config
from mqtt_handler import MqttHandler

__version__ = '0.0.13'


class Prom2Mqtt:
    def __init__(self) -> None:
        self.config = get_first_config()
        self.setup_logging()
        self.metric_url = self.config.get('victoriametrics_prom_import_url')
        self.update_rate: int = self.config.get('update_rate', 60)
        self.mqtt_handler: MqttHandler = MqttHandler(self.config)

    def setup_logging(self):
        if 'logging' in self.config:
            logging_level_name: str = self.config['logging'].upper()
            logging_level: int = logging.getLevelNamesMapping().get(logging_level_name, logging.NOTSET)
            if logging_level != logging.NOTSET:
                logging.getLogger().setLevel(logging_level)
            else:
                logging.warning(f'unknown logging level: %s.', logging_level)

    async def loop_iteration(self) -> None:
        if not await self.mqtt_handler.connect():
            return
        for scraper in self.config['scrapers']:
            for family in text_string_to_metric_families(await self.fetch(scraper['exporter_url'])):
                if family.name in scraper['filters']:
                    label_filters = scraper['filters'][family.name]
                    for sample in family.samples:
                        if label_filters and not all(
                                sample.labels.get(label_name)
                                in ([allowed] if isinstance(allowed, str) else allowed)
                                for label_name, allowed in label_filters.items()
                        ):
                            continue
                        labels = '_'.join(f'{label}_{value}' for label, value in sample.labels.items())
                        logging.debug("Name: {0} Labels: {1} Value: {2}".format(*sample))
                        topic = f'{sample.name}_{labels}'.replace('/', '_').replace('__', '_')
                        self.mqtt_handler.publish(topic, sample.value)
                        if self.metric_url:
                            await self.send_metric(topic, str(sample.value))

    async def send_metric(self, metric_name: str, value: str) -> str:
        async with httpcore.AsyncConnectionPool() as http:
            try:
                content = f'{metric_name} {value}'
                response = await http.request(
                    method='POST',
                    url=self.metric_url,
                    content=content.encode()
                )
                return response.content.decode()
            except ConnectError as e:
                logging.warning(f'{e=}, {content=}')
            except Exception as e:
                logging.error(f'{e=}, {content=}')
            return ''

    async def loop(self) -> None:
        while True:
            start_time: float = time.perf_counter()
            await self.loop_iteration()
            time_taken: float = time.perf_counter() - start_time
            time_to_sleep: float = self.update_rate - time_taken
            logging.debug('looped in %.2fms, sleeping %.2fs.', time_taken * 1000, time_to_sleep)
            if time_to_sleep > 0:
                await asyncio.sleep(time_to_sleep)

    async def exit(self):
        await self.mqtt_handler.disconnect()

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
