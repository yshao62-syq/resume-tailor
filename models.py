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


# --- 提问式挖掘（miner）---
class MiningQuestion(BaseModel):
    """基于 JD 差距生成的一道追问，挖出候选人没主动讲的材料。"""
    target_skill: str = Field(default="", description="这道题想补的 JD 必须 skill / 关键词")
    question: str = Field(description="问候选人的问题，具体、可答，引导讲真实做过的事 + 数字")
    why: str = Field(default="", description="为什么问：哪个 JD 要求 + 当前材料缺什么")


class MiningResult(BaseModel):
    questions: list[MiningQuestion] = Field(default_factory=list)


# --- narrative synthesis（主线推断 + 取舍）---
class NarrativeDecision(BaseModel):
    """对单条经历的取舍。"""
    experience_id: str
    emphasis: str = Field(description="heavy | light | drop")
    reason: str = ""


class Narrative(BaseModel):
    """推断出的职业主线 + 定位 + 每条经历取舍。"""
    mainline: str = Field(description="从所有经历真实事实推断出的贯穿职业主线（故事线）")
    positioning: str = Field(default="", description="适配 JD 的一句定位")
    decisions: list[NarrativeDecision] = Field(default_factory=list)
    rationale: str = ""


# --- 压力测试（stress-test）---
class StressTestResult(BaseModel):
    """对一条 bullet 的 stress-test 结论。"""
    bullet: str
    hardest_question: str = Field(description="面试官会问的最难追问")
    holds: bool = Field(description="在现有锁定事实下能否 defend 住")
    weakness: str = Field(default="", description="逻辑薄弱点：自相矛盾 / 证据不足 / 过度拔高 / 因果跳跃")
    suggestion: str = Field(default="", description="怎么改更严密")


class StressTestVerdict(BaseModel):
    experience_id: str
    results: list[StressTestResult] = Field(default_factory=list)
    overall: str = Field(default="", description="这条经历整体逻辑严密度评估")
