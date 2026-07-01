"""工位 3a · 模块选择（JD + 岗类命中率双驱动）。

archetype preset（如 ai_builder.yaml）定义了模块目录、命中率驱动因素、选模块的指引。
工具本身通用；preset 是可替换的领域知识。
"""
import os

import yaml

from llm import LLMClient
from models import JDAnalysis, ModuleSelection

SYS = (
    "你是简历模块选择器。根据 JD 分析、岗位原型、以及'这类岗位什么简历命中率高'，"
    "从给定的模块目录里选模块并排序。再写一句定位（positioning），"
    "点明候选人是什么样的 builder、最匹配这个岗位的哪一点。\n"
    "定位铁律：只能基于候选人材料里真实出现过的能力、工具、项目来写；"
    "严禁把 JD 里出现、但候选人材料里没有的东西套到候选人头上"
    "（例如 JD 提到某工具，但候选人材料里没声明用过，就绝对不能写'会用该工具'）。"
)


class ArchetypePreset:
    def __init__(self, data: dict):
        self.data = data

    @classmethod
    def load(cls, name: str) -> "ArchetypePreset":
        path = os.path.join(os.path.dirname(__file__), "archetypes", f"{name}.yaml")
        with open(path, encoding="utf-8") as f:
            return cls(yaml.safe_load(f))


def select_modules(
    client: LLMClient, preset: ArchetypePreset, jd: JDAnalysis, bg_type: str
) -> ModuleSelection:
    preset_text = yaml.dump(preset.data, allow_unicode=True, sort_keys=False)
    user = (
        f"岗位原型: {jd.archetype_hint}\n"
        f"候选人背景类型: {bg_type}\n"
        f"JD 必须技能: {jd.required_skills}\n"
        f"JD 关键词: {jd.required_keywords}\n\n"
        f"archetype preset（模块目录 + 命中率指引）:\n{preset_text}\n\n"
        "选模块（modules 用 module_catalog 里的 key，按命中优先级排序），并写 positioning。"
    )
    return client.structured(SYS, user, ModuleSelection, temperature=0.2)
