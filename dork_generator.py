import yaml
import itertools
import re
import random
from pathlib import Path


class DorkGenerator:

    def __init__(self, yaml_file: str, max_combinations: int = 500):
        self.yaml_file = Path(yaml_file)
        self.max_combinations = max_combinations
        self.variables = {}
        self.templates = {}
        self._load()

    def _load(self):
        if not self.yaml_file.exists():
            raise FileNotFoundError(f"Template file not found: {self.yaml_file}")

        with open(self.yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.variables = data.get("variables", {})
        self.templates = data.get("templates", {})

    def _extract_placeholders(self, template: str):
        return re.findall(r"{(.*?)}", template)

    def _generate_from_template(self, template: str):
        placeholders = self._extract_placeholders(template)

        if not placeholders:
            return [template]

        value_lists = []

        for ph in placeholders:
            values = self.variables.get(ph)
            if not values:
                values = [f"{{{ph}}}"]
            value_lists.append(values)

        combinations = list(itertools.product(*value_lists))

        generated = []
        for combo in combinations:
            result = template
            for ph, value in zip(placeholders, combo):
                result = result.replace(f"{{{ph}}}", str(value))
            generated.append(result)

        return generated

    def generate(self, categories=None, mode=None):
        all_dorks = []

        selected_templates = self.templates

        if categories:
            selected_templates = {
                k: v for k, v in self.templates.items() if k in categories
            }

        for category, data in selected_templates.items():

            template_mode = data.get("mode", "soft")

            # Mode filtering
            if mode and template_mode != mode:
                continue

            templates = data.get("dorks", [])

            for template in templates:
                generated = self._generate_from_template(template)
                all_dorks.extend(generated)

        all_dorks = list(set(all_dorks))
        random.shuffle(all_dorks)

        if len(all_dorks) > self.max_combinations:
            all_dorks = all_dorks[:self.max_combinations]

        return all_dorks

