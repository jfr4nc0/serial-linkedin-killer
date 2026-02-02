"""Kafka topic configuration and bootstrap utilities."""

from confluent_kafka.admin import AdminClient, NewTopic
from loguru import logger

from src.config.config_loader import load_config

TOPIC_JOB_RESULTS = "job-results"
TOPIC_OUTREACH_RESULTS = "outreach-results"
TOPIC_OUTREACH_SEARCH_RESULTS = "outreach-search-results"
TOPIC_MCP_SEARCH_COMPLETE = "mcp-search-complete"

ALL_TOPICS = [
    TOPIC_JOB_RESULTS,
    TOPIC_OUTREACH_RESULTS,
    TOPIC_OUTREACH_SEARCH_RESULTS,
    TOPIC_MCP_SEARCH_COMPLETE,
]


def ensure_topics(bootstrap_servers: str | None = None) -> None:
    """Create all required Kafka topics if they don't exist."""
    config = load_config()
    servers = bootstrap_servers or config.kafka.bootstrap_servers
    try:
        admin = AdminClient({"bootstrap.servers": servers})
        metadata = admin.list_topics(timeout=5)
        missing = [t for t in ALL_TOPICS if t not in metadata.topics]
        if not missing:
            return
        futures = admin.create_topics(
            [NewTopic(t, num_partitions=1, replication_factor=1) for t in missing]
        )
        for topic, future in futures.items():
            future.result(timeout=10)
            logger.info("Created Kafka topic", topic=topic)
    except Exception as e:
        logger.warning("Failed to ensure Kafka topics", error=str(e))
