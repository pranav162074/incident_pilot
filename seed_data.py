"""
seed_data.py - realistic historical incidents + demo alerts for IncidentPilot.
Keys match IncidentMemory.retain_incident(**incident).
"""

SEED_INCIDENTS = [
    {
        "incident_id": "INC-8815",
        "service": "auth-service",
        "summary": "504 Gateway Timeout on /api/v1/auth, p99 latency > 12s during morning peak.",
        "root_cause": "Not yet understood at the time; assumed the gateway timeout was too low.",
        "fix_applied": "Raised nginx proxy_read_timeout from 30s to 60s and restarted auth-service pods. "
                       "504s came back within 10 minutes - this only masked the real problem.",
        "outcome": "fix_failed",
        "minutes_to_resolve": 25,
        "tags": ["auth", "timeout", "504", "gateway"],
    },
    {
        "incident_id": "INC-8821",
        "service": "auth-service",
        "summary": "504 Gateway Timeout on /api/v1/auth, latency spiking above 12000ms after the v2.4 deployment.",
        "root_cause": "Postgres connection pool exhaustion in auth-service: pool max of 20 connections "
                      "saturated after v2.4 added an extra DB call per login.",
        "fix_applied": "Set DB_POOL_MAX from 20 to 100 in Helm values (charts/auth/values-prod.yaml), "
                       "then `kubectl rollout restart deployment/auth-service`. Verified with "
                       "`SELECT count(*) FROM pg_stat_activity WHERE application_name='auth-service'`.",
        "outcome": "resolved",
        "minutes_to_resolve": 47,
        "tags": ["auth", "timeout", "504", "postgres", "connection-pool"],
    },
    {
        "incident_id": "INC-9901",
        "service": "payments-worker",
        "summary": "payments-worker pods pinned at 100% CPU, queue depth growing, third-party API returning HTTP 429.",
        "root_cause": "Infinite retry loop in the queue consumer: on 429 the message was re-enqueued "
                      "immediately with no backoff and no retry cap.",
        "fix_applied": "Added exponential backoff (base 2s, jitter) and a max of 3 retries in the queue "
                       "consumer, dead-lettered the rest. Scaled workers back to 4 after the fix.",
        "outcome": "resolved",
        "minutes_to_resolve": 35,
        "tags": ["payments", "cpu", "429", "queue", "retry"],
    },
    {
        "incident_id": "INC-7703",
        "service": "redis-sessions",
        "summary": "Redis OOM killer triggered, sessions dropped, users logged out en masse.",
        "root_cause": "Session tokens written without a TTL, so keys accumulated until maxmemory was hit.",
        "fix_applied": "Emergency patch to set a 24h TTL on all session keys; deleted stale keys with a "
                       "SCAN + UNLINK script (never KEYS/FLUSHALL in prod); set maxmemory-policy volatile-lru.",
        "outcome": "resolved",
        "minutes_to_resolve": 52,
        "tags": ["redis", "oom", "memory", "ttl", "sessions"],
    },
    {
        "incident_id": "INC-9120",
        "service": "postgres-replica",
        "summary": "Read replica replication lag above 300s, stale data shown in dashboards.",
        "root_cause": "A long-running analytics query on the replica blocked WAL replay "
                      "(max_standby_streaming_delay set too high).",
        "fix_applied": "Terminated the query with pg_terminate_backend, lowered "
                       "max_standby_streaming_delay to 30s, and moved analytics to a dedicated replica.",
        "outcome": "resolved",
        "minutes_to_resolve": 68,
        "tags": ["postgres", "replication", "lag", "analytics"],
    },
    {
        "incident_id": "INC-9305",
        "service": "checkout-frontend",
        "summary": "HTTP 502 on checkout right after a deploy; pods running but failing readiness probes.",
        "root_cause": "New release referenced env var STRIPE_WEBHOOK_SECRET which was missing from the "
                      "production Kubernetes secret.",
        "fix_applied": "`kubectl rollout undo deployment/checkout-frontend` restored service in minutes; "
                       "secret added afterwards and a CI check for required env vars introduced.",
        "outcome": "resolved",
        "minutes_to_resolve": 12,
        "tags": ["checkout", "502", "deploy", "rollback", "config"],
    },
    {
        "incident_id": "INC-8544",
        "service": "search-service",
        "summary": "Search latency > 8s, Elasticsearch nodes at 95% heap with long GC pauses.",
        "root_cause": "Fielddata cache growth on a high-cardinality field with a 4g heap.",
        "fix_applied": "Cleared fielddata cache (POST /_cache/clear?fielddata=true), increased heap to 16g, "
                       "and mapped the field as keyword with doc_values.",
        "outcome": "resolved",
        "minutes_to_resolve": 41,
        "tags": ["elasticsearch", "heap", "gc", "latency"],
    },
    {
        "incident_id": "INC-9412",
        "service": "invoice-generator",
        "summary": "Nightly invoice CronJob pods repeatedly OOMKilled (exit code 137).",
        "root_cause": "Batch size of 5000 invoices loaded fully into memory against a 512Mi limit.",
        "fix_applied": "Reduced batch size to 500 and raised the memory limit to 2Gi in the CronJob spec.",
        "outcome": "resolved",
        "minutes_to_resolve": 30,
        "tags": ["kubernetes", "oomkilled", "cronjob", "memory"],
    },
    {
        "incident_id": "INC-9488",
        "service": "notifications-service",
        "summary": "notifications-service in CrashLoopBackOff; logs show TLS handshake failures to SMTP relay.",
        "root_cause": "Expired TLS certificate on the internal SMTP relay.",
        "fix_applied": "Renewed via cert-manager (`kubectl delete certificaterequest ...` to force reissue) "
                       "and restarted the deployment. Added a 14-day cert expiry alert.",
        "outcome": "resolved",
        "minutes_to_resolve": 25,
        "tags": ["tls", "certificate", "crashloop", "smtp"],
    },
    {
        "incident_id": "INC-9601",
        "service": "ingress-nginx",
        "summary": "Burst of 503s from ingress during a node drain for maintenance.",
        "root_cause": "No PodDisruptionBudget: the drain evicted all replicas of a service at once. "
                      "(Scaling replicas up mid-incident did not help.)",
        "fix_applied": "Added a PodDisruptionBudget with minAvailable: 2 and drained nodes one at a time.",
        "outcome": "resolved",
        "minutes_to_resolve": 33,
        "tags": ["ingress", "503", "pdb", "node-drain"],
    },
    {
        "incident_id": "INC-9710",
        "service": "core-dns",
        "summary": "Intermittent 5s latency on service-to-service calls inside the cluster.",
        "root_cause": "Default ndots:5 caused multiple failed search-domain lookups per request; "
                      "conntrack races on UDP DNS added 5s delays.",
        "fix_applied": "Set dnsConfig ndots:2 on affected pods and enabled NodeLocal DNSCache.",
        "outcome": "resolved",
        "minutes_to_resolve": 90,
        "tags": ["dns", "latency", "coredns", "kubernetes"],
    },
]

KAFKA_RESOLUTION = {
    "service": "orders-service",
    "root_cause": "Consumer group rebalance storm: slow calls to the inventory API pushed poll time past "
                  "max.poll.interval.ms (300000), so consumers were kicked from the group repeatedly.",
    "fix_applied": "Lowered max.poll.records from 500 to 50, raised max.poll.interval.ms to 600000, "
                   "switched to the CooperativeStickyAssignor, and added a 2s timeout on the inventory call.",
    "outcome": "resolved",
    "minutes_to_resolve": 55,
}

DEMO_ALERTS = {
    "1) 504 on auth endpoint (memory already knows this)": {
        "alert": "CRITICAL: Production gateway returning HTTP 504 Gateway Timeout on /api/v1/auth. "
                 "Latency spiking > 12000ms since 09:40 UTC.",
        "resolution": None,
    },
    "2) Payment worker CPU pegged (memory already knows this)": {
        "alert": "WARNING: payments-worker pods at 100% CPU for 20 minutes, queue depth rising, "
                 "upstream provider returning 429 Too Many Requests.",
        "resolution": None,
    },
    "3) Kafka consumer lag on orders-service (NEW - teach it!)": {
        "alert": "CRITICAL: orders-service Kafka consumer lag at 1.8M messages and growing. "
                 "Consumers keep dropping out of group 'orders-cg'; logs show frequent rebalances.",
        "resolution": KAFKA_RESOLUTION,
    },
    "4) Kafka lag follow-up (run AFTER teaching #3)": {
        "alert": "ALERT: orders-service consumers constantly rejoining consumer group, throughput near zero, "
                 "lag exceeding 2M. Inventory API calls are slow.",
        "resolution": KAFKA_RESOLUTION,
    },
    "Custom (type your own)": {"alert": "", "resolution": None},
}