"""Kafka consumer for receiving agent workflow results."""

import json
from typing import Type, TypeVar

from confluent_kafka import Consumer, KafkaError
from loguru import logger
from pydantic import BaseModel

from src.config.config_loader import load_config

T = TypeVar("T", bound=BaseModel)


class KafkaResultConsumer:
    """Consumes workflow results from Kafka topics, filtering by task_id."""

    def __init__(self, bootstrap_servers: str | None = None, group_id: str = "cli"):
        config = load_config()
        servers = bootstrap_servers or config.kafka.bootstrap_servers
        self._consumer = Consumer(
            {
                "bootstrap.servers": servers,
                "group.id": group_id,
                "auto.offset.reset": "latest",
                "enable.auto.commit": True,
            }
        )

    def consume(
        self,
        topic: str,
        task_id: str,
        response_type: Type[T],
        timeout: float = 600.0,
    ) -> T | None:
        """Subscribe to topic and wait for a message matching task_id.

        Args:
            topic: Kafka topic to consume from.
            task_id: The task_id key to filter for.
            response_type: Pydantic model class to deserialize into.
            timeout: Max seconds to wait.

        Returns:
            Deserialized response or None on timeout.
        """
        self._consumer.subscribe([topic])
        logger.info("Waiting for results", topic=topic, task_id=task_id)

        import time

        deadline = time.monotonic() + timeout

        try:
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                msg = self._consumer.poll(timeout=min(remaining, 1.0))

                if msg is None:
                    continue
                if msg.error():
                    err = msg.error()
                    if err.code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error(
                        f"Kafka consumer error: {err.str()} (code={err.code()})"
                    )
                    continue

                msg_key = msg.key().decode() if msg.key() else None
                if msg_key == task_id:
                    data = json.loads(msg.value().decode())
                    return response_type(**data)

            logger.warning("Consumer timed out", topic=topic, task_id=task_id)
            return None
        finally:
            self._consumer.close()
