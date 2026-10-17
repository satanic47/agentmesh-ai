"""
Cypher Query Catalog for AgentMesh on FalkorDB
Contains optimized Cypher queries for agent memory, coordination, and graph traversal.
"""

# Initialize Constraints and Indexes in FalkorDB
INIT_INDEXES = [
    "CREATE CONSTRAINT FOR (a:Agent) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT FOR (g:Goal) REQUIRE g.id IS UNIQUE",
    "CREATE CONSTRAINT FOR (t:Task) REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT FOR (m:Memory) REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT FOR (d:Decision) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT FOR (art:Artifact) REQUIRE art.id IS UNIQUE",
    "CREATE INDEX FOR (t:Task) ON (t.status)",
    "CREATE INDEX FOR (m:Memory) ON (m.category)",
]

# Create Nodes
CREATE_AGENT = """
MERGE (a:Agent {id: $id})
SET a.name = $name,
    a.role = $role,
    a.status = $status,
    a.capabilities = $capabilities,
    a.last_active = $last_active
RETURN a
"""

CREATE_GOAL = """
MERGE (g:Goal {id: $id})
SET g.title = $title,
    g.description = $description,
    g.status = $status,
    g.created_at = $created_at
RETURN g
"""

CREATE_TASK = """
MERGE (t:Task {id: $id})
SET t.title = $title,
    t.description = $description,
    t.status = $status,
    t.priority = $priority,
    t.assigned_to = $assigned_to,
    t.created_at = $created_at,
    t.completed_at = $completed_at
RETURN t
"""

CREATE_MEMORY = """
MERGE (m:Memory {id: $id})
SET m.content = $content,
    m.category = $category,
    m.confidence = $confidence,
    m.source_agent = $source_agent,
    m.timestamp = $timestamp
RETURN m
"""

CREATE_DECISION = """
MERGE (d:Decision {id: $id})
SET d.rationale = $rationale,
    d.outcome = $outcome,
    d.decided_by = $decided_by,
    d.timestamp = $timestamp
RETURN d
"""

CREATE_ARTIFACT = """
MERGE (art:Artifact {id: $id})
SET art.title = $title,
    art.uri = $uri,
    art.artifact_type = $artifact_type,
    art.created_at = $created_at
RETURN art
"""

# Create Relationships
LINK_DEPENDENCY = """
MATCH (t1:Task {id: $task_id}), (t2:Task {id: $depends_on_id})
MERGE (t1)-[r:DEPENDS_ON]->(t2)
RETURN r
"""

LINK_SUBTASK = """
MATCH (t:Task {id: $task_id}), (g:Goal {id: $goal_id})
MERGE (t)-[r:SUBTASK_OF]->(g)
RETURN r
"""

LINK_AGENT_TASK = """
MATCH (a:Agent {id: $agent_id}), (t:Task {id: $task_id})
MERGE (a)-[r:ASSIGNED_TO]->(t)
SET t.assigned_to = a.name
RETURN r
"""

LINK_AGENT_MEMORY = """
MATCH (a:Agent {id: $agent_id}), (m:Memory {id: $memory_id})
MERGE (a)-[r:DISCOVERED]->(m)
RETURN r
"""

LINK_AGENT_DECISION = """
MATCH (a:Agent {id: $agent_id}), (d:Decision {id: $decision_id})
MERGE (a)-[r:DECIDED]->(d)
RETURN r
"""

LINK_DECISION_TASK = """
MATCH (d:Decision {id: $decision_id}), (t:Task {id: $task_id})
MERGE (d)-[r:RESOLVES]->(t)
RETURN r
"""

LINK_DECISION_CONTRADICTION = """
MATCH (d1:Decision {id: $decision_id_1}), (d2:Decision {id: $decision_id_2})
MERGE (d1)-[r:CONTRADICTS]->(d2)
RETURN r
"""

LINK_TASK_ARTIFACT = """
MATCH (t:Task {id: $task_id}), (art:Artifact {id: $artifact_id})
MERGE (t)-[r:PRODUCED]->(art)
RETURN r
"""

# Query Ready Tasks (Coordination Layer)
# Retrieves all pending tasks that either have NO dependencies or all dependencies are 'completed'
GET_READY_TASKS = """
MATCH (t:Task {status: 'pending'})
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(dep:Task)
WITH t, count(dep) AS total_deps, count(CASE WHEN dep.status = 'completed' THEN 1 END) AS done_deps
WHERE total_deps = done_deps
RETURN t.id AS id, t.title AS title, t.description AS description, t.priority AS priority
ORDER BY t.priority DESC, t.created_at ASC
"""

# Context Subgraph Extraction for Agent LLM Injection
# Retrieves 2-hop connected neighborhood: tasks, prerequisites, resolved decisions, and discovered facts
GET_TASK_CONTEXT_SUBGRAPH = """
MATCH (t:Task {id: $task_id})
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(prereq:Task)
OPTIONAL MATCH (t)-[:SUBTASK_OF]->(g:Goal)
OPTIONAL MATCH (d:Decision)-[:RESOLVES]->(prereq)
OPTIONAL MATCH (a:Agent)-[:ASSIGNED_TO]->(prereq)
OPTIONAL MATCH (a)-[:DISCOVERED]->(m:Memory)
RETURN t.title AS task_title,
       t.description AS task_desc,
       g.title AS goal_title,
       collect(DISTINCT {id: prereq.id, title: prereq.title, status: prereq.status}) AS prerequisites,
       collect(DISTINCT {rationale: d.rationale, outcome: d.outcome}) AS past_decisions,
       collect(DISTINCT {content: m.content, category: m.category}) AS memory_facts
"""

# Deadlock and Cycle Detection (Cypher Multi-Hop Traversal)
DETECT_CYCLES = """
MATCH p = (t:Task)-[:DEPENDS_ON*1..10]->(t)
RETURN nodes(p) AS cycle_nodes, length(p) AS cycle_length
LIMIT 5
"""

# Full Graph Extraction for Frontend Visualizer
GET_FULL_GRAPH = """
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
RETURN labels(n) AS labels, 
       properties(n) AS node_props, 
       type(r) AS rel_type, 
       properties(r) AS rel_props, 
       labels(m) AS target_labels, 
       properties(m) AS target_props
"""

# Cross-Session Memory Search
SEARCH_MEMORIES = """
MATCH (m:Memory)
OPTIONAL MATCH (a:Agent)-[:DISCOVERED]->(m)
RETURN m.id AS id, m.content AS content, m.category AS category, 
       m.confidence AS confidence, m.timestamp AS timestamp, 
       a.name AS discovered_by
ORDER BY m.timestamp DESC
LIMIT 50
"""
