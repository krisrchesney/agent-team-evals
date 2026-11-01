from dataclasses import dataclass


@dataclass
class Project:
    id: str
    name: str
    archived: bool
    created_at: object


@dataclass
class Member:
    id: str
    name: str
    email: str            # always lower case


@dataclass
class Label:
    name: str             # always lower case
    color: str


@dataclass
class Task:
    id: str
    project: str
    title: str
    status: str
    assignee: str         # member id or None
    labels: tuple         # label names, sorted
    due: object           # a date or None
    priority: int
    created_at: object
    updated_at: object


@dataclass
class Comment:
    id: str
    task: str
    author: str           # member id
    text: str
    created_at: object
