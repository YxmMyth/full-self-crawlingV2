# Full-Self-Crawling - System Architecture

**Version**: v1.0.0
**Date**: 2026-02-20
**Scope**: Overall system architecture and orchestration

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Orchestration Layer](#2-orchestration-layer)
3. [Multi-Site Scheduling](#3-multi-site-scheduling)
4. [Status Monitoring](#4-status-monitoring)
5. [Result Presentation](#5-result-presentation)
6. [Data Storage](#6-data-storage)
7. [Configuration](#7-configuration)

---

## 1. System Architecture

### 1.1 Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator Layer                       │
│  ┌───────────┐  ┌──────────┐  ┌───────────┐  ┌───────────┐  │
│  │ Decide1   │→│   Scan   │→│  Decide2  │→│  Agent    │  │
│  │ (Intent)  │  │ (Site)   │  │ (Feasibility) │ Manager  │  │
│  └───────────┘  └──────────┘  └───────────┘  └───────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agent Layer                            │
│                  (Per Site Instance)                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           SOOAL Loop (Sense→Orient→Act→Verify→Learn) │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Execution Layer                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐  │
│  │ Strategies│ │Plugins  │ │Verify   │ │ Artifacts Output │  │
│  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Component Relationships

```
User Request
     │
     ▼
┌─────────────┐
│ Orchestrator│◄───── Site Knowledge Base
│             │
│  ┌────────┐ │
│  │ Parser │ │    Intent Contract
│  └────┬───┘ │          │
│       │     │          ▼
│  ┌────▼────┐ │    ┌─────────┐
│  │ Scanner │ │    │ Decide2 │
│  └────┬────┘ │    └────┬────┘
│       │     │         │
│  ┌────▼─────┼────┐    │
│  │   Agent  │◀───┴────┘
│  │ Manager  │
│  └────┬─────┘
│       │
│       ▼
│  ┌──────────┐
│  │ Monitor  │
│  └────┬─────┘
│       │
│       ▼
│  ┌─────────┐
│  │ Display │
│  └─────────┘
└───────────┘
```

### 1.3 Phase-wise Development

| Phase | Scope | Status |
|-------|-------|--------|
| **单 Agent 模式** | Single-site Agent capability | 当前 |
| **多 Agent 并行** | Multi-site parallel scheduling | 未来 |

---

## 2. Orchestration Layer

### 2.1 Overview

The Orchestrator is responsible for:
- **User interaction**: Receive and interpret user requests
- **Intent parsing**: Understand what the user wants to crawl
- **Agent management**: Create, monitor, and control Agent instances
- **Result presentation**: Format and display results

### 2.2 Decide1: Intent Parsing

#### Input
```python
{
    "user_intent": str,      # User's natural language request
    "site_url": str,         # Target site URL
    "constraints": Optional[Dict]
}
```

#### Output
```python
{
    "should_proceed": bool,
    "confidence": float,
    "intent_contract": Optional[IntentContract],
    "estimated_cost": Optional[CostProjection]
}
```

#### Intent Contract
```python
{
    "target_fields": List[str],      # Fields to extract
    "content_type": Optional[ContentType],  # article, image, etc.
    "scope": CrawlScope,             # full, partial, custom
    "constraints": Dict              # User constraints
}
```

#### Intent Parsing Process

1. **Extract intent** from user's natural language
2. **Check site knowledge** for existing patterns
3. **Compare constraints** vs historical data
4. **Generate go/no-go decision** with confidence

### 2.3 Scan: Site Probing

#### Input
```python
{
    "site_url": str,
    "intent_contract": IntentContract
}
```

#### Output
```python
{
    "resource_inventory": {
        "total_pages": int,
        "page_types": List[str]
    },
    "crawlability_assessment": {
        "difficulty": str,  # easy, medium, hard, impossible
        "anti_bot": List[str]
    },
    "risk_signals": List[str],
    "cost_projection": {
        "time_minutes": int,
        "pages": int,
        "tokens": int
    }
}
```

### 2.4 Decide2: Feasibility Scoring

#### Composite Score Formula

```
composite_score =
    0.30 * intent_fit           # Does site match intent?
  + 0.25 * field_completeness   # Can we extract required fields?
  + 0.20 * confidence           # How confident in our approach?
  + 0.15 * resource_coverage    # How much of site can we cover?
  - 0.10 * risk_inverse         # Anti-bot, login required, etc.
```

#### Thresholds

| Score | Action |
|-------|--------|
| >= 0.6 | Proceed to Crawl |
| >= 0.3 | Proceed to Scan (deeper) |
| < 0.3 | Decline |

### 2.5 Agent Manager

#### Agent Lifecycle

```python
class AgentManager:
    """Manages SiteAgent lifecycle"""

    def __init__(self):
        self.agents: Dict[str, SiteAgent] = {}
        self.agent_states: Dict[str, AgentState] = {}

    def create_agent(self, site_url: str, task_params: Dict) -> str:
        """Create new agent instance, return agent_id"""

    def start_agent(self, agent_id: str) -> None:
        """Start agent execution"""

    def cancel_agent(self, agent_id: str, reason: str) -> None:
        """Cancel running agent"""

    def pause_agent(self, agent_id: str) -> None:
        """Pause agent"""

    def resume_agent(self, agent_id: str) -> None:
        """Resume paused agent"""

    def get_agent_status(self, agent_id: str) -> Dict:
        """Get current agent status"""
```

#### Callback Handlers

```python
class Orchestrator:
    """Main orchestrator with callback handlers"""

    def handle_progress(self, agent_id: str, data: Dict) -> None:
        """Handle progress updates from agent"""
        # Update UI, log progress, etc.

    def handle_stuck(self, agent_id: str, reason: str, detail: Dict) -> None:
        """Handle agent stuck event"""
        # Decide whether to:
        # - Let agent continue self-repair
        # - Cancel agent
        # - Modify task and retry

    def handle_result(self, agent_id: str, result: Dict) -> None:
        """Handle final result from agent"""
        # Process and display results
```

---

## 3. Multi-Site Scheduling

### 3.1 Overview

多 Agent 并行模式支持同时爬取多个站点，带资源管理。

### 3.2 Task Queue

```python
class TaskScheduler:
    """Multi-site task scheduler"""

    def __init__(self, config: SchedulerConfig):
        self.queue: Queue[Task] = Queue()
        self.running: Dict[str, SiteAgent] = {}
        self.config = config

    async def schedule(self, tasks: List[Task]) -> None:
        """Schedule multiple tasks"""

    async def run(self) -> None:
        """Execute scheduled tasks with concurrency control"""
```

### 3.3 Concurrency Control

```yaml
# Concurrency configuration
scheduler:
  max_parallel_agents: 3
  max_pages_per_site: 100
  total_page_limit: 500
  agent_timeout_min: 30
```

### 3.4 Resource Allocation

```python
class ResourceAllocator:
    """Allocate resources across agents"""

    def allocate_bandwidth(self, agent_id: str) -> int:
        """Calculate bandwidth allocation per agent"""

    def allocate_tokens(self, agent_id: str) -> int:
        """Calculate token budget per agent"""
```

---

## 4. Status Monitoring

### 4.1 Monitor Overview

```python
class Monitor:
    """Real-time status monitoring"""

    def __init__(self):
        self.metrics: Dict[str, Any] = {}

    def track_progress(self, agent_id: str, progress: ProgressEvent) -> None:
        """Track agent progress"""

    def track_stuck(self, agent_id: str, stuck: StuckEvent) -> None:
        """Track stuck events"""

    def get_dashboard(self) -> Dict:
        """Get current dashboard state"""
```

### 4.2 Dashboard State

```python
{
    "active_agents": int,
    "total_crawled": int,
    "stuck_agents": List[str],
    "recent_events": List[Event],
    "resource_usage": {
        "cpu": float,
        "memory": float,
        "bandwidth": float
    }
}
```

### 4.3 Event Types

| Event | Severity | Action |
|-------|----------|--------|
| `agent_started` | INFO | Log |
| `progress_update` | INFO | Update UI |
| `agent_stuck` | WARNING | Notify user |
| `agent_failed` | ERROR | Alert |
| `agent_completed` | INFO | Summarize |

---

## 5. Result Presentation

### 5.1 Display Manifest

```python
{
    "layout": DisplayLayout,  # article, gallery, video_grid, etc.
    "primary_field": str,     # Main display field
    "preview_field": Optional[str],
    "sort_field": Optional[str],
    "group_by": Optional[str],
    "metadata_fields": List[str]
}
```

### 5.2 Output Artifacts

```
output/{run_id}/
├── result.json          # Crawled records
├── diagnosis.json       # Failure diagnosis (if any)
├── summary.json         # Execution summary
├── decision_card.json   # Decision made by Decide2
└── display_manifest.json # Display configuration
```

### 5.3 Result JSON Structure

```json
{
  "success": true,
  "agent_id": "agent_123",
  "site_url": "https://example.com",
  "records": [
    {
      "url": "https://example.com/article/1",
      "url_hash": "abc123",
      "title": "Article Title",
      "content": "Article content...",
      "metadata": {
        "author": "John Doe",
        "date": "2026-02-20"
      },
      "crawl_timestamp": "2026-02-20T10:30:00Z",
      "strategy_used": "browser"
    }
  ],
  "display_manifest": {
    "layout": "article",
    "primary_field": "title",
    "sort_field": "date"
  },
  "summary": {
    "total_records": 50,
    "duration_sec": 120,
    "strategy_used": "browser",
    "quality_score": 0.85
  }
}
```

---

## 6. Data Storage

### 6.1 Storage Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer Architecture                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │
│  │   Agent     │────▶│   Redis     │────▶│ PostgreSQL  │  │
│  │             │     │  (Hot Data) │     │ (Cold Data) │  │
│  └─────────────┘     └─────────────┘     └─────────────┘  │
│                             │                   │         │
│                             ▼                   ▼         │
│                        ┌──────────┐        ┌──────────┐    │
│                        │ 任务队列  │        │ 持久存储  │    │
│                        │ 实时状态  │        │ 知识库   │    │
│                        │ 去重缓存  │        │ 历史记录 │    │
│                        │ 分布式锁  │        │ 用户配置  │    │
│                        └──────────┘        └──────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Redis (Hot Data)

**Purpose**: In-memory storage for fast access and real-time coordination.

#### Data Structures

| Key Pattern | Type | Purpose | TTL |
|-------------|------|---------|-----|
| `crawl:queue` | List | Task queue (FIFO) | - |
| `crawl:queue:pending` | Sorted Set | Priority queue (score = priority) | - |
| `crawled:urls` | Set | Deduplication (url_hash) | 7d |
| `agent:{agent_id}:state` | Hash | Agent real-time state | 1h |
| `agent:{agent_id}:progress` | Hash | Crawl progress | 1h |
| `lock:site:{site_key}` | String | Distributed lock | 60s |
| `rate_limit:{site_key}` | String | Rate limiting | 60s |
| `progress:global` | Pub/Sub | Real-time updates | - |

#### Usage Examples

```python
import redis

class RedisManager:
    """Redis operations for Orchestrator"""

    def __init__(self, url: str = "redis://localhost:6379"):
        self.redis = redis.from_url(url, decode_responses=True)

    # Task Queue
    def push_task(self, task: Dict, priority: int = 0) -> None:
        """Add task to queue"""
        if priority > 0:
            self.redis.zadd("crawl:queue:pending", {json.dumps(task): priority})
        else:
            self.redis.lpush("crawl:queue", json.dumps(task))

    def pop_task(self) -> Optional[Dict]:
        """Get next task (priority first, then FIFO)"""
        # Try priority queue first
        task = self.redis.zpopmax("crawl:queue:pending")
        if task:
            return json.loads(task[0][0])
        # Fall back to regular queue
        task = self.redis.rpop("crawl:queue")
        return json.loads(task) if task else None

    # Deduplication
    def is_crawled(self, url_hash: str) -> bool:
        """Check if URL already crawled"""
        return self.redis.sismember("crawled:urls", url_hash)

    def mark_crawled(self, url_hash: str) -> None:
        """Mark URL as crawled"""
        self.redis.sadd("crawled:urls", url_hash)

    # Agent State
    def set_agent_state(self, agent_id: str, state: Dict) -> None:
        """Update agent state"""
        self.redis.hset(f"agent:{agent_id}:state", mapping=state)
        self.redis.expire(f"agent:{agent_id}:state", 3600)

    def get_agent_state(self, agent_id: str) -> Dict:
        """Get agent state"""
        return self.redis.hgetall(f"agent:{agent_id}:state")

    # Distributed Lock
    def acquire_lock(self, site_key: str, agent_id: str, ttl: int = 60) -> bool:
        """Acquire lock for site"""
        key = f"lock:site:{site_key}"
        return self.redis.set(key, agent_id, nx=True, ex=ttl)

    def release_lock(self, site_key: str, agent_id: str) -> bool:
        """Release lock (only if owner)"""
        key = f"lock:site:{site_key}"
        lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                redis.call("del", KEYS[1])
                return true
            end
            return false
        """
        return self.redis.eval(lua_script, 1, key, agent_id)
```

#### Redis Configuration

```yaml
# src/orchestrator/config/redis.yaml
redis:
  url: "redis://localhost:6379"
  db: 0
  password: null  # Set in production

  # Connection pool
  pool:
    max_connections: 50
    socket_timeout: 5
    socket_connect_timeout: 5

  # Key expiration
  expiration:
    crawled_urls: 604800  # 7 days
    agent_state: 3600      # 1 hour
    locks: 60              # 1 minute
```

### 6.3 PostgreSQL (Cold Data)

**Purpose**: Persistent storage for results, knowledge base, and historical records.

#### Schema Design

```sql
-- Core table: Crawl results
CREATE TABLE crawl_records (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    url_hash TEXT NOT NULL UNIQUE,
    title TEXT,
    content TEXT,
    metadata JSONB DEFAULT '{}',
    site_key TEXT NOT NULL,
    crawl_timestamp TIMESTAMP DEFAULT NOW(),
    strategy_used TEXT,
    quality_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for common queries
CREATE INDEX idx_crawl_url_hash ON crawl_records(url_hash);
CREATE INDEX idx_crawl_site_key ON crawl_records(site_key);
CREATE INDEX idx_crawl_timestamp ON crawl_records(crawl_timestamp);
CREATE INDEX idx_crawl_metadata ON crawl_records USING GIN(metadata);

-- Site knowledge base
CREATE TABLE site_knowledge (
    site_key TEXT PRIMARY KEY,
    version INTEGER DEFAULT 1,
    last_updated TIMESTAMP DEFAULT NOW(),

    -- Strategy scores
    strategy_scores JSONB DEFAULT '{}',

    -- Effective patterns
    effective_patterns JSONB DEFAULT '[]',

    -- Failure history
    failure_history JSONB DEFAULT '[]',

    -- Site metadata
    anti_bot_measures TEXT[] DEFAULT '{}',
    recommended_strategy TEXT,
    difficulty TEXT
);

-- Crawl tasks (for tracking)
CREATE TABLE crawl_tasks (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL UNIQUE,
    site_url TEXT NOT NULL,
    site_key TEXT NOT NULL,
    intent TEXT,
    status TEXT NOT NULL,  -- pending/running/completed/failed/cancelled

    -- Input
    task_params JSONB DEFAULT '{}',

    -- Output
    result_summary JSONB,

    -- Tracking
    agent_id TEXT,
    error_message TEXT,
    stuck_info JSONB,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Quality
    quality_score FLOAT,
    records_count INTEGER DEFAULT 0
);

CREATE INDEX idx_tasks_status ON crawl_tasks(status);
CREATE INDEX idx_tasks_site ON crawl_tasks(site_key);
CREATE INDEX idx_tasks_created ON crawl_tasks(created_at);

-- Failures log (for analysis)
CREATE TABLE crawl_failures (
    id SERIAL PRIMARY KEY,
    task_id TEXT,
    site_key TEXT,
    url TEXT,
    failure_type TEXT,  -- selector_error/rate_limit/blocked/structure_change

    -- Diagnosis
    error_message TEXT,
    root_cause TEXT,
    suggested_actions TEXT[],

    -- Resolution
    resolution_action TEXT,  -- plugin_update/strategy_switch/patch_apply/terminated
    resolution_successful BOOLEAN,

    -- Timestamp
    occurred_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

CREATE INDEX idx_failures_site ON crawl_failures(site_key);
CREATE INDEX idx_failures_type ON crawl_failures(failure_type);
CREATE INDEX idx_failures_occurred ON crawl_failures(occurred_at);

-- User configurations
CREATE TABLE user_configs (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    config_key TEXT NOT NULL,
    config_value JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, config_key)
);
```

#### Usage Examples

```python
import psycopg
from psycopg import sql
from psycopg.rows import dict_row

class PostgresManager:
    """PostgreSQL operations for Orchestrator"""

    def __init__(self, dsn: str = "postgres://user:pass@localhost/crawler"):
        self.conn = psycopg.connect(dsn, autocommit=True)
        self.conn.cursor_factory = dict_row

    # Crawl Records
    def save_record(self, record: Dict) -> None:
        """Save crawl result"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO crawl_records
                (url, url_hash, title, content, metadata, site_key, strategy_used, quality_score)
                VALUES (%(url)s, %(url_hash)s, %(title)s, %(content)s,
                        %(metadata)s, %(site_key)s, %(strategy_used)s, %(quality_score)s)
                ON CONFLICT (url_hash) DO UPDATE SET
                    title = EXCLUDED.title,
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    crawl_timestamp = NOW()
            """, record)

    def get_records(self, site_key: str, limit: int = 100) -> List[Dict]:
        """Get records for a site"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM crawl_records
                WHERE site_key = %s
                ORDER BY crawl_timestamp DESC
                LIMIT %s
            """, (site_key, limit))
            return cur.fetchall()

    # Site Knowledge
    def get_site_knowledge(self, site_key: str) -> Optional[Dict]:
        """Get site knowledge"""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM site_knowledge WHERE site_key = %s
            """, (site_key,))
            return cur.fetchone()

    def update_site_knowledge(self, site_key: str, updates: Dict) -> None:
        """Update site knowledge"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO site_knowledge (site_key, version, last_updated,
                                            strategy_scores, effective_patterns)
                VALUES (%s, 1, NOW(), %s, %s)
                ON CONFLICT (site_key) DO UPDATE SET
                    version = site_knowledge.version + 1,
                    last_updated = NOW(),
                    strategy_scores = COALESCE(EXCLUDED.strategy_scores, site_knowledge.strategy_scores) || %s::jsonb,
                    effective_patterns = COALESCE(EXCLUDED.effective_patterns, site_knowledge.effective_patterns) || %s::jsonb
            """, (site_key,
                  updates.get('strategy_scores', {}),
                  updates.get('effective_patterns', []),
                  updates.get('strategy_scores', {}),
                  updates.get('effective_patterns', [])))

    # Task tracking
    def create_task(self, task: Dict) -> str:
        """Create new task record"""
        task_id = task.get('task_id') or str(uuid.uuid4())
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO crawl_tasks (task_id, site_url, site_key, intent, task_params, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
                RETURNING task_id
            """, (task_id, task['site_url'], task.get('site_key'),
                  task.get('intent'), json.dumps(task.get('params', {}))))
            return cur.fetchone()['task_id']

    def update_task_status(self, task_id: str, status: str, **kwargs) -> None:
        """Update task status"""
        updates = ['status = %s']
        values = [status]

        if status == 'running':
            updates.append('started_at = NOW()')
        elif status in ['completed', 'failed', 'cancelled']:
            updates.append('completed_at = NOW()')

        for key, value in kwargs.items():
            updates.append(f'{key} = %s')
            values.append(value)

        values.append(task_id)

        with self.conn.cursor() as cur:
            cur.execute(f"""
                UPDATE crawl_tasks SET {', '.join(updates)}
                WHERE task_id = %s
            """, values)
```

#### PostgreSQL Configuration

```yaml
# src/orchestrator/config/postgres.yaml
postgres:
  dsn: "postgres://crawler:password@localhost:5432/crawler"

  # Connection pool
  pool:
    min_connections: 5
    max_connections: 20
    connection_timeout: 10

  # Batch writes (for performance)
  batch:
    enabled: true
    size: 100  # Flush every 100 records
    timeout: 5  # Or every 5 seconds

  # Retention
  retention:
    records_days: 90      # Keep crawl records for 90 days
    failures_days: 30     # Keep failure logs for 30 days
    tasks_days: 60        # Keep task history for 60 days
```

### 6.4 Data Flow

```
Agent Callback                  Redis                    PostgreSQL
─────────────                  ─────                   ───────────
                              │
handle_progress ──────────────▶│─▶ agent:{id}:progress │
                              │                       │
                              │◀── check lock ───────│
handle_stuck ─────────────────▶│─▶ Set alert flag     │
                              │                       │
                              │◀── check rate limit ─│
                              │                       │
handle_result ───────────────▶│─▶ Mark task done     │
                              │         │             │
                              │         ▼             │
                              │    ┌─────────────────┤
                              │    │ Batch queue     │
                              │    └────────┬────────┤
                              │             ▼        │
                              │         (flush)      │
                              │             │        │
                              │             ▼        │
                              │    ┌─────────────────┤
                              │    │ Save records    │
                              │    │ Update knowledge│
                              │    │ Log failures    │
                              │    └─────────────────┘
                              │                       │
```

### 6.5 部署建议

```
┌─────────────────────────────────────────────────────────────┐
│                       存储方案                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              PostgreSQL (必须)                        │   │
│  │  - 爬取结果                                          │   │
│  │  - 站点知识库                                        │   │
│  │  - 任务记录                                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Redis (可选)                             │   │
│  │  - 多 Agent 并行时需要                               │   │
│  │  - 任务队列、状态缓存、分布式锁                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**单 Agent 场景**：只装 PostgreSQL 即可
**多 Agent 并行**：PostgreSQL + Redis

---

## 7. Configuration

### 7.1 Orchestrator Config

```yaml
# src/orchestrator/config.yaml
orchestrator:
  # Decide1 config
  intent_parser:
    min_confidence: 0.7
    llm_model: "GLM-4.7"

  # Scanner config
  scanner:
    timeout_sec: 30
    max_pages_to_scan: 10
    user_agent: "Full-Self-Crawler/1.0"

  # Decide2 config
  feasibility:
    min_composite_score: 0.6
    weights:
      intent_fit: 0.30
      field_completeness: 0.25
      confidence: 0.20
      resource_coverage: 0.15
      risk_inverse: -0.10

  # Agent manager
  agent_manager:
    default_timeout_min: 30
    max_concurrent_agents: 1  # 单 Agent 模式

  # Monitor
  monitor:
    update_interval_sec: 5
    stuck_threshold_sec: 120
```

### 7.2 多 Agent 并行配置

```yaml
scheduler:
  # Concurrency
  max_parallel_agents: 3

  # Resource limits
  max_pages_per_site: 100
  total_page_limit: 500

  # Timeouts
  agent_timeout_min: 30
  task_timeout_min: 60

  # Priority
  priority_queue: true
  preemption_enabled: false
```

---

## Appendix A: Orchestrator State Machine

```
┌────────┐   user_request   ┌─────────────┐
│  Idle  │ ──────────────>  │  Deciding   │
└────────┘                  └─────────────┘
     ▲                            │
     │                            ▼
     │                      ┌───────────┐
     │                      │  Scanning │
     │                      └───────────┘
     │                            │
     │                            ▼
     │                      ┌───────────┐
     │                      │ Feasibility│
     │                      └───────────┘
     │                            │
     │                    ┌───────┴───────┐
     │                    ▼               ▼
     │              ┌──────────┐    ┌──────────┐
     │              │ Approved │    │ Rejected │
     │              └──────────┘    └──────────┘
     │                    │
     │                    ▼
     │              ┌───────────┐
     │              │Executing  │◄──┐
     │              └───────────┘   │
     │                    │         │
     │                    ▼         │
     │              ┌───────────┐   │
     │              │Completed  │───┘
     │              └───────────┘
     │                    │
     └────────────────────┘
```

## Appendix B: Error Handling

| Error | Handler | Recovery |
|-------|---------|----------|
| Invalid intent | Decide1 | Ask user for clarification |
| Site unreachable | Scanner | Report to user, suggest alternatives |
| Agent stuck | Monitor | Allow self-repair, or cancel after timeout |
| Out of resources | Scheduler | Queue task, or reject |

---

**Document Version**: 1.1.0
**Last Updated**: 2026-02-20
