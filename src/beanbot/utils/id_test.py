"""Tests for the BBID class."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from unittest.mock import patch

import pytest

from beanbot.utils.id import BBID


@pytest.fixture(autouse=True)
def reset_global_ids():
    """Reset global IDs before each test."""
    original_ids = BBID._global_ids.copy()
    BBID._global_ids.clear()
    yield
    BBID._global_ids = original_ids


class TestBBIDInitialization:
    """Test BBID initialization."""

    def test_init_without_id_generates_unique_id(self):
        """Test that initialization without ID generates a unique ID."""
        bbid = BBID()
        assert isinstance(bbid.id, str)
        assert len(bbid.id) == BBID._id_bytes * 2  # hex encoding doubles length
        assert bbid.id in BBID._global_ids

    def test_init_with_valid_id(self):
        """Test initialization with a valid ID."""
        test_id = "test123"
        bbid = BBID(test_id)
        assert bbid.id == test_id
        assert test_id in BBID._global_ids

    def test_init_with_duplicate_id_raises_error(self):
        """Test that duplicate ID raises RuntimeError."""
        test_id = "duplicate123"
        BBID(test_id)

        with pytest.raises(RuntimeError, match="ID 'duplicate123' already exists"):
            BBID(test_id)

    def test_init_with_invalid_type_raises_error(self):
        """Test that non-string ID raises TypeError."""
        with pytest.raises(TypeError, match="id_value must be str or None"):
            BBID(123)

        with pytest.raises(TypeError, match="id_value must be str or None"):
            BBID([])


class TestBBIDUniqueness:
    """Test BBID uniqueness and collision handling."""

    def test_multiple_ids_are_unique(self):
        """Test that multiple generated IDs are unique."""
        n_samples = 10000
        ids = [BBID() for _ in range(n_samples)]
        id_strings = [bbid.id for bbid in ids]
        assert len(set(id_strings)) == n_samples  # All unique

    def test_max_attempts_exceeded(self):
        """Test behavior when max attempts is exceeded."""
        # Mock token_hex to always return the same value
        with patch("secrets.token_hex", return_value="collision"):
            # Fill global pool with the collision value
            BBID._global_ids.add("collision")

            with pytest.raises(RuntimeError, match="Failed to generate unique ID"):
                BBID()


class TestBBIDThreadSafety:
    """Test BBID thread safety."""

    def test_concurrent_id_generation(self):
        """Test that concurrent ID generation is thread-safe."""

        def generate_id():
            return BBID()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(generate_id) for _ in range(50)]
            ids = [future.result() for future in as_completed(futures)]

        id_strings = [bbid.id for bbid in ids]
        assert len(set(id_strings)) == 50  # All unique
        assert len(BBID._global_ids) == 50

    def test_concurrent_initialization_with_same_id(self):
        """Test concurrent initialization with the same ID."""
        test_id = "concurrent123"
        results = []
        exceptions = []

        def init_with_id():
            try:
                return BBID(test_id)
            except RuntimeError as e:
                exceptions.append(e)
                return None

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(init_with_id) for _ in range(5)]
            results = [future.result() for future in as_completed(futures)]

        # Only one should succeed, others should raise exceptions
        successful_results = [r for r in results if r is not None]
        assert len(successful_results) == 1
        assert len(exceptions) == 4
        assert successful_results[0].id == test_id


class TestBBIDComparison:
    """Test BBID comparison operations."""

    def test_equality_with_bbid(self):
        """Test equality comparison with another BBID."""
        bbid1 = BBID("test123")
        bbid2 = BBID("test456")
        bbid3 = deepcopy(bbid1)

        assert bbid1 == bbid3
        assert bbid1 != bbid2

    def test_equality_with_string(self):
        """Test equality comparison with string."""
        bbid = BBID("test123")
        assert bbid == "test123"
        assert bbid != "different"

    def test_equality_with_other_types(self):
        """Test equality comparison with other types."""
        bbid = BBID("test123")
        assert bbid != 123
        assert bbid != []
        assert bbid != None  # noqa: E711

    def test_less_than_comparison(self):
        """Test less than comparison."""
        bbid1 = BBID("aaa")
        bbid2 = BBID("bbb")

        assert bbid1 < bbid2
        assert bbid1 < "bbb"
        assert not (bbid2 < bbid1)

    def test_hash_functionality(self):
        """Test that BBID is hashable and works in sets/dicts."""
        bbid1 = BBID("test123")
        bbid2 = BBID("test456")

        # Test in set
        id_set = {bbid1, bbid2}
        assert len(id_set) == 2

        # Test in dict
        id_dict = {bbid1: "value1", bbid2: "value2"}
        assert id_dict[bbid1] == "value1"


class TestBBIDStringRepresentation:
    """Test BBID string representations."""

    def test_str_representation(self):
        """Test __str__ method."""
        bbid = BBID("test123")
        assert str(bbid) == "test123"

    def test_repr_representation(self):
        """Test __repr__ method."""
        bbid = BBID("test123")
        assert repr(bbid) == "BBID('test123')"


class TestBBIDProperties:
    """Test BBID properties."""

    def test_id_property(self):
        """Test the id property."""
        test_id = "property_test"
        bbid = BBID(test_id)
        assert bbid.id == test_id


class TestBBIDEdgeCases:
    """Test BBID edge cases and error conditions."""

    def test_empty_string_id(self):
        """Test initialization with empty string."""
        bbid = BBID("")
        assert bbid.id == ""
        assert "" in BBID._global_ids

    def test_very_long_id(self):
        """Test initialization with very long ID."""
        long_id = "a" * 1000
        bbid = BBID(long_id)
        assert bbid.id == long_id

    def test_id_with_special_characters(self):
        """Test ID with special characters."""
        special_id = "test!@#$%^&*()_+-="
        bbid = BBID(special_id)
        assert bbid.id == special_id

    def test_unicode_id(self):
        """Test ID with unicode characters."""
        unicode_id = "测试🚀"
        bbid = BBID(unicode_id)
        assert bbid.id == unicode_id
