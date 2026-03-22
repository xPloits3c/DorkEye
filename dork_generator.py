# Google Dork Generator — DorkEye v4.8 | I.C.W.T 2026
"""
dork_generator.py
=================
YAML-driven dork generation engine for DorkEye.

A DorkGenerator loads a template YAML file that contains variable definitions
and dork templates, then expands every combination of variable values into a
flat, deduplicated list of ready-to-search dork strings.

Supported template YAML structures
-----------------------------------
Nested (recommended):
    variables:
      domain: [example.com, target.org]
      ext:    [php, asp]

    templates:
      sqli:
        dorks:
          soft:
            - 'site:{domain} inurl:.{ext}?id='
          medium:
            - 'site:{domain} inurl:.{ext}?id= intext:error'
          aggressive:
            - 'site:{domain} inurl:.{ext}?id= "mysql_fetch"'

Flat / legacy:
    templates:
      admin:
        mode: soft
        dorks:
          - 'inurl:admin intitle:login'

Generation modes (additive hierarchy)
--------------------------------------
    soft       — soft templates only
    medium     — soft + medium
    aggressive — soft + medium + aggressive
    None       — no filter; all templates included regardless of mode tag
"""

import yaml
import itertools
import re
import random
from pathlib import Path


MODE_HIERARCHY: dict = {
    "soft":       ["soft"],
    "medium":     ["soft", "medium"],
    "aggressive": ["soft", "medium", "aggressive"],
}


class DorkGenerator:
    """YAML-driven dork generator that expands variable placeholders into search strings.

    Loads a template YAML file, interpolates every {variable} placeholder with
    the values defined in the variables block, and returns a deduplicated,
    shuffled list of dork strings ready to pass to a search engine.

    The total combination count is capped at max_combinations per template to
    avoid memory explosions when variable lists are large. When the theoretical
    total exceeds the cap, random sampling is used instead of full enumeration.

    Attributes:
        yaml_file (Path):        Resolved path to the loaded template file.
        max_combinations (int):  Per-template combination ceiling (default 800).
        variables (dict):        Variable name -> list-of-values mapping.
        templates (dict):        Category name -> template data mapping.
    """

    def __init__(self, yaml_file: str, max_combinations: int = 800):
        """Initialise the generator and immediately load the template file.

        Args:
            yaml_file (str):        Path to the YAML template file.
            max_combinations (int): Maximum dork combinations per template.
                                    Random sampling is used when exceeded.
                                    Defaults to 800.

        Raises:
            FileNotFoundError: If yaml_file does not exist on disk.
            ValueError:        If the YAML file does not contain a top-level dict.
        """
        self.yaml_file = Path(yaml_file)
        self.max_combinations = max_combinations
        self.variables: dict = {}
        self.templates: dict = {}
        self._load()

    # ─────────────────────────────────────────────
    # LOAD
    # ─────────────────────────────────────────────

    def _load(self):
        """Parse the YAML template file and populate self.variables and self.templates.

        Raises:
            FileNotFoundError: If self.yaml_file does not exist.
            ValueError:        If the parsed YAML is not a top-level dict.
        """
        if not self.yaml_file.exists():
            raise FileNotFoundError(f"Template file not found: {self.yaml_file}")

        with open(self.yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML structure in: {self.yaml_file}")

        self.variables = data.get("variables", {})
        self.templates = data.get("templates", {})

    # ─────────────────────────────────────────────
    # PLACEHOLDER UTILITIES
    # ─────────────────────────────────────────────

    def _extract_placeholders(self, template: str) -> list:
        """Return unique placeholder names from template, preserving first-seen order.

        Args:
            template (str): A dork template string containing {placeholder} tokens.

        Returns:
            list[str]: Unique placeholder names in first-appearance order.
        """
        seen = set()
        unique = []
        for ph in re.findall(r"\{(.*?)\}", template):
            if ph not in seen:
                seen.add(ph)
                unique.append(ph)
        return unique

    def _validate_placeholders(self, template: str, category: str):
        """Warn to stdout if a placeholder has no matching variable definition.

        Args:
            template (str):  Dork template string to validate.
            category (str):  Category name used in the warning message for context.
        """
        placeholders = re.findall(r"\{(.*?)\}", template)
        unknown = [ph for ph in placeholders if ph not in self.variables]
        if unknown:
            print(
                f"[WARNING] Category '{category}': "
                f"unknown placeholder(s) {unknown} in: {template}"
            )

    # ─────────────────────────────────────────────
    # GENERATION
    # ─────────────────────────────────────────────

    def _generate_from_template(self, template: str) -> list:
        """Expand a single template string into a list of concrete dork strings.

        When the total number of combinations (product of all variable list
        lengths) exceeds max_combinations, random sampling is performed before
        expansion to keep memory usage bounded.

        Args:
            template (str): A dork template string with {placeholder} tokens.

        Returns:
            list[str]: Expanded dork strings with all placeholders substituted.
        """
        placeholders = self._extract_placeholders(template)

        if not placeholders:
            return [template]

        value_lists = []
        for ph in placeholders:
            values = self.variables.get(ph)
            if not values:
                values = [f"{{{ph}}}"]
            value_lists.append(values)

        # Estimate the total number of combinations without generating them all
        total = 1
        for vl in value_lists:
            total *= len(vl)

        # Sample before expanding if it exceeds the cap
        if total > self.max_combinations:
            sampled: set = set()
            attempts = 0
            max_attempts = self.max_combinations * 3

            while len(sampled) < self.max_combinations and attempts < max_attempts:
                combo = tuple(random.choice(vl) for vl in value_lists)
                sampled.add(combo)
                attempts += 1

            combinations = list(sampled)
        else:
            combinations = list(itertools.product(*value_lists))

        generated = []
        for combo in combinations:
            result = template
            for ph, value in zip(placeholders, combo):
                result = result.replace(f"{{{ph}}}", str(value))
            generated.append(result)

        return generated

    def _get_dork_list(self, data: dict, allowed_modes: list) -> list:
        """Extract dork template strings from a category dict.

        Supports two YAML structures transparently:

        Structure A — nested (recommended):
            dorks:
              soft:
                - 'dork1'
              medium:
                - 'dork2'
              aggressive:
                - 'dork3'

        Structure B — flat with a single mode field (legacy):
            mode: soft
            dorks:
              - 'dork1'
              - 'dork2'

        Args:
            data (dict):          Category data dict from self.templates.
            allowed_modes (list): Mode names permitted by the active MODE_HIERARCHY,
                                  or None to include all levels.

        Returns:
            list[str]: Raw dork template strings for the given modes.
        """
        raw_dorks = data.get("dorks", [])

        # ── Structure A: dorks is a dict keyed by mode (soft/medium/aggressive) ──
        if isinstance(raw_dorks, dict):
            collected = []
            for level, dork_list in raw_dorks.items():
                # Include only the levels permitted by the mode hierarchy
                if allowed_modes is None or level in allowed_modes:
                    if isinstance(dork_list, list):
                        collected.extend(dork_list)
            return collected

        # ── Structure B: dorks is a flat list; mode is declared at category level ──
        if isinstance(raw_dorks, list):
            template_mode = data.get("mode", "soft")
            if allowed_modes is None or template_mode in allowed_modes:
                return raw_dorks
            return []

        return []

    def generate(self, categories: list = None, mode: str = None) -> list:
        """Generate dorks filtered by category and mode; return deduplicated and shuffled.

        Mode hierarchy (additive):
            soft       — soft templates only
            medium     — soft + medium
            aggressive — soft + medium + aggressive
            None       — no filter; all templates included

        Args:
            categories (list[str] | None): Category names to include.
                                           None includes all categories.
            mode (str | None):             Generation mode string.
                                           None disables mode filtering.

        Returns:
            list[str]: Unique, shuffled dork strings capped at max_combinations.
        """
        all_dorks = []

        selected_templates = self.templates

        if categories:
            selected_templates = {
                k: v for k, v in self.templates.items() if k in categories
            }

        # Resolve the allowed mode levels from the hierarchy
        allowed_modes = MODE_HIERARCHY.get(mode) if mode else None

        for category, data in selected_templates.items():
            dork_templates = self._get_dork_list(data, allowed_modes)

            for template in dork_templates:
                self._validate_placeholders(template, category)
                generated = self._generate_from_template(template)
                all_dorks.extend(generated)

        # Global dedup + shuffle
        all_dorks = list(set(all_dorks))
        random.shuffle(all_dorks)

        # Global safety cap
        if len(all_dorks) > self.max_combinations:
            all_dorks = all_dorks[:self.max_combinations]

        return all_dorks

    # ─────────────────────────────────────────────
    # INTROSPECTION
    # ─────────────────────────────────────────────

    def get_available_categories(self) -> list:
        """Return a sorted list of category names available in the loaded template.

        Returns:
            list[str]: Sorted category names from self.templates.
        """
        return sorted(self.templates.keys())

    def get_available_modes(self) -> list:
        """Return a sorted list of mode names detected across all template entries.

        Automatically handles both nested (dict dorks) and flat (mode field)
        YAML structures without requiring the caller to know which is in use.

        Returns:
            list[str]: Sorted unique mode names found in the template file.
        """
        modes: set = set()
        for data in self.templates.values():
            raw_dorks = data.get("dorks", [])
            if isinstance(raw_dorks, dict):
                modes.update(raw_dorks.keys())
            else:
                modes.add(data.get("mode", "soft"))
        return sorted(modes)

    def get_stats(self) -> dict:
        """Return a statistics dict useful for debugging and reporting.

        Returns:
            dict: Keys:
                yaml_file (str):        Path to the loaded template file.
                categories (list):      Available category names.
                available_modes (list): Mode names found in the file.
                total_templates (int):  Raw template count before expansion.
                variables (dict):       Mapping of variable name to value count.
        """
        total = 0
        for data in self.templates.values():
            raw_dorks = data.get("dorks", [])
            if isinstance(raw_dorks, dict):
                for dlist in raw_dorks.values():
                    if isinstance(dlist, list):
                        total += len(dlist)
            elif isinstance(raw_dorks, list):
                total += len(raw_dorks)

        return {
            "yaml_file":       str(self.yaml_file),
            "categories":      self.get_available_categories(),
            "available_modes": self.get_available_modes(),
            "total_templates": total,
            "variables": {
                k: len(v) for k, v in self.variables.items()
            },
        }
