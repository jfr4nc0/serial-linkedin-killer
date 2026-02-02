"""Kafka producer for publishing agent workflow results."""

import json

from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
from loguru import logger
from pydantic import BaseModel

from src.config.config_loader import load_config

TOPIC_JOB_RESULTS = "job-results"
TOPIC_OUTREACH_RESULTS = "outreach-results"
TOPIC_OUTREACH_SEARCH_RESULTS = "outreach-search-results"


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
        self._servers = servers
        self._ensured_topics: set[str] = set()

    def _ensure_topic(self, topic: str) -> None:
        """Create topic if it doesn't exist yet."""
        if topic in self._ensured_topics:
            return
        try:
            admin = AdminClient({"bootstrap.servers": self._servers})
            metadata = admin.list_topics(timeout=5)
            if topic not in metadata.topics:
                futures = admin.create_topics(
                    [NewTopic(topic, num_partitions=1, replication_factor=1)]
                )
                futures[topic].result(timeout=10)
                logger.info("Created Kafka topic", topic=topic)
            self._ensured_topics.add(topic)
        except Exception as e:
            logger.warning("Failed to ensure Kafka topic", topic=topic, error=str(e))

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
        self._ensure_topic(topic)
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
