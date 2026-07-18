from app.diagram.ir import DiagramIR


def sample_diagram() -> DiagramIR:
    return DiagramIR.from_dict(
        {
            "version": "1.0",
            "diagram_type": "pipeline",
            "title": "Test Pipeline",
            "direction": "left-to-right",
            "nodes": [
                {"id": "input", "label": "Input", "type": "input"},
                {"id": "plan", "label": "Plan", "type": "process"},
                {"id": "result", "label": "Result", "type": "output"},
            ],
            "edges": [
                {"id": "e1", "source": "input", "target": "plan", "kind": "main"},
                {"id": "e2", "source": "plan", "target": "result", "kind": "main"},
                {
                    "id": "feedback",
                    "source": "result",
                    "target": "plan",
                    "label": "Retry",
                    "kind": "feedback",
                },
            ],
        }
    )

