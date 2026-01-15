"""
State management for recovery.

Enables system restoration after failures through state persistence.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import aiofiles

from llm_guardian.core.exceptions import (
    CheckpointLoadError,
    CheckpointNotFoundError,
    CheckpointSaveError,
)
from llm_guardian.core.models import RequestContext, StateSnapshot


class StateManager:
    """
    Manage state persistence and recovery.

    Enables system restoration after failures by saving checkpoints.
    """

    def __init__(self, storage_path: Path):
        """
        Initialize state manager.

        Args:
            storage_path: Path to store checkpoint files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def save_checkpoint(
        self,
        request_id: str,
        context: RequestContext,
        checkpoint_data: Dict[str, Any],
    ) -> str:
        """
        Save checkpoint for recovery.

        Args:
            request_id: Request identifier
            context: Request context
            checkpoint_data: Additional data to checkpoint

        Returns:
            Checkpoint ID (same as request_id)

        Raises:
            CheckpointSaveError: If save fails
        """
        try:
            snapshot = {
                "snapshot_id": request_id,
                "request_context": context.model_dump(),
                "checkpoint_data": checkpoint_data,
                "timestamp": context.timestamp.isoformat(),
            }

            file_path = self.storage_path / f"{request_id}.json"

            async with aiofiles.open(file_path, "w") as f:
                await f.write(json.dumps(snapshot, indent=2))

            return request_id

        except Exception as e:
            raise CheckpointSaveError(
                f"Failed to save checkpoint: {e}", details={"request_id": request_id}
            ) from e

    async def load_checkpoint(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint for recovery.

        Args:
            request_id: Request identifier

        Returns:
            Checkpoint data or None if not found

        Raises:
            CheckpointLoadError: If load fails
        """
        file_path = self.storage_path / f"{request_id}.json"

        if not file_path.exists():
            return None

        try:
            async with aiofiles.open(file_path, "r") as f:
                data = await f.read()
                return json.loads(data)

        except Exception as e:
            raise CheckpointLoadError(
                f"Failed to load checkpoint: {e}", details={"request_id": request_id}
            ) from e

    async def delete_checkpoint(self, request_id: str) -> bool:
        """
        Delete checkpoint file.

        Args:
            request_id: Request identifier

        Returns:
            True if deleted, False if not found
        """
        file_path = self.storage_path / f"{request_id}.json"

        if file_path.exists():
            file_path.unlink()
            return True
        return False
