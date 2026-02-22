# Google Dork Generator I.C.W.T 2026
import yaml
import itertools
import re
import random
from pathlib import Path


MODE_HIERARCHY = {
    "soft":       ["soft"],
    "medium":     ["soft", "medium"],
    "aggressive": ["soft", "medium", "aggressive"]
}


class DorkGenerator:

    def __init__(self, yaml_file: str, max_combinations: int = 3500):
        self.yaml_file = Path(yaml_file)
        self.max_combinations = max_combinations
        self.variables = {}
        self.templates = {}
        self._load()

    # ─────────────────────────────────────────────
    # LOAD
    # ─────────────────────────────────────────────

    def _load(self):
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
        """Estrae i placeholder mantenendo l'ordine ma senza duplicati."""
        seen = set()
        unique = []
        for ph in re.findall(r"\{(.*?)\}", template):
            if ph not in seen:
                seen.add(ph)
                unique.append(ph)
        return unique

    def _validate_placeholders(self, template: str, category: str):
        """Avvisa se un placeholder non è definito nelle variabili."""
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
        """
        Generates all combinations for a single template.
        Sampling occurs BEFORE expanding to avoid
        memory explosions on templates with many variables.
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

        # Sample before expanding if it exceeds the limit
        if total > self.max_combinations:
            sampled = set()
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
        """
        Extracts dorks from a category by supporting two YAML structures:

        Structure A — nested (recommended):
            dorks:
              soft:
                - 'dork1'
              medium:
                - 'dork2'
              aggressive:
                - 'dork3'

        Structure B — flat with single mode (legacy):
            mode: soft
            dorks:
              - 'dork1'
              - 'dork2'
        """
        raw_dorks = data.get("dorks", [])

        # ── Structure A: dorks is a dict with keys soft/medium/aggressive ──
        if isinstance(raw_dorks, dict):
            collected = []
            for level, dork_list in raw_dorks.items():
                # Includi solo i livelli consentiti dalla gerarchia
                if allowed_modes is None or level in allowed_modes:
                    if isinstance(dork_list, list):
                        collected.extend(dork_list)
            return collected

        # ── Structure B: dorks is a flat list, mode is at category level ──
        if isinstance(raw_dorks, list):
            template_mode = data.get("mode", "soft")
            if allowed_modes is None or template_mode in allowed_modes:
                return raw_dorks
            return []

        return []

    def generate(self, categories: list = None, mode: str = None) -> list:
        """
        Generates dorks filtered by category and mode.

        Mode hierarchy:
          soft       → solo template "soft"
          medium     → "soft" + "medium"
          aggressive → "soft" + "medium" + "aggressive"
          None       → nessun filtro, tutti i template
        """
        all_dorks = []

        selected_templates = self.templates

        if categories:
            selected_templates = {
                k: v for k, v in self.templates.items() if k in categories
            }

        # Calculate the allowed modes based on the hierarchy
        allowed_modes = MODE_HIERARCHY.get(mode) if mode else None

        for category, data in selected_templates.items():
            dork_templates = self._get_dork_list(data, allowed_modes)

            for template in dork_templates:
                # Validate placeholders before generating
                self._validate_placeholders(template, category)
                generated = self._generate_from_template(template)
                all_dorks.extend(generated)

        # Dedup globale + shuffle
        all_dorks = list(set(all_dorks))
        random.shuffle(all_dorks)

        # Global safety limit
        if len(all_dorks) > self.max_combinations:
            all_dorks = all_dorks[:self.max_combinations]

        return all_dorks

    # ─────────────────────────────────────────────
    # INTROSPECTION
    # ─────────────────────────────────────────────

    def get_available_categories(self) -> list:
        """Returns the categories available in the loaded template."""
        return sorted(self.templates.keys())

    def get_available_modes(self) -> list:
        """
        Returns the available modes by automatically detecting bothnested and flat structures..
        """
        modes = set()
        for data in self.templates.values():
            raw_dorks = data.get("dorks", [])
            if isinstance(raw_dorks, dict):
                modes.update(raw_dorks.keys())
            else:
                modes.add(data.get("mode", "soft"))
        return sorted(modes)

    def get_stats(self) -> dict:
        """Useful statistics for debugging and reporting."""
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
            "yaml_file":        str(self.yaml_file),
            "categories":       self.get_available_categories(),
            "available_modes":  self.get_available_modes(),
            "total_templates":  total,
            "variables": {
                k: len(v) for k, v in self.variables.items()
            }
        }
