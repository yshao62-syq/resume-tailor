"""数据模型（pydantic）。整个系统的结构化骨架。

scope-bound（边界受控）的核心在 Experience：每条经历自带 facts 列表，
改写时只能引用自己的 facts，跨条引用由 verifier 拦截。
"""
from pydantic import BaseModel, Field


class AtomicFact(BaseModel):
    """原子事实：claim 级别的一句话，必须能被经历原文直接支持。"""
    fact: str = Field(description="原子事实，claim 级别，必须能被经历原文支持")
    is_metric: bool = False


class Experience(BaseModel):
    """一段经历 = 一个带锁的容器。facts 进来后就被锁定到这个 id。"""
    id: str
    type: str = "work"           # work | practice | community
    role: str = ""
    org: str = ""
    dates: str = ""
    original_text: str
    facts: list[AtomicFact] = Field(default_factory=list)


class FactList(BaseModel):
    facts: list[AtomicFact]


class JDAnalysis(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    required_keywords: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    archetype_hint: str = "general"   # ai_builder_product | ai_builder_tech | general


class ModuleSelection(BaseModel):
    modules: list[str] = Field(default_factory=list)   # 选中的模块 key，按顺序
    positioning: str = ""                                # 一句定位
    rationale: str = ""


class Bullet(BaseModel):
    text: str
    source_facts: list[str] = Field(default_factory=list, description="这条 bullet 基于的原子事实（原文片段）")


class RewriteResult(BaseModel):
    experience_id: str
    bullets: list[Bullet] = Field(default_factory=list)


class VerifierVerdict(BaseModel):
    experience_id: str
    clean: bool
    violations: list[str] = Field(default_factory=list)   # 每条违规的具体描述
    reasoning: str = ""
