"""Read a Terraform directory with python-hcl2 and give plain Python values back."""

import pathlib

import hcl2


def plain(value):
    """python-hcl2 keeps the quotes of string literals and adds __is_block__ markers: drop both."""
    if isinstance(value, str):
        if len(value) >= 2 and value[0] == value[-1] == '"':
            return value[1:-1]
        return value
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {plain(key): plain(item) for key, item in value.items() if key != "__is_block__"}
    return value


class TerraformConfig:
    def __init__(self, directory):
        self.resources = {}
        self.data = {}
        self.variables = {}
        self.locals = {}
        self.providers = {}
        self.terraform = []
        for path in sorted(pathlib.Path(directory).glob("*.tf")):
            with path.open(encoding="utf-8") as handle:
                parsed = plain(hcl2.load(handle))
            for block in parsed.get("resource", []):
                for rtype, named in block.items():
                    self.resources.setdefault(rtype, {}).update(named)
            for block in parsed.get("data", []):
                for dtype, named in block.items():
                    self.data.setdefault(dtype, {}).update(named)
            for block in parsed.get("variable", []):
                self.variables.update(block)
            for block in parsed.get("locals", []):
                self.locals.update(block)
            for block in parsed.get("provider", []):
                self.providers.update(block)
            self.terraform.extend(parsed.get("terraform", []))

    def resource(self, rtype, name):
        return self.resources[rtype][name]

    def default(self, variable):
        return self.variables[variable]["default"]

    def required_providers(self):
        merged = {}
        for block in self.terraform:
            for entry in block.get("required_providers", []):
                merged.update(entry)
        return merged
