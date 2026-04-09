import json
import asyncio

from services.post_service import send_post_async

class QueueService:
    def __init__(self, repo, post_service):
        self.repo = repo
        self.post_service = post_service

    async def process_task(self, task):
        task_id = task["id"]
        payload = json.loads(task["payload"])
        attempts = task["attempts"]

        try:
            self.repo.mark_processing(task_id)

            if task["action"] == "send_post":
                import uuid
                session_id = str(uuid.uuid4())

                await send_post_async(session_id, payload)

            elif task["action"] == "edit_post":
                await self.post_service.edit_post(payload)

            self.repo.mark_success(task_id)

        except Exception as e:
            attempts += 1
            self.repo.mark_error(task_id, str(e), attempts)