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
	"TotalDot", "TotalDotDPS", "WithBleedDPS", "WithPoisonDPS", "WithIgniteDPS",
	"Life", "EnergyShield", "Mana", "Armour", "Evasion", "TotalEHP",
	"PhysicalMaximumHitTaken", "FireResist", "ColdResist", "LightningResist", "ChaosResist",
	"Str", "Dex", "Int",
}

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
	build.skillsTab:PasteSocketGroup(cmd.text)
	local index = #build.skillsTab.socketGroupList
	if index == before then error("no gems recognised in: " .. cmd.text) end
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
	build.skillsTab:PasteSocketGroup(cmd.text)
	if #list == count then error("no gems recognised in: " .. cmd.text) end
	local new = table.remove(list)
	list[cmd.group] = new
	build.mainSocketGroup = cmd.group
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
	local result = {}
	for _, f in ipairs(cmd.fields or DEFAULT_FIELDS) do
		if type(out[f]) == "number" then result[f] = out[f] end
	end
	return { output = result, supported = supported, main_skill = mainSkillName() }
end

function handlers.remove_skill(cmd)
	table.remove(build.skillsTab.socketGroupList, cmd.group)
	build.mainSocketGroup = math.min(build.mainSocketGroup, math.max(1, #build.skillsTab.socketGroupList))
	build.buildFlag = true
	frame()
	return {}
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

function handlers.calc(cmd)
	frame()
	local out = build.calcsTab.mainOutput
	local result = {}
	for _, f in ipairs(cmd.fields or DEFAULT_FIELDS) do
		if type(out[f]) == "number" then result[f] = out[f] end
	end
	return { main_skill = mainSkillName(), output = result }
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
			table.insert(gems, { name = gem.name, tags = gem.tagString, family = gem.gemFamily, tier = gem.Tier })
		end
	end
	table.sort(gems, function(a, b) return a.name < b.name end)
	return { gems = gems }
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
			table.insert(list, { name = item.name, base = item.baseName, type = item.type, raw = item.raw })
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
