"""Tidy the place list before the site is built:

- names typed in all lowercase or ALL CAPS get normal capitals, common misspellings are fixed
- obvious non-places (test entries, caterers, convenience stores) are dropped
- the same place entered twice (same name within 150 m) is merged into one
- pure veg and Jain food are marked from the name and cuisine, where they're clear

Used by build.py: items = cleanup.run(items)."""
import math
import re
import unicodedata

SMALL = {"and", "of", "the", "a", "an", "in", "on", "at", "by", "for", "to", "n"}
KEEP_UPPER = {"kfc", "bbq", "ccd", "mg", "rk", "rr", "jb", "kk", "dp", "sk", "ss", "vip", "ii", "iii", "iv", "it", "hq"}
FIX = [  # whole-word spelling fixes, applied after capitalising
    (r"\bProtien\b", "Protein"), (r"\bResturant\b", "Restaurant"), (r"\bResturent\b", "Restaurant"),
    (r"\bRestaraunt\b", "Restaurant"), (r"\bBristo\b", "Bistro"), (r"\bCentar\b", "Centre"), (r"\bRivar\b", "River"),
    (r"^Dominos$", "Domino's"), (r"^Dominos Pizza$", "Domino's"), (r"^Shivsagar$", "Shiv Sagar"),
    (r"^La Pinoz'?s Pizza$", "La Pino'z Pizza"), (r"^Mcdonald'?s$", "McDonald's"), (r"^Mc Donald'?s$", "McDonald's"),
    (r"^Starbucks Coffee$", "Starbucks"), (r"^Cafe Coffee Day \(Ccd\)$", "Cafe Coffee Day"),
]
DROP = re.compile(r"^(drfg|test|asdf|xyz)$|caterers?\b|\bcatering\b|^7/11|^department store$|^pinky store$|^\(.*\)$", re.I)


def tidy_name(name):
    n = re.sub(r"\s+", " ", name).strip()
    letters = [c for c in n if c.isalpha() and ord(c) < 128]
    if letters and (n == n.lower() or (n == n.upper() and len(letters) >= 4)):
        words = []
        for i, w in enumerate(n.lower().split(" ")):
            core = re.sub(r"[^a-z0-9]", "", w)
            if core in KEEP_UPPER:
                words.append(w.upper())
            elif i > 0 and core in SMALL:
                words.append(w)
            else:
                # capitalise the first letter, and after a hyphen or bracket ("sher-e-punjab", "(fort)")
                words.append(re.sub(r"(^|[-(/])([a-z])", lambda m: m.group(1) + m.group(2).upper(), w))
        n = " ".join(words)
    for pat, rep in FIX:
        n = re.sub(pat, rep, n, flags=re.I)
    return n


def key(name):
    """Name key for spotting duplicates; keeps non-Latin letters (Devanagari names)."""
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c)).lower().replace("&", "and")   # Café = Cafe
    return re.sub(r"[\W_]+", "", n)


def km(a, b):
    return math.hypot((a["lat"] - b["lat"]) * 111.0, (a["lng"] - b["lng"]) * 105.0)


def info(it):
    return sum(bool(it.get(k)) for k in ("street", "cuisine", "hours", "phone", "website", "menu", "rating", "priceTwo")) + (0 if it.get("web") else 1)


def merge(a, b):
    """Keep the entry with more details and fill its gaps from the other."""
    keep, other = (a, b) if info(a) >= info(b) else (b, a)
    for k in ("street", "hours", "phone", "website", "menu"):
        if not keep.get(k) and other.get(k):
            keep[k] = other[k]
    if not keep.get("rating") and other.get("rating"):
        for k in ("rating", "ratingSrc", "src", "srcUrl"):
            keep[k] = other[k]
    if not keep.get("priceTwo") and other.get("priceTwo"):
        keep["priceTwo"], keep["priceSrc"] = other["priceTwo"], other.get("priceSrc", "")
    cs = [c for c in keep.get("cuisine", "").split(";") if c]
    cs += [c for c in other.get("cuisine", "").split(";") if c and c not in cs]
    keep["cuisine"] = ";".join(cs)
    keep["diet"] = keep.get("diet", 0) | other.get("diet", 0)
    if keep["diet"] & 4:
        keep["diet"] &= ~1
    return keep


# ---------------------------------------------------------------- veg and Jain
NONVEG_HINT = re.compile(r"malvan|fish|sea ?food|chicken|mutton|biryani|kebab|kabab|non ?veg|tandoor|darbar|mughlai|"
                         r"bar\b|pub\b|brew|wine|beer|grill|bbq|barbeque|shawarma|egg|meat|prawn|koliwada|irani", re.I)
VEG_NAME = re.compile(r"pure ?veg|shudh|shakahari|vegetarian|\bveg\b(?! ?(and|&|n) ?non)|udupi|udipi|\bbhavan\b|bhojanalay|"
                      r"\bthali\b|rajdhani|haldiram|bikanervala|shiv ?sagar|sukh ?sagar|status restaurant|gurukripa|guru ?kripa|"
                      r"kailash parbat|govinda|\bsoam\b|cream cent(re|er)|swati snacks|jumbo king|goli vada|vada ?pav|farsan|"
                      r"\bsweets?\b|mithai|\bjain\b|thaker|naturals|natural ice cream|sagar ratna|anand bhavan|chaat|"
                      r"\bdosa\b|\bidli\b|annapurna|rasoi|\bbhel\b|pani ?puri|juice|ice cream|dairy|tea stall|chai", re.I)
VEG_CUISINE = {"Gujarati", "Rajasthani", "Marwari", "Jain", "Vegetarian only", "Vegan", "Udupi", "Juice", "Ice Cream", "Chaat"}
JAIN_NAME = re.compile(r"\bjain\b|rajdhani|thaker|haldiram|bikanervala|shiv ?sagar|kailash parbat|status restaurant|"
                       r"swati snacks|\bsoam\b|cream cent(re|er)|sukh ?sagar|gurukripa|guru ?kripa", re.I)
JAIN_CUISINE = {"Jain", "Gujarati", "Rajasthani", "Marwari"}


def tag_veg(it):
    name, cs = it["name"], {c for c in it.get("cuisine", "").split(";") if c}
    if it.get("diet", 0) & 4 or NONVEG_HINT.search(name) or cs & {"Seafood", "Chicken", "Kebab", "Mughlai", "Barbecue", "Fish", "Burger", "Steak", "Biryani"}:
        return False, False
    veg = bool(VEG_NAME.search(name)) or bool(cs & VEG_CUISINE)
    jain = bool(JAIN_NAME.search(name)) or bool(cs & JAIN_CUISINE)
    return veg or jain, jain


def run(items):
    out, dropped = [], 0
    renamed = 0
    for it in items:
        if DROP.search(it["name"]):
            dropped += 1
            continue
        new = it["name"] if it.get("web") else tidy_name(it["name"])   # listing-site names are already written properly
        if new != it["name"]:
            it["name"] = new
            renamed += 1
        out.append(it)

    # Merge duplicates: same name key within 150 m.
    groups = {}
    for it in out:
        groups.setdefault(key(it["name"]), []).append(it)
    merged, result = 0, []
    for k, lst in groups.items():
        if not k or len(lst) == 1:
            result.extend(lst)
            continue
        kept = []
        for it in lst:
            near = next((x for x in kept if km(x, it) <= 0.15), None)
            if near is None:
                kept.append(it)
            else:
                kept[kept.index(near)] = merge(near, it)
                merged += 1
        result.extend(kept)

    veg_n = jain_n = 0
    for it in result:
        veg, jain = tag_veg(it)
        before = it.get("diet", 0)
        if veg:
            it["diet"] = before | 1
        if jain:
            it["diet"] = it["diet"] | 2
        veg_n += bool(veg and not before & 1)
        jain_n += bool(jain and not before & 2)
    print(f"cleanup: {renamed} names tidied, {dropped} non-places dropped, {merged} duplicates merged, "
          f"{veg_n} more marked pure veg, {jain_n} more marked Jain food")
    return result
