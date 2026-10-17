import os
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "AgentMesh AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Graph-Native Multi-Agent Memory & Context Coordination Engine powered by FalkorDB"
    
    FALKORDB_HOST: str = os.getenv("FALKORDB_HOST", "localhost")
    FALKORDB_PORT: int = int(os.getenv("FALKORDB_PORT", "6379"))
    FALKORDB_PASSWORD: str | None = os.getenv("FALKORDB_PASSWORD", None)
    FALKORDB_GRAPH_NAME: str = os.getenv("FALKORDB_GRAPH_NAME", "agentmesh_graph")
    
    # Auto fallback to in-memory graph engine if FalkorDB daemon is not reachable
    AUTO_FALLBACK_LOCAL: bool = os.getenv("AUTO_FALLBACK_LOCAL", "true").lower() in ("true", "1", "yes")
    
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

settings = Settings()
