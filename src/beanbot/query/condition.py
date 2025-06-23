import re
from abc import ABC, abstractmethod
from typing import Any, Callable


class Condition(ABC):
    """Abstract base class for query conditions."""

    @abstractmethod
    def evaluate(self, record: Any) -> bool:
        """Evaluate the condition against a record.

        Args:
            record: The record to evaluate the condition against.

        Returns:
            bool: True if the condition is satisfied, False otherwise.
        """
        pass

    @abstractmethod
    def explain(self, record: Any) -> str:
        """Explain why the condition evaluates to true or false.

        Args:
            record: The record to evaluate the condition against.

        Returns:
            str: A human-readable explanation of the evaluation.
        """
        pass

    @abstractmethod
    def __str__(self) -> str:
        """Return a human-readable string representation of the condition."""
        pass

    def __repr__(self) -> str:
        """Return a detailed string representation of the condition."""
        return str(self)

    def __and__(self, other: "Condition") -> "AndCondition":
        """Combine conditions with logical AND (&)."""
        return AndCondition(self, other)

    def __or__(self, other: "Condition") -> "OrCondition":
        """Combine conditions with logical OR (|)."""
        return OrCondition(self, other)

    def __invert__(self) -> "NotCondition":
        """Negate condition with logical NOT (~)."""
        return NotCondition(self)


class FieldCondition(Condition):
    """Condition that evaluates a field against a value using an operator."""

    def __init__(self, field: str, operator: str, value: Any):
        """Initialize a field condition.

        Args:
            field: The field name to evaluate.
            operator: The comparison operator ('eq', 'ne', 'lt', 'le', 'gt', 'ge', 'in', 'contains', 'regex').
            value: The value to compare against.
        """
        self.field = field
        self.operator = operator
        self.value = value

        # Compile regex pattern if using regex operator
        if self.operator == "regex":
            self.pattern = re.compile(self.value)

    def evaluate(self, record: Any) -> bool:
        """Evaluate the field condition against a record."""
        field_value = getattr(record, self.field, None)

        if self.operator == "eq":
            return field_value == self.value
        elif self.operator == "ne":
            return field_value != self.value
        elif self.operator == "lt":
            return field_value < self.value
        elif self.operator == "le":
            return field_value <= self.value
        elif self.operator == "gt":
            return field_value > self.value
        elif self.operator == "ge":
            return field_value >= self.value
        elif self.operator == "in":
            return field_value in self.value
        elif self.operator == "contains":
            return self.value in field_value
        elif self.operator == "regex":
            return bool(self.pattern.search(str(field_value)))
        else:
            raise ValueError(f"Unsupported operator: {self.operator}")

    def explain(self, record: Any) -> str:
        """Explain why the field condition evaluates to true or false."""
        field_value = getattr(record, self.field, None)
        result = self.evaluate(record)

        operator_symbols = {
            "eq": "==",
            "ne": "!=",
            "lt": "<",
            "le": "<=",
            "gt": ">",
            "ge": ">=",
            "in": "in",
            "contains": "contains",
            "regex": "matches",
        }

        symbol = operator_symbols.get(self.operator, self.operator)

        if self.operator == "contains":
            explanation = f"'{self.value}' {symbol} '{field_value}'"
        elif self.operator == "regex":
            explanation = f"'{field_value}' {symbol} pattern '{self.value}'"
        else:
            explanation = f"'{field_value}' {symbol} '{self.value}'"

        return f"{self.field}: {explanation} → {result}"

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        operator_symbols = {
            "eq": "==",
            "ne": "!=",
            "lt": "<",
            "le": "<=",
            "gt": ">",
            "ge": ">=",
            "in": "in",
            "contains": "contains",
            "regex": "~",
        }

        symbol = operator_symbols.get(self.operator, self.operator)

        if self.operator == "contains":
            return f"'{self.value}' {symbol} {self.field}"
        elif self.operator == "regex":
            return f"{self.field} {symbol} /{self.value}/"
        else:
            return f"{self.field} {symbol} '{self.value}'"


class CustomCondition(Condition):
    """Condition that uses a custom evaluation function."""

    def __init__(self, func: Callable[[Any], bool], description: str = None):
        """Initialize a custom condition.

        Args:
            func: A function that takes a record and returns a boolean.
            description: Optional description of what the function does.
        """
        self.func = func
        self.description = description or "custom function"

    def evaluate(self, record: Any) -> bool:
        """Evaluate the custom condition against a record."""
        return self.func(record)

    def explain(self, record: Any) -> str:
        """Explain why the custom condition evaluates to true or false."""
        result = self.evaluate(record)
        return f"{self.description} → {result}"

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"custom({self.description})"


class AndCondition(Condition):
    """Condition that combines two conditions with logical AND."""

    def __init__(self, left: Condition, right: Condition):
        self.left = left
        self.right = right

    def evaluate(self, record: Any) -> bool:
        """Evaluate both conditions and return True if both are True."""
        return self.left.evaluate(record) and self.right.evaluate(record)

    def explain(self, record: Any) -> str:
        """Explain why the AND condition evaluates to true or false."""
        left_result = self.left.evaluate(record)
        right_result = self.right.evaluate(record)
        result = left_result and right_result

        left_explain = self.left.explain(record)
        right_explain = self.right.explain(record)

        return (
            f"({left_explain}) AND ({right_explain}) → "
            f"{left_result} AND {right_result} → {result}"
        )

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"({self.left}) AND ({self.right})"


class OrCondition(Condition):
    """Condition that combines two conditions with logical OR."""

    def __init__(self, left: Condition, right: Condition):
        self.left = left
        self.right = right

    def evaluate(self, record: Any) -> bool:
        """Evaluate both conditions and return True if either is True."""
        return self.left.evaluate(record) or self.right.evaluate(record)

    def explain(self, record: Any) -> str:
        """Explain why the OR condition evaluates to true or false."""
        left_result = self.left.evaluate(record)
        right_result = self.right.evaluate(record)
        result = left_result or right_result

        left_explain = self.left.explain(record)
        right_explain = self.right.explain(record)

        return (
            f"({left_explain}) OR ({right_explain}) → "
            f"{left_result} OR {right_result} → {result}"
        )

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"({self.left}) OR ({self.right})"


class NotCondition(Condition):
    """Condition that negates another condition."""

    def __init__(self, condition: Condition):
        self.condition = condition

    def evaluate(self, record: Any) -> bool:
        """Evaluate the condition and return its negation."""
        return not self.condition.evaluate(record)

    def explain(self, record: Any) -> str:
        """Explain why the NOT condition evaluates to true or false."""
        inner_result = self.condition.evaluate(record)
        result = not inner_result
        inner_explain = self.condition.explain(record)

        return f"NOT ({inner_explain}) → NOT {inner_result} → {result}"

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return f"NOT ({self.condition})"


# Convenience functions for creating conditions
def field(name: str) -> "FieldConditionBuilder":
    """Create a field condition builder."""
    return FieldConditionBuilder(name)


class FieldConditionBuilder:
    """Builder class for creating field conditions with fluent syntax."""

    def __init__(self, field_name: str):
        self.field_name = field_name

    def eq(self, value: Any) -> FieldCondition:
        """Create an equality condition."""
        return FieldCondition(self.field_name, "eq", value)

    def ne(self, value: Any) -> FieldCondition:
        """Create a not-equal condition."""
        return FieldCondition(self.field_name, "ne", value)

    def lt(self, value: Any) -> FieldCondition:
        """Create a less-than condition."""
        return FieldCondition(self.field_name, "lt", value)

    def le(self, value: Any) -> FieldCondition:
        """Create a less-than-or-equal condition."""
        return FieldCondition(self.field_name, "le", value)

    def gt(self, value: Any) -> FieldCondition:
        """Create a greater-than condition."""
        return FieldCondition(self.field_name, "gt", value)

    def ge(self, value: Any) -> FieldCondition:
        """Create a greater-than-or-equal condition."""
        return FieldCondition(self.field_name, "ge", value)

    def in_(self, values: list) -> FieldCondition:
        """Create an 'in' condition."""
        return FieldCondition(self.field_name, "in", values)

    def contains(self, value: Any) -> FieldCondition:
        """Create a 'contains' condition."""
        return FieldCondition(self.field_name, "contains", value)

    def regex(self, pattern: str) -> FieldCondition:
        """Create a regex condition."""
        return FieldCondition(self.field_name, "regex", pattern)
