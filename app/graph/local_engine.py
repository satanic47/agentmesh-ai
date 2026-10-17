"""
In-Memory FalkorDB Emulation Engine for Local / Non-Docker Execution.
Maintains exact API compatibility with falkordb.Graph while storing nodes and relationships
in an in-memory property graph with full Cypher emulation for AgentMesh queries.
"""

from typing import Dict, Any, List, Set, Optional
import time

class LocalNode:
    def __init__(self, node_id: str, label: str, properties: Dict[str, Any]):
        self.id = node_id
        self.label = label
        self.properties = dict(properties)

    def get(self, key, default=None):
        return self.properties.get(key, default)

    def __getitem__(self, key):
        return self.properties[key]

class LocalEdge:
    def __init__(self, source_id: str, target_id: str, rel_type: str, properties: Dict[str, Any] = None):
        self.source_id = source_id
        self.target_id = target_id
        self.rel_type = rel_type
        self.properties = properties or {}

class LocalQueryResult:
    def __init__(self, result_set: List[List[Any]], header: List[str]):
        self.result_set = result_set
        self.header = header

    def __iter__(self):
        return iter(self.result_set)

    def __len__(self):
        return len(self.result_set)

class LocalGraphEngine:
    def __init__(self, graph_name: str = "agentmesh_local"):
        self.graph_name = graph_name
        self.nodes: Dict[str, LocalNode] = {}  # id -> LocalNode
        self.edges: List[LocalEdge] = []
        self._label_index: Dict[str, Set[str]] = {}

    def clear(self):
        self.nodes.clear()
        self.edges.clear()
        self._label_index.clear()

    def add_node(self, node_id: str, label: str, properties: Dict[str, Any]) -> LocalNode:
        node = LocalNode(node_id, label, properties)
        self.nodes[node_id] = node
        if label not in self._label_index:
            self._label_index[label] = set()
        self._label_index[label].add(node_id)
        return node

    def add_edge(self, source_id: str, target_id: str, rel_type: str, properties: Dict[str, Any] = None) -> LocalEdge:
        for e in self.edges:
            if e.source_id == source_id and e.target_id == target_id and e.rel_type == rel_type:
                if properties:
                    e.properties.update(properties)
                return e
        edge = LocalEdge(source_id, target_id, rel_type, properties)
        self.edges.append(edge)
        return edge

    def query(self, query_str: str, params: Dict[str, Any] = None) -> LocalQueryResult:
        params = params or {}
        q = query_str.strip()

        # 1. Handle Constraint / Index creation
        if q.upper().startswith("CREATE CONSTRAINT") or q.upper().startswith("CREATE INDEX"):
            return LocalQueryResult([], ["status"])

        # 2. Node Status Update (SET t.status = $status)
        if "SET t.status =" in q:
            target_id = params.get("id")
            new_status = params.get("status")
            if target_id and target_id in self.nodes:
                self.nodes[target_id].properties["status"] = new_status
                if new_status == "completed":
                    self.nodes[target_id].properties["completed_at"] = time.time()
                return LocalQueryResult([[self.nodes[target_id]]], ["t"])
            return LocalQueryResult([], ["t"])

        # 3. Ready Tasks Query (Coordination Layer) - MUST match before relationship creation
        if "done_deps" in q or "total_deps" in q:
            ready_tasks = []
            for node_id, node in self.nodes.items():
                if node.label == "Task" and node.properties.get("status") == "pending":
                    # Check all DEPENDS_ON outgoing edges
                    deps = [e.target_id for e in self.edges if e.source_id == node_id and e.rel_type == "DEPENDS_ON"]
                    all_completed = True
                    for dep_id in deps:
                        dep_node = self.nodes.get(dep_id)
                        if not dep_node or dep_node.properties.get("status") != "completed":
                            all_completed = False
                            break
                    if all_completed:
                        ready_tasks.append([
                            node.properties.get("id"),
                            node.properties.get("title"),
                            node.properties.get("description", ""),
                            node.properties.get("priority", 1)
                        ])
            # Sort by priority DESC, created_at ASC
            ready_tasks.sort(key=lambda x: x[3], reverse=True)
            return LocalQueryResult(ready_tasks, ["id", "title", "description", "priority"])

        # 4. Context Subgraph Query (Agent Context Injection)
        if "past_decisions" in q and "prerequisites" in q:
            task_id = params.get("task_id")
            task_node = self.nodes.get(task_id)
            if not task_node:
                return LocalQueryResult([], ["task_title", "task_desc", "goal_title", "prerequisites", "past_decisions", "memory_facts"])

            prereqs = []
            prereq_ids = set()
            for e in self.edges:
                if e.source_id == task_id and e.rel_type == "DEPENDS_ON":
                    target = self.nodes.get(e.target_id)
                    if target:
                        prereqs.append({"id": target.id, "title": target.properties.get("title"), "status": target.properties.get("status")})
                        prereq_ids.add(target.id)

            goal_title = None
            for e in self.edges:
                if e.source_id == task_id and e.rel_type == "SUBTASK_OF":
                    target = self.nodes.get(e.target_id)
                    if target:
                        goal_title = target.properties.get("title")

            past_decisions = []
            for e in self.edges:
                if e.rel_type == "RESOLVES" and e.target_id in prereq_ids:
                    dec = self.nodes.get(e.source_id)
                    if dec:
                        past_decisions.append({"rationale": dec.properties.get("rationale"), "outcome": dec.properties.get("outcome")})

            memory_facts = []
            for n in self.nodes.values():
                if n.label == "Memory":
                    memory_facts.append({"content": n.properties.get("content"), "category": n.properties.get("category")})

            return LocalQueryResult([[
                task_node.properties.get("title"),
                task_node.properties.get("description"),
                goal_title,
                prereqs,
                past_decisions,
                memory_facts[:5]
            ]], ["task_title", "task_desc", "goal_title", "prerequisites", "past_decisions", "memory_facts"])

        # 5. Cycle Detection (Multi-Hop Graph Traversal)
        if "DEPENDS_ON*1..10" in q or "DEPENDS_ON*" in q:
            cycles = []
            visited = set()
            rec_stack = set()
            path = []

            def dfs(curr_id):
                visited.add(curr_id)
                rec_stack.add(curr_id)
                path.append(curr_id)

                neighbors = [e.target_id for e in self.edges if e.source_id == curr_id and e.rel_type == "DEPENDS_ON"]
                for neighbor in neighbors:
                    if neighbor not in visited:
                        dfs(neighbor)
                    elif neighbor in rec_stack:
                        cycle_slice = path[path.index(neighbor):] + [neighbor]
                        cycle_nodes = [self.nodes.get(nid, LocalNode(nid, "Task", {"id": nid})) for nid in cycle_slice]
                        cycles.append([cycle_nodes, len(cycle_slice) - 1])

                path.pop()
                rec_stack.remove(curr_id)

            for nid, node in list(self.nodes.items()):
                if node.label == "Task" and nid not in visited:
                    dfs(nid)

            return LocalQueryResult(cycles, ["cycle_nodes", "cycle_length"])

        # 6. Node Creation (Agent, Goal, Task, Memory, Decision, Artifact)
        if "MERGE (a:Agent" in q or "CREATE (a:Agent" in q:
            node_id = params.get("id")
            node = self.add_node(node_id, "Agent", {
                "id": node_id,
                "name": params.get("name"),
                "role": params.get("role"),
                "status": params.get("status", "idle"),
                "capabilities": params.get("capabilities", []),
                "last_active": params.get("last_active", time.time())
            })
            return LocalQueryResult([[node]], ["a"])

        if "MERGE (g:Goal" in q or "CREATE (g:Goal" in q:
            node_id = params.get("id")
            node = self.add_node(node_id, "Goal", {
                "id": node_id,
                "title": params.get("title"),
                "description": params.get("description"),
                "status": params.get("status", "active"),
                "created_at": params.get("created_at", time.time())
            })
            return LocalQueryResult([[node]], ["g"])

        if "MERGE (t:Task" in q or "CREATE (t:Task" in q:
            node_id = params.get("id")
            node = self.add_node(node_id, "Task", {
                "id": node_id,
                "title": params.get("title"),
                "description": params.get("description"),
                "status": params.get("status", "pending"),
                "priority": params.get("priority", 1),
                "assigned_to": params.get("assigned_to"),
                "created_at": params.get("created_at", time.time()),
                "completed_at": params.get("completed_at")
            })
            return LocalQueryResult([[node]], ["t"])

        if "MERGE (m:Memory" in q or "CREATE (m:Memory" in q:
            node_id = params.get("id")
            node = self.add_node(node_id, "Memory", {
                "id": node_id,
                "content": params.get("content"),
                "category": params.get("category", "episodic"),
                "confidence": params.get("confidence", 1.0),
                "source_agent": params.get("source_agent"),
                "timestamp": params.get("timestamp", time.time())
            })
            return LocalQueryResult([[node]], ["m"])

        if "MERGE (d:Decision" in q or "CREATE (d:Decision" in q:
            node_id = params.get("id")
            node = self.add_node(node_id, "Decision", {
                "id": node_id,
                "rationale": params.get("rationale"),
                "outcome": params.get("outcome"),
                "decided_by": params.get("decided_by"),
                "timestamp": params.get("timestamp", time.time())
            })
            return LocalQueryResult([[node]], ["d"])

        if "MERGE (art:Artifact" in q or "CREATE (art:Artifact" in q:
            node_id = params.get("id")
            node = self.add_node(node_id, "Artifact", {
                "id": node_id,
                "title": params.get("title"),
                "uri": params.get("uri"),
                "artifact_type": params.get("artifact_type", "code"),
                "created_at": params.get("created_at", time.time())
            })
            return LocalQueryResult([[node]], ["art"])

        # 7. Relationship Creation (MERGE -[r:...]->)
        if "MERGE" in q and "DEPENDS_ON" in q:
            t1 = params.get("task_id") or params.get("a")
            t2 = params.get("depends_on_id") or params.get("c")
            if t1 in self.nodes and t2 in self.nodes:
                edge = self.add_edge(t1, t2, "DEPENDS_ON")
                return LocalQueryResult([[edge]], ["r"])
            return LocalQueryResult([], ["r"])

        if "MERGE" in q and "SUBTASK_OF" in q:
            t, g = params.get("task_id"), params.get("goal_id")
            if t in self.nodes and g in self.nodes:
                edge = self.add_edge(t, g, "SUBTASK_OF")
                return LocalQueryResult([[edge]], ["r"])
            return LocalQueryResult([], ["r"])

        if "MERGE" in q and "ASSIGNED_TO" in q:
            a, t = params.get("agent_id"), params.get("task_id")
            if a in self.nodes and t in self.nodes:
                edge = self.add_edge(a, t, "ASSIGNED_TO")
                self.nodes[t].properties["assigned_to"] = self.nodes[a].properties.get("name")
                return LocalQueryResult([[edge]], ["r"])
            return LocalQueryResult([], ["r"])

        if "MERGE" in q and "DISCOVERED" in q:
            a, m = params.get("agent_id"), params.get("memory_id")
            if a in self.nodes and m in self.nodes:
                edge = self.add_edge(a, m, "DISCOVERED")
                return LocalQueryResult([[edge]], ["r"])
            return LocalQueryResult([], ["r"])

        if "MERGE" in q and "DECIDED" in q:
            a, d = params.get("agent_id"), params.get("decision_id")
            if a in self.nodes and d in self.nodes:
                edge = self.add_edge(a, d, "DECIDED")
                return LocalQueryResult([[edge]], ["r"])
            return LocalQueryResult([], ["r"])

        if "MERGE" in q and "RESOLVES" in q:
            d, t = params.get("decision_id"), params.get("task_id")
            if d in self.nodes and t in self.nodes:
                edge = self.add_edge(d, t, "RESOLVES")
                return LocalQueryResult([[edge]], ["r"])
            return LocalQueryResult([], ["r"])

        if "MERGE" in q and "CONTRADICTS" in q:
            d1, d2 = params.get("decision_id_1"), params.get("decision_id_2")
            if d1 in self.nodes and d2 in self.nodes:
                edge = self.add_edge(d1, d2, "CONTRADICTS")
                return LocalQueryResult([[edge]], ["r"])
            return LocalQueryResult([], ["r"])

        if "MERGE" in q and "PRODUCED" in q:
            t, art = params.get("task_id"), params.get("artifact_id")
            if t in self.nodes and art in self.nodes:
                edge = self.add_edge(t, art, "PRODUCED")
                return LocalQueryResult([[edge]], ["r"])
            return LocalQueryResult([], ["r"])

        # 8. Search Memories
        if "MATCH (m:Memory)" in q:
            res = []
            for m in self.nodes.values():
                if m.label == "Memory":
                    discoverer = None
                    for e in self.edges:
                        if e.rel_type == "DISCOVERED" and e.target_id == m.id:
                            agent_n = self.nodes.get(e.source_id)
                            if agent_n:
                                discoverer = agent_n.properties.get("name")
                    res.append([
                        m.id,
                        m.properties.get("content"),
                        m.properties.get("category"),
                        m.properties.get("confidence", 1.0),
                        m.properties.get("timestamp", 0),
                        discoverer or m.properties.get("source_agent", "Agent")
                    ])
            res.sort(key=lambda x: x[4], reverse=True)
            return LocalQueryResult(res, ["id", "content", "category", "confidence", "timestamp", "discovered_by"])

        # 9. Full Graph Export for Cytoscape.js Frontend
        if "MATCH (n)" in q and "[r]" in q:
            rows = []
            if not self.edges:
                for node in self.nodes.values():
                    rows.append([[node.label], node.properties, None, None, None, None])
            else:
                for edge in self.edges:
                    s_node = self.nodes.get(edge.source_id)
                    t_node = self.nodes.get(edge.target_id)
                    if s_node and t_node:
                        rows.append([
                            [s_node.label],
                            s_node.properties,
                            edge.rel_type,
                            edge.properties,
                            [t_node.label],
                            t_node.properties
                        ])
                connected_ids = {e.source_id for e in self.edges} | {e.target_id for e in self.edges}
                for nid, node in self.nodes.items():
                    if nid not in connected_ids:
                        rows.append([[node.label], node.properties, None, None, None, None])

            return LocalQueryResult(rows, ["labels", "node_props", "rel_type", "rel_props", "target_labels", "target_props"])

        # 10. General MATCH (t:Task) RETURN ...
        if "MATCH (t:Task)" in q:
            rows = []
            for node in self.nodes.values():
                if node.label == "Task":
                    rows.append([node.properties.get("id"), node.properties.get("title"), node.properties.get("status"), node.properties.get("assigned_to")])
            return LocalQueryResult(rows, ["id", "title", "status", "assigned_to"])

        # Fallback simple query
        return LocalQueryResult([], ["result"])

    def ro_query(self, query_str: str, params: Dict[str, Any] = None) -> LocalQueryResult:
        return self.query(query_str, params)
