import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.images.generator import NodeImageGenerator
from app.layout.engine import LayoutEngine
from tests.helpers import sample_diagram


class FakeNodeImageGenerator(NodeImageGenerator):
    def _generate_or_cached(self, node, diagram_title: str) -> str:
        return "data:image/webp;base64,AAAA"


class NodeImageGeneratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_unconfigured_generator_falls_back_without_images(self) -> None:
        with TemporaryDirectory() as directory:
            generator = NodeImageGenerator(
                api_key="",
                base_url="https://api.openai.com/v1",
                model="gpt-image-2",
                quality="low",
                max_images=2,
                cache_dir=Path(directory),
            )
            diagram, warnings = await generator.enrich(LayoutEngine().apply(sample_diagram()))
        self.assertTrue(warnings)
        self.assertTrue(all(not node.image_data for node in diagram.nodes))

    async def test_generator_limits_images_to_major_nodes(self) -> None:
        with TemporaryDirectory() as directory:
            generator = FakeNodeImageGenerator(
                api_key="test",
                base_url="https://api.openai.com/v1",
                model="gpt-image-2",
                quality="low",
                max_images=2,
                cache_dir=Path(directory),
            )
            diagram, warnings = await generator.enrich(LayoutEngine().apply(sample_diagram()))
        illustrated = [node for node in diagram.nodes if node.image_data]
        self.assertEqual(len(illustrated), 2)
        self.assertTrue(warnings)
        self.assertTrue(all(node.width >= 260 and node.height >= 110 for node in illustrated))


if __name__ == "__main__":
    unittest.main()
