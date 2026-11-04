"""Mission 15 (Hardcoded): the export token is in the ABAP source, but split,
out of order, partly reversed, and next to a complete-looking decoy."""
import re

FLAG = "TRIATHLON{sap_abap_test}"          # conftest's FLAG_15_SAP_ABAP


def source(dist):
    return (dist / "ZDFLOP_RESULT_EXPORT.abap").read_text()


def solve(src):
    """What a player does: take the production branch, follow normalize and CONCATENATE."""
    prod = src.split("  ELSE.", 1)[1].split("  ENDIF.", 1)[0]
    values = dict(re.findall(r"(lv_k\d) = '([^']*)'\.", prod))
    for var in re.findall(r"PERFORM normalize CHANGING (lv_k\d)\.", prod):
        assert "reverse( cv_part )" in src.split("FORM normalize", 1)[1]
        values[var] = values[var][::-1]
    order = re.search(r"CONCATENATE ((?:lv_k\d\s*)+)INTO lv_token\.", prod).group(1).split()
    return "".join(values[v] for v in order)


def test_reading_the_logic_gives_the_flag(dist):
    assert solve(source(dist)) == FLAG


def test_shortcuts_do_not_work(dist):
    src = source(dist)
    assert FLAG not in src                                          # not one literal
    whole = re.findall(r"TRIATHLON\{[^}']*\}", src)
    assert len(whole) == 1 and whole[0] != FLAG                     # grep finds the decoy only
    assert "IF sy-sysid <> 'DFL'." in src and "DFL (production)" in src
    order = re.search(r"CONCATENATE (.*) INTO", src).group(1).split()
    assert order != sorted(order)                                   # not k1 k2 k3
    assert "Ordre" not in src and "piege" not in src and "factice" not in src   # no giveaway comment


def test_hints_and_guide_follow_the_new_source(hub_module):
    import pathlib
    readme = (pathlib.Path(__file__).resolve().parents[1] / "challenges" / "15-sap-abap" / "README.md").read_text()
    assert "lv_k3 lv_k1 lv_k2" in readme and "lv_decoy" not in readme
    steps = " ".join(hub_module.GUIDE["15"][2])
    assert "lv_k3 lv_k1 lv_k2" in steps and "Reverse" in steps and "lv_decoy" not in steps
