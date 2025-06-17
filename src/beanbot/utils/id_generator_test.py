"""Tests for the IDGenerator class."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

import pytest

from beanbot.utils.id_generator import IDGenerator


class TestIDGeneratorInitialization:
    """Test IDGenerator initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        generator = IDGenerator()
        assert generator._id_bytes == 4
        assert generator._max_attempts == 10
        assert len(generator._generated_ids) == 0

    def test_init_with_custom_params(self):
        """Test initialization with custom parameters."""
        generator = IDGenerator(id_bytes=8, max_attempts=20)
        assert generator._id_bytes == 8
        assert generator._max_attempts == 20


class TestIDGeneratorGeneration:
    """Test ID generation functionality."""

    def test_generate_returns_string(self):
        """Test that generate returns a string."""
        generator = IDGenerator()
        id_str = generator.generate()
        assert isinstance(id_str, str)
        assert len(id_str) == generator._id_bytes * 2  # hex encoding doubles length

    def test_generate_unique_ids(self):
        """Test that generate produces unique IDs."""
        generator = IDGenerator()
        n_samples = 1000
        ids = [generator.generate() for _ in range(n_samples)]
        assert len(set(ids)) == n_samples  # All unique

    def test_iterator_protocol(self):
        """Test that IDGenerator works as an iterator."""
        generator = IDGenerator()

        # Test __iter__
        assert iter(generator) is generator

        # Test __next__
        id1 = next(generator)
        id2 = next(generator)

        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert id1 != id2

    def test_iterator_in_for_loop(self):
        """Test using IDGenerator in a for loop."""
        generator = IDGenerator()
        ids = []

        for i, id_str in enumerate(generator):
            ids.append(id_str)
            if i >= 9:  # Get first 10 IDs
                break

        assert len(ids) == 10
        assert len(set(ids)) == 10  # All unique

    def test_custom_id_bytes(self):
        """Test generation with custom id_bytes."""
        generator = IDGenerator(id_bytes=2)
        id_str = generator.generate()
        assert len(id_str) == 4  # 2 bytes * 2 (hex encoding)

    def test_max_attempts_exceeded(self):
        """Test behavior when max attempts is exceeded."""
        generator = IDGenerator(max_attempts=3)

        # Mock token_hex to always return the same value
        with patch("secrets.token_hex", return_value="collision"):
            # Generate one ID to fill the set
            generator.generate()

            # Next generation should fail after max attempts
            with pytest.raises(RuntimeError, match="Failed to generate unique ID"):
                generator.generate()


class TestIDGeneratorRegistration:
    """Test ID registration functionality."""

    def test_register_new_id(self):
        """Test registering a new ID."""
        generator = IDGenerator()
        test_id = "test123"

        generator.register(test_id)
        assert test_id in generator._generated_ids

    def test_register_duplicate_id_raises_error(self):
        """Test that registering a duplicate ID raises RuntimeError."""
        generator = IDGenerator()
        test_id = "duplicate123"

        generator.register(test_id)

        with pytest.raises(RuntimeError, match="ID 'duplicate123' already exists"):
            generator.register(test_id)

    def test_register_prevents_future_generation(self):
        """Test that registered IDs prevent future generation conflicts."""
        generator = IDGenerator()
        test_id = "conflict"

        # Register the ID
        generator.register(test_id)

        # Mock token_hex to return the registered ID
        with patch("secrets.token_hex", return_value=test_id):
            # Should generate a different ID or fail
            with pytest.raises(RuntimeError, match="Failed to generate unique ID"):
                generator.generate()

    def test_unregister_existing_id(self):
        """Test unregistering an existing ID."""
        generator = IDGenerator()
        test_id = "test123"

        generator.register(test_id)
        assert test_id in generator._generated_ids

        result = generator.unregister(test_id)
        assert result is True
        assert test_id not in generator._generated_ids

    def test_unregister_non_existent_id(self):
        """Test unregistering a non-existent ID."""
        generator = IDGenerator()
        test_id = "nonexistent"

        result = generator.unregister(test_id)
        assert result is False

    def test_unregister_allows_regeneration(self):
        """Test that unregistered IDs can be generated again."""
        generator = IDGenerator()
        test_id = "reusable"

        # Register and then unregister
        generator.register(test_id)
        generator.unregister(test_id)

        # Mock token_hex to return the unregistered ID
        with patch("secrets.token_hex", return_value=test_id):
            generated_id = generator.generate()
            assert generated_id == test_id
            assert test_id in generator._generated_ids

    def test_unregister_generated_id(self):
        """Test unregistering a previously generated ID."""
        generator = IDGenerator()

        # Generate an ID
        generated_id = generator.generate()
        assert generated_id in generator._generated_ids

        # Unregister it
        result = generator.unregister(generated_id)
        assert result is True
        assert generated_id not in generator._generated_ids


class TestIDGeneratorThreadSafety:
    """Test IDGenerator thread safety."""

    def test_concurrent_id_generation(self):
        """Test that concurrent ID generation is thread-safe."""
        generator = IDGenerator()

        def generate_id():
            return generator.generate()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(generate_id) for _ in range(50)]
            ids = [future.result() for future in as_completed(futures)]

        assert len(set(ids)) == 50  # All unique
        assert len(generator._generated_ids) == 50

    def test_concurrent_registration(self):
        """Test concurrent registration of different IDs."""
        generator = IDGenerator()
        results = []
        exceptions = []

        def register_id(id_value):
            try:
                generator.register(id_value)
                return id_value
            except RuntimeError as e:
                exceptions.append(e)
                return None

        test_ids = [f"id_{i}" for i in range(10)]

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(register_id, id_val) for id_val in test_ids]
            results = [future.result() for future in as_completed(futures)]

        successful_results = [r for r in results if r is not None]
        assert len(successful_results) == 10
        assert len(exceptions) == 0

    def test_concurrent_registration_same_id(self):
        """Test concurrent registration of the same ID."""
        generator = IDGenerator()
        test_id = "concurrent123"
        results = []
        exceptions = []

        def register_id():
            try:
                generator.register(test_id)
                return test_id
            except RuntimeError as e:
                exceptions.append(e)
                return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(register_id) for _ in range(5)]
            results = [future.result() for future in as_completed(futures)]

        # Only one should succeed, others should raise exceptions
        successful_results = [r for r in results if r is not None]
        assert len(successful_results) == 1
        assert len(exceptions) == 4

    def test_concurrent_unregistration(self):
        """Test concurrent unregistration of the same ID."""
        generator = IDGenerator()
        test_id = "concurrent_unreg"

        # Register the ID first
        generator.register(test_id)

        results = []

        def unregister_id():
            return generator.unregister(test_id)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(unregister_id) for _ in range(5)]
            results = [future.result() for future in as_completed(futures)]

        # Only one should succeed in unregistering
        successful_results = [r for r in results if r is True]
        failed_results = [r for r in results if r is False]

        assert len(successful_results) == 1
        assert len(failed_results) == 4
        assert test_id not in generator._generated_ids
