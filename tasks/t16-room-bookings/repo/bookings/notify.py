"""Messages to users are collected in an outbox."""
from .models import Message


class Outbox:
    def __init__(self):
        self.messages = []

    def send(self, user_id, subject, body):
        self.messages.append(Message(user_id, subject, body))

    def for_user(self, user_id):
        return [m for m in self.messages if m.user_id == user_id]
