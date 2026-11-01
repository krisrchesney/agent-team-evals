from dataclasses import dataclass, field


@dataclass(frozen=True)
class Context:
    """Who is asking. `user_id` may be missing for anonymous visitors."""
    user_id: object = None
    attrs: dict = field(default_factory=dict)

    def user_key(self):
        if self.user_id is None:
            return None
        key = str(self.user_id).strip()
        return key or None
