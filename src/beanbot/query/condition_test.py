import re
from dataclasses import dataclass

import pytest

from .condition import (
    AndCondition,
    CustomCondition,
    FieldCondition,
    FieldConditionBuilder,
    NotCondition,
    OrCondition,
    field,
)


@dataclass
class MockRecord:
    """Mock record for testing conditions."""

    amount: float
    account: str
    description: str
    payee: str
    year: int


class TestFieldCondition:
    """Test FieldCondition class."""

    def setup_method(self):
        """Set up test data."""
        self.record = MockRecord(
            amount=150.50,
            account="Assets:Cash",
            description="Coffee transfer payment",
            payee="john doe",
            year=2024,
        )

    def test_eq_operator_true(self):
        condition = FieldCondition("amount", "eq", 150.50)
        assert condition.evaluate(self.record) is True

    def test_eq_operator_false(self):
        condition = FieldCondition("amount", "eq", 100.00)
        assert condition.evaluate(self.record) is False

    def test_ne_operator_true(self):
        condition = FieldCondition("amount", "ne", 100.00)
        assert condition.evaluate(self.record) is True

    def test_ne_operator_false(self):
        condition = FieldCondition("amount", "ne", 150.50)
        assert condition.evaluate(self.record) is False

    def test_lt_operator_true(self):
        condition = FieldCondition("amount", "lt", 200.00)
        assert condition.evaluate(self.record) is True

    def test_lt_operator_false(self):
        condition = FieldCondition("amount", "lt", 100.00)
        assert condition.evaluate(self.record) is False

    def test_le_operator_true(self):
        condition = FieldCondition("amount", "le", 150.50)
        assert condition.evaluate(self.record) is True

    def test_le_operator_false(self):
        condition = FieldCondition("amount", "le", 100.00)
        assert condition.evaluate(self.record) is False

    def test_gt_operator_true(self):
        condition = FieldCondition("amount", "gt", 100.00)
        assert condition.evaluate(self.record) is True

    def test_gt_operator_false(self):
        condition = FieldCondition("amount", "gt", 200.00)
        assert condition.evaluate(self.record) is False

    def test_ge_operator_true(self):
        condition = FieldCondition("amount", "ge", 150.50)
        assert condition.evaluate(self.record) is True

    def test_ge_operator_false(self):
        condition = FieldCondition("amount", "ge", 200.00)
        assert condition.evaluate(self.record) is False

    def test_in_operator_true(self):
        condition = FieldCondition("account", "in", ["Assets:Cash", "Assets:Bank"])
        assert condition.evaluate(self.record) is True

    def test_in_operator_false(self):
        condition = FieldCondition("account", "in", ["Liabilities:CreditCard"])
        assert condition.evaluate(self.record) is False

    def test_contains_operator_true(self):
        condition = FieldCondition("description", "contains", "transfer")
        assert condition.evaluate(self.record) is True

    def test_contains_operator_false(self):
        condition = FieldCondition("description", "contains", "salary")
        assert condition.evaluate(self.record) is False

    def test_regex_operator_true(self):
        condition = FieldCondition("description", "regex", r"transfer")
        assert condition.evaluate(self.record) is True

    def test_regex_operator_false(self):
        condition = FieldCondition("description", "regex", r"^salary")
        assert condition.evaluate(self.record) is False

    def test_regex_pattern_compilation(self):
        condition = FieldCondition("payee", "regex", r"\b(john|jane)\b")
        assert hasattr(condition, "pattern")
        assert isinstance(condition.pattern, re.Pattern)

    def test_regex_case_sensitive(self):
        condition = FieldCondition("payee", "regex", r"John")
        assert condition.evaluate(self.record) is False

    def test_regex_case_insensitive(self):
        condition = FieldCondition("payee", "regex", r"(?i)John")
        assert condition.evaluate(self.record) is True

    def test_unsupported_operator(self):
        with pytest.raises(ValueError, match="Unsupported operator: invalid"):
            condition = FieldCondition("amount", "invalid", 100)
            condition.evaluate(self.record)

    def test_missing_field(self):
        condition = FieldCondition("nonexistent", "eq", "value")
        assert condition.evaluate(self.record) is False


class TestCustomCondition:
    """Test CustomCondition class."""

    def setup_method(self):
        self.record = MockRecord(
            amount=150.50,
            account="Assets:Cash",
            description="Coffee transfer payment",
            payee="john doe",
            year=2024,
        )

    def test_custom_function_true(self):
        condition = CustomCondition(lambda record: record.year == 2024)
        assert condition.evaluate(self.record) is True

    def test_custom_function_false(self):
        condition = CustomCondition(lambda record: record.year == 2023)
        assert condition.evaluate(self.record) is False

    def test_complex_custom_function(self):
        condition = CustomCondition(
            lambda record: record.amount > 100 and "Assets" in record.account
        )
        assert condition.evaluate(self.record) is True


class TestLogicalConditions:
    """Test logical combination conditions."""

    def setup_method(self):
        self.record = MockRecord(
            amount=150.50,
            account="Assets:Cash",
            description="Coffee transfer payment",
            payee="john doe",
            year=2024,
        )

    def test_and_condition_both_true(self):
        left = FieldCondition("amount", "gt", 100)
        right = FieldCondition("account", "contains", "Assets")
        condition = AndCondition(left, right)
        assert condition.evaluate(self.record) is True

    def test_and_condition_one_false(self):
        left = FieldCondition("amount", "gt", 200)
        right = FieldCondition("account", "contains", "Assets")
        condition = AndCondition(left, right)
        assert condition.evaluate(self.record) is False

    def test_or_condition_both_true(self):
        left = FieldCondition("amount", "gt", 100)
        right = FieldCondition("account", "contains", "Assets")
        condition = OrCondition(left, right)
        assert condition.evaluate(self.record) is True

    def test_or_condition_one_true(self):
        left = FieldCondition("amount", "gt", 200)
        right = FieldCondition("account", "contains", "Assets")
        condition = OrCondition(left, right)
        assert condition.evaluate(self.record) is True

    def test_or_condition_both_false(self):
        left = FieldCondition("amount", "gt", 200)
        right = FieldCondition("account", "contains", "Liabilities")
        condition = OrCondition(left, right)
        assert condition.evaluate(self.record) is False

    def test_not_condition_true(self):
        inner = FieldCondition("amount", "gt", 200)
        condition = NotCondition(inner)
        assert condition.evaluate(self.record) is True

    def test_not_condition_false(self):
        inner = FieldCondition("amount", "gt", 100)
        condition = NotCondition(inner)
        assert condition.evaluate(self.record) is False


class TestOperatorOverloading:
    """Test operator overloading (&, |, ~)."""

    def setup_method(self):
        self.record = MockRecord(
            amount=150.50,
            account="Assets:Cash",
            description="Coffee transfer payment",
            payee="john doe",
            year=2024,
        )

    def test_and_operator(self):
        condition1 = FieldCondition("amount", "gt", 100)
        condition2 = FieldCondition("account", "contains", "Assets")
        combined = condition1 & condition2

        assert isinstance(combined, AndCondition)
        assert combined.evaluate(self.record) is True

    def test_or_operator(self):
        condition1 = FieldCondition("amount", "gt", 200)
        condition2 = FieldCondition("account", "contains", "Assets")
        combined = condition1 | condition2

        assert isinstance(combined, OrCondition)
        assert combined.evaluate(self.record) is True

    def test_not_operator(self):
        condition = FieldCondition("amount", "gt", 200)
        negated = ~condition

        assert isinstance(negated, NotCondition)
        assert negated.evaluate(self.record) is True

    def test_complex_combination(self):
        condition1 = FieldCondition("amount", "gt", 100)
        condition2 = FieldCondition("account", "contains", "Assets")
        condition3 = FieldCondition("description", "in", ["salary", "bonus"])

        # (amount > 100 & account contains "Assets") | description in ["salary", "bonus"]
        combined = (condition1 & condition2) | condition3
        assert combined.evaluate(self.record) is True


class TestFieldConditionBuilder:
    """Test FieldConditionBuilder class."""

    def setup_method(self):
        self.record = MockRecord(
            amount=150.50,
            account="Assets:Cash",
            description="Coffee transfer payment",
            payee="john doe",
            year=2024,
        )

    def test_field_function(self):
        builder = field("amount")
        assert isinstance(builder, FieldConditionBuilder)
        assert builder.field_name == "amount"

    def test_builder_eq(self):
        condition = field("amount").eq(150.50)
        assert isinstance(condition, FieldCondition)
        assert condition.evaluate(self.record) is True

    def test_builder_ne(self):
        condition = field("amount").ne(100.00)
        assert condition.evaluate(self.record) is True

    def test_builder_lt(self):
        condition = field("amount").lt(200.00)
        assert condition.evaluate(self.record) is True

    def test_builder_le(self):
        condition = field("amount").le(150.50)
        assert condition.evaluate(self.record) is True

    def test_builder_gt(self):
        condition = field("amount").gt(100.00)
        assert condition.evaluate(self.record) is True

    def test_builder_ge(self):
        condition = field("amount").ge(150.50)
        assert condition.evaluate(self.record) is True

    def test_builder_in(self):
        condition = field("account").in_(["Assets:Cash", "Assets:Bank"])
        assert condition.evaluate(self.record) is True

    def test_builder_contains(self):
        condition = field("description").contains("transfer")
        assert condition.evaluate(self.record) is True

    def test_builder_regex(self):
        condition = field("description").regex(r"transfer")
        assert condition.evaluate(self.record) is True


class TestUsageExamples:
    """Test the usage examples from the documentation."""

    def setup_method(self):
        self.record1 = MockRecord(
            amount=150.50,
            account="Assets:Cash",
            description="salary payment",
            payee="employer",
            year=2024,
        )
        self.record2 = MockRecord(
            amount=50.00,
            account="Liabilities:CreditCard",
            description="bonus transfer",
            payee="john smith",
            year=2024,
        )

    def test_simple_field_conditions(self):
        condition1 = field("amount").gt(100)
        condition2 = field("account").eq("Assets:Cash")

        assert condition1.evaluate(self.record1) is True
        assert condition1.evaluate(self.record2) is False
        assert condition2.evaluate(self.record1) is True
        assert condition2.evaluate(self.record2) is False

    def test_combining_conditions(self):
        condition1 = field("amount").gt(100)
        condition2 = field("account").eq("Assets:Cash")

        # AND
        combined = condition1 & condition2
        assert combined.evaluate(self.record1) is True
        assert combined.evaluate(self.record2) is False

        # OR
        either = condition1 | condition2
        assert either.evaluate(self.record1) is True
        assert either.evaluate(self.record2) is False

        # NOT
        negated = ~condition1
        assert negated.evaluate(self.record1) is False
        assert negated.evaluate(self.record2) is True

    def test_complex_combinations(self):
        complex_condition = (
            field("amount").gt(100) & field("account").contains("Assets")
        ) | field("description").in_(["salary", "bonus transfer"])

        assert complex_condition.evaluate(self.record1) is True  # Both sides true
        assert complex_condition.evaluate(self.record2) is True  # Right side true

    def test_custom_condition_example(self):
        custom = CustomCondition(lambda record: record.year == 2024)
        assert custom.evaluate(self.record1) is True
        assert custom.evaluate(self.record2) is True

    def test_regex_examples(self):
        # Match description containing "transfer" (case-sensitive)
        condition1 = field("description").regex(r"transfer")
        assert condition1.evaluate(self.record2) is True
        assert condition1.evaluate(self.record1) is False

        # Match account names starting with "Assets" or "Liabilities"
        condition2 = field("account").regex(r"^(Assets|Liabilities)")
        assert condition2.evaluate(self.record1) is True
        assert condition2.evaluate(self.record2) is True

        # Complex regex with word boundaries
        condition4 = field("payee").regex(r"\b(john|jane)\b")
        assert condition4.evaluate(self.record2) is True
        assert condition4.evaluate(self.record1) is False


class TestExplainAndStringRepresentation:
    """Test explain method and string representations."""

    def setup_method(self):
        self.record = MockRecord(
            amount=150.50,
            account="Assets:Cash",
            description="Coffee transfer payment",
            payee="john doe",
            year=2024,
        )

    def test_field_condition_str(self):
        condition = field("amount").gt(100)
        assert str(condition) == "amount > '100'"

    def test_field_condition_eq_str(self):
        condition = field("account").eq("Assets:Cash")
        assert str(condition) == "account == 'Assets:Cash'"

    def test_field_condition_contains_str(self):
        condition = field("description").contains("transfer")
        assert str(condition) == "'transfer' contains description"

    def test_field_condition_regex_str(self):
        condition = field("description").regex(r"transfer")
        assert str(condition) == "description ~ /transfer/"

    def test_field_condition_in_str(self):
        condition = field("account").in_(["Assets:Cash", "Assets:Bank"])
        assert str(condition) == "account in '['Assets:Cash', 'Assets:Bank']'"

    def test_custom_condition_str(self):
        condition = CustomCondition(lambda r: r.year == 2024, "year is 2024")
        assert str(condition) == "custom(year is 2024)"

    def test_custom_condition_default_str(self):
        condition = CustomCondition(lambda r: r.year == 2024)
        assert str(condition) == "custom(custom function)"

    def test_and_condition_str(self):
        left = field("amount").gt(100)
        right = field("account").contains("Assets")
        condition = left & right
        assert str(condition) == "(amount > '100') AND ('Assets' contains account)"

    def test_or_condition_str(self):
        left = field("amount").gt(100)
        right = field("account").contains("Assets")
        condition = left | right
        assert str(condition) == "(amount > '100') OR ('Assets' contains account)"

    def test_not_condition_str(self):
        inner = field("amount").gt(100)
        condition = ~inner
        assert str(condition) == "NOT (amount > '100')"

    def test_field_condition_explain_true(self):
        condition = field("amount").gt(100)
        explanation = condition.explain(self.record)
        assert explanation == "amount: '150.5' > '100' → True"

    def test_field_condition_explain_false(self):
        condition = field("amount").gt(200)
        explanation = condition.explain(self.record)
        assert explanation == "amount: '150.5' > '200' → False"

    def test_field_condition_explain_eq(self):
        condition = field("account").eq("Assets:Cash")
        explanation = condition.explain(self.record)
        assert explanation == "account: 'Assets:Cash' == 'Assets:Cash' → True"

    def test_field_condition_explain_contains(self):
        condition = field("description").contains("transfer")
        explanation = condition.explain(self.record)
        assert (
            explanation
            == "description: 'transfer' contains 'Coffee transfer payment' → True"
        )

    def test_field_condition_explain_regex(self):
        condition = field("description").regex(r"transfer")
        explanation = condition.explain(self.record)
        assert (
            explanation
            == "description: 'Coffee transfer payment' matches pattern 'transfer' → True"
        )

    def test_custom_condition_explain(self):
        condition = CustomCondition(lambda r: r.year == 2024, "year is 2024")
        explanation = condition.explain(self.record)
        assert explanation == "year is 2024 → True"

    def test_and_condition_explain_true(self):
        left = field("amount").gt(100)
        right = field("account").contains("Assets")
        condition = left & right
        explanation = condition.explain(self.record)
        expected = (
            "(amount: '150.5' > '100' → True) AND "
            "(account: 'Assets' contains 'Assets:Cash' → True) → "
            "True AND True → True"
        )
        assert explanation == expected

    def test_and_condition_explain_false(self):
        left = field("amount").gt(200)
        right = field("account").contains("Assets")
        condition = left & right
        explanation = condition.explain(self.record)
        expected = (
            "(amount: '150.5' > '200' → False) AND "
            "(account: 'Assets' contains 'Assets:Cash' → True) → "
            "False AND True → False"
        )
        assert explanation == expected

    def test_or_condition_explain_true(self):
        left = field("amount").gt(200)
        right = field("account").contains("Assets")
        condition = left | right
        explanation = condition.explain(self.record)
        expected = (
            "(amount: '150.5' > '200' → False) OR "
            "(account: 'Assets' contains 'Assets:Cash' → True) → "
            "False OR True → True"
        )
        assert explanation == expected

    def test_not_condition_explain(self):
        inner = field("amount").gt(200)
        condition = ~inner
        explanation = condition.explain(self.record)
        expected = "NOT (amount: '150.5' > '200' → False) → NOT False → True"
        assert explanation == expected

    def test_complex_condition_explain(self):
        condition = (
            field("amount").gt(100) & field("account").contains("Assets")
        ) | field("year").eq(2023)
        explanation = condition.explain(self.record)
        # This will be a complex nested explanation
        assert "→" in explanation
        assert "AND" in explanation
        assert "OR" in explanation

    def test_repr_equals_str(self):
        condition = field("amount").gt(100)
        assert repr(condition) == str(condition)


if __name__ == "__main__":
    pytest.main([__file__])
