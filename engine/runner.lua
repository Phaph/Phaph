-- Headless Path of Building runner.
-- Reads one JSON command per line on stdin and writes one JSON reply per line,
-- prefixed with "@@", on stdout. Everything else on stdout is PoB log noise.
-- Run from PoB's src directory (see pob.py).

dofile("HeadlessWrapper.lua")
local json = require("dkjson")

local function reply(t)
	io.stdout:write("@@", json.encode(t), "\n")
	io.stdout:flush()
end

local afterFrame = nil   -- set below (usage limits), once mainSkillName exists

local function frame()
	runCallback("OnFrame")
	if afterFrame then afterFrame() end
end

local DEFAULT_FIELDS = {
	"FullDPS", "TotalDPS", "CombinedDPS", "AverageHit", "Speed", "HitChance",
	"CritChance", "CritMultiplier", "BleedDPS", "BleedChance", "PoisonDPS", "IgniteDPS",
	"TotalDot", "TotalDotDPS", "MinionDPS", "MinionDotDPS", "FullDPS", "FullDotDPS", "WithBleedDPS", "WithPoisonDPS", "WithIgniteDPS",
	"Life", "EnergyShield", "Mana", "Armour", "Evasion", "TotalEHP",
	"PhysicalMaximumHitTaken", "FireResist", "ColdResist", "LightningResist", "ChaosResist",
	"Str", "Dex", "Int", "Spirit", "SpiritUnreserved", "EffectiveMovementSpeedMod", "EffectiveLootRarityMod",
	"BlockChance", "SpellBlockChance", "LifeLeechRate", "LifeRegen", "UsageLimit", "UncappedSpeed",
}

-- Supports that put a usage condition on the skill (move first, build Glory, etc.).
-- PoB applies their bonus but not the downtime, so they look better than they play.
local function isConditional(gem)
	local ge = gem.grantedEffect
	if not ge then return false end
	for _, t in ipairs(ge.addSkillTypes or {}) do
		if t == SkillType.HasUsageCondition then return true end
	end
	local d = (ge.description or ""):lower()
	return d:find("requirement") ~= nil or d:find("can only be used") ~= nil
end

local function warnings()
	local w = {}
	local env = build.calcsTab.mainEnv
	for kind, list in pairs(env and env.itemWarnings or {}) do
		-- some warnings are a flag, not a list (seen after a support like Unleash): report the name alone
		if type(list) ~= "table" then
			if list then table.insert(w, kind) end
			list = {}
		end
		for _, entry in ipairs(list) do
			table.insert(w, kind .. ": " .. table.concat((function()
				local parts = {}
				if type(entry) ~= "table" then return { tostring(entry) } end
				for _, v in ipairs(entry) do
					if type(v) ~= "table" then table.insert(parts, tostring(v)) end
				end
				return parts
			end)(), " "))
		end
	end
	return w
end

-- Copy the requested numeric fields out of a PoB output table. Minion damage lives in
-- out.Minion, so it is exposed as MinionDPS / MinionDotDPS for minion builds.
local function pick(out, fields)
	local result = {}
	local minion = type(out.Minion) == "table" and out.Minion or {}
	for _, f in ipairs(fields or DEFAULT_FIELDS) do
		local v
		if f == "MinionDPS" then v = minion.TotalDPS
		elseif f == "MinionDotDPS" then v = minion.TotalDotDPS
		elseif out[f] == nil and f:sub(1, 6) == "Minion" then v = minion[f:sub(7)]   -- e.g. MinionPoisonDPS
		else v = out[f] end
		if type(v) == "number" then result[f] = v end
	end
	return result
end

-- Some names belong to two gems (e.g. "Lightning Bolt" and its triggered version).
-- Prefix those lines with the main gem's skillId so PoB picks the castable one.
local function disambiguate(text)
	local out = {}
	for line in text:gmatch("[^\r\n]+") do
		local name = line:match("^([ %a':]+) %d+/%d+")
		if name and not line:match("^skillId:") then
			local found = {}
			for _, gem in pairs(data.gems) do
				if gem.name == name and not (gem.tags and gem.tags.support) then table.insert(found, gem) end
			end
			if #found > 1 then
				table.sort(found, function(a, b)
					local at, bt = (a.tags.trigger and 1 or 0), (b.tags.trigger and 1 or 0)
					if at ~= bt then return at < bt end
					return a.grantedEffectId < b.grantedEffectId
				end)
				local id = found[1].grantedEffectId
				if id and id:match("^%w+$") then line = "skillId:" .. id .. " " .. line end
			end
		end
		table.insert(out, line)
	end
	return table.concat(out, "\n")
end

-- Use PoB's Full DPS (sum over every included skill, with minion counts) whenever the build
-- has more than one damage source or any minion skill; otherwise the main skill's output is
-- identical and much cheaper to compute.
local function useFull()
	local n, minion = 0, false
	for _, g in ipairs(build.skillsTab.socketGroupList) do
		if g.enabled ~= false and g.includeInFullDPS then
			n = n + 1
			for _, s in ipairs(g.displaySkillList or {}) do
				if s.minion or (s.skillTypes and s.skillTypes[SkillType.Minion]) then minion = true end
			end
		end
	end
	return n > 1 or minion
end

local function findClass(name)
	for id, class in pairs(build.spec.tree.classes) do
		if class.name:lower() == name:lower() then return id, class end
	end
end

local function findAscend(class, name)
	for id, asc in pairs(class.classes) do
		if asc.name and asc.name:lower() == name:lower() then return id end
	end
end

local function findNode(spec)
	local nodes = build.spec.nodes
	if type(spec) == "number" then return nodes[spec] end
	for _, node in pairs(nodes) do
		if node.dn and node.dn:lower() == spec:lower() then return node end
	end
end

local function mainSkillName()
	local sg = build.skillsTab.socketGroupList[build.mainSocketGroup]
	if sg and sg.displaySkillList then
		local s = sg.displaySkillList[sg.mainActiveSkill or 1]
		if s then return s.activeEffect.grantedEffect.name end
	end
end

-- Usage limits Path of Building doesn't model. PoB counts every skill as cast back to back at its cast speed. A few
-- skills can only be used when something else has happened first, so PoB's DPS for them is several times too high
-- and they won every search on every class (Hexblast, 2026-11-18). Each rule gives the most uses per second the
-- skill really gets against one target; the main skill's DPS is scaled down to it. Estimates: confirm in game.
local USAGE_LIMITS = {
	-- Detonates a Curse that is at least half expired, and removes it. One target: cast the curse (0.7 s), wait
	-- for it to land (1.5 s curse delay), then half its duration (Despair 7.4 s at level 20) before Hexblast can go.
	Hexblast = function(out) return 1 / (0.7 + 1.5 + 7.4 / 2) end,
	-- Explodes a corpse each cast. Maps are full of corpses (no limit); a boss leaves none, so against a boss only
	-- the adds it summons feed it. Our estimate: one usable corpse every 4 seconds in a pinnacle fight (to check in
	-- game). Without this, Detonate Dead won Blood Mage, Lich, Oracle and Shaman as a boss skill (A-to-Z sweep).
	["Detonate Dead"] = function(out)
		local boss = build.configTab.input.enemyIsBoss
		if boss == "None" then return nil end
		return 0.25
	end,
	-- Ember Fusillade: each cast conjures one Ember (up to 10 at gem level 20); recasting resets the launch timer of all
	-- of them, so a player casts 10 then waits the duration (~1.3-1.5 s) for the volley. Embers per second
	-- = 10 / (10 / cast rate + duration). PoB counts every cast as a hit straight away: without this it won the
	-- blind test's search on all 23 ascendancies (2026-11-20). Its "5% more damage per Ember fired" is not counted
	-- (unclear in game; leaving it out errs low). In-game check in TESTS.md #5.
	["Ember Fusillade"] = function(out)
		local speed, dur = out.Speed or 0, out.Duration or 1.3
		if speed <= 0 then return nil end
		return 10 / (10 / speed + dur)
	end,
}

afterFrame = function()
	local out = build.calcsTab and build.calcsTab.mainOutput
	if type(out) ~= "table" or out._usageLimited then return end
	local rule = USAGE_LIMITS[mainSkillName() or ""]
	if not rule then return end
	local cap, speed = rule(out), out.Speed or 0
	out._usageLimited = true
	if not cap or speed <= cap then return end
	local f = cap / speed
	local before = out.TotalDPS or 0
	out.UsageLimit, out.UncappedSpeed = cap, speed
	out.Speed = cap
	for _, k in ipairs({ "TotalDPS", "CombinedDPS", "WithBleedDPS", "WithPoisonDPS", "WithIgniteDPS" }) do
		if type(out[k]) == "number" then out[k] = out[k] * f end
	end
	if type(out.FullDPS) == "number" and out.FullDPS > 0 then
		out.FullDPS = math.max(out.FullDPS - before * (1 - f), 0)
	end
end

local handlers = {}

-- Armour Break amounts. PoB turns "Break Armour equal to X% of Physical damage dealt" into a flag only (the enemy can
-- be Armour Broken), never into an amount, so it can't tell how long breaking a boss takes. The combo finder needs that
-- time: each such stat also adds its value to a stat of our own, read back by handlers.armour_break.
local AB_PCT_STATS = {
	["armour_break_physical_damage_%_dealt_as_armour_break"] = "WsArmourBreakPhysPct",
	["armour_break_damage_%_dealt_as_armour_break"] = "WsArmourBreakAllPct",
	["chaos_damage_%_dealt_as_armour_break"] = "WsArmourBreakChaosPct",
	["armour_break_fire_damage_%_dealt_as_armour_break"] = "WsArmourBreakFirePct",
	["crushed_target_%_physical_damage_taken_as_armour_break"] = "WsArmourBreakCrushedPct",
	["armour_break_for_%_of_poison_damage_over_poison_duration"] = "WsArmourBreakPoisonPct",
}
for stat, name in pairs(AB_PCT_STATS) do
	local map = data.skillStatMap[stat]
	if map then table.insert(map, { name = name, type = "BASE", value = nil, flags = 0, keywordFlags = 0 }) end
end

-- How the main skill breaks armour: flat break per hit, the "% of damage dealt as Armour Break" stats, the hit damage
-- they apply to, hits per second, and the enemy's armour before any break (what has to be broken to reach Fully Broken).
function handlers.armour_break(cmd)
	build.buildFlag = true
	frame()
	local env = build.calcsTab.mainEnv
	local out = build.calcsTab.mainOutput
	local skill = env and env.player and env.player.mainSkill
	if not skill then return { can = false } end
	local ml, cfg = skill.skillModList, skill.skillCfg
	local res = { can = ml:Flag(cfg, "Condition:CanArmourBreak") or env.modDB:Flag(nil, "Condition:CanArmourBreak") or false,
		cannot = ml:Flag(cfg, "CannotArmourBreak") or false,
		flat = out.ArmourBreakPerHit or 0, inc = ml:Sum("INC", cfg, "ArmourBreakPerHit"), pct = {} }
	for _, name in pairs(AB_PCT_STATS) do
		local v = ml:Sum("BASE", cfg, name)
		if v ~= 0 then res.pct[name] = v end
	end
	-- Attacks keep per-type hit damage on the hand that hits (main hand first); spells on the output itself.
	local hand = (out.MainHand and out.MainHand.PhysicalHitAverage) and out.MainHand or out
	for _, t in ipairs({ "Physical", "Fire", "Cold", "Lightning", "Chaos" }) do
		res[t .. "HitAverage"] = hand[t .. "HitAverage"] or out[t .. "HitAverage"] or 0
	end
	res.more = ml:More(cfg, "ArmourBreakEffect")   -- Armour Demolisher's "more Armour Break"
	res.speed = out.Speed or 0
	res.hit_speed = out.HitSpeed or 0
	res.hits_per_use = (out.HitSpeed and out.Speed and out.Speed > 0) and out.HitSpeed / out.Speed or 1
	res.enemy_armour = env.enemyDB:Sum("BASE", nil, "Armour") * calcLib.mod(env.enemyDB, nil, "Armour")
	res.enemy_armour_config = env.enemyDB:Sum("BASE", { source = "Config" }, "Armour")
	return res
end

function handlers.new(cmd)
	newBuild()
	return {}
end

function handlers.load_xml(cmd)
	loadBuildFromXML(cmd.xml, cmd.name)
	return { class = build.spec.curClassName, ascendancy = build.spec.curAscendClassName }
end

function handlers.save_xml(cmd)
	return { xml = build:SaveDB("code") }
end

function handlers.set_class(cmd)
	local classId, class = findClass(cmd.class)
	if not classId then error("unknown class: " .. tostring(cmd.class)) end
	build.spec:SelectClass(classId)
	if cmd.ascendancy then
		local ascId = findAscend(class, cmd.ascendancy)
		if not ascId then error("unknown ascendancy: " .. cmd.ascendancy) end
		build.spec:SelectAscendClass(ascId)
	end
	build.spec:AddUndoState()
	build.buildFlag = true
	frame()
	return { class = build.spec.curClassName, ascendancy = build.spec.curAscendClassName }
end

function handlers.set_level(cmd)
	build.characterLevelAutoMode = false
	build.characterLevel = math.max(1, math.min(100, cmd.level))
	build.controls.characterLevel:SetText(build.characterLevel)
	build.buildFlag = true
	frame()
	return { level = build.characterLevel }
end

function handlers.add_item(cmd)
	build.itemsTab:CreateDisplayItemFromRaw(cmd.raw)
	if not build.itemsTab.displayItem then error("could not parse item") end
	local name = build.itemsTab.displayItem.name
	build.itemsTab:AddDisplayItem()
	frame()
	return { name = name }
end

-- Item bases. types: list of item types ("Boots", "Ring", "One Handed Mace"...); max_level filters by level req.
function handlers.bases(cmd)
	local want = {}
	for _, t in ipairs(cmd.types or {}) do want[t] = true end
	local list = {}
	for name, base in pairs(data.itemBases) do
		local lvl = base.req and base.req.level or 0
		if (not cmd.types or want[base.type]) and lvl <= (cmd.max_level or 100) and not base.hidden then
			local tags = {}
			for k in pairs(base.tags or {}) do table.insert(tags, k) end
			table.insert(list, {
				name = name, type = base.type, subType = base.subType, level = lvl, tags = tags,
				implicit = base.implicit, armour = base.armour, weapon = base.weapon,
				req = base.req,
			})
		end
	end
	return { bases = list }
end

-- Affixes that can roll on a base, up to item level max_level.
-- Weight rule: the first weightKey present in the base's tags decides the weight.
function handlers.affixes(cmd)
	local base = data.itemBases[cmd.base]
	if not base then error("unknown base: " .. tostring(cmd.base)) end
	local list = {}
	local pool = base.type == "Jewel" and data.itemMods.Jewel or data.itemMods.Item
	-- The item's tags, as the game rolls them. "genesis_tree_*" tags only open mods through the Genesis tree
	-- (a league crafting mechanic), so ordinary crafting ignores them.
	local tags = {}
	for k in pairs(base.tags or {}) do
		if not k:find("^genesis_") then tags[k] = true end
	end
	for id, mod in pairs(pool) do
		if (mod.type == "Prefix" or mod.type == "Suffix") and (mod.level or 0) <= (cmd.max_level or 100) then
			local weight = 0
			for i, key in ipairs(mod.weightKey or {}) do
				if tags[key] then weight = mod.weightVal[i] or 0 break end
			end
			if weight > 0 then
				local lines = {}
				for _, line in ipairs(mod) do table.insert(lines, line) end
				-- wk/wv: the mod's weights, so the crafter can re-check it as other mods add tags to the item.
				-- adds: tags this mod puts on the item (e.g. +cold spell levels adds "no_fire_spell_mods"...),
				-- which block other mods, exactly as in game.
				local wk, wv = {}, {}
				for i, key in ipairs(mod.weightKey or {}) do
					if not key:find("^genesis_") then table.insert(wk, key); table.insert(wv, mod.weightVal[i] or 0) end
				end
				table.insert(list, { id = id, type = mod.type, group = mod.group, level = mod.level or 0,
					lines = lines, tags = mod.modTags, weight = weight, wk = wk, wv = wv, adds = mod.tags or {},
					stats = mod.statOrder or {} })
			end
		end
	end
	local itemTags = {}
	for k in pairs(tags) do table.insert(itemTags, k) end
	return { affixes = list, item_tags = itemTags }
end

-- An item's mod lines as the game shows them, with its selected variants applied (e.g. the four
-- "Legacy of ..." choices on Mageblood). Used to show a unique's mods.
function handlers.item_lines(cmd)
	local item = new("Item"):Item(cmd.raw)
	if not item.base then error("could not parse item") end
	local chosen = {}
	for _, v in ipairs({ item.variant, item.variantAlt, item.variantAlt2, item.variantAlt3, item.variantAlt4, item.variantAlt5 }) do
		chosen[v] = true
	end
	local function active(ml)
		if not ml.variantList then return true end
		for v in pairs(chosen) do if ml.variantList[v] then return true end end
		return false
	end
	local function collect(list)
		local out = {}
		for _, ml in ipairs(list or {}) do
			if active(ml) and ml.line and ml.line ~= "" then table.insert(out, (ml.line:gsub("{[^}]*}", ""))) end
		end
		return out
	end
	-- Every choice in order, duplicates included (Mageblood's Legacies grow stronger per duplicate).
	local variants = {}
	local slots = { item.variant }
	if item.hasAltVariant then table.insert(slots, item.variantAlt) end
	if item.hasAltVariant2 then table.insert(slots, item.variantAlt2) end
	if item.hasAltVariant3 then table.insert(slots, item.variantAlt3) end
	if item.hasAltVariant4 then table.insert(slots, item.variantAlt4) end
	if item.hasAltVariant5 then table.insert(slots, item.variantAlt5) end
	if item.variantList and #item.variantList > 1 then
		for _, v in ipairs(slots) do if v and item.variantList[v] then table.insert(variants, item.variantList[v]) end end
	end
	return { implicits = collect(item.implicitModLines), explicits = collect(item.explicitModLines), variants = variants }
end

-- Equip an item from raw text into a named slot, replacing (and deleting) what was there.
function handlers.equip(cmd)
	local slot = build.itemsTab.slots[cmd.slot]
	if not slot then error("unknown slot: " .. tostring(cmd.slot)) end
	local item = new("Item"):Item(cmd.raw)
	if not item.base then error("could not parse item base") end
	item:NormaliseQuality()
	item:BuildModList()
	local oldId = slot.selItemId
	build.itemsTab:AddItem(item, true)
	slot:SetSelItemId(item.id)
	if oldId and oldId ~= 0 and build.itemsTab.items[oldId] and cmd.delete_old ~= false then
		local still = false
		for _, s in pairs(build.itemsTab.slots) do
			if s ~= slot and s.selItemId == oldId then still = true end
		end
		if not still then build.itemsTab:DeleteItem(build.itemsTab.items[oldId], true) end
	end
	build.itemsTab:PopulateSlots()
	build.buildFlag = true
	frame()
	local out = build.calcsTab.mainOutput
	local result = pick(out, cmd.fields)
	return { id = item.id, name = item.name, output = result }
end

-- Score several candidate items for one slot without equipping them, using PoB's fast
-- what-if calculator (the one behind its item tooltips). Returns one output per item,
-- or {error=...} for an item that does not parse.
function handlers.try_items(cmd)
	local calcFunc = build.calcsTab:GetMiscCalculator()
	local full = useFull()
	local results = {}
	for i, raw in ipairs(cmd.items) do
		local item = new("Item"):Item(raw)
		if item.base then
			item:NormaliseQuality()
			item:BuildModList()
			local out = calcFunc({ repSlotName = cmd.slot, repItem = item }, full)
			local r = pick(out, cmd.fields)
			results[i] = r
		else
			results[i] = { error = "could not parse item" }
		end
	end
	return { results = results }
end

function handlers.unequip(cmd)
	local slot = build.itemsTab.slots[cmd.slot]
	if not slot then error("unknown slot: " .. tostring(cmd.slot)) end
	slot:SetSelItemId(0)
	build.buildFlag = true
	frame()
	return {}
end

-- What is equipped where, as raw item text.
-- Empty some slots for a what-if and put the same items back after (the Breaker's bench: a unique tried in a slot
-- replaces what the build wears there). Returns the item ids to restore.
function handlers.clear_slots(cmd)
	local prev = {}
	for _, name in ipairs(cmd.slots or {}) do
		local slot = build.itemsTab.slots[name]
		if slot then prev[name] = slot.selItemId or 0; slot:SetSelItemId(0) end
	end
	build.buildFlag = true
	frame()
	return { prev = prev }
end

function handlers.restore_slots(cmd)
	for name, id in pairs(cmd.prev or {}) do
		local slot = build.itemsTab.slots[name]
		if slot then slot:SetSelItemId(id) end
	end
	build.buildFlag = true
	frame()
	return {}
end

function handlers.equipped(cmd)
	local slots = {}
	for name, slot in pairs(build.itemsTab.slots) do
		local item = slot.selItemId and build.itemsTab.items[slot.selItemId]
		if item and not slot.nodeId then
			slots[name] = { name = item.name, base = item.baseName, type = item.type, rarity = item.rarity, raw = item.raw }
		end
	end
	return { slots = slots }
end

function handlers.clear_skills(cmd)
	wipeTable(build.skillsTab.socketGroupList)
	build.mainSocketGroup = 1
	build.buildFlag = true
	frame()
	return {}
end

-- A gem can't be above the level its level requirement allows at this character level (a level 55 character has no
-- level 20 gems). Applied to every group the engine creates or changes.
local function capGemLevels(group)
	local charLevel = build.characterLevel or 100
	for _, gem in ipairs(group.gemList or {}) do
		local ge = gem.gemData and gem.gemData.grantedEffect
		if ge and ge.levels and gem.level then
			local best = 1
			for lvl, d in pairs(ge.levels) do
				if type(lvl) == "number" and lvl <= gem.level and (d.levelRequirement or 0) <= charLevel and lvl > best then best = lvl end
			end
			gem.level = best
		end
	end
end

-- text is PoB's paste format, one gem per line: "Name level/quality  count"
-- A totem gem holds two skills: placing the totem (no damage) and what the totem does (Shockwave Slam, Ballista
-- Bolt...). PoB scores the first by default, which reads as 0 DPS; score the totem's own skill instead.
local function scoreTotemSkill(group)
	local first = group.gemList[1]
	local gd = first and first.gemData
	local ge = gd and gd.grantedEffect
	local second = group.gemList[2] and group.gemList[2].gemData
	local socketed = second and not (second.tags and second.tags.support)   -- Spell Totem + Fireball
	if ge and ge.skillTypes and ge.skillTypes[SkillType.SummonsTotem] and (#(gd.additionalGrantedEffects or {}) > 0 or socketed) then
		group.mainActiveSkill = 2
		group.mainActiveSkillCalcs = 2
	end
end

function handlers.add_skill(cmd)
	local before = #build.skillsTab.socketGroupList
	build.skillsTab:PasteSocketGroup(disambiguate(cmd.text))
	local index = #build.skillsTab.socketGroupList
	if index == before then error("no gems recognised in: " .. cmd.text) end
	capGemLevels(build.skillsTab.socketGroupList[index])
	build.skillsTab:ProcessSocketGroup(build.skillsTab.socketGroupList[index])
	scoreTotemSkill(build.skillsTab.socketGroupList[index])
	-- Full DPS costs a second calculation pass, so it is only switched on for builds that
	-- need it (several damage sources or minion counts); see set_full_dps.
	build.skillsTab.socketGroupList[index].includeInFullDPS = cmd.full_dps == true
	if cmd.main ~= false then build.mainSocketGroup = index end
	frame()
	local missing = {}
	for _, gem in ipairs(build.skillsTab.socketGroupList[index].gemList) do
		if not gem.gemData then table.insert(missing, gem.nameSpec) end
	end
	return { group = index, main_skill = mainSkillName(), unknown_gems = missing }
end

-- Replace the gems of an existing group in place and return chosen output fields.
-- Used by the optimiser so each candidate costs one recalculation.
-- Allocated passive node ids and the tree version, for the website's tree viewer.
function handlers.allocated(cmd)
	local ids = {}
	for id in pairs(build.spec.allocNodes) do table.insert(ids, id) end
	table.sort(ids)
	return { nodes = ids, version = build.spec.treeVersion }
end

-- Jewel sockets on the passive tree. A plain socket takes any jewel; special ones (charm sockets,
-- ascendancy sockets that only take basic jewels, cluster sockets) are flagged so callers can skip them.
local function isPlainSocket(node)
	return (node.type == "Socket" or node.isJewelSocket) and not node.ascendancyName and not node.charmSocket
		and not node.containJewelSocket and not node.expansionJewel
end

function handlers.jewel_sockets(cmd)
	local out = {}
	for id, node in pairs(build.spec.nodes) do
		if node.type == "Socket" or node.isJewelSocket then
			table.insert(out, { id = id, slot = "Jewel " .. id, alloc = node.alloc and true or false,
				dist = node.path and #node.path or nil, plain = isPlainSocket(node),
				has_slot = build.itemsTab.slots["Jewel " .. id] ~= nil, type = node.type,
				charm = node.charmSocket and true or false, asc = node.ascendancyName,
				name = node.dn, linked = node.linked and #node.linked or 0, pathDist = node.pathDist,
				locked = node.unlockConstraint and true or false })
		end
	end
	table.sort(out, function(a, b) return a.id < b.id end)
	return { sockets = out }
end

-- Allocate nodes by id (with the path to each), or take them back. Used to try a jewel in a socket.
function handlers.alloc_ids(cmd)
	for _, id in ipairs(cmd.ids or {}) do
		local node = build.spec.nodes[id]
		if node and not node.alloc and node.path then build.spec:AllocNode(node) end
	end
	build.spec:AddUndoState(); build.buildFlag = true; frame()
	local used = build.spec:CountAllocNodes()
	return { used = used }
end

function handlers.dealloc_ids(cmd)
	for _, id in ipairs(cmd.ids or {}) do
		local node = build.spec.nodes[id]
		if node and node.alloc then build.spec:DeallocNode(node) end
	end
	build.spec:AddUndoState(); build.buildFlag = true; frame()
	return {}
end

-- The build's skill groups: index, gem names in order, and whether it is the main group.
function handlers.groups(cmd)
	local out = {}
	for i, g in ipairs(build.skillsTab.socketGroupList) do
		local gems, levels = {}, {}
		for _, gem in ipairs(g.gemList) do
			table.insert(gems, gem.nameSpec)
			local ge = gem.gemData and gem.gemData.grantedEffect
			local d = ge and ge.levels and ge.levels[gem.level or 1]
			-- Each gem's level here, and the character level that gem level needs.
			table.insert(levels, { level = gem.level, req = d and d.levelRequirement or 0 })
		end
		table.insert(out, { group = i, gems = gems, levels = levels, main = build.mainSocketGroup == i })
	end
	return { groups = out }
end

function handlers.try_skill(cmd)
	local list = build.skillsTab.socketGroupList
	local old = list[cmd.group]
	if not old then error("no group " .. tostring(cmd.group)) end
	local count = #list
	build.skillsTab:PasteSocketGroup(disambiguate(cmd.text))
	if #list == count then error("no gems recognised in: " .. cmd.text) end
	local new = table.remove(list)
	new.includeInFullDPS = old.includeInFullDPS
	new.set1, new.set2 = old.set1, old.set2
	for i, gem in ipairs(new.gemList) do
		if old.gemList[i] and old.gemList[i].count then gem.count = old.gemList[i].count end
	end
	list[cmd.group] = new
	capGemLevels(new)
	if not cmd.keep_main then build.mainSocketGroup = cmd.group end
	-- Resolve gems and global gem counts before recalculating, otherwise the
	-- calculation sees the previous gem list and results lag one step behind.
	build.skillsTab:ProcessSocketGroup(new)
	scoreTotemSkill(new)
	build.skillsTab:UpdateGlobalGemCountAssignments()
	build.buildFlag = true
	frame()
	local supported = {}
	for _, gem in ipairs(new.gemList) do
		if gem.gemData and gem.gemData.tags and gem.gemData.tags.support then
			supported[gem.nameSpec] = false
		end
	end
	local active = new.displaySkillList and new.displaySkillList[new.mainActiveSkill or 1]
	if active then
		for _, effect in ipairs(active.effectList) do
			if effect.grantedEffect.support then
				local name = effect.srcInstance and effect.srcInstance.nameSpec
				if name and supported[name] ~= nil then supported[name] = true end
			end
		end
	end
	local out = build.calcsTab.mainOutput
	local result = pick(out, cmd.fields)
	return { output = result, supported = supported, main_skill = mainSkillName(), warnings = warnings() }
end

-- Spirit safety net for skills the optimisers didn't add: an item can grant spirit skills (The Coming Calamity grants
-- three heralds) and PoB turns them on, so a build can end up reserving more spirit than it has. Turn such groups off,
-- item-granted ones first, then the latest added, until the spirit fits. The main group is never touched.
-- Returns the names turned off.
function handlers.fit_spirit(cmd)
	local list = build.skillsTab.socketGroupList
	local function left()
		build.buildFlag = true
		frame()
		return build.calcsTab.mainOutput.SpiritUnreserved or 0
	end
	local off = {}
	if left() >= 0 then return { off = off } end
	local order = {}
	for i = #list, 1, -1 do
		local g = list[i]
		if i ~= build.mainSocketGroup and g.enabled ~= false and g.source then table.insert(order, i) end
	end
	for i = #list, 1, -1 do
		local g = list[i]
		if i ~= build.mainSocketGroup and g.enabled ~= false and not g.source then table.insert(order, i) end
	end
	local before = left()
	for _, i in ipairs(order) do
		local g = list[i]
		g.enabled = false
		local now = left()
		if now > before then
			local gem = g.gemList[1]
			table.insert(off, (gem and (gem.nameSpec ~= "" and gem.nameSpec or gem.skillId)) or g.label or "?")
			before = now
			if now >= 0 then break end
		else
			g.enabled = true   -- reserved no spirit: leave it on
		end
	end
	left()
	return { off = off, left = before }
end

function handlers.remove_skill(cmd)
	table.remove(build.skillsTab.socketGroupList, cmd.group)
	build.mainSocketGroup = math.min(build.mainSocketGroup, math.max(1, #build.skillsTab.socketGroupList))
	build.buildFlag = true
	frame()
	return {}
end

-- Put a skill group on weapon set 1 or 2 (PoE 2 weapon swap).
function handlers.set_weapon_set(cmd)
	local g = build.skillsTab.socketGroupList[cmd.group]
	if not g then error("no group " .. tostring(cmd.group)) end
	g.set1 = cmd.set == 1
	g.set2 = cmd.set == 2
	build.buildFlag = true
	frame()
	return {}
end

-- Count every enabled group toward Full DPS.
function handlers.full_dps_all(cmd)
	for _, g in ipairs(build.skillsTab.socketGroupList) do
		if g.enabled ~= false then g.includeInFullDPS = true end
	end
	build.buildFlag = true
	frame()
	return { groups = #build.skillsTab.socketGroupList }
end

-- Mark a group to count toward PoB's Full DPS (the sum over several skills, e.g. minions + buffs).
function handlers.set_full_dps(cmd)
	local g = build.skillsTab.socketGroupList[cmd.group]
	if not g then error("no group " .. tostring(cmd.group)) end
	g.includeInFullDPS = cmd.include ~= false
	build.buildFlag = true
	frame()
	return {}
end

-- For minion skills with a limit above one (e.g. zombies), set the gem count to the limit so
-- Full DPS counts every minion, not just one. Returns {group = count}.
function handlers.sync_minion_counts(cmd)
	local main = build.mainSocketGroup
	local counts = {}
	for i, g in ipairs(build.skillsTab.socketGroupList) do
		if g.includeInFullDPS and g.enabled ~= false then
			build.mainSocketGroup = i
			build.buildFlag = true
			frame()
			local limit = build.calcsTab.mainOutput.ActiveMinionLimit
			local active = g.gemList[1]
			-- also lowers a count back down (e.g. a one-minion skill after a Breaker test raised its limit)
			if active and limit and active.count ~= limit and (limit > 1 or (active.count or 1) > limit) then
				active.count = limit
				counts[tostring(i)] = limit
			end
		end
	end
	build.mainSocketGroup = main
	build.buildFlag = true
	frame()
	return { counts = counts }
end

-- How many minions Full DPS counts (gem counts of minion groups in Full DPS), and every minion limit stat PoB's
-- skills use (ActiveSkeletonLimit, WolfLimit, ...), so the Breaker can raise them all with raw mods.
local minionLimitStats
function handlers.minion_count(cmd)
	if not minionLimitStats then
		local seen = {}
		minionLimitStats = {}
		for _, gem in pairs(data.gems) do
			local ge = gem.grantedEffect
			for _, id in ipairs(ge and ge.minionList or {}) do
				local m = data.minions[id]
				if m and m.limit and not seen[m.limit] then seen[m.limit] = true; table.insert(minionLimitStats, m.limit) end
			end
		end
		for name in pairs({ ActiveSkeletonLimit = 1, ActiveZombieLimit = 1, ActiveRagingSpiritLimit = 1, ActiveSpectreLimit = 1 }) do
			if not seen[name] then table.insert(minionLimitStats, name) end
		end
		table.sort(minionLimitStats)
	end
	local total = 0
	for _, g in ipairs(build.skillsTab.socketGroupList) do
		if g.includeInFullDPS and g.enabled ~= false then
			for _, s in ipairs(g.displaySkillList or {}) do
				if s.minion then total = total + ((g.gemList[1] and g.gemList[1].count) or 1); break end
			end
		end
	end
	return { count = total, limits = minionLimitStats }
end

-- Support gems PoB's own rules allow on a group's active skill (skill type requirements and
-- exclusions), without running any calculation. Used to skip supports that cannot apply.
function handlers.compatible_supports(cmd)
	local g = build.skillsTab.socketGroupList[cmd.group]
	if not g then error("no group " .. tostring(cmd.group)) end
	local active = g.displaySkillList and g.displaySkillList[g.mainActiveSkill or 1]
	if not active then return { supports = {} } end
	local names, seen = {}, {}
	for _, gem in pairs(data.gems) do
		local ge = gem.grantedEffect
		if ge and ge.support and not seen[gem.name] and calcLib.canGrantedEffectSupportActiveSkill(ge, active) then
			seen[gem.name] = true
			table.insert(names, gem.name)
		end
	end
	table.sort(names)
	return { supports = names }
end

-- Supports made for a skill, most specific first. For skills PoB can't score (buffs, remnants, defensive skills), the
-- best supports are the ones built for that kind of skill: a support that needs a rare skill type (GeneratesRemnants,
-- Herald, Cooldown) is made for it, while one that only needs Damage or Spell is generic. Rarity of a type = how few
-- active skills have it. Returns { name, specific (0..1), family, tier } for every compatible support.
local typeRarity
local function skillTypeRarity()
	if typeRarity then return typeRarity end
	local count, total = {}, 0
	for _, gem in pairs(data.gems) do
		local ge = gem.grantedEffect
		if ge and not ge.support and ge.skillTypes then
			total = total + 1
			for t in pairs(ge.skillTypes) do count[t] = (count[t] or 0) + 1 end
		end
	end
	typeRarity = {}
	for t, n in pairs(count) do typeRarity[t] = 1 - n / math.max(total, 1) end
	return typeRarity
end

function handlers.fitting_supports(cmd)
	local g = build.skillsTab.socketGroupList[cmd.group]
	if not g then error("no group " .. tostring(cmd.group)) end
	local active = g.displaySkillList and g.displaySkillList[g.mainActiveSkill or 1]
	if not active then return { supports = {} } end
	local rarity, out, seen = skillTypeRarity(), {}, {}
	local types = active.skillTypes or {}
	for _, gem in pairs(data.gems) do
		local ge = gem.grantedEffect
		if ge and ge.support and not seen[gem.name] and calcLib.canGrantedEffectSupportActiveSkill(ge, active) then
			seen[gem.name] = true
			local specific = 0
			for _, t in ipairs(ge.requireSkillTypes or {}) do
				if type(t) == "number" and types[t] then specific = math.max(specific, rarity[t] or 0) end
			end
			table.insert(out, { name = gem.name, specific = specific, family = gem.gemFamily, tier = gem.Tier or 0 })
		end
	end
	table.sort(out, function(a, b)
		if a.specific ~= b.specific then return a.specific > b.specific end
		if a.tier ~= b.tier then return a.tier > b.tier end
		return a.name < b.name
	end)
	return { supports = out }
end

function handlers.set_main(cmd)
	build.mainSocketGroup = cmd.group
	-- Optional: which active skill of the group is the main one (e.g. a spell socketed in a Cast on X gem).
	local g = build.skillsTab.socketGroupList[cmd.group]
	if cmd.skill and g then g.mainActiveSkill = cmd.skill; g.mainActiveSkillCalcs = cmd.skill end
	build.buildFlag = true
	frame()
	return { main_skill = mainSkillName() }
end

-- Config tab inputs, e.g. {"customMods": "...", "enemyIsBoss": "Pinnacle"}
-- PoB's "Custom Modifiers" box (one mod per line), for experiments like the Breaker's stat scans. Empty text clears it.
-- `raw` adds mods PoB has no text for, as {name, type, value} (e.g. ActiveSkeletonLimit BASE 1); they ride on the
-- config mod list, so they are rebuilt every time PoB rebuilds it, until the next set_custom_mods.
local breakerRaw, breakerNodes = {}, {}
function handlers.set_custom_mods(cmd)
	local cfg = build.configTab
	if not cfg.breakerWrapped then   -- per config tab: loading a build makes a new one
		local orig = cfg.BuildModList
		cfg.BuildModList = function(self, ...)
			local r = orig(self, ...)
			for _, m in ipairs(breakerRaw) do self.modList:NewMod(m.name, m.type or "BASE", m.value, "Breaker") end
			for _, node in ipairs(breakerNodes) do if node.modList then self.modList:AddList(node.modList) end end
			return r
		end
		cfg.breakerWrapped = true
	end
	breakerRaw = cmd.raw or {}
	-- `nodes`: passive nodes by name (keystones) whose parsed mods apply as if allocated, with their own conditions
	-- kept (text would lose them: "Storm and Plant Spells:" is a line of its own on Wildsurge Incantation).
	breakerNodes = {}
	for _, name in ipairs(cmd.nodes or {}) do
		local node = findNode(name)
		if not node then error("no passive node called " .. name) end
		table.insert(breakerNodes, node)
	end
	local set = cfg.configSets[cfg.activeConfigSetId]
	set.customModsList = { { title = "Breaker", enabled = true, text = cmd.text or "" } }
	cfg:BuildModList()
	build.buildFlag = true
	frame()
	return {}
end

function handlers.set_config(cmd)
	for k, v in pairs(cmd.values or {}) do
		build.configTab.input[k] = v
	end
	build.configTab:BuildModList()
	build.buildFlag = true
	frame()
	return {}
end

-- Turn on the conditional bonuses this build can actually keep up, and only those.
-- Rules (ours, written to be conservative):
--   * In combat you have always hit and used a skill recently. Mapping: you have also killed recently.
--   * An enemy ailment counts as up when the build keeps it up at least 90% of the time:
--     chance per hit x uses per second x ailment duration >= 0.9 (player or minions).
--   * Crit recently: crit chance >= 40%.
--   * Charges: only when something in the build says it gains that charge (passives, items, gems).
--   * Armour broken: the build breaks armour on hit. Exposure: a gem in the build applies it.
local AILMENT_VARS = {
	Bleed = { "conditionEnemyBleeding" }, Poison = { "conditionEnemyPoisoned" },
	Ignite = { "conditionEnemyIgnited", "conditionEnemyBurning" }, Shock = { "conditionEnemyShocked" },
	Chill = { "conditionEnemyChilled" },
}
-- Seconds an ailment lasts when PoB reports no duration (PoE 2 base durations, roughly).
local AILMENT_DEFAULT_DURATION = { Bleed = 5, Poison = 2, Ignite = 4, Shock = 4, Chill = 2 }
local MANAGED_VARS = {
	"conditionHitRecently", "conditionUsedSkillRecently", "conditionKilledRecently", "conditionCritRecently",
	"usePowerCharges", "useFrenzyCharges", "useEnduranceCharges", "conditionEnemyArmourBroken",
	"conditionEnemyFireExposure", "conditionEnemyColdExposure", "conditionEnemyLightningExposure",
}
for _, vars in pairs(AILMENT_VARS) do for _, v in ipairs(vars) do table.insert(MANAGED_VARS, v) end end

local function buildText()
	-- Everything the build "says": allocated passives, equipped item mods, gem descriptions.
	local parts = {}
	for _, node in pairs(build.spec.allocNodes) do
		for _, line in ipairs(node.sd or {}) do table.insert(parts, line) end
	end
	for _, slot in pairs(build.itemsTab.slots) do
		local item = slot.selItemId and build.itemsTab.items[slot.selItemId]
		if item and item.raw then table.insert(parts, item.raw) end
	end
	for _, group in ipairs(build.skillsTab.socketGroupList) do
		for _, gem in ipairs(group.gemList) do
			local ge = gem.gemData and gem.gemData.grantedEffect
			if ge and ge.description then table.insert(parts, ge.description) end
			if gem.nameSpec then table.insert(parts, gem.nameSpec) end
		end
	end
	return table.concat(parts, "\n"):lower()
end

-- Ailment application for the combo finder: per ailment, the main skill's chance per hit (%) and duration (s), plus
-- uses per second and hit chance. Attacks keep these on the hand that hits. Same fields auto_config reads.
function handlers.ailment_rates(cmd)
	build.buildFlag = true
	frame()
	local out = build.calcsTab.mainOutput
	local hand = (out.MainHand and out.MainHand.Speed) and out.MainHand or out
	local res = { speed = out.Speed or 0, hit_chance = out.HitChance or hand.HitChance or 100, ailments = {} }
	for _, a in ipairs({ "Shock", "Poison", "Ignite", "Chill", "Bleed" }) do
		local chance = hand[a .. "ChancePerHit"] or hand[a .. "ChanceOnHit"] or hand[a .. "Chance"]
			or out[a .. "ChancePerHit"] or out[a .. "ChanceOnHit"] or out[a .. "Chance"] or 0
		res.ailments[a] = { chance = chance, duration = hand[a .. "Duration"] or out[a .. "Duration"] or AILMENT_DEFAULT_DURATION[a] }
	end
	if cmd.debug then
		res.keys = {}
		for k, v in pairs(hand) do if type(v) == "number" and (k:find("Poison") or k:find("Shock")) then res.keys[k] = v end end
	end
	return res
end

function handlers.auto_config(cmd)
	local mode = cmd.mode or "bossing"
	local input = build.configTab.input
	for _, v in ipairs(MANAGED_VARS) do input[v] = nil end
	local applied = {}
	local function set(var, why)
		if not input[var] then input[var] = true; table.insert(applied, { var = var, why = why }) end
	end
	-- Two passes: turning conditions on changes chances and speed.
	for _ = 1, 2 do
		build.configTab:BuildModList()
		build.buildFlag = true
		frame()
		local out = build.calcsTab.mainOutput
		local minion = type(out.Minion) == "table" and out.Minion or {}
		set("conditionHitRecently", "always true in combat")
		set("conditionUsedSkillRecently", "always true in combat")
		if mode == "mapping" then set("conditionKilledRecently", "mapping: monsters die constantly") end
		for ailment, vars in pairs(AILMENT_VARS) do
			local uptime, rate = 0, 0
			for _, src in ipairs({ out, minion }) do
				local chance = src[ailment .. "ChancePerHit"] or src[ailment .. "ChanceOnHit"] or 0
				local perSec = chance / 100 * (src.Speed or 0)
				local duration = src[ailment .. "Duration"] or AILMENT_DEFAULT_DURATION[ailment]
				if perSec * duration > uptime then uptime, rate = perSec * duration, perSec end
			end
			if uptime >= 0.9 then
				for _, v in ipairs(vars) do
					set(v, string.format("%s applied %.1f times a second, up %d%% of the time", ailment:lower(), rate, math.floor(math.min(uptime, 1) * 100)))
				end
			end
		end
		if (out.CritChance or 0) >= 40 then set("conditionCritRecently", string.format("%.0f%% crit chance", out.CritChance)) end
		if (out.ArmourBreakPerHit or 0) > 0 then set("conditionEnemyArmourBroken", "build breaks armour on hit") end
		local text = buildText()
		for _, c in ipairs({ { "Frenzy", "useFrenzyCharges" }, { "Power", "usePowerCharges" }, { "Endurance", "useEnduranceCharges" } }) do
			local name = c[1]:lower() .. " charge"
			if text:find("gains? [^\n]-" .. name) or text:find("generates? [^\n]-" .. name) or text:find(name .. "s? on") then
				set(c[2], "build gains " .. name .. "s")
			end
		end
		for _, e in ipairs({ "Fire", "Cold", "Lightning" }) do
			if text:find(e:lower() .. " exposure") then set("conditionEnemy" .. e .. "Exposure", "build applies " .. e:lower() .. " exposure") end
		end
	end
	build.configTab:BuildModList()
	build.buildFlag = true
	frame()
	return { applied = applied }
end

function handlers.alloc_nodes(cmd)
	local done, missing = {}, {}
	for _, spec in ipairs(cmd.nodes) do
		local node = findNode(spec)
		if node and not node.alloc then
			build.spec:AllocNode(node)
			table.insert(done, node.dn)
		elseif not node then
			table.insert(missing, spec)
		end
	end
	build.spec:AddUndoState()
	build.buildFlag = true
	frame()
	return { allocated = done, missing = missing, points_used = build.spec:CountAllocNodes() }
end

local function passivePoints()
	local acts = build.acts and build.acts[build.maxActs]
	local quest = acts and acts.questPoints or 0
	local extra = build.calcsTab.mainOutput and build.calcsTab.mainOutput.ExtraPoints or 0
	return build.characterLevel - 1 + quest + extra
end

-- Put a raw item in a slot without returning stats (the tree optimiser fills sockets this way).
local function equipRaw(slotName, raw)
	local slot = build.itemsTab.slots[slotName]
	if not slot then return false end
	local item = new("Item"):Item(raw)
	if not item.base then return false end
	item:NormaliseQuality()
	item:BuildModList()
	local oldId = slot.selItemId
	build.itemsTab:AddItem(item, true)
	slot:SetSelItemId(item.id)
	if oldId and oldId ~= 0 and build.itemsTab.items[oldId] then build.itemsTab:DeleteItem(build.itemsTab.items[oldId], true) end
	build.itemsTab:PopulateSlots()
	return true
end

-- Attribute requirements: the tree's "+5 to any Attribute" passives are switched from attributes with points to
-- spare to the ones the gear and gems are short of. Returns what is still short afterwards.
local ATTRS = { { name = "Strength", have = "Str", need = "ReqStr" }, { name = "Dexterity", have = "Dex", need = "ReqDex" },
	{ name = "Intelligence", have = "Int", need = "ReqInt" } }
local function attributeOf(spec, id)
	local node = spec.hashOverrides[id] or spec.nodes[id]
	local text = table.concat(node and node.sd or {}, " ") .. " " .. (node and node.dn or "")
	for i, a in ipairs(ATTRS) do if text:find(a.name) then return i end end
	return nil
end
local function optionIndex(id, attr)
	local base = build.spec.tree.nodes[id]
	for i, opt in ipairs(base and base.options or {}) do
		local text = table.concat(opt.sd or {}, " ") .. " " .. (opt.dn or "")
		if text:find(ATTRS[attr].name) then return i end
	end
	return nil
end
function handlers.balance_attributes(cmd)
	local spec = build.spec
	local switched = 0
	for _ = 1, 400 do
		build.buildFlag = true
		frame()
		local out = build.calcsTab.mainOutput
		local short, worst, spare = nil, 0, {}
		for i, a in ipairs(ATTRS) do
			local gap = (out[a.need] or 0) - (out[a.have] or 0)
			if gap > worst then short, worst = i, gap end
			spare[i] = (out[a.have] or 0) - (out[a.need] or 0)
		end
		if not short then break end
		-- A node from an attribute with at least 5 to spare (one node's worth), the one with the most to spare first.
		local moved = false
		local order = { 1, 2, 3 }
		table.sort(order, function(x, y) return spare[x] > spare[y] end)
		for _, from in ipairs(order) do
			if from ~= short and spare[from] >= 5 then
				for id, node in pairs(spec.allocNodes) do
					if node.isAttribute and attributeOf(spec, id) == from then
						local opt = optionIndex(id, short)
						if opt then
							spec:SwitchAttributeNode(id, opt)
							moved = true
							switched = switched + 1
							break
						end
					end
				end
			end
			if moved then break end
		end
		if not moved then break end
		spec:BuildAllDependsAndPaths()
	end
	spec:BuildAllDependsAndPaths()
	spec:AddUndoState()
	build.buildFlag = true
	frame()
	local out = build.calcsTab.mainOutput
	local short = {}
	for _, a in ipairs(ATTRS) do
		local gap = (out[a.need] or 0) - (out[a.have] or 0)
		if gap > 0 then short[a.have] = gap end
	end
	return { switched = switched, short = short }
end

-- What sets each attribute requirement that isn't met: an item (slot, name), one gem, or "Support Gems" (5 per
-- support gem of that colour, added up across the build). Used by the item audit and by fit_gems.
local function requirementSource(attr)
	local out = build.calcsTab.mainOutput
	local src = out["Req" .. attr .. "Item"]
	if not src then return nil end
	local r = { source = src.source, need = out["Req" .. attr] or 0, have = out[attr] or 0 }
	if src.source == "Item" and src.sourceItem then
		r.name = src.sourceItem.name
		r.slot = src.sourceSlot
	elseif src.source == "Gem" and src.sourceGem then
		r.name = src.sourceGem.nameSpec
		r.level = src.sourceGem.level
	elseif src.source == "Support Gems" then
		r.count = (src[attr] or 0) / 5
	end
	return r
end

function handlers.attribute_sources(cmd)
	build.buildFlag = true
	frame()
	local res = {}
	for _, a in ipairs(ATTRS) do
		local s = requirementSource(a.have)
		if s and s.need > s.have then res[a.have] = s end
	end
	return { short = res }
end

-- Last resort for attribute requirements: lower the level of the gems that need the short attribute, one level at a
-- time, extra skills first (movement, auras, curses) and the main skill's group last. In game you'd simply use a
-- lower-level gem. Returns the gems lowered and anything still short.
function handlers.fit_gems(cmd)
	local short = handlers.balance_attributes({}).short or {}
	local lowered, itemBound, removed = {}, {}, {}
	local ATTR = { Str = { field = "reqStr", out = "ReqStr" }, Dex = { field = "reqDex", out = "ReqDex" }, Int = { field = "reqInt", out = "ReqInt" } }
	for _ = 1, 300 do
		local attr
		for k in pairs(short) do if not itemBound[k] then attr = k break end end
		if not attr then break end
		local need = build.calcsTab.mainOutput[ATTR[attr].out] or 0
		-- PoE 2: every support gem needs 5 of its colour's attribute, summed over all skills (8 blue supports = 40 Int).
		-- Support gems have no levels to lower: take one of that colour out, from the extra skills first (last group,
		-- last support), the main skill last.
		local src = requirementSource(attr)
		if src and src.source == "Support Gems" then
			local colour = ({ Str = 1, Dex = 2, Int = 3 })[attr]
			local pick
			local mainG = build.mainSocketGroup
			local order = {}
			for gi = #build.skillsTab.socketGroupList, 1, -1 do if gi ~= mainG then table.insert(order, gi) end end
			table.insert(order, mainG)
			for _, gi in ipairs(order) do
				local g = build.skillsTab.socketGroupList[gi]
				for k = #(g and g.gemList or {}), 1, -1 do
					local gem = g.gemList[k]
					local ge = gem.gemData and gem.gemData.grantedEffect
					if ge and ge.support and ge.color == colour and g.enabled ~= false then pick = { g = g, k = k } break end
				end
				if pick then break end
			end
			if pick then
				local gem = table.remove(pick.g.gemList, pick.k)
				local first = pick.g.gemList[1]
				removed[#removed + 1] = { support = gem.nameSpec, skill = first and first.nameSpec or "?" }
				for _, g in ipairs(build.skillsTab.socketGroupList) do build.skillsTab:ProcessSocketGroup(g) end
				build.skillsTab:UpdateGlobalGemCountAssignments()
				short = handlers.balance_attributes({}).short or {}
				goto continue
			end
		end
		do
		-- The gems that set this requirement (their own requirement is the highest); extra skills before the main one.
		local best, bestKey
		for gi, g in ipairs(build.skillsTab.socketGroupList) do
			for _, gem in ipairs(g.gemList or {}) do
				local req = gem[ATTR[attr].field] or 0
				if req >= need and req > 0 and (gem.level or 1) > 1 then
					local key = ((gi == build.mainSocketGroup) and 1000 or 0) - (gem.level or 1)
					if not best or key < bestKey then best, bestKey = gem, key end
				end
			end
		end
		if not best then
			itemBound[attr] = true   -- an item sets this requirement, not a gem: lowering gems won't help
		else
			best.level = best.level - 1
			lowered[best.nameSpec] = best.level
			for _, g in ipairs(build.skillsTab.socketGroupList) do build.skillsTab:ProcessSocketGroup(g) end
			build.skillsTab:UpdateGlobalGemCountAssignments()
			short = handlers.balance_attributes({}).short or {}
		end
		end
		::continue::
	end
	return { lowered = lowered, short = short, removed = removed }
end

function handlers.points(cmd)
	local used, ascUsed = build.spec:CountAllocNodes()
	return { available = passivePoints(), used = used, ascendancy_used = ascUsed }
end

-- Passive tree optimiser using PoB's fast what-if calculator.
-- Build phase: each step tries every reachable node, scores the whole path to it
-- (relative DPS gain + def_weight * relative EHP gain, per point spent) and takes the
-- best path. Small passives are looked at up to max_dist points away; notables and
-- keystones up to far_dist, so a strong one behind a long run of weak passives is found.
-- Ascendancy points are spent the same way.
-- Swap phase (refine): the build phase never takes a pick back, so afterwards the
-- weakest allocated branches are removed one at a time and their points re-spent;
-- a swap is kept only when the whole build scores higher. This catches points spent
-- early on passives that later picks made worthless, and pairs of passives that are
-- only strong together.
function handlers.optimise_tree(cmd)
	local maxDist = cmd.max_dist or 6
	local farDist = math.max(cmd.far_dist or 12, maxDist)
	local capDist = nil   -- set while only a few points are left
	-- Jewel sockets: with cmd.jewel (a raw jewel, the best one for this build), a socket is a target worth
	-- its path plus that jewel, and every socket taken gets the jewel at once, so later picks see it.
	local proxy
	if cmd.jewel then
		proxy = new("Item"):Item(cmd.jewel)
		if proxy.base then proxy:NormaliseQuality(); proxy:BuildModList() else proxy = nil end
	end
	local function isSocketTarget(node)
		return proxy and isPlainSocket(node) and node.linked and #node.linked > 0
	end
	local quiet = false   -- no live events while a swap is only being tried
	local defWeight = cmd.def_weight or 0.25
	local budget = cmd.points or passivePoints()
	local ascBudget = cmd.ascendancy_points or 8
	local steps, evals = {}, 0
	local t0 = os.clock()

	local metric = cmd.metric or "total"
	local mapping = metric:find("mapping") ~= nil
	local AILMENT_FIELD = { bleed = "BleedDPS", poison = "PoisonDPS", ignite = "IgniteDPS" }
	local ailmentField
	for name, f in pairs(AILMENT_FIELD) do if metric:find(name) then ailmentField = f end end
	local function areaFactor(o)
		return math.sqrt(math.max(o.AreaOfEffectMod or 1, 0.1)) * math.sqrt(math.max(o.ProjectileCount or 1, 1))
	end
	-- The guard (see optimize.IMPOSSIBLE_DPS): a broken calculation (infinite, not a number, or at the 32-bit
	-- ceiling) scores zero, so the tree never chases it.
	local function sane(v)
		if v ~= v or v == math.huge or v == -math.huge or math.abs(v) >= 2.0e9 then return 0 end
		return v
	end
	local dpsRaw
	-- Stat focuses ("+crit", "+es"... in the metric): same table as goals.FOCUS, damage x (1 + stat / scale), max x2.
	local FOCUS = {
		crit = { { "CritChance" }, 100 }, speed = { { "Speed" }, 6 }, block = { { "BlockChance", "SpellBlockChance" }, 75 },
		es = { { "EnergyShield" }, 8000 }, life = { { "Life" }, 6000 }, armour = { { "Armour" }, 30000 },
		evasion = { { "Evasion" }, 30000 }, leech = { { "LifeLeechRate" }, 1500 }, regen = { { "LifeRegen" }, 500 },
		mana = { { "Mana" }, 4000 }, str = { { "Str" }, 400 }, dex = { { "Dex" }, 400 }, int = { { "Int" }, 400 },
		spirit = { { "Spirit" }, 400 },
	}
	local focus = {}
	for part in metric:gmatch("[^+]+") do if FOCUS[part] then focus[#focus + 1] = FOCUS[part] end end
	local function dps(o)
		local v = sane(dpsRaw(o))
		for _, f in ipairs(focus) do
			local x = 0
			for _, field in ipairs(f[1]) do x = math.max(x, o[field] or 0) end
			v = v * (1 + math.min(math.max(x, 0), f[2]) / f[2])
		end
		return v
	end
	dpsRaw = function(o)
		if ailmentField then
			-- Same as optimize.ailment_score: the ailment counts fully, hits a quarter, minions included, and below
			-- 40% of the damage the score falls in proportion (so the tree never trades the ailment for hits).
			local m = type(o.Minion) == "table" and o.Minion or {}
			local a = math.max((o[ailmentField] or 0) + (m[ailmentField] or 0), 0)
			local h = math.max((o.TotalDPS or 0) + (m.TotalDPS or 0), 0)
			local share = (a + h) > 0 and a / (a + h) or 0
			local d = (a + 0.25 * h) * math.min(1, share / 0.4)
			return mapping and d * areaFactor(o) or d
		end
		if o.FullDPS and o.FullDPS > 0 then
			if mapping then
				return (o.FullDPS - 0.5 * (o.FullDotDPS or 0)) * math.sqrt(math.max(o.AreaOfEffectMod or 1, 0.1)) * math.sqrt(math.max(o.ProjectileCount or 1, 1))
			end
			return o.FullDPS
		end
		if mapping then
			-- Same clear score as optimize.py: hits full, DoT half, sqrt(area) x sqrt(projectiles)
			local m = type(o.Minion) == "table" and o.Minion or {}
			local d = (o.TotalDPS or 0) + 0.5 * (o.TotalDotDPS or 0) + (m.TotalDPS or 0) + 0.5 * (m.TotalDotDPS or 0)
			return d * math.sqrt(math.max(o.AreaOfEffectMod or 1, 0.1)) * math.sqrt(math.max(o.ProjectileCount or 1, 1))
		end
		local m = type(o.Minion) == "table" and o.Minion or {}
		return (o.TotalDPS or 0) + (o.TotalDotDPS or 0) + (m.TotalDPS or 0) + (m.TotalDotDPS or 0)
	end
	local function ehp(o) return o.TotalEHP or 0 end
	-- Build goals (see goals.py): movement speed and loot rarity as extra score.
	local msWeight, rarityWeight = cmd.movement_weight or 0, cmd.rarity_weight or 0
	local function goalTerms(o, base)
		local s = 0
		if msWeight > 0 then
			local m0 = math.max(base.EffectiveMovementSpeedMod or 1, 0.1)
			s = s + msWeight * ((o.EffectiveMovementSpeedMod or m0) - m0) / m0
		end
		if rarityWeight > 0 then
			local r0 = math.max(base.EffectiveLootRarityMod or 1, 0.1)
			s = s + rarityWeight * ((o.EffectiveLootRarityMod or r0) - r0) / r0
		end
		return s
	end

	-- Full scans are expensive, so between them only the best `shortlist` nodes from the
	-- last full scan are re-checked. A full scan runs every `refresh` picks.
	local refresh = cmd.refresh or 3
	local shortlistSize = cmd.shortlist or 150
	local shortlist = { [true] = nil, [false] = nil }
	local sinceFull = { [true] = math.huge, [false] = math.huge }

	local function eligible(node, ascend)
		local isAsc = node.ascendancyName ~= nil
		local reach = (node.type == "Normal" or ascend) and maxDist or farDist
		if capDist then reach = math.min(reach, capDist) end
		if not ascend and not node.alloc and node.path and #node.path <= reach and isSocketTarget(node) then
			return true
		end
		return not node.alloc and node.path and node.modKey and node.modKey ~= ""
			and (node.type == "Normal" or node.type == "Notable" or node.type == "Keystone")
			and #node.path <= reach
			and isAsc == ascend
			and (not ascend or node.ascendancyName == build.spec.curAscendClassBaseName or node.ascendancyName == build.spec.curAscendClassName)
			and not node.isMultipleChoiceOption
	end

	local lastScan = { n = 0, top = {} }
	local function bestStep(ascend)
		local calcFunc, base = build.calcsTab:GetMiscCalculator()
		local useFullDPS = useFull()
		local d0, e0 = math.max(dps(base), 1), math.max(ehp(base), 1)
		local full = sinceFull[ascend] >= refresh or not shortlist[ascend]
		local pool = {}
		if full then
			for _, node in pairs(build.spec.nodes) do
				if eligible(node, ascend) then table.insert(pool, node) end
			end
		else
			for _, node in ipairs(shortlist[ascend]) do
				if eligible(node, ascend) then table.insert(pool, node) end
			end
		end
		-- pairs() order is not stable between runs; sort so ties always break the same way.
		table.sort(pool, function(a, b) return a.id < b.id end)
		local scored = {}
		for _, node in ipairs(pool) do
			local pathNodes = {}
			for _, n in ipairs(node.path) do pathNodes[n] = true end
			local override = { addNodes = pathNodes }
			if node.type == "Socket" then override.repSlotName = "Jewel " .. node.id; override.repItem = proxy end
			local out = calcFunc(override, useFullDPS)
			evals = evals + 1
			local gain = (dps(out) - d0) / d0 + defWeight * (ehp(out) - e0) / e0 + goalTerms(out, base)
			table.insert(scored, { node = node, eff = gain / #node.path })
		end
		table.sort(scored, function(a, b)
			if a.eff ~= b.eff then return a.eff > b.eff end
			return a.node.id < b.node.id
		end)
		if full then
			local list = {}
			for i = 1, math.min(shortlistSize, #scored) do list[i] = scored[i].node end
			shortlist[ascend] = list
			sinceFull[ascend] = 0
		end
		lastScan = { n = #scored, top = {} }
		for i = 1, math.min(8, #scored) do lastScan.top[i] = scored[i].node.id end
		local top = scored[1]
		if not top or top.eff <= 0 then
			-- Nothing positive on the shortlist: force a full scan before giving up.
			if not full then
				sinceFull[ascend] = math.huge
				return bestStep(ascend)
			end
			return nil, 0
		end
		sinceFull[ascend] = sinceFull[ascend] + 1
		return top.node, top.eff
	end

	local function spend(ascend, limit)
		while true do
			local used, ascUsed = build.spec:CountAllocNodes()
			local have = ascend and ascUsed or used
			if have >= limit then break end
			local node, eff = bestStep(ascend)
			if not node then break end
			if have + #node.path > limit then
				-- Path too long for the points left: try only short paths.
				capDist = limit - have
				sinceFull[ascend] = math.huge
				node, eff = bestStep(ascend)
				capDist = nil
				sinceFull[ascend] = math.huge
				if not node then break end
			end
			local cost = #node.path
			local pathIds = {}
			for _, n in ipairs(node.path) do table.insert(pathIds, n.id) end   -- PoB clears node.path once allocated
			build.spec:AllocNode(node)
			build.spec:AddUndoState()
			if proxy and node.type == "Socket" then equipRaw("Jewel " .. node.id, cmd.jewel) end
			build.buildFlag = true
			frame()
			table.insert(steps, { node = node.dn, id = node.id, path = pathIds, type = node.type, cost = cost, gain_per_point = eff, ascendancy = ascend })
			if cmd.live and not quiet then
				-- Streamed while the search runs, so the website can show the tree growing: the node taken, the
				-- path to it, the best candidates it beat, how many were scored, and the build's score now.
				io.stdout:write("@@", json.encode({ event = "tree_step", chosen = node.id, name = node.dn, type = node.type,
					path = pathIds, considered = lastScan.top, scanned = lastScan.n, evals = evals, ascendancy = ascend,
					score = dps(build.calcsTab.mainOutput) }), "\n")
				io.stdout:flush()
			end
		end
	end

	spend(true, ascBudget)
	spend(false, budget)
	local buildSeconds = os.clock() - t0

	-- Swap phase. One whole-build score, fixed to the build as the build phase left it.
	local swaps, swapTries = {}, 0
	local refineRounds = cmd.refine_rounds or 12
	local refineTries = cmd.refine_tries or 4
	local maxRemove = cmd.refine_max_remove or 8
	-- Nodes the build is made around (an anchor keystone): the swap phase never takes them back.
	local locked = {}
	for _, spec in ipairs(cmd.locked or {}) do
		local node = findNode(spec)
		if node then locked[node.id] = true end
	end
	local deadline = os.clock() + (cmd.refine_seconds or math.max(5, buildSeconds * 0.6))
	local function recalc()
		build.buildFlag = true
		frame()
		return build.calcsTab.mainOutput
	end
	local ref = recalc()
	local D0, E0 = math.max(dps(ref), 1), math.max(ehp(ref), 1)
	local function J(o) return dps(o) / D0 + defWeight * ehp(o) / E0 + goalTerms(o, ref) end
	local scoreBefore = J(ref)

	local function snapshot()
		local ids = {}
		for id, node in pairs(build.spec.allocNodes) do
			if not node.ascendancyName then ids[id] = true end
		end
		return ids
	end
	local function restore(snap)
		local spec = build.spec
		for id, node in pairs(spec.allocNodes) do
			if not node.ascendancyName and not snap[id] then spec:DeallocSingleNode(node) end
		end
		for id in pairs(snap) do
			local node = spec.nodes[id]
			if node and not node.alloc then
				node.alloc = true
				node.allocMode = 0
				spec.allocNodes[id] = node
				if node.isAttribute then spec:SwitchAttributeNode(id, spec.attributeIndex or 1) end
			end
		end
		spec:BuildAllDependsAndPaths()
		spec:AddUndoState()
	end

	if refineRounds > 0 then
		for round = 1, refineRounds do
			if os.clock() > deadline then break end
			local calcFunc, base = build.calcsTab:GetMiscCalculator()
			local useFullDPS = useFull()
			local cur = J(base)
			-- What each allocated branch is worth: the score lost per point if it (and everything
			-- that only connects through it) were removed.
			local groups = {}
			for id, node in pairs(build.spec.allocNodes) do
				if not node.ascendancyName and node.type ~= "ClassStart" and node.type ~= "AscendClassStart"
					and not node.isMultipleChoiceOption and node.depends and #node.depends <= maxRemove then
					local set, n, ok = {}, 0, true
					for _, d in ipairs(node.depends) do
						if d.ascendancyName or d.type == "ClassStart" or locked[d.id] then ok = false end
						set[d] = true
						n = n + 1
					end
					if ok and n > 0 then
						local out = calcFunc({ removeNodes = set }, useFullDPS)
						evals = evals + 1
						table.insert(groups, { node = node, n = n, loss = (cur - J(out)) / n })
					end
				end
			end
			table.sort(groups, function(a, b)
				if a.loss ~= b.loss then return a.loss < b.loss end
				return a.node.id < b.node.id
			end)
			local kept = false
			for i = 1, math.min(refineTries, #groups) do
				if os.clock() > deadline then break end
				local g = groups[i]
				local snap, stepsBefore = snapshot(), #steps
				local removed = {}
				for _, d in ipairs(g.node.depends) do table.insert(removed, d.id) end
				swapTries = swapTries + 1
				quiet = true
				build.spec:DeallocNode(g.node)
				build.spec:AddUndoState()
				recalc()
				sinceFull[false] = math.huge
				spend(false, budget)
				local now = J(recalc())
				quiet = false
				if now > cur * (1 + 1e-4) + 1e-6 then
					table.insert(swaps, { removed = removed, name = g.node.dn, gain = now - cur })
					if cmd.live then
						local added = {}
						for k = stepsBefore + 1, #steps do
							for _, id in ipairs(steps[k].path) do table.insert(added, id) end
						end
						io.stdout:write("@@", json.encode({ event = "tree_step", removed = removed, added = added, name = g.node.dn,
							evals = evals, score = dps(build.calcsTab.mainOutput) }), "\n")
						io.stdout:flush()
					end
					kept = true
					break
				end
				for k = #steps, stepsBefore + 1, -1 do steps[k] = nil end
				restore(snap)
				recalc()
			end
			if not kept then break end
		end
	end

	-- The order to take passives, after swaps: steps whose target was swapped out are dropped,
	-- and any of their path passives still in the tree move to the next step that needs them.
	local finalOrder = {}
	if #swaps > 0 then
		local carry = {}
		local covered = {}
		for _, st in ipairs(steps) do
			local live = {}
			for _, id in ipairs(st.path) do
				local n = build.spec.nodes[id]
				if n and n.alloc and not covered[id] then table.insert(live, id) end
			end
			local target = build.spec.nodes[st.id]
			if target and target.alloc and not covered[st.id] then
				for _, id in ipairs(carry) do table.insert(live, id) end
				carry = {}
				for _, id in ipairs(live) do covered[id] = true end
				covered[st.id] = true
				st.path = live
				st.cost = #live
				table.insert(finalOrder, st)
			else
				for _, id in ipairs(live) do
					if id ~= st.id then table.insert(carry, id) end
					covered[id] = true
				end
			end
		end
		if #carry > 0 and #finalOrder > 0 then
			local last = finalOrder[#finalOrder]
			for _, id in ipairs(carry) do table.insert(last.path, id) end
			last.cost = #last.path
		end
		steps = finalOrder
	end

	local used, ascUsed = build.spec:CountAllocNodes()
	return { steps = steps, used = used, ascendancy_used = ascUsed, available = budget,
		evaluations = evals, seconds = os.clock() - t0, build_seconds = buildSeconds,
		swaps = swaps, swap_tries = swapTries, score_before_swaps = scoreBefore, score_after_swaps = J(recalc()) }
end

-- Weapon set passive points: each weapon set gets this many points of its own (quest points, plus Weapon Master's
-- "N passive skill points become weapon set skill points").
function handlers.weapon_set_points(cmd)
	frame()
	local extra = build.calcsTab.mainOutput and build.calcsTab.mainOutput.PassivePointsToWeaponSetPoints or 0
	local _, _, _, _, ws1, ws2 = build.spec:CountAllocNodes()
	return { points = (build.maxWeaponSets or 0) + extra, set1_used = ws1, set2_used = ws2 }
end

-- Weapon set mode for the next allocations: 0 shared, 1 or 2 for that set only (PoB's PassiveSpec.allocMode).
function handlers.set_alloc_mode(cmd)
	build.spec.allocMode = cmd.mode or 0
	return {}
end

-- Make room for set-specific passives: the `points` shared leaf nodes the current main skill (the other set's) needs
-- least become `keep_set` only. They still work on that set; the freed points can then be spent on the other set.
-- Only leaves (nothing else hangs off them), never keystones, sockets or ascendancy nodes, so no path breaks.
function handlers.split_weapon_set(cmd)
	local spec, keepSet, points = build.spec, cmd.keep_set or 1, cmd.points or 0
	local function score(o)
		if o.FullDPS and o.FullDPS > 0 then return o.FullDPS end
		return (o.TotalDPS or 0) + (o.TotalDotDPS or 0)
	end
	local moved = {}
	for _ = 1, points do
		local calcFunc, base = build.calcsTab:GetMiscCalculator()
		local useFullDPS = useFull()
		local cur, best, bestLoss = score(base), nil, math.huge
		for _, node in pairs(spec.allocNodes) do
			if (node.allocMode or 0) == 0 and not node.ascendancyName and node.type ~= "ClassStart"
				and node.type ~= "AscendClassStart" and node.type ~= "Keystone" and node.type ~= "Socket"
				and not node.isJewelSocket and node.depends and #node.depends == 1 then
				local loss = cur - score(calcFunc({ removeNodes = { [node] = true } }, useFullDPS))
				if loss < bestLoss then best, bestLoss = node, loss end
			end
		end
		if not best then break end
		best.allocMode = keepSet
		table.insert(moved, best.dn or tostring(best.id))
		spec:BuildAllDependsAndPaths()
		build.buildFlag = true
		frame()
	end
	spec:AddUndoState()
	return { moved = moved }
end

function handlers.reset_tree(cmd)
	build.spec:ResetNodes()
	build.spec:BuildAllDependsAndPaths()
	build.spec:AddUndoState()
	build.buildFlag = true
	frame()
	return {}
end

function handlers.calc(cmd)
	for _, group in ipairs(build.skillsTab.socketGroupList) do
		build.skillsTab:ProcessSocketGroup(group)
	end
	build.skillsTab:UpdateGlobalGemCountAssignments()
	build.buildFlag = true
	frame()
	local out = build.calcsTab.mainOutput
	local result = pick(out, cmd.fields)
	return { main_skill = mainSkillName(), output = result, warnings = warnings() }
end

-- Every numeric output of the main skill (minion ones prefixed "Minion"), and PoB's breakdown lines for the
-- requested keys. The Breaker uses it to see which mechanic moves when one stat changes.
function handlers.outputs(cmd)
	build.buildFlag = true
	frame()
	local out, res, bd = build.calcsTab.mainOutput, {}, {}
	for k, v in pairs(out) do if type(v) == "number" then res[k] = v end end
	if type(out.Minion) == "table" then
		for k, v in pairs(out.Minion) do if type(v) == "number" then res["Minion" .. k] = v end end
	end
	local env = build.calcsTab.mainEnv
	local breakdown = env and env.player and env.player.breakdown or {}
	for _, key in ipairs(cmd.breakdown or {}) do
		local b = breakdown[key]
		if type(b) == "table" then
			local lines = {}
			for _, l in ipairs(b) do if type(l) == "string" then table.insert(lines, l) end end
			bd[key] = lines
		end
	end
	local skill = env and env.player and env.player.mainSkill
	local part = skill and skill.skillPart
	local parts = {}
	for i, p in ipairs(skill and skill.activeEffect.grantedEffect.parts or {}) do parts[i] = p.name end
	return { output = res, breakdown = bd, skill_part = part, parts = parts }
end

-- Lists gems. filter: "support" | "active" | nil; tags: every tag must match
-- What each gem does, for the website's hover cards: PoB's own description and tag line, per gem name.
function handlers.gem_texts(cmd)
	local out = {}
	for _, gem in pairs(data.gems) do
		local ge = gem.grantedEffect
		if gem.name and ge and not out[gem.name] then
			local isSupport = (gem.tags and gem.tags.support) and true or false
			out[gem.name] = { desc = ge.description or "", tags = gem.tagString or "", support = isSupport }
		end
	end
	return { gems = out }
end

-- Full gem tooltips for the website: PoB's own gem tooltip (Classes/GemTooltip), drawn into a list of lines instead
-- of onto the screen. Each line is {t = text, k = kind}: kind is "title", "type", "tags", "info", "desc", "stat",
-- "unsupported", "head" or "sep". Gems are shown at their top natural level with quality 0, plus quality effects.
local function tooltipLines(gem)
	local GemTooltip = LoadModule("Classes/GemTooltip")
	local lines, kinds = {}, {
		{ colorCodes.GEMDESCRIPTION, "desc" }, { colorCodes.UNSUPPORTED, "unsupported" }, { colorCodes.MAGIC, "stat" },
		{ colorCodes.ENCHANTED, "stat" }, { colorCodes.GEMINFO, "info" }, { colorCodes.GEM, "title" },
	}
	local tip = { maxWidth = 600 }
	function tip:AddLine(_, text)
		text = tostring(text or "")
		local kind = "info"
		for _, k in ipairs(kinds) do
			if k[1] and text:sub(1, #k[1]) == k[1] then kind = k[2] break end
		end
		if text:find("Additional Effects From Quality", 1, true) then kind = "head" end
		if text:find("^%^x7F7F7F") or text:find("^%s+%^x7F7F7F") then kind = "tags" end
		local plain = text:gsub("%^x%x%x%x%x%x%x", ""):gsub("%^%d", ""):gsub("^%s+", ""):gsub("%s+$", "")
		if plain ~= "" then table.insert(lines, { t = plain, k = kind }) end
	end
	function tip:AddSeparator() if #lines > 0 and lines[#lines].k ~= "sep" then table.insert(lines, { k = "sep" }) end end
	function tip:AddBuildPlannerNote() end
	local level = math.min(20, gem.naturalMaxLevel or 20)
	local inst = { gemData = gem, level = level, quality = 0, nameSpec = gem.name, corruptLevel = 0, enabled = true }
	GemTooltip.AddGemTooltip(tip, build, inst, { includeQualityRange = true })
	if lines[1] then lines[1].k = "title" end
	if lines[2] then lines[2].k = "type" end
	if lines[#lines] and lines[#lines].k == "sep" then table.remove(lines) end
	return lines
end

function handlers.gem_tooltips(cmd)
	local out, failed = {}, 0
	for _, gem in pairs(data.gems) do
		if gem.name and gem.grantedEffect and not out[gem.name] then
			local ok, lines = pcall(tooltipLines, gem)
			if ok then out[gem.name] = lines else failed = failed + 1 end
		end
	end
	return { gems = out, failed = failed }
end

function handlers.list_gems(cmd)
	local gems = {}
	for _, gem in pairs(data.gems) do
		local isSupport = gem.tags and gem.tags.support
		local ok = (cmd.filter == nil)
			or (cmd.filter == "support" and isSupport)
			or (cmd.filter == "active" and not isSupport)
		for _, tag in ipairs(cmd.tags or {}) do
			if not (gem.tags and gem.tags[tag]) then ok = false end
		end
		if ok then
			table.insert(gems, { name = gem.name, tags = gem.tagString, family = gem.gemFamily, tier = gem.Tier,
				lineage = gem.tags and gem.tags.lineage or false, conditional = isSupport and isConditional(gem) or false })
		end
	end
	table.sort(gems, function(a, b) return a.name < b.name end)
	return { gems = gems }
end

-- Every castable (non-support) gem with what the build generator needs to reason about it:
-- skill types (Attack, Spell, Minion, Persistent...), required weapon types, spirit cost, tags.
local skillTypeName = {}
for n, v in pairs(SkillType) do skillTypeName[v] = n end

function handlers.skill_catalog(cmd)
	local out = {}
	for id, gem in pairs(data.gems) do
		local ge = gem.grantedEffect
		if ge and not ge.support and not (gem.tags and gem.tags.support) and gem.name and gem.name ~= "" then
			local types, weapons, tags = {}, {}, {}
			for k in pairs(ge.skillTypes or {}) do
				if skillTypeName[k] then table.insert(types, skillTypeName[k]) end
			end
			-- A totem gem's own effect only places the totem; what the totem does (Attack, Physical...) is in
			-- its additional effects, so those types count too.
			if ge.skillTypes and ge.skillTypes[SkillType.SummonsTotem] then
				local have = {}
				for _, t in ipairs(types) do have[t] = true end
				for _, extra in ipairs(gem.additionalGrantedEffects or {}) do
					for k in pairs(extra.skillTypes or {}) do
						local n = skillTypeName[k]
						if n and not have[n] then have[n] = true; table.insert(types, n) end
					end
				end
			end
			for k in pairs(ge.weaponTypes or {}) do table.insert(weapons, k) end
			for k in pairs(gem.tags or {}) do table.insert(tags, k) end
			table.sort(types); table.sort(weapons); table.sort(tags)
			local lvl = ge.levels and (ge.levels[20] or ge.levels[#ge.levels])
			table.insert(out, {
				name = gem.name, id = ge.id, types = types, weapons = weapons, tags = tags,
				spirit = lvl and lvl.spiritReservationFlat or 0,
				-- Not a gem anyone can socket: granted by an item, or by a passive / ascendancy node (Virtuous Barrier).
				from_item = (ge.fromItem or ge.fromTree) and true or false,
				from_tree = ge.fromTree and true or false,
				tier = gem.Tier, str = gem.reqStr, dex = gem.reqDex, int = gem.reqInt,
			})
		end
	end
	table.sort(out, function(a, b) return a.name < b.name or (a.name == b.name and a.id < b.id) end)
	return { skills = out }
end

-- Base cast time and cooldown of gems by name (what Cast on X uses for its energy: base, not modified, cast time).
function handlers.gem_info(cmd)
	local out = {}
	for _, name in ipairs(cmd.names or {}) do
		for _, gem in pairs(data.gems) do
			if gem.name == name and gem.grantedEffect then
				local ge = gem.grantedEffect
				local lvl = ge.levels and (ge.levels[cmd.level or 20] or ge.levels[#ge.levels]) or {}
				out[name] = { cast_time = ge.castTime or 0, cooldown = lvl.cooldown, types = {}, req_level = lvl.levelRequirement,
					support = (ge.support or (gem.tags and gem.tags.support)) and true or false }
				for k in pairs(ge.skillTypes or {}) do
					for n, v in pairs(SkillType) do if v == k then table.insert(out[name].types, n) end end
				end
				break
			end
		end
	end
	return { gems = out }
end

-- Keystones on the passive tree (not ascendancy ones): what a build can be made around.
function handlers.list_keystones(cmd)
	local out = {}
	for _, node in pairs(build.spec.nodes) do
		if node.type == "Keystone" and not node.ascendancyName and node.dn then
			table.insert(out, { name = node.dn, text = table.concat(node.sd or {}, " / ") })
		end
	end
	table.sort(out, function(a, b) return a.name < b.name end)
	return { keystones = out }
end

function handlers.list_classes(cmd)
	local classes = {}
	for _, class in pairs(build.spec.tree.classes) do
		local asc = {}
		for id, a in pairs(class.classes) do
			if id ~= 0 and a.name then table.insert(asc, a.name) end
		end
		table.insert(classes, { name = class.name, ascendancies = asc })
	end
	return { classes = classes }
end

-- Everything a game update can change, each entry with a stable text form that Python hashes, so
-- tools/catalog_diff.py can list what PoB 1.0 added, removed or reworked (gems, uniques, bases, tree).
local function ser(v, depth)
	depth = depth or 0
	local t = type(v)
	if t == "table" then
		if depth > 6 then return "{...}" end
		local keys = {}
		for k in pairs(v) do table.insert(keys, k) end
		table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
		local parts = {}
		for _, k in ipairs(keys) do
			local sv = ser(v[k], depth + 1)
			if sv then table.insert(parts, tostring(k) .. "=" .. sv) end
		end
		return "{" .. table.concat(parts, ",") .. "}"
	elseif t == "number" or t == "boolean" then return tostring(v)
	elseif t == "string" then return string.format("%q", v)
	end
	return nil   -- functions and userdata say nothing stable
end

function handlers.catalog_snapshot(cmd)
	local gems, uniques, bases, nodes = {}, {}, {}, {}
	for _, gem in pairs(data.gems) do
		local ge = gem.grantedEffect
		if gem.name and gem.name ~= "" then
			local lvl = ge and ge.levels and (ge.levels[20] or ge.levels[#ge.levels])
			table.insert(gems, { name = gem.name, support = (gem.tags and gem.tags.support) and true or false,
				tags = gem.tagString or "", text = ser({ ge and ge.stats, ge and ge.constantStats, lvl,
				ge and ge.skillTypes, ge and ge.statMap and true, gem.reqStr, gem.reqDex, gem.reqInt }) or "" })
		end
	end
	for _, item in pairs(main.uniqueDB.list) do
		table.insert(uniques, { name = item.name, text = item.raw or "" })
	end
	for name, base in pairs(data.itemBases) do
		if not base.hidden then
			table.insert(bases, { name = name, type = base.type, subType = base.subType, text = ser(base) or "" })
		end
	end
	local tree = build.spec.tree
	local counts = {}
	for _, node in pairs(tree.nodes) do
		local kind = node.type or "Normal"
		counts[kind] = (counts[kind] or 0) + 1
		if node.dn and (kind == "Notable" or kind == "Keystone" or node.ascendancyName) then
			table.insert(nodes, { name = node.dn, type = kind, asc = node.ascendancyName,
				text = table.concat(node.sd or {}, " / ") })
		end
	end
	return { gems = gems, uniques = uniques, bases = bases,
		tree = { version = build.spec.treeVersion, counts = counts, nodes = nodes } }
end

function handlers.list_uniques(cmd)
	local list = {}
	for _, item in pairs(main.uniqueDB.list) do
		if not cmd.type or (item.type and item.type:lower() == cmd.type:lower()) then
			local parsed = new("Item"):Item(item.raw)
			table.insert(list, { name = item.name, base = item.baseName, type = item.type, raw = item.raw,
				level = parsed.requirements and parsed.requirements.level or 0,
				subType = parsed.base and parsed.base.subType })
		end
	end
	return { uniques = list }
end


-- Trade site link for an item: the official PoE 2 trade search, pre-filled with the item's base and its
-- affixes at a minimum just under the planned values (or the unique's name). Uses PoB's own "Buy similar"
-- mapping from mod text to trade stat ids (Data/TradeSiteStats.lua), and packs the query into the link
-- itself, so nothing is sent to GGG's servers: the player's browser opens the search.
local buySimilar
function handlers.trade_query(cmd)
	if not buySimilar then
		buySimilar = LoadModule("Classes/CompareBuySimilar")
	end
	local item = new("Item"):Item(cmd.raw)
	local q = { status = { option = "available" }, stats = { { type = "and", filters = {} } } }
	local isUnique = item.rarity == "UNIQUE" or item.rarity == "RELIC"
	if isUnique then
		q.name, q.type = item.title, item.baseName
	else
		q.type = item.baseName
		local entries = buySimilar.addModEntries(item, {
			{ list = item.implicitModLines, type = "implicit" },
			{ list = item.explicitModLines, type = "explicit" },
		})
		local scale = cmd.slack or 0.9
		for _, e in ipairs(entries) do
			local function filter(id)
				local f = { id = id }
				if e.isOption then
					f.value = { min = e.value, max = e.value }
				elseif e.value then
					local v = math.floor(e.value * scale * 100 + 0.5) / 100
					f.value = e.invert and { max = -v } or { min = v }
				end
				return f
			end
			if #e.tradeIds == 1 then
				table.insert(q.stats[1].filters, filter(e.tradeIds[1]))
			elseif #e.tradeIds > 1 then
				local count = { type = "count", value = { min = 1 }, filters = {} }
				for _, id in ipairs(e.tradeIds) do table.insert(count.filters, filter(id)) end
				table.insert(q.stats, count)
			end
		end
	end
	-- The query goes back as JSON; Python gzips and base64url-encodes it into the link (PoB's Deflate()
	-- belongs to its graphics layer, which isn't loaded headless).
	return { query = { query = q, sort = { price = "asc" } } }
end

-- patch: the game version PoB's data is for (its newest passive tree, "0_5"); saved builds are labelled with it.
reply({ ok = true, ready = true, version = launch.versionNumber, patch = latestTreeVersion })
for line in io.stdin:lines() do
	local okDecode, cmd = pcall(json.decode, line)
	if not okDecode or type(cmd) ~= "table" then
		reply({ ok = false, error = "bad json" })
	else
		local handler = handlers[cmd.cmd]
		if not handler then
			reply({ ok = false, error = "unknown cmd: " .. tostring(cmd.cmd) })
		else
			local ok, res = pcall(handler, cmd)
			if ok then
				res.ok = true
				reply(res)
			else
				reply({ ok = false, error = tostring(res) })
			end
		end
	end
end
