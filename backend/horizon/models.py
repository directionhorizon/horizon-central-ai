"""Modèles Pydantic des contrats exposés par les nouveaux routeurs.

Les noms de champs suivent le style déjà utilisé par `app.py` (snake_case).
Aucun modèle ne contient de secret : les clés API ne sont référencées que par
le nom de la variable d'environnement qui les contient (`api_key_env`).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ProjectStatus = Literal["active", "paused", "archived"]
OrchestratorStatus = Literal["active", "inactive", "disabled"]
HealthStatus = Literal["unverified", "available", "unavailable", "degraded"]
MissionStatus = Literal["draft", "planned", "running", "paused", "completed", "failed", "cancelled"]
StepStatus = Literal["pending", "running", "completed", "failed", "skipped"]
Priority = Literal["low", "normal", "high", "critical"]


# --- Projets ---------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=4000)
    status: ProjectStatus = "active"


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=4000)
    status: ProjectStatus | None = None


# --- Orchestrateurs --------------------------------------------------------

class CapabilityCreate(BaseModel):
    capability_id: str = Field(min_length=1, max_length=120)
    level: str = Field(default="standard", max_length=40)
    detail: str = Field(default="", max_length=2000)


class OrchestratorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    kind: str = Field(default="local", max_length=60)
    description: str = Field(default="", max_length=4000)
    endpoint: str = Field(default="", max_length=500)
    version: str = Field(default="", max_length=60)
    status: OrchestratorStatus = "active"
    config: dict = Field(default_factory=dict)
    capabilities: list[CapabilityCreate] = Field(default_factory=list)


class OrchestratorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    kind: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=4000)
    endpoint: str | None = Field(default=None, max_length=500)
    version: str | None = Field(default=None, max_length=60)
    status: OrchestratorStatus | None = None
    config: dict | None = None


class OrchestratorProjectLink(BaseModel):
    project_id: str = Field(min_length=1)
    role: str = Field(default="member", max_length=60)


class OrchestratorModelSelection(BaseModel):
    provider_id: str = Field(min_length=1)
    model: str = Field(min_length=1, max_length=200)


# --- Agents (concept générique, tous les systèmes d'orchestration) -----------

AgentRole = Literal["orchestrator", "specialist"]


class AgentCreate(BaseModel):
    orchestrator_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=160)
    role: AgentRole = "specialist"
    description: str = Field(default="", max_length=4000)
    spec: str = Field(default="", max_length=8000)


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    role: AgentRole | None = None
    description: str | None = Field(default=None, max_length=4000)
    spec: str | None = Field(default=None, max_length=8000)
    status: Literal["active", "inactive"] | None = None


class ToolRun(BaseModel):
    """Exécution d'une main (outil) avec ses paramètres."""

    params: dict = Field(default_factory=dict)
    agent_id: str | None = None


class PaymentCreate(BaseModel):
    """Création d'un paiement. La validation humaine est obligatoire.

    `provider` choisit l'adaptateur (registre ouvert) ; `mode` distingue une
    intention de paiement, une page de paiement hébergée et l'enregistrement
    d'un moyen de paiement. Aucune donnée bancaire n'est jamais transmise ici.
    """

    amount: int = Field(gt=0, description="Montant en plus petite unité (ex. centimes).")
    currency: str = Field(default="eur", min_length=3, max_length=3)
    confirm: bool = False
    detail: str = Field(default="", max_length=500)
    provider: str = Field(default="", max_length=40, description="Adaptateur choisi.")
    mode: Literal["intent", "checkout", "setup"] = "intent"
    account: str = Field(default="", max_length=120, description="Connexion du registre.")
    customer_email: str = Field(default="", max_length=200)
    customer_name: str = Field(default="", max_length=200)
    success_url: str = Field(default="", max_length=500)
    cancel_url: str = Field(default="", max_length=500)


class MCPServerCreate(BaseModel):
    """Enregistrement d'un serveur MCP (transport stdio)."""

    name: str = Field(min_length=1, max_length=120)
    command: str = Field(min_length=1, max_length=500)
    args: list[str] = Field(default_factory=list)
    enabled: bool = True


# --- Missions --------------------------------------------------------------

class MissionCreate(BaseModel):
    project_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=8000)
    priority: Priority = "normal"
    orchestrator_id: str | None = None


class MissionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=8000)
    status: MissionStatus | None = None
    priority: Priority | None = None
    orchestrator_id: str | None = None


class MissionStepCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    position: int | None = Field(default=None, ge=0)
    assigned_orchestrator_id: str | None = None


class MissionStepUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    status: StepStatus | None = None
    assigned_orchestrator_id: str | None = None
    error: str | None = Field(default=None, max_length=4000)


class CheckpointCreate(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    step_id: str | None = None
    state: dict = Field(default_factory=dict)


# --- Exécution CORE ↔ Hermes -----------------------------------------------

class DispatchRequest(BaseModel):
    """Lance l'exécution réelle d'une mission via l'orchestrateur pilote.

    `step_id` est optionnel : sans étape, toute la mission est envoyée.
    """
    step_id: str | None = None
    orchestrator_id: str | None = None


class ApprovalRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=300)
    execution_generation: int = Field(ge=0)
    choice: Literal["once", "deny"]


class ClarifyRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=300)
    execution_generation: int = Field(ge=0)
    answer: str = Field(min_length=1, max_length=4000)


# --- Fournisseurs LLM ------------------------------------------------------

class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(min_length=1, max_length=500)
    kind: str = Field(default="openai_compatible", max_length=60)
    api_key_env: str = Field(default="", max_length=120)
    default_model: str = Field(default="", max_length=200)


class ProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    base_url: str | None = Field(default=None, min_length=1, max_length=500)
    kind: str | None = Field(default=None, max_length=60)
    api_key_env: str | None = Field(default=None, max_length=120)
    default_model: str | None = Field(default=None, max_length=200)


class ModelSelectionUpdate(BaseModel):
    mode: Literal["auto", "manual"] = "auto"
    provider_id: str | None = None
    model: str | None = Field(default=None, max_length=200)


# --- Mémoire documentaire --------------------------------------------------

class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(default="", max_length=200000)
    project_id: str | None = None
    tags: str = Field(default="", max_length=600)
    source: str = Field(default="", max_length=600)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    content: str | None = Field(default=None, max_length=200000)
    project_id: str | None = None
    tags: str | None = Field(default=None, max_length=600)
    source: str | None = Field(default=None, max_length=600)


# --- Bibliothèque de skills (compétences) ----------------------------------

class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(default="general", max_length=120)
    subcategory: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=4000)
    level: str = Field(default="standard", max_length=40)
    tags: str = Field(default="", max_length=400)
    status: Literal["active", "disabled"] = "active"
    origin: str = Field(default="manual", max_length=40)
    source_url: str = Field(default="", max_length=600)
    author: str = Field(default="", max_length=200)
    license: str = Field(default="", max_length=200)
    usage: str = Field(default="", max_length=2000)
    outputs: str = Field(default="", max_length=2000)
    example: str = Field(default="", max_length=2000)


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    category: str | None = Field(default=None, max_length=120)
    subcategory: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    level: str | None = Field(default=None, max_length=40)
    tags: str | None = Field(default=None, max_length=400)
    status: Literal["active", "disabled"] | None = None
    origin: str | None = Field(default=None, max_length=40)
    source_url: str | None = Field(default=None, max_length=600)
    author: str | None = Field(default=None, max_length=200)
    license: str | None = Field(default=None, max_length=200)
    usage: str | None = Field(default=None, max_length=2000)
    outputs: str | None = Field(default=None, max_length=2000)
    example: str | None = Field(default=None, max_length=2000)


class SkillAttach(BaseModel):
    skill_id: str = Field(min_length=1)


class SkillImportRequest(BaseModel):
    """Import sécurisé : bundle JSON, URL d'une source autorisée, ou paquet npm/PyPI."""

    url: str | None = Field(default=None, max_length=1000)
    bundle: list[dict] = Field(default_factory=list)
    origin: str = Field(default="github", max_length=40)
    #: Source paquet : "npm" ou "pypi". `package` = nom du paquet.
    source: str | None = Field(default=None, max_length=20)
    package: str | None = Field(default=None, max_length=214)
