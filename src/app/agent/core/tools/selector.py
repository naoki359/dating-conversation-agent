class ToolSelector:
    def select(self, decided_action: str) -> str:
        text = (decided_action or "").lower()

        if "返信" in decided_action or "reply" in text:
            return "generate_reply"

        return "generate_reply"