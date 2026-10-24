from __future__ import annotations
import json
from pathlib import Path

import discord
import pytest

import classes.my_client as my_client_module
from classes.my_client import MyClient
from constants import DEFAULT_SETTINGS


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MyClient:
    """Client whose settings are stored in a temporary folder."""
    monkeypatch.setattr(my_client_module, "SETTINGS_FOLDER", tmp_path)
    return MyClient(intents=discord.Intents.default())


def write(folder: Path, guild_id: int, content: str) -> None:
    (folder / f"{guild_id}.json").write_text(content, encoding="utf-8")


def read(folder: Path, guild_id: int) -> dict:
    return json.loads((folder / f"{guild_id}.json").read_text(encoding="utf-8"))


class TestLoadSettings:
    def test_missing_file_gives_defaults(self, client: MyClient) -> None:
        assert client.load_settings(1) == DEFAULT_SETTINGS

    def test_completes_missing_keys(self, client: MyClient, tmp_path: Path) -> None:
        write(tmp_path, 1, '{"default_platform": "local"}')
        settings = client.load_settings(1)
        assert settings["default_platform"] == "local"
        assert (
            settings["delete_replies_after"] == DEFAULT_SETTINGS["delete_replies_after"]
        )

    def test_drops_unknown_keys(self, client: MyClient, tmp_path: Path) -> None:
        write(tmp_path, 1, '{"old_key": 1}')
        assert "old_key" not in client.load_settings(1)

    @pytest.mark.parametrize("content", ["{not json", "[1, 2]"])
    def test_invalid_file_gives_defaults(
        self, client: MyClient, tmp_path: Path, content: str
    ) -> None:
        write(tmp_path, 1, content)
        assert client.load_settings(1) == DEFAULT_SETTINGS

    def test_defaults_are_copies(self, client: MyClient) -> None:
        client.load_settings(1)["default_tracks"]["link"] = "changed"
        assert DEFAULT_SETTINGS["default_tracks"]["link"] is None

    def test_rejects_missing_guild(self, client: MyClient) -> None:
        with pytest.raises(ValueError):
            client.load_settings(None)


class TestUpdateSetting:
    def test_writes_the_file(self, client: MyClient, tmp_path: Path) -> None:
        client.update_setting(1, "delete_replies_after", 0)
        assert read(tmp_path, 1)["delete_replies_after"] == 0
        assert (
            read(tmp_path, 1)["default_platform"]
            == DEFAULT_SETTINGS["default_platform"]
        )

    def test_updates_the_connected_player(self, client: MyClient) -> None:
        client.add_player(1)
        client.update_setting(1, "default_platform", "local")
        assert client.get_player(1).default_platform == "local"


class TestInitGuildSettings:
    def test_creates_and_completes_files(
        self, client: MyClient, tmp_path: Path
    ) -> None:
        write(tmp_path, 1, '{"default_platform": "local"}')
        client.init_guild_settings([1, 2])
        assert read(tmp_path, 1)["default_platform"] == "local"
        assert read(tmp_path, 1).keys() == DEFAULT_SETTINGS.keys()
        assert read(tmp_path, 2) == DEFAULT_SETTINGS

    def test_keeps_files_of_left_guilds(self, client: MyClient, tmp_path: Path) -> None:
        write(tmp_path, 3, json.dumps(DEFAULT_SETTINGS))
        client.init_guild_settings([1])
        assert (tmp_path / "3.json").exists()
