# Prom2MQTT

A lightweight Python bridge to scrape Prometheus metrics and publish them to an MQTT broker. Designed for IoT, smart home systems (like Home Assistant), and monitoring pipelines.

## Overview

Prom2MQTT periodically fetches metrics from configured Prometheus exporters, applies filters, and publishes them to an MQTT broker. Metrics are converted to MQTT topics for easy integration with IoT platforms or dashboards.

## Features

- **Scrape Prometheus endpoints** on a configurable interval.
- **Filter metrics** by name to publish only relevant data.
- **MQTT support** with authentication and retained availability messages.
- **Async I/O** for efficient performance.
- **Customizable MQTT topic structure** using metric names and labels.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/jesseklm/prom2mqtt.git
cd prom2mqtt
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Create a `config.yaml` file:

```yaml
mqtt_server: "mqtt://localhost:1883"
mqtt_topic: "home/metrics/"
mqtt_username: "user"
mqtt_password: "pass"
update_rate: 60  # Seconds between updates

scrapers:
  - exporter_url: "http://localhost:9100/metrics"
    filters: ["node_cpu_seconds_total", "node_memory_Active_bytes"]
```
- **mqtt_topic**: Base topic for published metrics (e.g., `home/metrics/cpu_usage`).
- **scrapers**: List of endpoints to scrape and their metric filters.

## Usage

Run the service:
```bash
python prom2mqtt.py
```

### Example MQTT Topic
A metric like `node_cpu_seconds_total{cpu="0",mode="idle"}` becomes:
```
home/metrics/node_cpu_seconds_total_cpu_0_mode_idle
```

## Metrics Filtering

Only metrics listed under `filters` in `config.yaml` are published. Use Prometheus metric names directly (e.g., `node_network_up`).
