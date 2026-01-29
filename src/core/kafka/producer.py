"""Kafka producer for publishing agent workflow results."""

import json

from confluent_kafka import Producer
from loguru import logger
from pydantic import BaseModel

from src.config.config_loader import load_config

TOPIC_JOB_RESULTS = "job-results"
TOPIC_OUTREACH_RESULTS = "outreach-results"


class KafkaResultProducer:
    """Publishes workflow results to Kafka topics."""

    def __init__(self, bootstrap_servers: str | None = None):
        config = load_config()
        servers = bootstrap_servers or config.kafka.bootstrap_servers
        self._producer = Producer({"bootstrap.servers": servers})

    def _delivery_report(self, err, msg):
        if err:
            logger.error("Kafka delivery failed", error=str(err), topic=msg.topic())
        else:
            logger.info(
                "Kafka message delivered",
                topic=msg.topic(),
                key=msg.key().decode() if msg.key() else None,
            )

    def publish(self, topic: str, key: str, value: BaseModel) -> None:
        """Publish a Pydantic model to a Kafka topic keyed by task_id."""
        self._producer.produce(
            topic=topic,
            key=key.encode(),
            value=value.model_dump_json().encode(),
            callback=self._delivery_report,
        )
        self._producer.flush()

    def close(self) -> None:
        self._producer.flush()
