# Magic words

This file documents every magic word registered by
`toontown/spellbook/MagicWordIndex.py`.

## Using magic words

Magic words are entered as chat messages. The default activator is `~` (it can
be changed in the client's `magic-word-activator` setting). Names are
case-insensitive, and the class name shown below is always a valid command name
in addition to its aliases.

The number of activators selects the target:

| Form | Target |
| --- | --- |
| `~~~word` | Yourself |
| `~~word` | The Toon whose nametag you last clicked |
| `~word` | Yourself and the clicked Toon |

The single-activator form still works without a clicked Toon: it affects just
the invoker. Client-side words can only target the invoker, regardless of their
declared target range.

Group selectors may be placed immediately after the activator(s):

| Selector | Meaning | Example |
| --- | --- | --- |
| `singular` | Normal self/clicked-Toon targeting | `~~~singularsethp 50` |
| `zone` | Other player-controlled Toons in the invoker's zone | `~zonesethp 50` |
| `server` | Other player-controlled Toons throughout the district | `~serversethp 50` |
| `rank<N>` | Other Toons whose numeric access level is exactly `N` | `~rank300sethp 50` |

The chosen activator range still applies with a group selector. For example,
`~zone...` includes the invoker as well as eligible Toons in the zone, while
`~~zone...` excludes the invoker. A Toon may always target itself, but other
targets at the same or a higher rounded access tier are filtered out.

All words require `MODERATOR` access unless noted otherwise. The server may
override a word's required access level (for all of its aliases) in
`config/spellbook.json`. Magic words cannot be used during the Toontorial or
while the invoker is changing zones. Servers running in non-cheaty mode reject
all currently registered words because none are marked administrative.

In syntax examples, `<value>` is required and `[value=default]` is optional.
Arguments containing spaces are only possible in the final argument.

## Toon state and inventory

### `SetHP <hp>`

Aliases: `hp`, `setlaff`, `laff`

Sets current laff to an integer from `-1` through the target's maximum laff.
Values below 1 make the Toon sad, unless immortal mode is enabled.

Example: `~~~hp 50`

### `SetMaxHP <maxhp>`

Aliases: `maxhp`, `setmaxlaff`, `maxlaff`

Sets maximum laff to an integer from 15 through 137, then fully heals the
target.

Example: `~~~maxlaff 137`

### `MaxToon`

Aliases: `max`, `idkfa`  
Required access: `ADMIN`

Maxes gag-track access, gag experience and inventory, gag and quest capacity,
laff, wallet and bank balances, quest reward history, Cog disguises, and Cog
suit types and levels. It also clears current quests.

Example: `~~~maxToon`

### `Inventory [command=""] [track=""] [level=0] [amount=0]`

Aliases: `gags`, `inv`

Changes the target's gag inventory. `restock`, `max`, `all`, `fill`, or an
omitted command fills the inventory. `empty`, `zero`, `null`, `clear`, `none`,
or `reset` empties it. The `track`, `level`, and `amount` arguments are accepted
but are not currently implemented; an unrecognized command has no effect.

Examples: `~~~inventory`, `~~~inv empty`

### `SetPinkSlips [amount=255]`

Aliases: `pinkslips`, `fires`, `setfires`

Sets the target's pink-slip count to `amount`.

Example: `~~~fires 50`

### `GlobalTeleport`

Aliases: `globaltp`, `tpaccess`

Marks every standard teleport hood as visited and grants the target teleport
access to all of them.

Example: `~~~globalTp`

### `ToggleSleep`

Aliases: `sleep`, `nosleep`, `neversleep`, `togglesleeping`, `insomnia`

Toggles sleeping for the target.

### `ToggleImmortal`

Aliases: `immortal`, `invincible`, `invulnerable`

Toggles immunity to damage for the target.

### `ToggleGhost`

Aliases: `ghost`, `invisible`, `spy`

Toggles ghost mode. Enabling it uses ghost mode 2, in which ghost Toons remain
visible to themselves and other ghost Toons.

### `SetGM [iconRequest=0]`

Aliases: `icon`, `seticon`, `gm`, `gmicon`, `setgmicon`

Sets the target's GM icon by numeric ID. `0` clears it. IDs must be between 0
and the number of entries in `TTLocalizer.GM_NAMES`, inclusive.

Example: `~~~gm 1`

### `SetMaxCarry <pouchSize>`

Aliases: `gagpouch`, `pouch`, `gagcapacity`

Sets gag capacity to an integer from 0 through 255. (The in-game error text
says 1 through 255, but the implementation accepts 0.)

Example: `~~~pouch 80`

### `GivePies <type> [amount=-1]`

Alias: `pies`

Gives the target throwable pies. Pie types range from 0 through 7: tart,
fruit-pie slice, cream-pie slice, fruit pie, cream pie, birthday cake, wedding
cake, and CJ evidence. Omitting `amount` gives an infinite supply; otherwise it
must be from 0 through 99. A type of `-1` removes all throwable pies.

Examples: `~~~pies 7`, `~~~pies 4 20`, `~~~pies -1`

### `ToggleInstantKill`

Aliases: `instantkill`, `instakill`

Toggles the target's ability to defeat a Cog with any gag.

## Client and activity controls

### `ToggleOobe`

Alias: `oobe`  
Execution: client-side; self only

Toggles out-of-body camera mode.

Example: `~~~oobe`

### `ToggleRun`

Alias: `run`  
Execution: client-side; self only

Toggles the client's fast debug-running input state.

### `ToggleFPS`

Alias: `fps`

Execution: client-side; self only

Toggles a fixed-width meter in the top-right corner showing instantaneous FPS
over a dark translucent background. Every 500 milliseconds it samples the
most recently completed frame's duration and converts it directly to FPS,
without averaging or smoothing.

### `AbortMinigame`

Aliases: `exitgame`, `exitminigame`, `quitgame`, `quitminigame`, `skipgame`,
`skipminigame`  
Execution: client-side; self only

Sends the local `minigameAbort` event to request that the current minigame end.

### `SkipMiniGolfHole`

Aliases: `skipgolfhole`, `skipgolf`, `skiphole`

Ends the invoker's current golf hole. On the final hole it advances directly to
the reward state. Despite accepting normal target syntax, the implementation
locates the course containing the invoker.

### `AbortGolfCourse`

Aliases: `abortminigolf`, `abortgolf`, `abortcourse`, `leavegolf`, `leavecourse`

Aborts the golf course containing the invoker. Despite accepting normal target
syntax, the implementation locates the course containing the invoker.

### `Minigame <command> [minigame=""] [difficulty=0]`

Alias: `mg`

Teleports the target to a trolley minigame or requests the next minigame.

- `teleport <name-or-ID> [difficulty]` (also `tp`) creates the minigame and
  teleports the target; the target must be in a playground.
- `request <name-or-ID> [difficulty]` (also `next`) selects the next minigame.
- A minigame name may be used directly as `command`; the word infers teleport
  in a playground and request elsewhere.
- Difficulty `0` means to use the normal/default difficulty.

Examples: `~~~mg teleport cannonGame 0.5`, `~~~minigame request 3`

### `Quests <command> [index=-1]`

Aliases: `quest`, `tasks`, `task`, `toontasks`

`finish` completes the quest at the zero-based `index`. Omitting the index (or
using `-1`) completes every current quest. No other command is implemented.

Examples: `~~~quests finish`, `~~~quest finish 0`

## Teleporting and encounters

### `Teleport [zoneName=""]`

Aliases: `tp`, `goto`

Teleports the target to one of these exact, lowercase zone keys:

| Key | Destination |
| --- | --- |
| `ttc` | Toontown Central |
| `dd` | Donald's Dock |
| `dg` | Daisy Gardens |
| `mml` | Minnie's Melodyland |
| `tb` | The Brrrgh |
| `ddl` | Donald's Dreamland |
| `gs` | Goofy Speedway |
| `oz`, `aa` | Outdoor Zone / Acorn Acres |
| `gz` | Golf Zone |
| `sbhq` | Sellbot HQ |
| `factory` | Sellbot Factory exterior |
| `cbhq` | Cashbot HQ |
| `lbhq` | Lawbot HQ |
| `bbhq` | Bossbot HQ |

Example: `~~~tp ddl`

### `Factory [sideEnterace=0]`

Creates a Sellbot Factory for the target and teleports them inside. A value
greater than 0 selects side entrance; 0 or a negative value selects front
entrance. `sideEnterace` is misspelled in the registered argument name but is
positional in use.

Examples: `~~~factory`, `~~~factory 1`

### `BossBattle <command> [type=""] [start=1]`

Alias: `boss`

Creates and controls boss battles:

- `create <vp|cfo|cj|ceo> [start=1]` creates a battle. A nonzero `start` adds
  the target and enters the waiting/movie flow; `0` creates it in `Frolic`.
- `<vp|cfo|cj|ceo> [start=1]` is shorthand for `create`.
- `list [type]` lists active battles, optionally filtered by boss type.
- `join <index>` joins the zero-based battle index reported by `list`.
- `start` or `stop` starts/restarts the current battle or moves it to `Frolic`.
- `skip` moves to the boss's next state when that boss implements one.
- `final` (also `pie` or `crane`) advances to the final round.
- `kill` (also `victory` or `finish`) advances to `Victory`.

Except for `create`, `list`, and `join`, the invoker must already be known to a
boss battle. Several operations are based on the invoker's battle rather than
the selected target.

Examples: `~~~boss vp`, `~~~boss list`, `~~~boss join 0`, `~~~boss final`

### `Rsc [seatedToons]`

Advances the caller's current CJ battle directly to the scale round while
putting the podium and jury box in their correct post-cannon positions. An
optional value from 0 through 12 simulates that many Toon jurors having been
seated by the caller. With no value, it uses 0 unless the CJ is already in the
scale round, in which case the round is restarted and the current number of
seated Toon jurors is kept. Supplying a value during the scale round restarts
it using the newly simulated result.

Examples: `~~~rsc`, `~~~rsc 8`

## World effects

### `Fireworks [name="newyear"] [hood=""]`

Alias: `firework`

Starts a firework show. Valid names are `newyear`, `newyears`, `summer`,
`combo`, and `party`. With no `hood`, the show starts in the target's current
zone. The only implemented nonempty hood value is `all`, which starts shows in
all supported playground zones. A zone with an active show is skipped.

Examples: `~~~fireworks`, `~~~firework combo all`

## Maintainer notes

The command list is populated by instantiating every `MagicWord` subclass in
`toontown/spellbook/MagicWordIndex.py`; aliases and class names are registered
in lowercase. When adding or changing a command, update this document alongside
that registry. Access overrides in `config/spellbook.json` name a command or
alias and apply to all aliases of that word. Entries that do not match a
registered word are silently ignored.
