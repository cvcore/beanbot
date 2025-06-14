"""Collision-resistant and thread-safe ID generator."""

import secrets
import threading


class BBID:
    """Class to manage BeanBot ID"""

    _global_ids: set[str] = set()
    _lock = threading.Lock()
    _id_bytes: int = 4
    _max_attempts: int = 10

    def __init__(self, id_value: str | None = None):
        """Initialize BBID with existing ID or generate new one.

        Args:
            id_value: Existing ID string to use, or None to generate new ID

        Raises:
            DuplicateIDError: If id_value already exists in global pool
            TypeError: If id_value is not a string or None
        """
        if id_value is not None and not isinstance(id_value, str):
            raise TypeError(f"id_value must be str or None, got {type(id_value)}")

        if id_value is None:
            self._id = self._generate_unique_id()
        else:
            with self._lock:
                if id_value in self._global_ids:
                    raise RuntimeError(f"ID '{id_value}' already exists in global pool")
                self._id = id_value
                self._global_ids.add(self._id)

    @classmethod
    def _generate_unique_id(cls) -> str:
        """Get or create the shared ID generator"""
        id_val = None

        with cls._lock:
            n_attempt = 0
            while n_attempt < cls._max_attempts and (
                id_val is None or id_val in cls._global_ids
            ):
                id_val = secrets.token_hex(cls._id_bytes)
                n_attempt += 1

            if n_attempt == cls._max_attempts:
                raise RuntimeError(
                    "Failed to generate unique ID after maximum attempts"
                )

            assert isinstance(id_val, str), (
                f"Generated ID must be a string, got {type(id_val)}"
            )

            cls._global_ids.add(id_val)

        return id_val

    def __str__(self) -> str:
        """String representation returns the ID value"""
        return self._id

    def __repr__(self) -> str:
        """Developer-friendly representation"""
        return f"BBID('{self._id}')"

    def __eq__(self, other: object) -> bool:
        """
        Equality comparison with other BBIDs or strings.

        Args:
            other: BBID instance, string, or other object

        Returns:
            bool: True if IDs are equal
        """
        if isinstance(other, BBID):
            return self._id == other._id
        elif isinstance(other, str):
            return self._id == other
        return False

    def __hash__(self) -> int:
        """Make BBID hashable for use as dictionary keys"""
        return hash(self._id)

    def __lt__(self, other: "BBID | str") -> bool:
        """Less than comparison for sorting"""
        if isinstance(other, BBID):
            return self._id < other._id
        elif isinstance(other, str):
            return self._id < other
        return NotImplemented

    @property
    def id(self) -> str:
        """Get the ID string value"""
        return self._id
