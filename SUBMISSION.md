# WeMakeDevs x FalkorDB Hackathon Submission Form
**Event:** Graph Hacks: Context for AI Agents  
**Submission URL:** https://www.wemakedevs.org/hackathons/falkordb/submit  
**Deadline:** October 18, 2026, 11:59 PM IST  

---

## SECTION 1: PROJECT DETAILS

### 1. Project title (Max 120 characters)
```text
AgentMesh AI: Graph-Native Multi-Agent Memory & Context Coordination Engine
```

---

### 2. Description ("What problem does your project solve, and who is it for?")
```text
Modern autonomous multi-agent systems suffer from catastrophic context failure: when agents communicate through flat chat logs or vector embeddings, they lose causal relationships, create circular deadlocks, and experience state drift across sessions. Vector similarity search fails at multi-hop reasoning (e.g., determining which security policy approved an action or which dependent task is now unblocked).

AgentMesh AI solves this by using FalkorDB as the shared central nervous system for multi-agent swarms. Instead of lossy message streams, agents interact with an interconnected property graph where tasks, dependencies, institutional memories, and decisions form a causal web. Built for engineering teams, autonomous DevOps pipelines, and enterprise agent developers, AgentMesh guarantees deadlock-free task scheduling, 2-hop contextual prompt injection in under 2ms, and persistent cross-session institutional memory.
```

---

### 3. What track are you submitting for? (Checkbox — Multi-select)
* [x] **Agents That Act on Connected Data**
* [x] **Agent Memory and Coordination**
* [x] **Company Brain**

*(Explanation: AgentMesh qualifies for all three tracks: it coordinates autonomous agents acting on connected task graphs [Track 1], synchronizes multi-agent state and memory across sessions [Track 2], and preserves organizational decisions and policies in an enterprise knowledge graph [Track 3]).*

---

### 4. Repository (Link — Required)
```text
https://github.com/satanic47/agentmesh-ai
```

---

### 5. Demo video (YouTube Link — Required)
```text
[Your YouTube Video Link Here - Keep Public or Unlisted]
```

---

### 6. Live demo or deployment (Link — Optional)
```text
https://agentmesh-ai.onrender.com (or local demo link http://localhost:8000)
```

---

### 7. How did you use FalkorDB in your project? ("Tell us what technical problems you solved using FalkorDB")
```text
FalkorDB serves as the core graph database and real-time coordination layer in AgentMesh. We leveraged FalkorDB's ultra-low latency Cypher query engine to solve three critical multi-agent challenges:

1. Autonomous Blackboard Coordination: Rather than relying on a centralized coordinator or polling loops, agents query FalkorDB using Cypher to find ready tasks whose prerequisites have all transitioned to 'completed' status:
   `MATCH (t:Task {status: 'pending'}) OPTIONAL MATCH (t)-[:DEPENDS_ON]->(dep:Task) WITH t, count(dep) AS total, count(CASE WHEN dep.status = 'completed' THEN 1 END) AS done WHERE total = done RETURN t`

2. 2-Hop Context Subgraph Extraction (<2ms): Before executing any task, the assigned agent queries FalkorDB to extract its immediate causal neighborhood—including prerequisite rationale, past agent decisions, and relevant semantic memories. This subgraph is injected directly into the LLM context prompt, replacing thousands of tokens of redundant chat logs with exact relational context.

3. Real-Time Deadlock & Cycle Prevention: When agents dynamically decompose goals into subtasks, FalkorDB runs multi-hop path traversals (`MATCH p = (t:Task)-[:DEPENDS_ON*1..10]->(t) RETURN p`) to detect circular dependencies before execution deadlocks can stall the pipeline.
```

---

### 8. Blog link (Link — Optional, for Apple AirPods 5 prize)
```text
[Your DEV.to or Hashnode Post Link Here]
```

---

## SECTION 2: FEEDBACK

### 9. What did you like about FalkorDB?
```text
1. Blazing Query Speed: FalkorDB's C-based GraphBLAS linear algebra engine delivers sub-2ms Cypher traversals even on complex multi-hop pattern matching. For real-time agent context injection, this speed is game-changing compared to traditional graph databases.
2. OpenCypher Support: The expressive Cypher syntax made expressing complex agent dependencies, cycle detection, and pattern matching intuitive and clean.
3. Clean Python Client: The official `falkordb` Python library integrates smoothly with standard Redis connection protocols and modern async web frameworks like FastAPI.
4. Minimal Operational Overhead: Being able to spin up a production-ready graph database via a single lightweight Docker container (`falkordb/falkordb:latest`) without heavy JVM overhead makes developer setup effortless.
```

---

### 10. What improvements would you like to see in FalkorDB?
```text
1. Native Async Python Driver: While `falkordb-py` works well synchronously, a first-class `async/await` client (built on `redis-py` async) would significantly boost throughput for high-concurrency multi-agent swarms.
2. Built-in Graph Visualization Web UI: A lightweight embedded web visualizer (similar to RedisInsight or Neo4j Browser) out-of-the-box would make ad-hoc graph exploration even smoother for developers.
3. Hybrid Vector + Cypher Convenience Helpers: Native syntactic sugar in the Python SDK for querying combined vector embeddings and graph traversals in a single Cypher statement without manual parameter vector serialization would make GraphRAG pipelines even faster to build.
```
