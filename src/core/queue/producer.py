"""Kafka producer for publishing agent workflow results."""

import json

from confluent_kafka import Producer
from loguru import logger
from pydantic import BaseModel

from src.config.config_loader import load_config
from src.core.queue.config import (  # noqa: F401 - re-exported
    TOPIC_JOB_RESULTS,
    TOPIC_OUTREACH_RESULTS,
    TOPIC_OUTREACH_SEARCH_RESULTS,
)


class KafkaResultProducer:
    """Publishes workflow results to Kafka topics with batching support."""

    def __init__(self, bootstrap_servers: str | None = None):
        config = load_config()
        servers = bootstrap_servers or config.kafka.bootstrap_servers
        # Batching config for better throughput
        self._producer = Producer(
            {
                "bootstrap.servers": servers,
                "batch.size": 32768,  # 32KB batch size
                "linger.ms": 10,  # Wait up to 10ms to batch messages
                "acks": "1",  # Wait for leader ack (faster than "all")
            }
        )
        self._pending = 0

    def _delivery_report(self, err, msg):
        if err:
            logger.error("Kafka delivery failed", error=str(err), topic=msg.topic())
        else:
            logger.debug(
                "Kafka message delivered",
                topic=msg.topic(),
                key=msg.key().decode() if msg.key() else None,
            )

    def publish(self, topic: str, key: str, value: BaseModel) -> None:
        """Publish a Pydantic model to a Kafka topic keyed by task_id.

        Messages are batched for better throughput. Use flush() to ensure delivery.
        """
        self._producer.produce(
            topic=topic,
            key=key.encode(),
            value=value.model_dump_json().encode(),
            callback=self._delivery_report,
        )
        self._pending += 1
        # Poll to trigger delivery reports without blocking
        self._producer.poll(0)
        # Flush periodically to prevent unbounded buffering
        if self._pending >= 10:
            self._producer.flush()
            self._pending = 0

    def flush(self) -> None:
        """Flush all pending messages. Call before shutdown or when delivery confirmation needed."""
        if self._producer:
            self._producer.flush()
            self._pending = 0

    def close(self) -> None:
        """Close the producer, flushing any pending messages."""
        if self._producer:
            self._producer.flush()
            self._producer = None
            self._pending = 0
