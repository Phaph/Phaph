"""Class weapons (data/class_weapons.json): builds keep to their class's weapons unless Off-meta or a picked weapon."""
import generate as g


def setup_module():
    g._ALL_ASCS[:] = [("Ranger", "Deadeye"), ("Ranger", "Pathfinder"), ("Mercenary", "Tactician"),
                      ("Mercenary", "Witchhunter"), ("Mercenary", "Gemling Legionnaire"), ("Monk", "Invoker")]


def test_class_keeps_to_its_weapons():
    assert g.weapon_ok({}, "Ranger", "Deadeye", "Bow", None)
    assert not g.weapon_ok({}, "Ranger", "Deadeye", "Spear", None)      # close weapon: not the main weapon...
    assert g.weapon_ok({}, "Ranger", "Deadeye", "Spear", None, second=True)   # ...but fine on weapon set 2
    assert g.weapon_ok({"_class_close": True}, "Ranger", "Deadeye", "Spear", None)   # or when nothing intended works
    assert not g.weapon_ok({}, "Ranger", "Deadeye", "Staff", "none")     # a staff spell isn't a Ranger build
    assert g.weapon_ok({}, "Monk", "Invoker", "Staff", "Warstaff")       # quarterstaff
    assert not g.weapon_ok({}, "Monk", "Invoker", "Staff", "none")       # caster staff


def test_off_meta_and_picked_weapons_unlock():
    assert g.weapon_ok({"off_meta": True}, "Ranger", "Deadeye", "Staff", "none")
    assert g.weapon_ok({"weapons": ["Staff"]}, "Ranger", "Deadeye", "Staff", "none")
    assert g.weapon_ok({"_class_unlocked": True}, "Ranger", "Deadeye", "Wand", None)


def test_gemling_can_use_a_mace_other_mercenaries_cannot():
    assert g.weapon_ok({}, "Mercenary", "Gemling Legionnaire", "Two Hand Mace", None)
    assert not g.weapon_ok({}, "Mercenary", "Tactician", "Two Hand Mace", None)
    assert g.weapon_ok({}, "Mercenary", None, "One Hand Mace", None)     # a class-wide search keeps it in play


def test_unknown_class_has_no_rule():
    assert g.weapon_ok({}, "Nobody", None, "Staff", None)


def test_huntress_mains_a_spear_and_may_swap_to_a_bow():
    g._ALL_ASCS[:] = [("Huntress", "Amazon")]
    assert g.weapon_ok({}, "Huntress", "Amazon", "Spear", None)
    assert not g.weapon_ok({}, "Huntress", "Amazon", "Bow", None)
    assert g.weapon_ok({}, "Huntress", "Amazon", "Bow", None, second=True)
    assert g.weapon_ok({"weapons": ["Bow"]}, "Huntress", "Amazon", "Bow", None)   # the player picked the bow
