from enum import Enum


class JobStatus(str, Enum):
    IN_QUEUE = "IN_QUEUE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


class EndpointStatus(str, Enum):
    DEPLOYING = "DEPLOYING"
    READY = "READY"
    UNHEALTHY = "UNHEALTHY"
