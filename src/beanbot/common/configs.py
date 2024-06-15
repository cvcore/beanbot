#!/usr/bin/env python3
# coding=utf-8

"""This module implements the configuration parser for beanbot.
The ConfigParser class is implemented as a singeton to share the same configuration among all files."""

from __future__ import annotations

from typing import Optional, Any, Dict
from beancount.core.data import Entries, Custom
from beancount.loader import load_file


class Config:
    _shared_instance = None

    def __init__(self, allow_missing=False):
        """Initialize an empty configuration instance."""
        self._config_values: Dict[str, Any] = {}
        self._config_types: Dict[str, type] = {}
        self._allow_missing = allow_missing
        self._fully_initialized = False

    def add_value(
        self, conf_name: str, conf_type: type, default_value: Optional[Any] = None
    ):
        """Define configuration with type and name"""
        self._config_types[conf_name] = conf_type
        if default_value is not None:
            self._config_values[conf_name] = default_value
        else:
            self._fully_initialized = False

    @classmethod
    def get_global(cls):
        """Get a global shared configuration instance"""
        if cls._shared_instance is None:
            cls._shared_instance = cls()
        return cls._shared_instance

    def __getitem__(self, key):
        """Get a config value"""
        return self._config_values[key]

    def __repr__(self):
        for config_name, config_value in self._config_values.items():
            print(f"{config_name}: {config_value}")

    def parse_entries(self, entries: Entries):
        """Parse configuration from a list of entries parsed from a `.bean` file.
        Each line of configuration should obey the following Beancount grammar (source
        https://beancount.github.io/docs/beancount_language_syntax.html#custom):

        YYYY-MM-DD custom "beanbot-config" CONFIG_NAME VALUE

        where `OPTION_NAME` should be a string. And `VALUE` should have the same type
        as defined in the `add_config` method. In case an unknown config is encountered,
        an exception will be raised.
        """
        custom_configs = [
            entry
            for entry in entries
            if isinstance(entry, Custom) and entry.type == "beanbot-config"
        ]

        for custom_config in custom_configs:
            self._parse_single(custom_config)
        if not self._allow_missing:
            self._check_completeness()

    def parse_file(self, path: str):
        entries, _, _ = load_file(path)
        self.parse_entries(entries)

    def _parse_single(self, custom_config: Custom):
        """Parse single config and add to dictionary"""

        assert (
            custom_config.type == "beanbot-config" and len(custom_config.values) == 2
        ), f"Got invalid config {custom_config}"

        conf_name = custom_config.values[0].value
        conf_value = custom_config.values[1].value
        assert (
            conf_name in self._config_types.keys()
        ), f"Got unknown config name {conf_name}"
        if type(conf_value) != self._config_types[conf_name]:
            conf_value = self._config_types[conf_name](conf_value)

        self._config_values[conf_name] = conf_value

        if len(self._config_values) == len(self._config_types):
            self._fully_initialized = True

    def _check_completeness(self):
        """Check if all configuration has been set."""
        if not self._fully_initialized:
            missing_keys = [
                key
                for key in self._config_types.keys()
                if key not in self._config_values.keys()
            ]
            raise RuntimeError(f"Mandatory configurations missing: {missing_keys}")


class BeanbotConfig(Config):
    def __init__(self, allow_missing=False):
        super().__init__(allow_missing)

        self.add_value("main-file", str)
        self.add_value("fallback-transaction-file", str)
        self.add_value("regex-source-account", str)
        self.add_value("regex-category-account", str)
        self.add_value("dedup-window-days", int)
