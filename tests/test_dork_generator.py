import pytest
from pathlib import Path

from dork_generator import DorkGenerator

TEMPLATES_DIR = Path(__file__).parent.parent / "Templates"
DEFAULT_TMPL = TEMPLATES_DIR / "dorks_templates.yaml"


@pytest.fixture
def gen():
    return DorkGenerator(str(DEFAULT_TMPL))


def test_load_valid_template(gen):
    assert gen.templates, "templates dict should not be empty"


def test_get_available_categories_returns_list(gen):
    cats = gen.get_available_categories()
    assert isinstance(cats, list)
    assert len(cats) > 0


def test_get_available_categories_sorted(gen):
    cats = gen.get_available_categories()
    assert cats == sorted(cats)


def test_generate_returns_list(gen):
    dorks = gen.generate()
    assert isinstance(dorks, list)
    assert len(dorks) > 0


def test_generate_items_are_nonempty_strings(gen):
    dorks = gen.generate()
    for dork in dorks[:50]:
        assert isinstance(dork, str)
        assert len(dork) > 0


def test_generate_mode_soft(gen):
    dorks = gen.generate(mode="soft")
    assert isinstance(dorks, list)


def test_generate_mode_aggressive(gen):
    dorks = gen.generate(mode="aggressive")
    soft = gen.generate(mode="soft")
    assert len(dorks) >= len(soft), "aggressive should produce >= dorks than soft"


def test_generate_respects_max_combinations():
    limit = 10
    g = DorkGenerator(str(DEFAULT_TMPL), max_combinations=limit)
    dorks = g.generate()
    assert len(dorks) <= limit


def test_generate_category_filter(gen):
    cats = gen.get_available_categories()
    first_cat = cats[0]
    all_dorks = gen.generate()
    filtered = gen.generate(categories=[first_cat])
    assert len(filtered) <= len(all_dorks)


def test_generate_no_duplicates(gen):
    dorks = gen.generate()
    assert len(dorks) == len(set(dorks)), "generate() must deduplicate results"


def test_get_stats_keys(gen):
    stats = gen.get_stats()
    for key in ("yaml_file", "categories", "available_modes", "total_templates", "variables"):
        assert key in stats, f"missing key: {key}"


def test_file_not_found():
    with pytest.raises(FileNotFoundError):
        DorkGenerator("nonexistent_template.yaml")


def test_invalid_yaml_structure(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- not\n- a\n- dict\n", encoding="utf-8")
    with pytest.raises(ValueError):
        DorkGenerator(str(bad))
