"""Collision-resistant and thread-safe ID generator."""

import secrets
import threading


class IDGenerator:
    """Thread-safe ID generator that ensures uniqueness within this generator instance."""

    def __init__(self, id_bytes: int = 4, max_attempts: int = 10):
        """Initialize the ID generator.

        Args:
            id_bytes: Number of bytes for the generated ID
            max_attempts: Maximum attempts to generate a unique ID
        """
        self._generated_ids: set[str] = set()
        self._lock = threading.Lock()
        self._id_bytes = id_bytes
        self._max_attempts = max_attempts

    def __iter__(self):
        """Make the generator iterable."""
        return self

    def __next__(self) -> str:
        """Generate the next unique ID.

        Returns:
            str: A unique hexadecimal ID string

        Raises:
            RuntimeError: If unable to generate unique ID after max attempts
        """
        return self.generate()

    def generate(self) -> str:
        """Generate a unique ID within this generator instance.

        Returns:
            str: A unique hexadecimal ID string

        Raises:
            RuntimeError: If unable to generate unique ID after max attempts
        """
        with self._lock:
            id_val = None
            n_attempt = 0

            while n_attempt < self._max_attempts and (
                id_val is None or id_val in self._generated_ids
            ):
                id_val = secrets.token_hex(self._id_bytes)
                n_attempt += 1

            if n_attempt == self._max_attempts:
                raise RuntimeError(
                    "Failed to generate unique ID after maximum attempts"
                )

            assert isinstance(id_val, str), (
                f"Generated ID must be a string, got {type(id_val)}"
            )

            self._generated_ids.add(id_val)
            return id_val

    def register(self, id_value: str) -> None:
        """Register an existing ID to prevent future collisions.

        Args:
            id_value: ID string to register

        Raises:
            RuntimeError: If ID already exists in this generator
        """
        with self._lock:
            if id_value in self._generated_ids:
                raise RuntimeError(f"ID '{id_value}' already exists in this generator")
            self._generated_ids.add(id_value)

    def unregister(self, id_value: str) -> bool:
        """Unregister an existing ID, allowing it to be generated again.

        Args:
            id_value: ID string to unregister

        Returns:
            bool: True if ID was found and removed, False if not found
        """
        with self._lock:
            if id_value in self._generated_ids:
                self._generated_ids.remove(id_value)
                return True
            return False

    def exists(self, id_value: str) -> bool:
        """Check if an ID exists in this generator.

        Args:
            id_value: ID string to check

        Returns:
            bool: True if ID exists, False otherwise
        """
        with self._lock:
            return id_value in self._generated_ids
