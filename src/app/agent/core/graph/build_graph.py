def build_graph():
    print("build_graph() called")

    class DummyGraph:
        def invoke(self, request):
            print("DummyGraph.invoke() called")
            return {
                "generated_reply": "ダミー返信です（build_graph経由）",
                "reply_reasoning": "graph.invoke() が呼ばれたことを確認",
            }

    return DummyGraph()