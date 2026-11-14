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

local function frame()
	runCallback("OnFrame")
end

local DEFAULT_FIELDS = {
	"FullDPS", "TotalDPS", "CombinedDPS", "AverageHit", "Speed", "HitChance",
	"CritChance", "CritMultiplier", "BleedDPS", "BleedChance", "PoisonDPS", "IgniteDPS",
	"TotalDot", "TotalDotDPS", "MinionDPS", "MinionDotDPS", "FullDPS", "FullDotDPS", "WithBleedDPS", "WithPoisonDPS", "WithIgniteDPS",
	"Life", "EnergyShield", "Mana", "Armour", "Evasion", "TotalEHP",
	"PhysicalMaximumHitTaken", "FireResist", "ColdResist", "LightningResist", "ChaosResist",
	"Str", "Dex", "Int", "Spirit", "SpiritUnreserved", "EffectiveMovementSpeedMod", "EffectiveLootRarityMod",
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
		for _, entry in ipairs(list) do
			table.insert(w, kind .. ": " .. table.concat((function()
				local parts = {}
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

local handlers = {}

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
	for id, mod in pairs(data.itemMods.Item) do
		if (mod.type == "Prefix" or mod.type == "Suffix") and (mod.level or 0) <= (cmd.max_level or 100) then
			local weight = 0
			for i, key in ipairs(mod.weightKey or {}) do
				if base.tags[key] then weight = mod.weightVal[i] or 0 break end
			end
			if weight > 0 then
				local lines = {}
				for _, line in ipairs(mod) do table.insert(lines, line) end
				table.insert(list, { id = id, type = mod.type, group = mod.group, level = mod.level or 0,
					lines = lines, tags = mod.modTags, weight = weight })
			end
		end
	end
	return { affixes = list }
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

-- text is PoB's paste format, one gem per line: "Name level/quality  count"
function handlers.add_skill(cmd)
	local before = #build.skillsTab.socketGroupList
	build.skillsTab:PasteSocketGroup(disambiguate(cmd.text))
	local index = #build.skillsTab.socketGroupList
	if index == before then error("no gems recognised in: " .. cmd.text) end
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
	if not cmd.keep_main then build.mainSocketGroup = cmd.group end
	-- Resolve gems and global gem counts before recalculating, otherwise the
	-- calculation sees the previous gem list and results lag one step behind.
	build.skillsTab:ProcessSocketGroup(new)
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
			if active and limit and limit > 1 and active.count ~= limit then
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

function handlers.set_main(cmd)
	build.mainSocketGroup = cmd.group
	build.buildFlag = true
	frame()
	return { main_skill = mainSkillName() }
end

-- Config tab inputs, e.g. {"customMods": "...", "enemyIsBoss": "Pinnacle"}
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

function handlers.points(cmd)
	local used, ascUsed = build.spec:CountAllocNodes()
	return { available = passivePoints(), used = used, ascendancy_used = ascUsed }
end

-- Greedy passive tree optimiser using PoB's fast what-if calculator.
-- Each step tries every reachable node (path up to max_dist points), scores
-- (relative DPS gain + def_weight * relative EHP gain) per point spent, and
-- allocates the best path. Ascendancy points are spent the same way.
function handlers.optimise_tree(cmd)
	local maxDist = cmd.max_dist or 6
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
	local function dps(o)
		if ailmentField then
			-- Same as optimize.score_of: the ailment counts fully, hits a quarter.
			local d = (o[ailmentField] or 0) + 0.25 * (o.TotalDPS or 0)
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
		return not node.alloc and node.path and node.modKey and node.modKey ~= ""
			and (node.type == "Normal" or node.type == "Notable" or node.type == "Keystone")
			and #node.path <= maxDist
			and isAsc == ascend
			and (not ascend or node.ascendancyName == build.spec.curAscendClassBaseName or node.ascendancyName == build.spec.curAscendClassName)
			and not node.isMultipleChoiceOption
	end

	local function bestStep(ascend)
		local calcFunc, base = build.calcsTab:GetMiscCalculator()
		local full = useFull()
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
			local out = calcFunc({ addNodes = pathNodes }, full)
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
				local saved = maxDist
				maxDist = limit - have
				sinceFull[ascend] = math.huge
				node, eff = bestStep(ascend)
				maxDist = saved
				if not node then break end
			end
			local cost = #node.path
			build.spec:AllocNode(node)
			build.spec:AddUndoState()
			build.buildFlag = true
			frame()
			table.insert(steps, { node = node.dn, type = node.type, cost = cost, gain_per_point = eff, ascendancy = ascend })
		end
	end

	spend(true, ascBudget)
	spend(false, budget)
	local used, ascUsed = build.spec:CountAllocNodes()
	return { steps = steps, used = used, ascendancy_used = ascUsed, available = budget,
		evaluations = evals, seconds = os.clock() - t0 }
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

-- Lists gems. filter: "support" | "active" | nil; tags: every tag must match
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
			for k in pairs(ge.weaponTypes or {}) do table.insert(weapons, k) end
			for k in pairs(gem.tags or {}) do table.insert(tags, k) end
			table.sort(types); table.sort(weapons); table.sort(tags)
			local lvl = ge.levels and (ge.levels[20] or ge.levels[#ge.levels])
			table.insert(out, {
				name = gem.name, id = ge.id, types = types, weapons = weapons, tags = tags,
				spirit = lvl and lvl.spiritReservationFlat or 0,
				from_item = ge.fromItem and true or false,
				tier = gem.Tier, str = gem.reqStr, dex = gem.reqDex, int = gem.reqInt,
			})
		end
	end
	table.sort(out, function(a, b) return a.name < b.name or (a.name == b.name and a.id < b.id) end)
	return { skills = out }
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

reply({ ok = true, ready = true, version = launch.versionNumber })
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
