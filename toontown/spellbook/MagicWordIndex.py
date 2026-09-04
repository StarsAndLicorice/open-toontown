##################################################
# The Toontown Offline Magic Word Manager
##################################################
# Author: Benjamin Frisby
# Copyright: Copyright 2020, Toontown Offline
# Credits: Benjamin Frisby, John Cote, Ruby Lord, Frank, Nick, Little Cat, Ooowoo
# License: MIT
# Version: 1.0.0
# Email: belloqzafarian@gmail.com
##################################################

import collections
import json
import math
import random
import re
import time
import types

from direct.distributed.ClockDelta import *
from direct.interval.IntervalGlobal import *
from direct.showbase.DirectObject import DirectObject
from direct.showbase.PythonUtil import *
from panda3d.otp import NametagGroup, WhisperPopup

from otp.otpbase import OTPGlobals, OTPLocalizer
from otp.otpbase.PythonUtil import *

from . import MagicWordConfig

magicWordIndex = collections.OrderedDict()


class MagicWord(DirectObject):
    notify = DirectNotifyGlobal.directNotify.newCategory("MagicWord")

    # Whether this Magic word should be considered "hidden"
    # If your Toontown source has a page for Magic Words in the Sthickerbook, this will be useful for that
    hidden = False

    # Whether this Magic Word is an administrative command or not
    # Good for config settings where you want to disable cheaty Magic Words, but still want moderation ones
    administrative = False

    # List of names that will also invoke this word - a setHP magic word might have "hp", for example
    # A Magic Word will always be callable with its class name, so you don't have to put that in the aliases
    aliases = None

    # Description of the Magic Word
    # If your Toontown source has a page for Magic Words in the Sthickerbook, this will be useful for that
    desc = MagicWordConfig.MAGIC_WORD_DEFAULT_DESC

    # Advanced description that gives the user a lot more information than normal
    # If your Toontown source has a page for Magic Words in the Sthickerbook, this will be useful for that
    advancedDesc = MagicWordConfig.MAGIC_WORD_DEFAULT_ADV_DESC

    # Default example with for commands with no arguments set
    # If your Toontown source has a page for Magic Words in the Sthickerbook, this will be useful for that
    example = ""

    # The minimum access level required to use this Magic Word
    accessLevel = "MODERATOR"

    # A restriction on the Magic Word which sets what kind or set of Distributed Objects it can be used on
    # By default, a Magic Word can affect everyone
    affectRange = [
        MagicWordConfig.AFFECT_SELF,
        MagicWordConfig.AFFECT_OTHER,
        MagicWordConfig.AFFECT_BOTH,
    ]

    # Where the magic word will be executed -- EXEC_LOC_CLIENT or EXEC_LOC_SERVER
    execLocation = MagicWordConfig.EXEC_LOC_INVALID

    # List of all arguments for this word, with the format [(type, isRequired), (type, isRequired)...]
    # If the parameter is not required, you must provide a default argument: (type, False, default)
    arguments = None

    def __init__(self):
        if self.__class__.__name__ != "MagicWord":
            self.aliases = self.aliases if self.aliases is not None else []
            self.aliases.insert(0, self.__class__.__name__)
            self.aliases = [x.lower() for x in self.aliases]
            self.arguments = self.arguments if self.arguments is not None else []

            if len(self.arguments) > 0:
                for arg in self.arguments:
                    argInfo = ""
                    if not arg[MagicWordConfig.ARGUMENT_REQUIRED]:
                        argInfo += "(default: {0})".format(
                            arg[MagicWordConfig.ARGUMENT_DEFAULT]
                        )
                    self.example += "[{0}{1}] ".format(
                        arg[MagicWordConfig.ARGUMENT_NAME], argInfo
                    )

            self.__register()

    def __register(self):
        for wordName in self.aliases:
            if wordName in magicWordIndex:
                self.notify.error(
                    "Duplicate Magic Word name or alias detected! Invalid name: {}".format(
                        wordName
                    )
                )
            magicWordIndex[wordName] = {
                "class": self,
                "classname": self.__class__.__name__,
                "hidden": self.hidden,
                "administrative": self.administrative,
                "aliases": self.aliases,
                "desc": self.desc,
                "advancedDesc": self.advancedDesc,
                "example": self.example,
                "execLocation": self.execLocation,
                "access": self.accessLevel,
                "affectRange": self.affectRange,
                "args": self.arguments,
            }

    def loadWord(self, air=None, cr=None, invokerId=None, targets=None, args=None):
        self.air = air
        self.cr = cr
        self.invokerId = invokerId
        self.targets = targets
        self.args = args

    def executeWord(self):
        executedWord = None
        validTargets = len(self.targets)
        for avId in self.targets:
            invoker = None
            toon = None
            if self.air:
                invoker = self.air.doId2do.get(self.invokerId)
                toon = self.air.doId2do.get(avId)
            elif self.cr:
                invoker = self.cr.doId2do.get(self.invokerId)
                toon = self.cr.doId2do.get(avId)
            if hasattr(toon, "getName"):
                name = toon.getName()
            else:
                name = avId

            if not self.validateTarget(toon):
                if len(self.targets) > 1:
                    validTargets -= 1
                    continue
                return "{} is not a valid target!".format(name)

            # TODO: Should we implement locking?
            # if toon.getLocked() and not self.administrative:
            #     if len(self.targets) > 1:
            #         validTargets -= 1
            #         continue
            #     return "{} is currently locked. You can only use administrative commands on them.".format(name)

            if invoker.getAccessLevel() <= toon.getAccessLevel() and toon != invoker:
                if len(self.targets) > 1:
                    validTargets -= 1
                    continue
                targetAccess = OTPGlobals.AccessLevelDebug2Name.get(
                    OTPGlobals.AccessLevelInt2Name.get(toon.getAccessLevel())
                )
                invokerAccess = OTPGlobals.AccessLevelDebug2Name.get(
                    OTPGlobals.AccessLevelInt2Name.get(invoker.getAccessLevel())
                )
                return "You don't have a high enough Access Level to target {0}! Their Access Level: {1}. Your Access Level: {2}.".format(
                    name, targetAccess, invokerAccess
                )

            if self.execLocation == MagicWordConfig.EXEC_LOC_CLIENT:
                self.args = json.loads(self.args)

            executedWord = self.handleWord(invoker, avId, toon, *self.args)
        # If you're only using the Magic Word on one person and there is a response, return that response
        if executedWord and len(self.targets) == 1:
            return executedWord
        # If the amount of targets is higher than one...
        elif validTargets > 0:
            # And it's only 1, and that's yourself, return None
            if validTargets == 1 and self.invokerId in self.targets:
                return None
            # Otherwise, state how many targets you executed it on
            return "Magic Word successfully executed on %s target(s)." % validTargets
        else:
            return "Magic Word unable to execute on any targets."

    def validateTarget(self, target):
        if self.air:
            from toontown.toon.DistributedToonAI import DistributedToonAI

            return isinstance(target, DistributedToonAI)
        elif self.cr:
            from toontown.toon.DistributedToon import DistributedToon

            return isinstance(target, DistributedToon)
        return False

    def handleWord(self, invoker, avId, toon, *args):
        raise NotImplementedError


class SetHP(MagicWord):
    aliases = ["hp", "setlaff", "laff"]
    desc = "Sets the target's current laff."
    advancedDesc = (
        "This Magic Word will change the current amount of laff points the target has to whichever "
        "value you specify. You are only allowed to specify a value between -1 and the target's maximum "
        "laff points. If you specify a value less than 1, the target will instantly go sad unless they "
        "are in Immortal Mode."
    )
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("hp", int, True)]

    def handleWord(self, invoker, avId, toon, *args):
        hp = args[0]

        if not -1 <= hp <= toon.getMaxHp():
            return "Can't set {0}'s laff to {1}! Specify a value between -1 and {0}'s max laff ({2}).".format(
                toon.getName(), hp, toon.getMaxHp()
            )

        if hp <= 0 and toon.immortalMode:
            return (
                "Can't set {0}'s laff to {1} because they are in Immortal Mode!".format(
                    toon.getName(), hp
                )
            )

        toon.b_setHp(hp)
        return "{}'s laff has been set to {}.".format(toon.getName(), hp)


class SetMaxHP(MagicWord):
    aliases = ["maxhp", "setmaxlaff", "maxlaff"]
    desc = "Sets the target's max laff."
    advancedDesc = (
        "This Magic Word will change the maximum amount of laff points the target has to whichever value "
        "you specify. You are only allowed to specify a value between 15 and 137 laff points."
    )
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("maxhp", int, True)]

    def handleWord(self, invoker, avId, toon, *args):
        maxhp = args[0]

        if not 15 <= maxhp <= 137:
            return "Can't set {}'s max laff to {}! Specify a value between 15 and 137.".format(
                toon.getName(), maxhp
            )

        toon.b_setMaxHp(maxhp)
        toon.toonUp(maxhp)
        return "{}'s max laff has been set to {}.".format(toon.getName(), maxhp)


class ToggleOobe(MagicWord):
    aliases = ["oobe"]
    desc = "Toggles the out of body experience mode, which lets you move the camera freely."
    advancedDesc = (
        "This Magic Word will toggle what is known as 'Out Of Body Experience' Mode, hence the name "
        "'Oobe'. When this mode is active, you are able to move the camera around with your mouse- "
        "though your camera will still follow your Toon."
    )
    execLocation = MagicWordConfig.EXEC_LOC_CLIENT

    def handleWord(self, invoker, avId, toon, *args):
        base.oobe()
        return "Oobe mode has been toggled."


class ToggleRun(MagicWord):
    aliases = ["run"]
    desc = "Toggles run mode, which gives you a faster running speed."
    advancedDesc = (
        "This Magic Word will toggle Run Mode. When this mode is active, the target can run around at a "
        "very fast speed."
    )
    execLocation = MagicWordConfig.EXEC_LOC_CLIENT

    def handleWord(self, invoker, avId, toon, *args):
        from direct.showbase.InputStateGlobal import inputState

        inputState.set("debugRunning", not inputState.isSet("debugRunning"))
        return "Run mode has been toggled."


class ToggleFPS(MagicWord):
    aliases = ["fps"]
    desc = "Toggles an instantaneous frame-rate meter."
    execLocation = MagicWordConfig.EXEC_LOC_CLIENT

    taskName = "magic-word-fps-meter"
    meterName = "magicWordFpsMeter"
    updateInterval = 0.5

    def __updateMeter(self, task=None):
        frameTime = globalClock.getDt()
        fps = 1.0 / frameTime if frameTime > 0.0 else 0.0
        getattr(base, self.meterName).setText("%7.2f FPS" % fps)
        if task is not None:
            return task.again

    def handleWord(self, invoker, avId, toon, *args):
        if hasattr(base, self.meterName):
            taskMgr.remove(self.taskName)
            getattr(base, self.meterName).destroy()
            delattr(base, self.meterName)
            return "Frame-rate meter hidden."

        from direct.gui.OnscreenText import OnscreenText
        from panda3d.core import TextNode

        meter = OnscreenText(
            parent=base.a2dpTopRight,
            text="",
            pos=(0.0, -0.04),
            scale=0.04,
            align=TextNode.ARight,
            font=loader.loadFont("phase_3/models/fonts/CourierBold.ttf"),
            fg=(0.0, 1.0, 0.0, 1.0),
            bg=(0.0, 0.0, 0.0, 0.5),
            mayChange=True,
            drawOrder=1000,
        )
        meter.textNode.setCardAsMargin(0.0, 1.0, 0.0, 1.0)
        meter.setBin("fixed", 100000)
        meter.setDepthTest(False)
        meter.setDepthWrite(False)
        setattr(base, self.meterName, meter)
        self.__updateMeter()
        taskMgr.remove(self.taskName)
        taskMgr.doMethodLater(self.updateInterval, self.__updateMeter, self.taskName)
        return "Frame-rate meter shown."


class SetMaxFps(MagicWord):
    aliases = ["maxfps"]
    desc = "Sets a client-side frame-rate cap; 0 removes it."
    execLocation = MagicWordConfig.EXEC_LOC_CLIENT
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [("fps", float, True)]

    def handleWord(self, invoker, avId, toon, *args):
        from panda3d.core import ClockObject

        fps = args[0]
        if not math.isfinite(fps) or fps < 0.0:
            return "The maximum frame rate must be a finite, non-negative number."
        if fps == 0.0:
            globalClock.setMode(ClockObject.MNormal)
            return "Frame-rate cap removed."

        globalClock.setFrameRate(fps)
        globalClock.setMode(ClockObject.MLimited)
        return "Maximum frame rate set to %g FPS." % fps


class MaxToon(MagicWord):
    aliases = ["max", "idkfa"]
    desc = "Maxes your target toon."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    accessLevel = "ADMIN"

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.coghq import CogDisguiseGlobals
        from toontown.quest import Quests
        from toontown.suit import SuitDNA
        from toontown.toonbase import ToontownGlobals

        # TODO: Handle this better, like giving out all awards, set the quest tier, stuff like that.
        # This is mainly copied from Anesidora just so I can better work on things.
        toon.b_setTrackAccess([1, 1, 1, 1, 1, 1, 1])

        toon.b_setMaxCarry(ToontownGlobals.MaxCarryLimit)
        toon.b_setQuestCarryLimit(ToontownGlobals.MaxQuestCarryLimit)

        toon.experience.maxOutExp()
        toon.d_setExperience(toon.experience.makeNetString())

        toon.inventory.maxOutInv()
        toon.d_setInventory(toon.inventory.makeNetString())

        toon.b_setMaxHp(ToontownGlobals.MaxHpLimit)
        toon.b_setHp(ToontownGlobals.MaxHpLimit)

        toon.b_setMaxMoney(250)
        toon.b_setMoney(toon.maxMoney)
        toon.b_setBankMoney(toon.maxBankMoney)

        toon.b_setQuests([])
        toon.b_setQuestCarryLimit(ToontownGlobals.MaxQuestCarryLimit)
        toon.b_setRewardHistory(Quests.LOOPING_FINAL_TIER, [])

        toon.b_setCogParts([*CogDisguiseGlobals.PartsPerSuitBitmasks])
        toon.b_setCogTypes([SuitDNA.suitsPerDept - 1] * 4)
        toon.b_setCogLevels([ToontownGlobals.MaxCogSuitLevel] * 4)

        return f"Successfully maxed {toon.getName()}!"


class Inventory(MagicWord):
    # by default restock the inventory
    aliases = ["gags", "inv"]
    desc = "This allows you to modify your inventory in various ways."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [
        ("command", str, False, ""),
        ("track", str, False, ""),
        ("level", int, False, 0),
        ("amount", int, False, 0),
    ]

    def handleWord(self, invoker, avId, toon, *args):
        command = args[0]
        # the list of words that can be used to restock the inventory
        restockInvWords = ["restock", "max", "all", "", "fill"]
        # the list of words that can be used to empty the inventory
        emptyInvWords = ["empty", "zero", "null", "clear", "none", "reset"]
        if command in restockInvWords:
            toon.inventory.maxOutInv()
            toon.d_setInventory(toon.inventory.makeNetString())
            return "Maxing out inventory for " + toon.getName() + "."
        if command in emptyInvWords:
            toon.inventory.zeroInv()
            toon.d_setInventory(toon.inventory.makeNetString())
            return "Zeroing inventory for " + toon.getName() + "."


class SetPinkSlips(MagicWord):
    # this command gives the target toon the specified amount of pink slips
    # default is 255
    aliases = ["pinkslips", "fires", "setfires"]
    desc = "Gives the target toon the specified amount of pink slips."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("amount", int, False, 255)]

    def handleWord(self, invoker, avId, toon, *args):
        toon.b_setPinkSlips(args[0])
        return f"Gave {toon.getName()} {args[0]} pink slips!"


class AbortMinigame(MagicWord):
    aliases = [
        "exitgame",
        "exitminigame",
        "quitgame",
        "quitminigame",
        "skipgame",
        "skipminigame",
    ]
    desc = "Aborts an ongoing minigame."
    execLocation = MagicWordConfig.EXEC_LOC_CLIENT
    arguments = []

    def handleWord(self, invoker, avId, toon, *args):
        messenger.send("minigameAbort")
        return "Requested minigame abort."


class SkipMiniGolfHole(MagicWord):
    aliases = ["skipgolfhole", "skipgolf", "skiphole"]
    desc = "Skips the current golf hole."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = []

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.golf.DistributedGolfCourseAI import DistributedGolfCourseAI

        course = None
        for do in simbase.air.doId2do.values():  # For all doids, check whether it's a golf course, then check if our target is part of it.
            if isinstance(do, DistributedGolfCourseAI):
                if invoker.doId in do.avIdList:
                    course = do
                    break
        if not course:
            return "You aren't in a golf course!"

        if course.isPlayingLastHole():  # If the Toon is on the final hole, calling holeOver() will softlock, so instead we move onto the reward screen.
            course.demand("WaitReward")
        else:
            course.holeOver()

        return "Skipped the current hole."


class AbortGolfCourse(MagicWord):
    aliases = ["abortminigolf", "abortgolf", "abortcourse", "leavegolf", "leavecourse"]
    desc = "Aborts the current golf course."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = []

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.golf.DistributedGolfCourseAI import DistributedGolfCourseAI

        course = None
        for do in simbase.air.doId2do.values():  # For all doids, check whether it's a golf course, then check if our target is part of it.
            if isinstance(do, DistributedGolfCourseAI):
                if invoker.doId in do.avIdList:
                    course = do
                    break
        if not course:
            return "You aren't in a golf course!"

        course.setCourseAbort()

        return "Aborted golf course."


class Minigame(MagicWord):
    aliases = ["mg"]
    desc = "Teleport to or request the next trolley minigame."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [
        ("command", str, True),
        ("minigame", str, False, ""),
        ("difficulty", float, False, 0),
    ]

    def handleWord(self, invoker, avId, toon, *args):
        command = args[0]
        minigame = args[1]
        difficulty = args[2]

        from toontown.hood import ZoneUtil
        from toontown.minigame import MinigameCreatorAI
        from toontown.toonbase import ToontownGlobals

        if command in ToontownGlobals.MinigameNames:
            # Shortcut
            minigame = args[0]
            try:
                difficulty = float(args[2])
            except ValueError:
                difficulty = 0

            if toon.zoneId in MinigameCreatorAI.MinigameZoneRefs:
                # Already in minigame zone, assume request
                command = "request"
            elif toon.zoneId == ZoneUtil.getSafeZoneId(toon.zoneId):
                # Assume teleport
                command = "teleport"
            else:
                # Request by default
                command = "request"

        isTeleport = command in ("teleport", "tp")
        isRequest = command in ("request", "next")

        mgId = None
        mgDiff = None if difficulty == 0 else difficulty
        mgKeep = None
        mgSzId = ZoneUtil.getSafeZoneId(toon.zoneId) if isTeleport else None

        if not any((isTeleport, isRequest)):
            return f'Unknown command or minigame "{command}".  Valid commands: "teleport", "request", or a minigame to automatically teleport or request'

        try:
            mgId = int(minigame)
            if mgId not in ToontownGlobals.MinigameIDs:
                return f"Unknown minigame ID {mgId}."
        except:
            if minigame not in ToontownGlobals.MinigameNames:
                return f'Unknown minigame name "{minigame}".'
            mgId = ToontownGlobals.MinigameNames.get(minigame)

        if any((isTeleport, isRequest)):
            if isTeleport:
                if ZoneUtil.isDynamicZone(toon.zoneId) or not toon.zoneId == mgSzId:
                    return (
                        "Target needs to be in a playground to teleport to a minigame."
                    )
                mgSzId = (
                    ToontownGlobals.ToontownCentral
                    if ZoneUtil.isWelcomeValley(mgSzId)
                    else mgSzId
                )
            MinigameCreatorAI.RequestMinigame[avId] = (mgId, mgKeep, mgDiff, mgSzId)
            if isTeleport:
                try:
                    result = MinigameCreatorAI.createMinigame(self.air, [avId], mgSzId)
                except:
                    return f'Unable to create "{minigame}" minigame'

                minigameZone = result["minigameZone"]
                retStr = f'Teleporting {toon.getName()} to minigame "{minigame}"'
                if mgDiff:
                    retStr += f" with difficulty {mgDiff}"
                return (
                    retStr + "...",
                    avId,
                    ["minigame", "minigame", "", mgSzId, minigameZone, 0],
                )

            # isRequest
            retStr = f'Successfully requested minigame "{minigame}"'
            if mgDiff:
                retStr += f" with difficulty {mgDiff}"
            return retStr + "."

        return f'Unknown command or minigame "{command}".  Valid commands: "teleport", "request", or a minigame to automatically teleport or request'


class Quests(MagicWord):
    aliases = ["quest", "tasks", "task", "toontasks"]
    desc = "Quest manupliation"
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("command", str, True), ("index", int, False, -1)]

    def handleWord(self, invoker, avId, toon, *args):
        command = args[0]
        index = args[1]
        """
        Commands:
        - "finish": Finish a task (sets the progress to 1000), finishes all by default
        """
        if command == "finish":
            if index == -1:
                self.air.questManager.completeAllQuestsMagically(toon)
                return "Finished all quests."
            else:
                if self.air.questManager.completeQuestMagically(toon, index):
                    return f"Finished quest {index}."
                return f"Quest {index} not found.  (Hint: Quest indexes start at 0)"
        else:
            return 'Valid commands: "finish"'


class Factory(MagicWord):
    desc = "Quickly start a Sellbot Factory."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("sideEnterace", int, False, 0)]

    def handleWord(self, invoker, avId, toon, *args):
        if not hasattr(self.air, "factoryMgr"):
            return "No factory manager."

        from toontown.toonbase import ToontownGlobals

        zoneId = self.air.factoryMgr.createFactory(
            ToontownGlobals.SellbotFactoryInt, 1 if args[0] > 0 else 0, [avId]
        )
        return (
            "Created factory, teleporting...",
            avId,
            [
                "cogHQLoader",
                "factoryInterior",
                "",
                ToontownGlobals.SellbotHQ,
                zoneId,
                0,
            ],
        )


class BossBattle(MagicWord):
    aliases = ["boss"]
    desc = "Create a new or manupliate the current boss battle."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [
        ("command", str, True),
        ("type", str, False, ""),
        ("start", int, False, 1),
    ]

    def handleWord(self, invoker, avId, toon, *args):
        command = args[0].lower()
        type = args[1].lower()
        start = args[2]

        """
        Commands:
          - create [type] [start: 1]: Creates a boss and teleports to it.
          - start: Starts/Restarts the battle from the beginning.
          - stop: Stops the battle by going to the Frolic state.
          - skip: Skips the boss to the next state (needs getNextState to be implemented).
          - final: Skips the boss to the final round.
          - kill: Skips the boss to the Victory state.
        """

        # create command shortcut:
        if command in ("vp", "cfo", "cj", "ceo"):
            type = command
            command = "create"
            try:
                start = int(args[1])
            except ValueError:
                start = 1

        from toontown.suit.DistributedBossCogAI import AllBossCogs

        boss = None
        for bc in AllBossCogs:
            if bc.isToonKnown(invoker.doId):
                boss = bc
                break

        if command == "create":
            if boss:
                return "You're already in a boss battle.  Please finish this one."
            if type == "vp":
                from toontown.suit.DistributedSellbotBossAI import (
                    DistributedSellbotBossAI,
                )

                boss = DistributedSellbotBossAI(self.air)
            elif type == "cfo":
                from toontown.suit.DistributedCashbotBossAI import (
                    DistributedCashbotBossAI,
                )

                boss = DistributedCashbotBossAI(self.air)
            elif type == "cj":
                from toontown.suit.DistributedLawbotBossAI import (
                    DistributedLawbotBossAI,
                )

                boss = DistributedLawbotBossAI(self.air)
            elif type == "ceo":
                from toontown.suit.DistributedBossbotBossAI import (
                    DistributedBossbotBossAI,
                )

                boss = DistributedBossbotBossAI(self.air)
            else:
                return f'Unknown boss type: "{type}"'

            zoneId = self.air.allocateZone()
            boss.generateWithRequired(zoneId)
            if start:
                boss.addToon(avId)
                boss.b_setState("WaitForToons")
            else:
                boss.b_setState("Frolic")

            self.acceptOnce(
                boss.uniqueName("BossDone"), self.__destroyBoss, extraArgs=[boss]
            )

            respText = f"Created {type.upper()} boss battle"
            if not start:
                respText += " in Frolic state"

            return (
                respText + ", teleporting...",
                toon.doId,
                [
                    "cogHQLoader",
                    "cogHQBossBattle",
                    "movie" if start else "teleportIn",
                    boss.getHoodId(),
                    boss.zoneId,
                    0,
                ],
            )

        elif command == "list":
            # List all the ongoing boss battles.
            dept2name = {"c": "ceo", "l": "cj", "m": "cfo", "s": "vp"}
            name2dept = invertDict(dept2name)

            if not AllBossCogs:
                return "No ongoing boss battles."

            respText = "\nBoss Battles:"

            if type:
                # Filter by boss type
                dept = name2dept.get(type)
                if not dept:
                    return f'Can\'t filter by unknown type "{type.upper()}"'
                bossBattles = (boss for boss in AllBossCogs if boss.dept == dept)
            else:
                bossBattles = AllBossCogs

            for boss in bossBattles:
                index = AllBossCogs.index(boss)
                respText += f"\n - #{index}: {dept2name.get(boss.dept, '???').upper()}, {boss.zoneId}, {boss.state}, {len(boss.involvedToons)}"
            return respText

        elif command == "join":
            # Join an ongoing boss battle.
            if boss:
                return "You're already in a boss battle.  Please finish this one."
            try:
                index = int(type)
            except ValueError:
                return "Boss index not an integer!"

            if index not in range(len(AllBossCogs)):
                return "Index out of range!"

            boss = AllBossCogs[index]
            return (
                "Teleporting to boss battle...",
                toon.doId,
                [
                    "cogHQLoader",
                    "cogHQBossBattle",
                    "",
                    boss.getHoodId(),
                    boss.zoneId,
                    0,
                ],
            )

        # The following commands needs the invoker to be in a boss battle.
        if not boss:
            return 'You ain\'t in a boss battle!  Use the "create" command to create a boss battle.'

        boss.acceptNewToons()
        if command == "start":
            boss.b_setState("WaitForToons")
            return "Boss battle started!"

        elif command == "stop":
            boss.b_setState("Frolic")
            return "Boss battle stopped!"

        elif command == "skip":
            try:
                nextState = boss.getNextState()
            except NotImplementedError:
                return '"getNextState" is not implemented for this boss battle!'
            if nextState:
                boss.b_setState(nextState)
                return f"Skipped to {nextState}!"
            return f'Cannot skip "{boss.getCurrentOrNextState()}" state.'

        elif command in ("final", "pie", "crane"):
            if boss.dept == "c":
                boss.b_setState("BattleFour")
            else:
                boss.b_setState("BattleThree")
            return "Skipped to final round!"

        elif command in ("kill", "victory", "finish"):
            boss.b_setState("Victory")
            return "Killed the boss!"

        # The create command is already described when the invoker is not in a battle.  These are the commands
        # they can use INSIDE the battle.
        return f'Unknown command: "{command}". Valid commands: "start", "stop", "skip", "final", "kill".'

    def __destroyBoss(self, boss):
        bossZone = boss.zoneId
        boss.requestDelete()
        self.air.deallocateZone(bossZone)


class Rsc(MagicWord):
    desc = "Advance a CJ battle to the scale round."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("seatedToons", int, False, -1)]

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.suit.DistributedBossCogAI import AllBossCogs

        boss = None
        for bossCog in AllBossCogs:
            if bossCog.isToonKnown(invoker.doId):
                boss = bossCog
                break

        if boss is None:
            return "You aren't in a boss battle."
        if boss.dept != "l":
            return "The rsc magic word can only be used in a CJ battle."

        requestedJurors = args[0]
        scaleStates = ("BattleThree", "NearVictory")
        if requestedJurors == -1 and boss.getCurrentOrNextState() in scaleStates:
            boss.b_setStunMode(False)
            boss.fixScaleRoundScenery()
            boss.restartScaleRound()
            return "Restarted the CJ scale round with %d seated Toon juror%s." % (
                boss.numToonJurorsSeated,
                "" if boss.numToonJurorsSeated == 1 else "s",
            )

        if requestedJurors == -1:
            requestedJurors = 0
        if requestedJurors < 0 or requestedJurors > 12:
            return "The seated Toon count must be between 0 and 12."

        boss.b_setStunMode(False)
        boss.acceptNewToons()
        boss.rushToScaleRound(invoker.doId, requestedJurors)
        return (
            "Advanced the CJ to the scale round with %d Toon juror%s seated by %s."
            % (requestedJurors, "" if requestedJurors == 1 else "s", invoker.getName())
        )


class StunMode(MagicWord):
    desc = "Enter a safe CJ lawyer-stunning practice round."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.suit.DistributedBossCogAI import AllBossCogs

        boss = None
        for bossCog in AllBossCogs:
            if bossCog.isToonKnown(invoker.doId):
                boss = bossCog
                break

        if boss is None:
            return "You aren't in a boss battle."
        if boss.dept != "l":
            return "The stunMode magic word can only be used in a CJ battle."

        boss.acceptNewToons()
        boss.rushToScaleRound(invoker.doId, 0, stunMode=True)
        return "Entered CJ lawyer stun practice mode."


class GlobalTeleport(MagicWord):
    aliases = ["globaltp", "tpaccess"]
    desc = "Enables teleport access to all zones."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.toonbase import ToontownGlobals

        toon.b_setHoodsVisited(ToontownGlobals.HoodsForTeleportAll)
        toon.b_setTeleportAccess(ToontownGlobals.HoodsForTeleportAll)
        return f"Enabled teleport access to all zones for {toon.getName()}."


class Teleport(MagicWord):
    aliases = ["tp", "goto"]
    desc = "Teleport to a specified zone."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("zoneName", str, False, "")]

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.hood import ZoneUtil
        from toontown.toonbase import ToontownGlobals

        zoneName = args[0]

        # Can add stuff like streets to this too if you wanted, but if you do you'll want it to be a valid zone on that street. eg: 2100 is invalid, but any value 2101 to 2156 is fine.
        # so if you wanted to add a silly street key, theroetically you could do something like this: 'sillystreet': ToontownGlobals.SillyStreet +1,
        zoneName2Id = {
            "ttc": ToontownGlobals.ToontownCentral,
            "dd": ToontownGlobals.DonaldsDock,
            "dg": ToontownGlobals.DaisyGardens,
            "mml": ToontownGlobals.MinniesMelodyland,
            "tb": ToontownGlobals.TheBrrrgh,
            "ddl": ToontownGlobals.DonaldsDreamland,
            "gs": ToontownGlobals.GoofySpeedway,
            "oz": ToontownGlobals.OutdoorZone,
            "aa": ToontownGlobals.OutdoorZone,
            "gz": ToontownGlobals.GolfZone,
            "sbhq": ToontownGlobals.SellbotHQ,
            "factory": ToontownGlobals.SellbotFactoryExt,
            "cbhq": ToontownGlobals.CashbotHQ,
            "lbhq": ToontownGlobals.LawbotHQ,
            "bbhq": ToontownGlobals.BossbotHQ,
        }

        try:
            zone = zoneName2Id[zoneName]
        except KeyError:
            return "Unknown zone name!"

        return (
            f"Requested to teleport {toon.getName()} to zone {zone}.",
            toon.doId,
            [
                ZoneUtil.getBranchLoaderName(zone),
                ZoneUtil.getToonWhereName(zone),
                "",
                ZoneUtil.getHoodId(zone),
                zone,
                0,
            ],
        )


class ToggleSleep(MagicWord):
    aliases = ["sleep", "nosleep", "neversleep", "togglesleeping", "insomnia"]
    desc = "Toggles sleeping for the target."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER

    def handleWord(self, invoker, avId, toon, *args):
        toon.d_toggleSleep()
        return f"Toggled sleeping for {toon.getName()}."


class ToggleImmortal(MagicWord):
    aliases = ["immortal", "invincible", "invulnerable"]
    desc = "Toggle immortal mode. This makes the Toon immune to damage."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER

    def handleWord(self, invoker, avId, toon, *args):
        toon.setImmortalMode(not toon.immortalMode)
        return f"Toggled immortal mode for {toon.getName()}"


class ToggleGhost(MagicWord):
    aliases = ["ghost", "invisible", "spy"]
    desc = "Toggle ghost mode."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER

    def handleWord(self, invoker, avId, toon, *args):
        # 1 is for the attic, 2 enables you to see yourself other ghost toons. 0 is off.
        toon.b_setGhostMode(
            2 if not toon.ghostMode else 0
        )  # As it's primarily for moderation purposes, we set it to 2 here, or 0 if it's already on.
        return f"Toggled ghost mode for {toon.getName()}"


class SetGM(MagicWord):
    aliases = ["icon", "seticon", "gm", "gmicon", "setgmicon"]
    desc = "Sets the GM icon on the target."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [
        ("iconRequest", int, False, 0),
    ]

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.toonbase import TTLocalizer

        iconRequest = args[0]
        if iconRequest > len(TTLocalizer.GM_NAMES) or iconRequest < 0:
            return "Invalid GM icon ID!"

        toon.b_setGM(
            0
        )  # Reset it first, otherwise the Toon keeps the old icon, but the name still changes.
        toon.b_setGM(iconRequest)
        return f"GM icon set to {iconRequest} for {toon.getName()}"


class SetMaxCarry(MagicWord):
    aliases = ["gagpouch", "pouch", "gagcapacity"]
    desc = "Set a Toon's gag pouch size."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("pouchSize", int, True)]

    def handleWord(self, invoker, avId, toon, *args):
        pouchSize = args[0]

        if pouchSize > 255 or pouchSize < 0:
            return "Specified pouch size must be between 1 and 255."

        toon.b_setMaxCarry(pouchSize)
        return f"Set gag pouch size to {pouchSize} for {toon.getName()}"


class GivePies(MagicWord):
    aliases = ["pies"]
    desc = "Gives the target throwable pies."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("type", int, True), ("amount", int, False, -1)]

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.toonbase import ToontownGlobals

        pieType = args[0]
        numPies = args[1]

        if pieType == -1:
            toon.b_setNumPies(0)
            return "Removed %s's pies." % toon.getName()
        if not 0 <= pieType <= 7:
            return "You can only specify between pie types 0 and 7."
        if numPies == -1:
            toon.b_setPieType(pieType)
            toon.b_setNumPies(ToontownGlobals.FullPies)
            return "Gave %s an infinite amount of pies." % toon.getName()
        if not 0 <= numPies <= 99:
            return "You can only specify between 0 and 99 pies."

        toon.b_setPieType(pieType)
        toon.b_setNumPies(numPies)
        return "Gave %s %d throwable pie%s." % (
            toon.getName(),
            numPies,
            "" if numPies == 1 else "s",
        )


def _getGameplayConfig(toon):
    from toontown.toonbase import ToontownGlobals

    if not hasattr(toon, '_magicWordGameplayConfig'):
        toon._magicWordGameplayConfig = {
            'pieThrowingInterval': ToontownGlobals.PieThrowingInterval,
            'toonForwardSpeed': OTPGlobals.ToonForwardSpeed,
            'toonReverseSpeed': OTPGlobals.ToonReverseSpeed,
            'toonRotateSpeed': OTPGlobals.ToonRotateSpeed,
        }
    return toon._magicWordGameplayConfig


def _setClientGameplayConfig(command, toon, setting, value):
    _getGameplayConfig(toon)[setting] = value
    command.air.magicWordManager.sendUpdateToAvatarId(
        toon.doId, 'applyGameplayConfig', [setting, repr(value)])


def _setLawbotBossConfig(command, setting, value):
    from otp.avatar.DistributedPlayerAI import DistributedPlayerAI
    from toontown.suit.DistributedLawbotBossAI import DistributedLawbotBossAI
    from toontown.toonbase import ToontownGlobals

    setattr(ToontownGlobals, setting, value)

    # Lawbot boss maximum damage is copied onto each boss when it is created.
    # Keep a battle already in progress in step with the new shard tuning.
    if setting == 'LawbotBossMaxDamage':
        for obj in list(command.air.doId2do.values()):
            if isinstance(obj, DistributedLawbotBossAI):
                obj.bossMaxDamage = value

    # Several of these values drive client-side animation or collision results,
    # so update every connected player as well as the AI's copy of the globals.
    for obj in list(command.air.doId2do.values()):
        if isinstance(obj, DistributedPlayerAI) and obj.isPlayerControlled():
            command.air.magicWordManager.sendUpdateToAvatarId(
                obj.doId, 'applyGameplayConfig', [setting, repr(value)])


class _LawbotBossConfigMixin:
    globalName = None
    displayName = None
    minimum = 0
    maximum = None

    def handleWord(self, invoker, avId, toon, *args):
        value = args[0]
        if isinstance(value, float) and not math.isfinite(value):
            return '%s must be a finite number.' % self.displayName
        if value < self.minimum or (self.maximum is not None and value > self.maximum):
            if self.maximum is None:
                return '%s must be at least %g.' % (self.displayName, self.minimum)
            return '%s must be between %g and %g.' % (
                self.displayName, self.minimum, self.maximum)
        _setLawbotBossConfig(self, self.globalName, value)
        return 'Set %s to %g for this shard.' % (self.displayName.lower(), value)


class SetPieThrowingInterval(MagicWord):
    aliases = ['pieinterval', 'piethrowinterval', 'piethrowdelay']
    desc = "Sets the delay before the caller can begin throwing another pie."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('seconds', float, True)]

    def handleWord(self, invoker, avId, toon, *args):
        seconds = args[0]
        if not math.isfinite(seconds) or seconds < 0.0:
            return 'The pie throwing interval must be a finite, non-negative number.'
        _setClientGameplayConfig(self, toon, 'pieThrowingInterval', seconds)
        return 'Set the pie throwing interval to %g seconds.' % seconds


class SetLawyerAttackChance(MagicWord):
    aliases = ['lawyerattackchance', 'lawyerchance', 'lawbotbosslawyerchancetoattack']
    desc = "Sets the shard-wide chance that a CJ lawyer attacks instead of prosecuting."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('percent', int, True)]

    def handleWord(self, invoker, avId, toon, *args):
        percent = args[0]
        if not 0 <= percent <= 100:
            return 'The lawyer attack chance must be between 0 and 100 percent.'
        _setLawbotBossConfig(self, 'LawbotBossLawyerChanceToAttack', percent)
        return 'Set the lawyer attack chance to %d%% for this shard.' % percent


class SetLawbotBossAreaAttackChance(_LawbotBossConfigMixin, MagicWord):
    aliases = ['cjareaattackchance', 'cjjumpchance', 'areaattackchance',
               'lawbotbosschancetodoareaattack']
    desc = "Sets the shard-wide chance that the CJ performs his jump attack."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('percent', int, True)]
    globalName = 'LawbotBossChanceToDoAreaAttack'
    displayName = 'CJ jump attack chance'
    maximum = 100


class SetLawbotBossBonusDuration(_LawbotBossConfigMixin, MagicWord):
    aliases = ['cjbonusduration', 'bonusduration', 'lawbotbossbonusduration']
    desc = "Sets the shard-wide duration of the CJ's bonus weight period."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('seconds', float, True)]
    globalName = 'LawbotBossBonusDuration'
    displayName = 'CJ bonus duration'


class SetLawbotBossBonusWeightMultiplier(_LawbotBossConfigMixin, MagicWord):
    aliases = ['cjbonusweightmultiplier', 'bonusweightmultiplier', 'bonusmultiplier',
               'lawbotbossbonusweightmultiplier']
    desc = "Sets the shard-wide CJ bonus weight multiplier."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('multiplier', int, True)]
    globalName = 'LawbotBossBonusWeightMultiplier'
    displayName = 'CJ bonus weight multiplier'


class SetLawbotBossLawyerStunTime(_LawbotBossConfigMixin, MagicWord):
    aliases = ['lawyerstuntime', 'cjlawyerstuntime', 'lawbotbosslawyerstuntime']
    desc = "Sets the shard-wide duration for which CJ lawyers remain stunned."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('seconds', float, True)]
    globalName = 'LawbotBossLawyerStunTime'
    displayName = 'CJ lawyer stun time'


class SetLawbotBossLawyerToPanTime(_LawbotBossConfigMixin, MagicWord):
    aliases = ['lawyertopantime', 'cjlawyertopantime', 'lawbotbosslawyertopantime']
    desc = "Sets the shard-wide duration of a CJ lawyer's throw toward the pan."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('seconds', float, True)]
    globalName = 'LawbotBossLawyerToPanTime'
    displayName = 'CJ lawyer-to-pan time'


class SetLawbotBossLawyerCycleTime(_LawbotBossConfigMixin, MagicWord):
    aliases = ['lawyercycletime', 'cjlawyercycletime', 'lawbotbosslawyercycletime']
    desc = "Sets the shard-wide delay between CJ lawyer attack cycles."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('seconds', float, True)]
    globalName = 'LawbotBossLawyerCycleTime'
    displayName = 'CJ lawyer cycle time'


class SetLawbotBossDefensePanDamage(_LawbotBossConfigMixin, MagicWord):
    aliases = ['defensepandamage', 'cjdefensepandamage', 'lawbotbossdefensepandamage']
    desc = "Sets the shard-wide damage generated by hitting the CJ's defense pan."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('damage', int, True)]
    globalName = 'LawbotBossDefensePanDamage'
    displayName = 'CJ defense pan damage'
    maximum = 65535


class SetLawbotBossInitialDamage(_LawbotBossConfigMixin, MagicWord):
    aliases = ['cjinitialdamage', 'initialdamage', 'lawbotbossinitialdamage']
    desc = "Sets the shard-wide initial scale-round damage for the CJ."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('damage', int, True)]
    globalName = 'LawbotBossInitialDamage'
    displayName = 'CJ initial damage'
    maximum = 65534

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.toonbase import ToontownGlobals

        if args[0] >= ToontownGlobals.LawbotBossMaxDamage:
            return 'CJ initial damage must be less than CJ maximum damage (%d).' % (
                ToontownGlobals.LawbotBossMaxDamage)
        return super().handleWord(invoker, avId, toon, *args)


class SetLawbotBossMaxDamage(_LawbotBossConfigMixin, MagicWord):
    aliases = ['cjmaxdamage', 'maxcjdamage', 'lawbotbossmaxdamage']
    desc = "Sets the shard-wide damage needed to defeat the CJ."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('damage', int, True)]
    globalName = 'LawbotBossMaxDamage'
    displayName = 'CJ maximum damage'
    maximum = 65535

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.toonbase import ToontownGlobals

        if args[0] <= ToontownGlobals.LawbotBossInitialDamage:
            return 'CJ maximum damage must exceed CJ initial damage (%d).' % (
                ToontownGlobals.LawbotBossInitialDamage)
        return super().handleWord(invoker, avId, toon, *args)


class SetToonForwardSpeed(MagicWord):
    aliases = ['forwardspeed', 'forwardmovespeed']
    desc = "Sets the caller's forward movement speed."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('speed', float, True)]

    def handleWord(self, invoker, avId, toon, *args):
        speed = args[0]
        if not math.isfinite(speed) or speed < 0.0:
            return 'Forward speed must be a finite, non-negative number.'
        _setClientGameplayConfig(self, toon, 'toonForwardSpeed', speed)
        return 'Set forward movement speed to %g.' % speed


class SetToonReverseSpeed(MagicWord):
    aliases = ['backwardsspeed', 'backwardspeed', 'reversespeed']
    desc = "Sets the caller's backward movement speed."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('speed', float, True)]

    def handleWord(self, invoker, avId, toon, *args):
        speed = args[0]
        if not math.isfinite(speed) or speed < 0.0:
            return 'Backward speed must be a finite, non-negative number.'
        _setClientGameplayConfig(self, toon, 'toonReverseSpeed', speed)
        return 'Set backward movement speed to %g.' % speed


class SetToonRotateSpeed(MagicWord):
    aliases = ['rotationspeed', 'rotatespeed']
    desc = "Sets the caller's rotation speed."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]
    arguments = [('speed', float, True)]

    def handleWord(self, invoker, avId, toon, *args):
        speed = args[0]
        if not math.isfinite(speed) or speed < 0.0:
            return 'Rotation speed must be a finite, non-negative number.'
        _setClientGameplayConfig(self, toon, 'toonRotateSpeed', speed)
        return 'Set rotation speed to %g degrees per second.' % speed


class GameplayConfig(MagicWord):
    aliases = ['configvalues', 'gameplayvalues', 'tuning']
    desc = "Displays the current pie, CJ, and Toon movement configuration."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    affectRange = [MagicWordConfig.AFFECT_SELF]

    def handleWord(self, invoker, avId, toon, *args):
        from toontown.toonbase import ToontownGlobals

        values = _getGameplayConfig(toon)
        text = '\n'.join((
            'Gameplay tuning',
            'Pie interval: %g s' % values['pieThrowingInterval'],
            'Forward speed: %g' % values['toonForwardSpeed'],
            'Rotation speed: %g deg/s' % values['toonRotateSpeed'],
            'Backward speed: %g' % values['toonReverseSpeed'],
            'Lawyer attack chance: %d%%' % ToontownGlobals.LawbotBossLawyerChanceToAttack,
            'CJ jump attack chance: %d%%' % ToontownGlobals.LawbotBossChanceToDoAreaAttack,
            'CJ bonus duration: %g s' % ToontownGlobals.LawbotBossBonusDuration,
            'CJ bonus weight multiplier: %g' % ToontownGlobals.LawbotBossBonusWeightMultiplier,
            'CJ lawyer stun time: %g s' % ToontownGlobals.LawbotBossLawyerStunTime,
            'CJ lawyer-to-pan time: %g s' % ToontownGlobals.LawbotBossLawyerToPanTime,
            'CJ lawyer cycle time: %g s' % ToontownGlobals.LawbotBossLawyerCycleTime,
            'CJ defense pan damage: %d' % ToontownGlobals.LawbotBossDefensePanDamage,
            'CJ initial damage: %d' % ToontownGlobals.LawbotBossInitialDamage,
            'CJ maximum damage: %d' % ToontownGlobals.LawbotBossMaxDamage,
        ))
        self.air.magicWordManager.sendUpdateToAvatarId(
            toon.doId, 'applyGameplayConfig', ['showTuning', text])
        return 'Displayed the current gameplay tuning.'


class ToggleInstantKill(MagicWord):
    aliases = ["instantkill", "instakill"]
    desc = "Toggle the ability to instantly kill a Cog with any gag."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER

    def handleWord(self, invoker, avId, toon, *args):
        toon.setInstantKillMode(not toon.instantKillMode)
        return f"Toggled instant-kill mode for {toon.getName()}"


class Fireworks(MagicWord):
    aliases = ["firework"]
    desc = "Starts a firework show."
    execLocation = MagicWordConfig.EXEC_LOC_SERVER
    arguments = [("name", str, False, "newyear"), ("hood", str, False, "")]

    # List of firework shows currently in progress
    fireworkShows = {}

    def handleWord(self, invoker, avId, toon, *args):
        name = args[0]
        hood = args[1]

        from toontown.parties import PartyGlobals
        from toontown.toonbase import ToontownGlobals

        name2showId = {
            "newyear": ToontownGlobals.NEWYEARS_FIREWORKS,
            "newyears": ToontownGlobals.NEWYEARS_FIREWORKS,
            "summer": ToontownGlobals.JULY4_FIREWORKS,
            "combo": ToontownGlobals.COMBO_FIREWORKS,
            "party": PartyGlobals.FireworkShows.Summer,
        }

        if name not in name2showId:
            return f'Unknown firework name "{name}".  Valid names: {list(name2showId.keys())}'
        showId = name2showId[name]

        zoneToStyleDict = {
            ToontownGlobals.DonaldsDock: 5,
            ToontownGlobals.ToontownCentral: 0,
            ToontownGlobals.TheBrrrgh: 4,
            ToontownGlobals.MinniesMelodyland: 3,
            ToontownGlobals.DaisyGardens: 1,
            ToontownGlobals.OutdoorZone: 0,
            ToontownGlobals.GoofySpeedway: 0,
            ToontownGlobals.DonaldsDreamland: 2,
        }

        from toontown.hood import ZoneUtil

        zones = []
        if not hood:
            zones = (toon.zoneId,)
        elif hood == "all":
            zones = zoneToStyleDict.keys()
        else:
            return "Missing hood argument."

        # Generate our firework shows
        from toontown.effects.DistributedFireworkShowAI import DistributedFireworkShowAI

        count = 0
        for zone in zones:
            if zone not in self.fireworkShows:
                show = DistributedFireworkShowAI(self.air, self)
                show.generateWithRequired(zone)
                self.fireworkShows[zone] = show
                show.d_startShow(showId, zoneToStyleDict.get(zone, 0))
                count += 1

        return f"Started firework {'show' if count == 1 else 'shows'} in {count} {'zone' if count == 1 else 'zones'}!"

    def stopShow(self, zoneId):
        if zoneId in self.fireworkShows:
            show = self.fireworkShows[zoneId]
            show.requestDelete()
            del self.fireworkShows[zoneId]


# Instantiate all classes defined here to register them.
# A bit hacky, but better than the old system
for item in list(globals().values()):
    if isinstance(item, type) and issubclass(item, MagicWord):
        i = item()
