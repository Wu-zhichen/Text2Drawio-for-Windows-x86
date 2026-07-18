import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from app.agent.deepseek import DeepSeekClient
from app.agent.workflow import DiagramAgentWorkflow
from app.skills.loader import FigureSkillLoader


class FakeDeepSeek:
    api_key = "configured"

    def __init__(self) -> None:
        self.planner_prompt = ""
        self.enhancer_prompt = ""

    async def enhance_diagram_prompt(self, _system: str, user: str) -> str:
        self.enhancer_prompt = user
        return "专业增强规格：输入、处理和输出使用从左到右布局。"

    async def create_diagram_ir(self, _system: str, user: str) -> dict:
        self.planner_prompt = user
        return {
            "version": "1.0",
            "diagram_type": "flowchart",
            "title": "Enhanced",
            "direction": "left-to-right",
            "nodes": [
                {"id": "input", "label": "输入", "type": "input"},
                {"id": "output", "label": "输出", "type": "output"},
            ],
            "edges": [{"id": "e1", "source": "input", "target": "output"}],
            "metadata": {},
        }


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_offline_end_to_end_generation(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        workflow = DiagramAgentWorkflow(
            FigureSkillLoader(project_root / ".agents" / "skills" / "figure"),
            DeepSeekClient(api_key="", model="deepseek-chat", base_url="https://api.deepseek.com"),
            allow_offline_fallback=True,
        )
        result = await workflow.run(
            "用户需求 → Agent 规划 → Diagram IR → draw.io 画布",
            use_default_style=True,
        )
        self.assertEqual(len(result.diagram.nodes), 4)
        self.assertEqual(ET.fromstring(result.drawio_xml).tag, "mxfile")
        self.assertTrue(result.warnings)

    async def test_online_prompt_enhancement_precedes_diagram_planning(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        deepseek = FakeDeepSeek()
        workflow = DiagramAgentWorkflow(
            FigureSkillLoader(project_root / ".agents" / "skills" / "figure"),
            deepseek,  # type: ignore[arg-type]
        )
        result = await workflow.run("画一个输入输出图", use_default_style=True)
        self.assertTrue(result.prompt_was_enhanced)
        self.assertIn("专业增强规格", result.enhanced_prompt)
        self.assertIn("专业增强规格", deepseek.planner_prompt)

    async def test_attachment_content_is_grounded_by_enhancer(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        deepseek = FakeDeepSeek()
        workflow = DiagramAgentWorkflow(
            FigureSkillLoader(project_root / ".agents" / "skills" / "figure"),
            deepseek,  # type: ignore[arg-type]
        )
        await workflow.run(
            "根据论文生成总结示意图",
            use_default_style=True,
            attachment_context="<<<ATTACHMENT name=paper.pdf>>>\n论文结论：准确率为92.4%\n<<<END ATTACHMENT>>>",
        )
        self.assertIn("准确率为92.4%", deepseek.enhancer_prompt)
        self.assertNotIn("<<<ATTACHMENT", deepseek.planner_prompt)


if __name__ == "__main__":
    unittest.main()
