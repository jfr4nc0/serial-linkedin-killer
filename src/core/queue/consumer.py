"""Kafka consumer for receiving agent workflow results."""

import json
import time
import uuid
from typing import Type, TypeVar

from confluent_kafka import Consumer, KafkaError
from loguru import logger
from pydantic import BaseModel

from src.config.config_loader import load_config

T = TypeVar("T", bound=BaseModel)


class KafkaResultConsumer:
    """Consumes workflow results from Kafka topics, filtering by task_id.

    Each instance creates a unique consumer group to avoid offset conflicts
    and group accumulation on the broker.
    """

    def __init__(
        self, bootstrap_servers: str | None = None, group_id: str | None = None
    ):
        config = load_config()
        servers = bootstrap_servers or config.kafka.bootstrap_servers
        # Use a unique ephemeral group_id to avoid group accumulation
        # and offset conflicts between different consume() calls.
        effective_group_id = group_id or f"ephemeral-{uuid.uuid4().hex[:12]}"
        self._consumer = Consumer(
            {
                "bootstrap.servers": servers,
                "group.id": effective_group_id,
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
        import time as perf_time

        t_start = perf_time.perf_counter()
        self._consumer.subscribe([topic])
        logger.info("Waiting for results", topic=topic, task_id=task_id)

        deadline = time.monotonic() + timeout
        poll_count = 0

        try:
            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                msg = self._consumer.poll(timeout=min(remaining, 5.0))
                poll_count += 1

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
                    t_msg_received = perf_time.perf_counter()

                    t_pre_parse = perf_time.perf_counter()
                    data = json.loads(msg.value().decode())
                    t_post_parse = perf_time.perf_counter()

                    # Set trace context from received message for subsequent logs
                    from src.config.trace_context import set_trace_id

                    msg_trace_id = data.get("trace_id", "")
                    if msg_trace_id:
                        set_trace_id(msg_trace_id)

                    logger.info(
                        "[TIMING] Message received",
                        elapsed_ms=round((t_msg_received - t_start) * 1000, 2),
                        poll_count=poll_count,
                    )

                    logger.info(
                        "[TIMING] JSON parsed",
                        elapsed_ms=round((t_post_parse - t_pre_parse) * 1000, 2),
                        payload_bytes=len(msg.value()),
                    )

                    t_pre_model = perf_time.perf_counter()
                    result = response_type(**data)
                    t_post_model = perf_time.perf_counter()
                    logger.info(
                        "[TIMING] Pydantic model created",
                        elapsed_ms=round((t_post_model - t_pre_model) * 1000, 2),
                    )

                    return result

            logger.warning("Consumer timed out", topic=topic, task_id=task_id)
            return None
        finally:
            self._consumer.close()
