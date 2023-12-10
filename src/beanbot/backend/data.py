from __future__ import annotations

import json
import uuid
from typing import Dict, Optional

from beancount.core.data import Directive

from beanbot.backend.serialization import deserialize_dict, serialize_dict


class DirectiveWithId:
    def __init__(self, directive: Directive, manual_id: Optional[uuid.UUID]=None):
        self._directive = directive
        if manual_id is None:
            self._id = uuid.uuid4()
        else:
            assert isinstance(manual_id, uuid.UUID), f"manual_id must be a uuid.UUID, got {type(manual_id)}"
            self._id = manual_id

    def as_dict(self) -> Dict:
        return {
            "id": self._id,
            "directive": self._directive,
        }

    def as_json(self) -> str:
        return json.dumps(
            serialize_dict(self.as_dict())
        )

    @classmethod
    def from_json(cls, json_str: str) -> DirectiveWithId:
        json_dict = deserialize_dict(json.loads(json_str))
        return cls(
            directive=json_dict["directive"],
            manual_id=json_dict["id"],
        )
