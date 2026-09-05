# Stun mode

## Stun refreshing

In stun mode, each lawyer has a non-negative stun level. A lawyer may be hit
only when its level equals the minimum level among all current lawyers. An
accepted hit increments that lawyer's level and restarts its five-second stun
timer.

When an accepted hit raises the minimum level of the entire group, the player
receives the all-lawyers-stunned bonus feedback. This permits successive rounds
such as `00000000` to `11111111`, then `21111111` to `22222222`.

When a lawyer's timer expires, its level returns directly to zero. For example,
`21111110` may become `21111111` when the expired lawyer is hit. That raises the
minimum from zero to one, rewards the bonus again, and still prevents a
level-two lawyer from advancing while level-one lawyers remain.

Outside stun mode, lawyer stuns retain the original boolean behavior and cannot
be refreshed while active.

Each completed group level displays `Stun xN` above the local Toon, where `N`
is the maximum stun level currently held by any lawyer. The previous display is
replaced if another group level is completed before it fades.

In top-down view, cursor-driven rotation uses the normal walking animation but
does not override an active pie animation. A short debounce keeps smooth cursor
turning in one continuous animation instead of restarting it each frame.
Positional sounds use the normal
camera as their default listener, and the stun-bonus clock is rendered in a
timer-only overlay in the normal-camera window.

Relax mode remembers the last successful throw time for each lawyer. Returning
to that lawyer cannot trigger another Relax throw until the configured grace
period has elapsed; the UI adjusts this period in 10 ms increments and defaults
to 100 ms.
