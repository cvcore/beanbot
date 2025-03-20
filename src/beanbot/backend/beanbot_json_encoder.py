from fastapi.responses import JSONResponse
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any


class BeanbotJSONEncoder:
    """Custom JSON encoder for Beancount-specific types."""

    @staticmethod
    def encode(obj: Any) -> Any:
        """Convert special types to JSON-serializable formats."""
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, set):
            return list(obj)
        elif hasattr(obj, "model_dump"):
            # For Pydantic models
            return obj.model_dump()
        elif isinstance(obj, dict):
            return {k: BeanbotJSONEncoder.encode(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [BeanbotJSONEncoder.encode(item) for item in obj]
        return obj


class BeanbotJSONResponse(JSONResponse):
    """Custom JSON response class that handles Beancount-specific types."""

    def render(self, content: Any) -> bytes:
        """Convert the content to JSON using our custom encoder."""
        encoded_content = BeanbotJSONEncoder.encode(content)
        return super().render(encoded_content)
