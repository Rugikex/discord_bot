# Discord Music Bot

A Discord music bot with slash commands. It plays YouTube videos and playlists, YouTube searches and audio files stored on the machine running the bot.

## Features

- Play a YouTube link, a playlist or a search (pick one of 5 results with buttons)
- Play local audio files (`.mp3`, `.wav`, `.flac`) from the `music/` folder
- Queue management: skip, move, remove, shuffle, loop, pagination
- Per-server settings: default platform, default tracks, welcome sound, reply lifetime

## Requirements

- [**uv**](https://docs.astral.sh/uv/getting-started/installation/) (it installs Python 3.12 if needed)
- **FFmpeg** installed and available in the `PATH` (`ffmpeg -version` must work)
- [**Deno**](https://docs.deno.com/runtime/getting_started/installation/) installed and available in the `PATH` (`deno --version` must work). yt-dlp needs it to solve YouTube's JavaScript challenges.
- A Discord application with a bot (see below)

## Discord setup

1. Create an application on the [Discord Developer Portal](https://discord.com/developers/applications).
2. In the **Bot** tab:
   - click **Reset Token** and keep the token for the `.env` file;
   - under **Privileged Gateway Intents**, enable **Server Members Intent**. Without it, the bot stops at startup with `PrivilegedIntentsRequired`.
3. Invite the bot with this link, after replacing `CLIENT_ID` with the **Application ID** of the **General Information** tab:

   ```
   https://discord.com/oauth2/authorize?client_id=CLIENT_ID&scope=bot+applications.commands&permissions=3263488
   ```

   It grants: View Channels, Send Messages, Embed Links, Attach Files, Read Message History, Connect and Speak.

## Installation

```bash
git clone git@github.com:Rugikex/discord_bot.git
cd discord_bot

uv sync
```

Create the `.env` file from the template and put your token in it:

```bash
cp .env.example .env
```

```env
DISCORD_KEY=your_bot_token
```

## Run

```bash
uv run main.py
```

The slash commands are synchronized at startup. Discord can take a few minutes to display new or changed commands.

## Configuration

| File / folder | Role |
|---|---|
| `.env` | Bot token (`DISCORD_KEY`) |
| `music/` | Local audio files used by `/add_local_tracks` and `/play platform:Local files`. Create it if needed. |
| `blacklist.txt` | Discord user IDs not allowed to use the bot, one per line |
| `guild_settings/` | One JSON file per server, created automatically. Edit it with `/settings` rather than by hand. |

## Commands

### Playback

| Command | Description |
|---|---|
| `/play track [platform] [position]` | Play a URL, a playlist or search terms. `position` inserts the tracks at this place in the queue. |
| `/play_next track [platform] [shuffle]` | Play this track right after the current one |
| `/play_shuffle track [platform]` | Play the tracks and shuffle the queue |
| `/play_default [shuffle] [position]` | Play the default tracks of the server (see `/settings default_tracks`) |
| `/add_local_tracks [shuffle] [position]` | Add every file of the `music/` folder to the queue |
| `/pause` / `/resume` | Pause or resume the current track |
| `/skip [number]` | Skip the current track, or the first `number` tracks |
| `/stop` | Stop playing and empty the queue |
| `/loop` | Loop the current track, or stop looping |
| `/nowplaying` | Display the current track and its progress |
| `/disconnect` | Disconnect the bot from the voice channel |

`platform` is **YouTube** or **Local files**. Without it, the default platform of the server is used.

### Queue

| Command | Description |
|---|---|
| `/queue [page]` | Display the queue, 10 tracks per page |
| `/move position new_position` | Move a track in the queue |
| `/remove begin [end]` | Remove one track, or the tracks from `begin` to `end` |
| `/shuffle` | Shuffle the queue |
| `/clear` | Empty the queue |

### Settings

Only members with the **Manage Server** permission see these commands by default. Server admins can change this in **Server Settings → Integrations**. The answers are only visible to the user who ran the command.

| Command | Description |
|---|---|
| `/settings show` | Display the settings of the server |
| `/settings default_platform platform` | Platform used when a command doesn't specify one |
| `/settings default_tracks [link] [platform]` | Tracks played by `/play_default`. Without `link`, removes them. |
| `/settings welcome_track [link] [platform]` | Track played when the bot joins a voice channel. Without `link`, disables it. For a local file, give its path, e.g. `music/intro.mp3`. |
| `/settings delete_replies_after seconds` | Seconds before the answers to commands are deleted, from 0 to 600 (default 60). 0 keeps them. |

`/help` lists all the commands in Discord.
