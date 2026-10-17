// AgentMesh AI Frontend Controller
let cy = null;

const PRESET_QUERIES = {
  ready: `// Find all tasks whose prerequisites are completed in FalkorDB
MATCH (t:Task {status: 'pending'})
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(dep:Task)
WITH t, count(dep) AS total_deps, count(CASE WHEN dep.status = 'completed' THEN 1 END) AS done_deps
WHERE total_deps = done_deps
RETURN t.id AS id, t.title AS title, t.priority AS priority
ORDER BY t.priority DESC`,

  context: `// Extract 2-hop contextual neighborhood for agent prompt injection
MATCH (t:Task)
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(prereq:Task)
OPTIONAL MATCH (d:Decision)-[:RESOLVES]->(prereq)
OPTIONAL MATCH (a:Agent)-[:DISCOVERED]->(m:Memory)
RETURN t.title AS task, collect(DISTINCT prereq.title) AS prereqs, collect(DISTINCT d.outcome) AS past_decisions
LIMIT 5`,

  cycles: `// Cypher multi-hop traversal to detect dependency deadlocks
MATCH p = (t:Task)-[:DEPENDS_ON*1..10]->(t)
RETURN nodes(p) AS cycle_nodes, length(p) AS cycle_length
LIMIT 5`,

  all_tasks: `// Inspect all tasks, their statuses, and assigned agents
MATCH (t:Task)
OPTIONAL MATCH (a:Agent)-[:ASSIGNED_TO]->(t)
RETURN t.id AS id, t.title AS title, t.status AS status, a.name AS agent`,

  decisions: `// Trace decisions made by agents and which tasks they resolved
MATCH (a:Agent)-[:DECIDED]->(d:Decision)-[:RESOLVES]->(t:Task)
RETURN a.name AS agent, d.rationale AS rationale, d.outcome AS outcome, t.title AS task`
};

document.addEventListener("DOMContentLoaded", () => {
  initCytoscape();
  initEventListeners();
  loadGraphData();
  updateStatus();
});

function initCytoscape() {
  cy = cytoscape({
    container: document.getElementById('cy'),
    boxSelectionEnabled: false,
    autounselectify: false,
    style: [
      {
        selector: 'node',
        style: {
          'label': 'data(label)',
          'color': '#f8fafc',
          'font-size': '11px',
          'font-family': 'monospace',
          'text-valign': 'bottom',
          'text-margin-y': 6,
          'text-background-color': '#020617',
          'text-background-opacity': 0.85,
          'text-background-padding': 3,
          'text-background-shape': 'roundrectangle',
          'border-width': 2,
          'transition-property': 'background-color, line-color, target-arrow-color',
          'transition-duration': '0.3s'
        }
      },
      {
        selector: 'node[type = "Agent"]',
        style: {
          'background-color': '#8b5cf6',
          'border-color': '#c4b5fd',
          'shape': 'hexagon',
          'width': 42,
          'height': 42
        }
      },
      {
        selector: 'node[type = "Goal"]',
        style: {
          'background-color': '#f59e0b',
          'border-color': '#fde68a',
          'shape': 'round-diamond',
          'width': 45,
          'height': 45
        }
      },
      {
        selector: 'node[type = "Task"]',
        style: {
          'background-color': '#0284c7',
          'border-color': '#38bdf8',
          'shape': 'round-rectangle',
          'width': 40,
          'height': 32
        }
      },
      {
        selector: 'node[type = "Decision"]',
        style: {
          'background-color': '#ec4899',
          'border-color': '#fbcfe8',
          'shape': 'ellipse',
          'width': 34,
          'height': 34
        }
      },
      {
        selector: 'node[type = "Memory"]',
        style: {
          'background-color': '#14b8a6',
          'border-color': '#99f6e4',
          'shape': 'tag',
          'width': 34,
          'height': 34
        }
      },
      {
        selector: 'edge',
        style: {
          'width': 2,
          'line-color': '#334155',
          'target-arrow-color': '#475569',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'label': 'data(label)',
          'font-size': '9px',
          'font-family': 'monospace',
          'color': '#64748b',
          'text-rotation': 'autorotate',
          'text-background-color': '#020617',
          'text-background-opacity': 0.85,
          'text-background-padding': 2
        }
      },
      {
        selector: 'edge[label = "DEPENDS_ON"]',
        style: {
          'line-color': '#0284c7',
          'target-arrow-color': '#0284c7',
          'line-style': 'solid',
          'color': '#38bdf8'
        }
      },
      {
        selector: 'edge[label = "CONTRADICTS"]',
        style: {
          'line-color': '#ef4444',
          'target-arrow-color': '#ef4444',
          'line-style': 'dashed',
          'width': 3,
          'color': '#f87171'
        }
      },
      {
        selector: 'edge[label = "ASSIGNED_TO"]',
        style: {
          'line-color': '#8b5cf6',
          'target-arrow-color': '#8b5cf6',
          'color': '#c4b5fd'
        }
      }
    ]
  });

  cy.on('tap', 'node', function(evt) {
    const node = evt.target;
    showNodeDetail(node.data());
  });
}

function initEventListeners() {
  document.getElementById("btnStep").addEventListener("click", stepSwarm);
  document.getElementById("btnRunAll").addEventListener("click", runAllSwarm);
  document.getElementById("btnReset").addEventListener("click", resetMission);
  document.getElementById("btnCycle").addEventListener("click", injectCycle);
  document.getElementById("btnFitGraph").addEventListener("click", () => cy.fit(null, 30));

  // Tab switching
  const tabCypherBtn = document.getElementById("tabCypherBtn");
  const tabFeedBtn = document.getElementById("tabFeedBtn");
  const tabMemBtn = document.getElementById("tabMemBtn");
  const tabCypher = document.getElementById("tabCypher");
  const tabFeed = document.getElementById("tabFeed");
  const tabMem = document.getElementById("tabMem");

  tabCypherBtn.addEventListener("click", () => {
    tabCypher.classList.remove("hidden");
    tabFeed.classList.add("hidden");
    tabMem.classList.add("hidden");
    tabCypherBtn.className = "flex-1 py-3 text-center border-b-2 border-violet-500 text-white flex items-center justify-center gap-2";
    tabFeedBtn.className = "flex-1 py-3 text-center text-slate-400 hover:text-white flex items-center justify-center gap-2";
    tabMemBtn.className = "flex-1 py-3 text-center text-slate-400 hover:text-white flex items-center justify-center gap-2";
  });

  tabFeedBtn.addEventListener("click", () => {
    tabCypher.classList.add("hidden");
    tabFeed.classList.remove("hidden");
    tabMem.classList.add("hidden");
    tabCypherBtn.className = "flex-1 py-3 text-center text-slate-400 hover:text-white flex items-center justify-center gap-2";
    tabFeedBtn.className = "flex-1 py-3 text-center border-b-2 border-indigo-500 text-white flex items-center justify-center gap-2";
    tabMemBtn.className = "flex-1 py-3 text-center text-slate-400 hover:text-white flex items-center justify-center gap-2";
  });

  tabMemBtn.addEventListener("click", () => {
    tabCypher.classList.add("hidden");
    tabFeed.classList.add("hidden");
    tabMem.classList.remove("hidden");
    tabCypherBtn.className = "flex-1 py-3 text-center text-slate-400 hover:text-white flex items-center justify-center gap-2";
    tabFeedBtn.className = "flex-1 py-3 text-center text-slate-400 hover:text-white flex items-center justify-center gap-2";
    tabMemBtn.className = "flex-1 py-3 text-center border-b-2 border-teal-500 text-white flex items-center justify-center gap-2";
    loadMemories();
  });

  // Query Preset Dropdown
  const queryPreset = document.getElementById("queryPreset");
  const cypherInput = document.getElementById("cypherInput");
  queryPreset.addEventListener("change", (e) => {
    cypherInput.value = PRESET_QUERIES[e.target.value] || "";
  });
  cypherInput.value = PRESET_QUERIES.ready;

  // Run Query
  document.getElementById("btnRunQuery").addEventListener("click", runCypherQuery);
}

async function loadGraphData() {
  try {
    const res = await fetch("/api/graph/elements");
    const elements = await res.json();
    cy.elements().remove();
    cy.add(elements);

    // Apply special style if task is completed
    cy.nodes('[type = "Task"]').forEach(n => {
      const props = n.data('properties') || {};
      if (props.status === 'completed') {
        n.style('background-color', '#10b981');
        n.style('border-color', '#6ee7b7');
      } else if (props.status === 'in_progress') {
        n.style('background-color', '#f59e0b');
        n.style('border-color', '#fde68a');
      }
    });

    cy.layout({
      name: 'cose',
      idealEdgeLength: 80,
      nodeOverlap: 20,
      refresh: 20,
      fit: true,
      padding: 40,
      randomize: false,
      componentSpacing: 100,
      nodeRepulsion: 400000,
      edgeElasticity: 100,
      nestingFactor: 5,
      gravity: 80,
      numIter: 1000
    }).run();
  } catch (err) {
    console.error("Failed to load graph elements:", err);
  }
}

async function updateStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    document.getElementById("statNodes").innerText = data.node_count;
    document.getElementById("statEdges").innerText = data.edge_count;
    
    // Check ready tasks
    const readyRes = await fetch("/api/tasks/ready");
    const readyTasks = await readyRes.json();
    document.getElementById("statReady").innerText = readyTasks.length;

    const deadlockBadge = document.getElementById("statDeadlock");
    if (data.deadlock_detected) {
      deadlockBadge.innerText = "DETECTED";
      deadlockBadge.className = "text-red-400 font-bold animate-pulse";
    } else {
      deadlockBadge.innerText = "CLEAR";
      deadlockBadge.className = "text-emerald-400 font-bold";
    }

    const engineBadge = document.getElementById("engineBadge");
    if (data.engine_mode === "falkordb_live") {
      engineBadge.innerHTML = `<i class="fa-solid fa-circle text-[8px] animate-pulse text-emerald-400 mr-1"></i> FalkorDB Live`;
      engineBadge.className = "px-2 py-0.5 text-xs font-mono rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30";
    } else {
      engineBadge.innerHTML = `<i class="fa-solid fa-circle text-[8px] animate-pulse text-violet-400 mr-1"></i> Graph Emulation Engine`;
      engineBadge.className = "px-2 py-0.5 text-xs font-mono rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/30";
    }
  } catch (err) {
    console.error("Failed to update status:", err);
  }
}

async function stepSwarm() {
  try {
    const res = await fetch("/api/swarm/step", { method: "POST" });
    const data = await res.json();
    appendActivityLog(data);
    await loadGraphData();
    await updateStatus();
  } catch (err) {
    console.error("Step failed:", err);
  }
}

async function runAllSwarm() {
  try {
    const res = await fetch("/api/swarm/run", { method: "POST" });
    const data = await res.json();
    for (const step of data.history || []) {
      appendActivityLog(step);
    }
    await loadGraphData();
    await updateStatus();
  } catch (err) {
    console.error("Run all failed:", err);
  }
}

async function resetMission() {
  try {
    await fetch("/api/scenarios/reset", { method: "POST" });
    document.getElementById("feedList").innerHTML = `
      <div class="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs text-slate-400">
        Reset to fresh <strong>Zero-Trust Architecture Mission</strong> in FalkorDB.
      </div>
    `;
    await loadGraphData();
    await updateStatus();
  } catch (err) {
    console.error("Reset failed:", err);
  }
}

async function injectCycle() {
  try {
    await fetch("/api/scenarios/cycle", { method: "POST" });
    await loadGraphData();
    await updateStatus();
    appendActivityLog({
      executed: false,
      message: "⚠️ Injected circular dependency into Task graph. Notice DEADLOCK DETECTED indicator in FalkorDB!"
    });
  } catch (err) {
    console.error("Inject cycle failed:", err);
  }
}

async function runCypherQuery() {
  const query = document.getElementById("cypherInput").value;
  const out = document.getElementById("queryOutput");
  const latencyBadge = document.getElementById("queryLatency");
  out.innerText = "Executing Cypher in FalkorDB...";

  try {
    const res = await fetch("/api/graph/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query })
    });
    const data = await res.json();
    latencyBadge.innerText = `${data.latency_ms} ms`;
    out.innerText = JSON.stringify(data.records, null, 2);
  } catch (err) {
    out.innerText = "Error: " + err.message;
  }
}

function showNodeDetail(data) {
  const box = document.getElementById("nodeDetailBox");
  box.classList.remove("hidden");
  document.getElementById("detailBadge").innerText = data.type;
  document.getElementById("detailId").innerText = data.id;

  const props = data.properties || {};
  document.getElementById("detailTitle").innerText = props.title || props.name || props.content || data.id;
  document.getElementById("detailDesc").innerText = props.description || props.rationale || `Role: ${props.role || 'N/A'}`;
  document.getElementById("detailExtra").innerText = JSON.stringify(props, null, 2);
}

function appendActivityLog(step) {
  const feed = document.getElementById("feedList");
  if (!step.executed) {
    feed.insertAdjacentHTML('afterbegin', `
      <div class="p-3 rounded-lg bg-amber-950/40 border border-amber-800/50 text-xs text-amber-200">
        <i class="fa-solid fa-info-circle mr-1 text-amber-400"></i> ${step.message}
      </div>
    `);
    return;
  }

  feed.insertAdjacentHTML('afterbegin', `
    <div class="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1.5">
      <div class="flex items-center justify-between">
        <span class="font-bold text-violet-300 flex items-center gap-1">
          <i class="fa-solid fa-robot text-violet-400"></i> ${step.agent}
        </span>
        <span class="px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-300 font-semibold">COMPLETED</span>
      </div>
      <div class="font-medium text-slate-200">${step.task.title}</div>
      <div class="text-slate-400 text-[11px]">${step.result.decision.outcome}</div>
      <div class="text-[10px] font-mono text-teal-400 border-t border-slate-900 pt-1">
        <i class="fa-solid fa-brain mr-1"></i> ${step.result.memory.content}
      </div>
    </div>
  `);
}

async function loadMemories() {
  try {
    const res = await fetch("/api/memories");
    const memories = await res.json();
    const list = document.getElementById("memoryList");
    list.innerHTML = memories.map(m => `
      <div class="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1">
        <div class="flex items-center justify-between text-[10px] font-mono">
          <span class="text-teal-400 font-bold uppercase">${m.category}</span>
          <span class="text-slate-500">${m.discovered_by || 'Agent'}</span>
        </div>
        <p class="text-slate-200 leading-relaxed">${m.content}</p>
        <div class="text-[10px] font-mono text-slate-500">Confidence: ${Math.round(m.confidence * 100)}%</div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Failed to load memories:", err);
  }
}
