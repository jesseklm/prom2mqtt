# Prom2MQTT

A lightweight Python bridge to scrape Prometheus metrics and publish them to an MQTT broker. Designed for IoT use cases, smart home systems (e.g., Home Assistant), and monitoring pipelines.

## Overview

Prom2MQTT periodically fetches metrics from configured Prometheus exporters, applies flexible label-based filters, and publishes the metrics to an MQTT broker. The metrics are converted into MQTT topics for straightforward integration with IoT platforms, dashboards, or automation systems.

## Features

- **Scrape Prometheus endpoints** on a configurable interval
- **Label-based filtering** to publish only specific metrics
- **Async I/O** for efficient performance
- **Customizable topic structure** using metric names and labels

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
    filters:
      node_cpu_seconds_total:
        cpu:
          - "0"
          - "1"
        mode: idle
      node_memory_Active_bytes:
```

- **mqtt_server**: The MQTT broker URL. For TLS, you could use `mqtts://your-broker:8883`.
- **mqtt_topic**: The base MQTT topic for published metrics (e.g., `home/metrics/node_cpu_seconds_total_cpu_0_mode_idle`).
- **update_rate**: Interval in seconds between scrapes.
- **scrapers**: A list of Prometheus endpoints to scrape along with filters:
  - In this example, `node_cpu_seconds_total` is published only for `cpu` values `"0"` or `"1"` and `mode="idle"`.  
  - `node_memory_Active_bytes` is published with no additional label filters.

## Usage

Run the service:
```bash
python prom2mqtt.py
```

### Example MQTT Topic

A metric like:
```
node_cpu_seconds_total{cpu="0",mode="idle"}
```
is published to the MQTT topic:
```
home/metrics/node_cpu_seconds_total_cpu_0_mode_idle
```

## Metrics Filtering

Only metrics (and their labels) listed under `filters` in `config.yaml` are published.  
Use the exact Prometheus metric names (e.g., `node_network_up`).  
For each label, you can specify either a single value or a list of values to allow.
