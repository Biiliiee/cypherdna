"""
Unit and CLI integration tests for the CypherDNA Ranker command.
"""

import json
import os
from click.testing import CliRunner
import commands.ranker as ranker_mod


def _patch_ranker_paths(monkeypatch, tmp_path):
    ranker_file = str(tmp_path / "ranker.json")
    strategies_dir = str(tmp_path / "strategies")
    tokens_dir = str(tmp_path / "custom_tokens")
    os.makedirs(strategies_dir, exist_ok=True)
    os.makedirs(tokens_dir, exist_ok=True)
    monkeypatch.setattr(ranker_mod, "RANKER_FILE", ranker_file)
    monkeypatch.setattr(ranker_mod, "STRATEGIES_DIR", strategies_dir)
    monkeypatch.setattr(ranker_mod, "CUSTOM_TOKENS_DIR", tokens_dir)
    return ranker_file, strategies_dir


class TestRankerCommand:
    def test_create_done_saves_dna_file_and_activates(self, monkeypatch, tmp_path):
        ranker_file, strategies_dir = _patch_ranker_paths(monkeypatch, tmp_path)
        runner = CliRunner()

        # Simula criação interativa: 2 padrões + DONE + nome do arquivo .dna
        result = runner.invoke(
            ranker_mod.ranker,
            ["-C"],
            input="NaME+SYMBOL+YEAR\nNAME+NUMBER\nDONE\nminha_corp\n",
            obj={"LANG_PT": True},
        )
        assert result.exit_code == 0

        dna_path = os.path.join(strategies_dir, "minha_corp.dna")
        assert os.path.isfile(dna_path)
        with open(dna_path, "r", encoding="utf-8") as f:
            assert json.load(f) == ["NaME+SYMBOL+YEAR", "NAME+NUMBER"]

        with open(ranker_file, "r", encoding="utf-8") as f:
            assert json.load(f) == ["NaME+SYMBOL+YEAR", "NAME+NUMBER"]

    def test_delete_specific_custom_dna_and_clear_matching_active(self, monkeypatch, tmp_path):
        ranker_file, strategies_dir = _patch_ranker_paths(monkeypatch, tmp_path)
        patterns = ["NaME+SYMBOL+YEAR"]
        dna_path = os.path.join(strategies_dir, "corp_test.dna")
        with open(dna_path, "w", encoding="utf-8") as f:
            json.dump(patterns, f)
        with open(ranker_file, "w", encoding="utf-8") as f:
            json.dump(patterns, f)

        runner = CliRunner()
        result = runner.invoke(
            ranker_mod.ranker,
            ["-D", "corp_test"],
            input="y\n",
            obj={"LANG_PT": False},
        )
        assert result.exit_code == 0
        assert not os.path.exists(dna_path)
        with open(ranker_file, "r", encoding="utf-8") as f:
            assert json.load(f) == []

    def test_delete_all_removes_all_custom_dna_files_and_active(self, monkeypatch, tmp_path):
        ranker_file, strategies_dir = _patch_ranker_paths(monkeypatch, tmp_path)
        for name in ("strat1.dna", "strat2.dna"):
            with open(os.path.join(strategies_dir, name), "w", encoding="utf-8") as f:
                json.dump(["NAME+YEAR"], f)
        with open(ranker_file, "w", encoding="utf-8") as f:
            json.dump(["NAME+YEAR"], f)

        runner = CliRunner()
        result = runner.invoke(
            ranker_mod.ranker,
            ["-D", "all"],
            input="y\n",
            obj={"LANG_PT": True},
        )
        assert result.exit_code == 0
        assert os.listdir(strategies_dir) == []
        with open(ranker_file, "r", encoding="utf-8") as f:
            assert json.load(f) == []

    def test_long_flags_list_preset_use_export(self, monkeypatch, tmp_path):
        ranker_file, strategies_dir = _patch_ranker_paths(monkeypatch, tmp_path)
        runner = CliRunner()

        # --preset corporate ativa sem precisar confirmar
        res_p = runner.invoke(ranker_mod.ranker, ["--preset", "corporate"], obj={"LANG_PT": True})
        assert res_p.exit_code == 0
        with open(ranker_file, "r", encoding="utf-8") as f:
            assert json.load(f) == ranker_mod.PRESETS["corporate"]["patterns"]

        # --export salva para strategies/exported.dna
        res_e = runner.invoke(ranker_mod.ranker, ["--export", "exported"], obj={"LANG_PT": True})
        assert res_e.exit_code == 0
        assert os.path.isfile(os.path.join(strategies_dir, "exported.dna"))

        # --delete active limpa apenas o ativo mantendo exported.dna
        res_da = runner.invoke(ranker_mod.ranker, ["--delete", "active"], input="y\n", obj={"LANG_PT": False})
        assert res_da.exit_code == 0
        assert os.path.isfile(os.path.join(strategies_dir, "exported.dna"))
        with open(ranker_file, "r", encoding="utf-8") as f:
            assert json.load(f) == []

        # --use exported recarrega exported.dna
        res_i = runner.invoke(ranker_mod.ranker, ["--use", "exported"], obj={"LANG_PT": False})
        assert res_i.exit_code == 0
        with open(ranker_file, "r", encoding="utf-8") as f:
            assert json.load(f) == ranker_mod.PRESETS["corporate"]["patterns"]

        # --list exibe ativo, presets e arquivos .dna
        res_l = runner.invoke(ranker_mod.ranker, ["--list"], obj={"LANG_PT": True})
        assert res_l.exit_code == 0
        assert "exported" in res_l.output
        assert "corporate" in res_l.output

    def test_conflicting_flags_rejected(self, monkeypatch, tmp_path):
        _patch_ranker_paths(monkeypatch, tmp_path)
        runner = CliRunner()
        res = runner.invoke(ranker_mod.ranker, ["-L", "-C"], obj={"LANG_PT": True})
        assert res.exit_code == 0
        assert "apenas uma ação" in res.output.lower()

    def test_delete_menu_renders_clean_prompts_without_raw_tags(self, monkeypatch, tmp_path):
        ranker_file, strategies_dir = _patch_ranker_paths(monkeypatch, tmp_path)
        dna_path = os.path.join(strategies_dir, "Naruto.dna")
        with open(dna_path, "w", encoding="utf-8") as f:
            json.dump(["NARUTOCHARACTER+YEAR"], f)
        with open(ranker_file, "w", encoding="utf-8") as f:
            json.dump(["NARUTOCHARACTER+YEAR"], f)

        runner = CliRunner()
        # Cancela exclusão na confirmação do item 1 e valida ausência de tags cruas + singular
        res_cancel = runner.invoke(
            ranker_mod.ranker,
            ["-D"],
            input="1\nn\n",
            obj={"LANG_PT": True},
        )
        assert res_cancel.exit_code == 0
        for raw_tag in ("[bold", "[/bold", "[white]", "[yellow]", "[red]", "[cyan]", "[dim]"):
            assert raw_tag not in res_cancel.output
        assert "[1] Naruto.dna (1 regra)" in res_cancel.output
        assert "[A]" in res_cancel.output
        assert "[ALL]" in res_cancel.output
        assert "[?] Apagar permanentemente a estratégia customizada Naruto.dna? [s/N]:" in res_cancel.output
        assert os.path.isfile(dna_path)

        # Confirma exclusão em PT usando 's' (sim)
        res_confirm = runner.invoke(
            ranker_mod.ranker,
            ["-D", "Naruto"],
            input="s\n",
            obj={"LANG_PT": True},
        )
        assert res_confirm.exit_code == 0
        assert "[bold" not in res_confirm.output
        assert not os.path.exists(dna_path)
        with open(ranker_file, "r", encoding="utf-8") as f:
            assert json.load(f) == []
