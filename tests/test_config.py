import pytest
from pathlib import Path
from societyos.config.loader import load_config
from societyos.config.models import SocietyConfig, AgentConfig

EXAMPLES_DIR = Path(__file__).parent.parent / "configs" / "examples"


class TestLoadConfig:
    def test_loads_startup_board(self):
        cfg = load_config(EXAMPLES_DIR / "startup_board.yaml")
        assert isinstance(cfg, SocietyConfig)
        assert cfg.name == "Startup Board"
        assert len(cfg.agents) == 5

    def test_agent_names_are_correct(self):
        cfg = load_config(EXAMPLES_DIR / "startup_board.yaml")
        names = {a.name for a in cfg.agents}
        assert "CEO" in names
        assert "CFO" in names
        assert "Journalist" in names

    def test_decision_strategy(self):
        cfg = load_config(EXAMPLES_DIR / "startup_board.yaml")
        assert cfg.decision_strategy == "weighted_vote"

    def test_rules_are_loaded(self):
        cfg = load_config(EXAMPLES_DIR / "startup_board.yaml")
        assert "CFO has financial veto" in cfg.rules

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            load_config("does_not_exist.yaml")

    def test_invalid_yaml_raises(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text(":::not valid yaml:::")
        with pytest.raises(Exception):
            load_config(bad)


class TestSocietyConfigValidation:
    def test_duplicate_agent_names_raise(self):
        with pytest.raises(ValueError, match="unique"):
            SocietyConfig(
                name="Test",
                agents=[
                    AgentConfig(name="Alice", role="r", personality="p"),
                    AgentConfig(name="Alice", role="r2", personality="p2"),
                ],
            )

    def test_weight_out_of_range_raises(self):
        with pytest.raises(ValueError):
            AgentConfig(name="X", role="r", personality="p", weight=99.0)

    def test_defaults_are_sensible(self):
        cfg = SocietyConfig(
            name="Minimal",
            agents=[AgentConfig(name="Solo", role="Generalist", personality="neutral")],
        )
        assert cfg.max_rounds == 5
        assert cfg.decision_strategy == "weighted_vote"
        assert cfg.benchmark_vs_single_agent is True
