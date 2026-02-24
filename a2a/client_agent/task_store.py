"""In-memory store for tracking A2A Task state."""

import logging
import uuid

from a2a.types import Artifact, Task, TaskArtifactUpdateEvent, TaskState, TaskStatus, TaskStatusUpdateEvent

from .remote import TaskCallbackArg

logger = logging.getLogger(__name__)


class TaskStore:

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._chunks: dict[str, list[Artifact]] = {}

    def update_task(self, event: TaskCallbackArg) -> Task:
        if isinstance(event, TaskStatusUpdateEvent):
            task = self._get_or_create(event.task_id, event.context_id)
            task.status = event.status
        elif isinstance(event, TaskArtifactUpdateEvent):
            task = self._get_or_create(event.task_id, event.context_id)
            self._process_artifact(task, event)
        else:
            task = event  # raw Task
        self._tasks[task.id] = task
        return task

    def _get_or_create(self, task_id: str | None, context_id: str | None) -> Task:
        if task_id and task_id in self._tasks:
            return self._tasks[task_id]
        tid = task_id or str(uuid.uuid4())
        task = Task(id=tid, status=TaskStatus(state=TaskState.submitted), artifacts=[], contextId=context_id)
        self._tasks[tid] = task
        return task

    def _process_artifact(self, task: Task, event: TaskArtifactUpdateEvent):
        artifact = event.artifact
        aid = artifact.artifactId
        if not event.append:
            if event.last_chunk is None or event.last_chunk:
                (task.artifacts or []).append(artifact) if task.artifacts else setattr(task, "artifacts", [artifact])
            else:
                self._chunks.setdefault(aid, []).append(artifact)
        else:
            temp = (self._chunks.get(aid) or [None])[-1]
            if not temp:
                return
            temp.parts.extend(artifact.parts)
            if event.last_chunk:
                (task.artifacts or []).append(temp) if task.artifacts else setattr(task, "artifacts", [temp])
                self._chunks[aid].pop()
