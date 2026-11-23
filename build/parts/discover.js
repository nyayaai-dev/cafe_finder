
  // ================================================================== discover
  // Dish finder, Food Match, budget planner, hidden gems, trending, friends' picks,
  // crowd estimate, facilities and AR view. Runs inside the main page script after
  // features.js, so it uses places, state, render, map, sheet and the other helpers.

  const nameCount = new Map();
  places.forEach((p) => { const k = norm(p.name); nameCount.set(k, (nameCount.get(k) || 0) + 1); });
  const isChain = (p) => (nameCount.get(norm(p.name)) || 0) >= 3;

  // ------------------------------------------------------------ dishes (Dish finder, Food Match, trending)
  // A place "serves" a dish when its name says so (strong) or its cuisine tags make it likely.
  const DISHES = {
    biryani: { label: "Biryani", icon: "🍛", c: ["Biryani", "Mughlai", "Hyderabadi", "Awadhi", "Lucknowi", "Kebab", "Kebabs", "North Indian"], n: /biryani|biriyani|darbar|mughal|nawab|hyderabad|lucknow|awadh|persian|lucky|zaffran|jaffer|dum pukht/i },
    pizza: { label: "Pizza", icon: "🍕", c: ["Pizza", "Italian Pizza"], n: /pizz/i },
    burger: { label: "Burgers", icon: "🍔", c: ["Burger", "Burgers", "American"], n: /burger|mcdonald|burger king|wendy/i },
    dosa: { label: "Dosa", icon: "🥞", c: ["South Indian", "Udupi", "Dosa"], n: /dosa|udupi|udipi|benne|madras|mysore|ram ?ashray|mani'?s|sharda bhavan/i },
    benne: { label: "Benne dosa", icon: "🧈", c: [], n: /benne|bangalore|bengaluru|rameshwaram/i },
    idli: { label: "Idli", icon: "🍚", c: ["South Indian", "Udupi"], n: /idli|udupi|udipi|madras|mysore|ram ?ashray|ayyappan/i },
    filtercoffee: { label: "Filter coffee", icon: "☕", c: ["South Indian", "Udupi"], n: /madras|mysore|udupi|benne|filter|rameshwaram|ram ?ashray|mani'?s/i },
    vadapav: { label: "Vada pav", icon: "🍔", c: ["Street Food", "Vada Pav"], n: /vada ?pav|wada ?pav|jumbo king|goli/i },
    pavbhaji: { label: "Pav bhaji", icon: "🍲", c: ["Pav Bhaji"], n: /pav ?bhaji|bhaji/i },
    misal: { label: "Misal pav", icon: "🌶️", c: ["Maharashtrian"], n: /misal|mamledar|aaswad|prakash|vinay health/i },
    momos: { label: "Momos", icon: "🥟", c: ["Momo", "Momos", "Tibetan", "Nepalese"], n: /momo/i },
    sushi: { label: "Sushi", icon: "🍣", c: ["Sushi", "Japanese"], n: /sushi|izakaya|japan/i },
    ramen: { label: "Ramen & Korean", icon: "🍜", c: ["Korean", "Ramen", "Japanese"], n: /ramen|korean|seoul|k-?food/i },
    noodles: { label: "Noodles & Chinese", icon: "🥢", c: ["Chinese", "Noodles", "Sichuan", "Asian", "Pan Asian"], n: /chinese|china|wok|noodle/i },
    shawarma: { label: "Shawarma", icon: "🌯", c: ["Shawarma", "Lebanese", "Arabic", "Middle Eastern", "Turkish"], n: /shawarma|doner|lebanese/i },
    kebab: { label: "Kebabs", icon: "🍢", c: ["Kebab", "Kebabs", "Barbecue", "Barbeque", "Grill", "Mughlai"], n: /kebab|kabab|tikka|grill|bbq|barbe/i },
    seafood: { label: "Seafood & fish thali", icon: "🐟", c: ["Seafood", "Fish", "Malvani", "Malwani", "Konkan", "Goan", "Mangalorean"], n: /fish|sea ?food|malvan|coastal|gomantak|gajalee|konkan|machhi|prawn|crab/i },
    thali: { label: "Thali", icon: "🍽️", c: ["Thali", "Gujarati", "Rajasthani"], n: /thali|rajdhani|thaker|bhojanalay/i },
    northindian: { label: "Butter chicken & North Indian", icon: "🍗", c: ["North Indian", "Punjabi", "Mughlai"], n: /punjab|dhaba|darbar|delhi/i },
    pasta: { label: "Pasta", icon: "🍝", c: ["Pasta", "Italian"], n: /pasta|trattoria|italian/i },
    sandwich: { label: "Sandwiches", icon: "🥪", c: ["Sandwich", "Sandwiches"], n: /sandwich|subway|sandwizz/i },
    tacos: { label: "Tacos & Mexican", icon: "🌮", c: ["Mexican", "Tex-Mex"], n: /taco|mexican|burrito/i },
    chaat: { label: "Chaat & pani puri", icon: "🥙", c: ["Chaat", "Street Food", "Bhel Puri"], n: /chaat|bhel|pani ?puri|sev puri|dahi puri/i },
    rolls: { label: "Rolls & frankies", icon: "🌯", c: ["Rolls", "Wraps"], n: /frank|roll|wrap/i },
    friedchicken: { label: "Fried chicken", icon: "🍗", c: ["Chicken", "Fried Chicken"], n: /kfc|chicken|popeyes/i },
    irani: { label: "Bun maska & Irani chai", icon: "🫖", c: ["Persian", "Irani"], n: /irani|kyani|kayani|merwan|yazdani|britannia|cafe excelsior/i },
    coffee: { label: "Coffee", icon: "☕", c: ["Coffee Shop", "Coffee"], n: /coffee|brew|roaster|starbucks|barista|blue tokai|third wave|ccd|costa|subko|tim hortons/i },
    matcha: { label: "Matcha", icon: "🍵", c: [], n: /matcha|blue tokai|third wave|subko|starbucks|japan|tea/i },
    cloudcoffee: { label: "Cloud coffee", icon: "☁️", c: ["Coffee Shop"], n: /coffee|brew|roaster|blue tokai|third wave|subko/i },
    chai: { label: "Chai", icon: "🫖", c: ["Tea"], n: /chai|tea|chaayos|tapri/i },
    icecream: { label: "Ice cream", icon: "🍨", c: ["Ice Cream", "Gelato", "Frozen Yogurt"], n: /ice ?cream|gelato|naturals|baskin|kulfi|havmor|amul/i },
    cake: { label: "Cakes & pastries", icon: "🍰", c: ["Cake", "Bakery", "Dessert", "Desserts"], n: /bake|cake|patisserie|pastry|theobroma|nutcracker/i },
    dubaichoc: { label: "Dubai chocolate", icon: "🍫", c: ["Dessert", "Desserts"], n: /chocolate|choco|dessert|patisserie|bake/i },
    waffle: { label: "Waffles & pancakes", icon: "🧇", c: ["Waffle", "Pancake"], n: /waffle|pancake/i },
    bubbletea: { label: "Bubble tea", icon: "🧋", c: ["Bubble Tea"], n: /boba|bubble/i },
    juice: { label: "Juice & shakes", icon: "🥤", c: ["Juice", "Milkshakes", "Shakes"], n: /juice|shake/i },
    salad: { label: "Salads & healthy", icon: "🥗", c: ["Salad", "Healthy Food", "Healthy"], n: /salad|bowl|healthy|protein/i },
    breakfast: { label: "Breakfast & brunch", icon: "🍳", c: ["Breakfast"], n: /breakfast|brunch|kuckeliku|egg/i },
  };
  const DISH_WORDS = [                                           // extra words people type
    ["biryani", /\bbiriyani|biryani\b/], ["pizza", /\bpizzas?\b/], ["burger", /\bburgers?\b/], ["benne", /\bbenne\b/],
    ["dosa", /\bdosas?\b/], ["idli", /\bidlis?\b/], ["filtercoffee", /\bfilter coffee\b/], ["vadapav", /\bvada ?pav|wada ?pav\b/],
    ["pavbhaji", /\bpav ?bhaji\b/], ["misal", /\bmisal\b/], ["momos", /\bmomos?\b|\bdumplings?\b/], ["sushi", /\bsushi\b/],
    ["ramen", /\bramen\b|\bkorean\b/], ["noodles", /\bnoodles?\b|\bhakka\b|\bmanchurian\b/], ["shawarma", /\bshawarma\b|\bfalafel\b/],
    ["kebab", /\bkebabs?\b|\bkababs?\b|\btikka\b/], ["seafood", /\bsea ?food\b|\bfish\b|\bprawns?\b|\bcrab\b|\bbombil\b|\bsurmai\b/],
    ["thali", /\bthali\b/], ["northindian", /\bbutter chicken\b|\bdal makhani\b|\bnaan\b|\bpaneer\b/], ["pasta", /\bpasta\b/],
    ["sandwich", /\bsandwich(es)?\b/], ["tacos", /\btacos?\b|\bburritos?\b|\bnachos\b/], ["chaat", /\bchaat\b|\bpani ?puri\b|\bbhel\b|\bsev puri\b/],
    ["rolls", /\bfrank(ie|y)s?\b|\brolls?\b|\bwraps?\b/], ["friedchicken", /\bfried chicken\b|\bwings\b/], ["irani", /\bbun maska\b|\birani\b/],
    ["matcha", /\bmatcha\b/], ["cloudcoffee", /\bcloud coffee\b/], ["coffee", /\bcoffee\b|\bcappuccino\b|\blatte\b/], ["chai", /\bchai\b|\btea\b/],
    ["icecream", /\bice ?creams?\b|\bgelato\b|\bkulfi\b|\bfalooda\b/], ["dubaichoc", /\bdubai chocolate\b/], ["cake", /\bcakes?\b|\bpastr(y|ies)\b|\bbrownies?\b/],
    ["waffle", /\bwaffles?\b|\bpancakes?\b/], ["bubbletea", /\bbubble tea\b|\bboba\b/], ["juice", /\bjuices?\b|\bshakes?\b|\bsmoothies?\b/],
    ["salad", /\bsalads?\b|\bhealthy\b|\bbowls?\b/], ["breakfast", /\bbrunch\b|\beggs?\b|\bomelette\b/],
  ];
  function dishMatch(p, key) {
    const d = DISHES[key];
    if (!d) return 0;
    if (d.n.test(p.name)) return 2;                                        // "known for"
    return p.cuisine.some((c) => d.c.includes(c)) ? 1 : 0;                 // "likely serves"
  }
  function findDish(text) {
    const q = " " + norm(text) + " ";
    for (const [key, re] of DISH_WORDS) if (re.test(q)) return { key, re };
    return null;
  }

  // ------------------------------------------------------------ cost per person (Budget planner)
  const KIND_COST = { "Fast food": 200, "Tea shop": 80, "Cafe": 350, "Bakery cafe": 250, "Dessert & ice cream": 200, "Food court": 250, "Cafe & restaurant": 450, "Restaurant": 450 };
  const PREMIUM_C = /italian|european|french|japanese|sushi|mediterranean|steak|continental|lebanese|fine dining|korean|pan asian/i;
  function costPP(p) {
    if (p.priceTwo) return { v: Math.round(p.priceTwo / 2), est: false };
    let v = KIND_COST[p.kind] || (p.cat === "cafe" ? 350 : 450);
    if (p.cat === "rest" && p.cuisine.some((c) => PREMIUM_C.test(c))) v = 900;
    if (/bar|brew|lounge|pub/i.test(p.name)) v = Math.max(v, 900);
    return { v, est: true };
  }

  // ------------------------------------------------------------ crowd estimate (not live)
  // Typical share of peak busyness by hour (0-23, Mumbai time) for each kind of place.
  const H = (o) => Array.from({ length: 24 }, (_, h) => o[h] || 0);
  const CURVES = {
    cafe: H({ 7: .15, 8: .3, 9: .4, 10: .45, 11: .5, 12: .55, 13: .6, 14: .5, 15: .55, 16: .65, 17: .75, 18: .8, 19: .75, 20: .65, 21: .5, 22: .35, 23: .2 }),
    rest: H({ 0: .25, 1: .1, 8: .1, 9: .1, 10: .1, 11: .2, 12: .45, 13: .75, 14: .65, 15: .3, 16: .2, 17: .25, 18: .35, 19: .55, 20: .8, 21: .95, 22: .8, 23: .5 }),
    fast: H({ 0: .2, 8: .1, 9: .15, 10: .2, 11: .35, 12: .6, 13: .75, 14: .6, 15: .4, 16: .4, 17: .5, 18: .6, 19: .7, 20: .85, 21: .8, 22: .6, 23: .4 }),
    sweet: H({ 10: .15, 11: .2, 12: .3, 13: .35, 14: .35, 15: .4, 16: .5, 17: .6, 18: .7, 19: .8, 20: .9, 21: .9, 22: .75, 23: .5 }),
    breakfast: H({ 6: .3, 7: .65, 8: .9, 9: .95, 10: .8, 11: .55, 12: .5, 13: .55, 14: .4, 15: .3, 16: .35, 17: .4, 18: .45, 19: .45, 20: .4, 21: .3 }),
  };
  function curveFor(p) {
    if (p.cuisine.includes("Breakfast")) return CURVES.breakfast;
    if (/Dessert|Ice cream|Bakery/.test(p.kind)) return CURVES.sweet;
    if (/Fast food|Food court|Tea/.test(p.kind)) return CURVES.fast;
    return p.cat === "cafe" ? CURVES.cafe : CURVES.rest;
  }
  function popularity(p) {
    let k = 0.72;
    if (p.rating >= 4.5) k += 0.2; else if (p.rating >= 4.2) k += 0.12; else if (p.rating) k += 0.05;
    if (isChain(p)) k += 0.08;
    if (p.web) k += 0.04;
    if (nearStation(p)) k += 0.05;
    return Math.min(1.05, k);
  }
  // Busyness 0..1 at a given day (0 Sun) and hour, or null when closed per listed hours.
  function busyAt(p, day, hour) {
    const w = week(p);
    if (w) {
      const m = hour * 60 + 30, prev = (day + 6) % 7;
      const open = w[day].some(([a, b]) => m >= a && m < b) || w[prev].some(([, b]) => b > 1440 && m < b - 1440);
      if (!open) return null;
    }
    const c = curveFor(p);
    let v = c[hour];
    const weekend = day === 0 || day === 6;
    if (weekend) v *= p.cat === "cafe" && hour >= 10 && hour <= 14 ? 1.35 : 1.2;
    if (day === 5 && hour >= 19) v *= 1.1;
    return Math.min(1, v * popularity(p));
  }
  const LEVELS = [[0.3, "Quiet", "q0"], [0.55, "Not too busy", "q1"], [0.78, "Busy", "q2"], [9, "Very busy", "q3"]];
  const level = (v) => LEVELS.find(([t]) => v < t);
  function crowdNow(p) {
    const { day, min } = nowIST();
    return busyAt(p, day, Math.floor(min / 60));
  }
  function bestTime(p) {
    const { day } = nowIST();
    let best = null;
    for (let h = 8; h <= 22; h++) {
      const v = busyAt(p, day, h);
      if (v === null || curveFor(p)[h] === 0) continue;
      if (!best || v < best.v - 0.02) best = { h, v };
    }
    return best;
  }
  const hh = (h) => `${((h + 11) % 12) + 1}${h < 12 ? " am" : " pm"}`;
  function waitText(p, v) {
    if (p.cat !== "rest" && p.cat !== "cafe") return "";
    if (v >= 0.8 && p.rating >= 4.3) return "Expect a 15–30 min wait at the door";
    if (v >= 0.65 && p.rating >= 4.0) return "Possible short wait (5–15 min)";
    return "";
  }
  function crowdLine(p) {
    const v = crowdNow(p);
    if (v === null) return "";
    const [, word, cls] = level(v);
    return `<div class="line"><span class="lbl">Now</span><span class="crowd ${cls}">● ${word}</span><span class="muted">typical for this hour</span></div>`;
  }
  function crowdDetail(p) {
    const { day, min } = nowIST();
    const nowH = Math.floor(min / 60);
    const bars = [];
    for (let h = 7; h <= 23; h++) {
      const v = busyAt(p, day, h);
      bars.push(`<span class="cb${h === nowH ? " now" : ""}${v === null ? " shut" : ""}" style="height:${v === null ? 4 : Math.max(6, Math.round(v * 44))}px" title="${hh(h)}: ${v === null ? "closed" : level(v)[1]}"></span>`);
    }
    const v = busyAt(p, day, nowH), b = bestTime(p), wt = v !== null ? waitText(p, v) : "";
    return `<div class="line top"><span class="lbl">How busy</span><span class="crowdbox">
      <span class="cbars" aria-hidden="true">${bars.join("")}</span>
      <span class="cticks muted"><span>7 am</span><span>12</span><span>6 pm</span><span>11</span></span>
      <span>${v === null ? `<span class="muted">Closed now</span>` : `<b class="crowd ${level(v)[2]}">● ${level(v)[1]} now</b>`}${b ? ` · <span class="muted">quietest today around</span> <b>${hh(b.h)}</b>` : ""}</span>
      ${wt ? `<span class="muted">${wt}</span>` : ""}
      <span class="muted small">Estimated from typical Mumbai patterns for this kind of place, its popularity and listed hours. Not live.</span>
    </span></div>`;
  }


  // ------------------------------------------------------------ photos
  // Free-licensed photos from Wikimedia Commons (credited), plus links to each place's
  // own photo galleries on Google Maps and Zomato, where inside photos live.
  const PH = typeof PHOTOS !== "undefined" ? PHOTOS : {};
  function photoLinks(p) {
    const zomato = "https://www.google.com/search?btnI=1&q=" + encodeURIComponent(`${p.name} ${where(p)} photos site:zomato.com`);
    return `<div class="actions phlinks"><a class="btn" href="${esc(gmaps(p))}" target="_blank" rel="noopener">📷 Inside photos on Google Maps</a>
      <a class="btn" href="${esc(zomato)}" target="_blank" rel="noopener">📷 Photos on Zomato</a></div>`;
  }
  function photosBlock(p) {
    const list = PH[p.key] || [];
    if (!list.length) return photoLinks(p);
    return `<div class="photos"><div class="phstrip">${list.map(([u, page, a, lic, inside, t]) => `<figure>
        <a href="${esc(page)}" target="_blank" rel="noopener"><img src="${esc(u)}" alt="${esc(t)}" loading="lazy" referrerpolicy="no-referrer"></a>
        ${inside ? `<span class="phin">Inside</span>` : ""}
        <figcaption><span class="pname">${esc(a)}</span> · ${esc(lic)} · <a href="${esc(page)}" target="_blank" rel="noopener">Wikimedia Commons</a></figcaption></figure>`).join("")}</div>
      ${photoLinks(p)}</div>`;
  }

  // ------------------------------------------------------------ facilities (dashboard)
  const FAC = [[1, "📶", "Wi-Fi"], [2, "🌳", "Outdoor seating"], [4, "🪑", "Indoor seating"], [8, "❄️", "AC"], [16, "♿", "Wheelchair access"],
    [32, "🥡", "Takeaway"], [64, "🛵", "Delivery"], [128, "🅿️", "Public parking nearby"], [256, "🔌", "EV charging nearby"]];
  const facIcons = (p) => (PH[p.key] ? `<span class="fi" title="Photos" aria-label="Photos">📷</span>` : "") + FAC.filter(([b]) => p.fac & b).map(([, i, t]) => `<span class="fi" title="${t}" aria-label="${t}">${i}</span>`).join("");
  function facDetail(p) {
    const have = FAC.filter(([b]) => p.fac & b);
    const v = crowdNow(p);
    const occ = v === null ? "" : `<span class="fchip">👥 ${level(v)[1]} (est.)</span>`;
    return `<div class="line top"><span class="lbl">Facilities</span><span class="fchips">${have.map(([, i, t]) => `<span class="fchip">${i} ${t}${t === "Indoor seating" && p.seats ? ` · ${p.seats} seats` : ""}</span>`).join("")}${occ}
      ${have.length ? "" : `<span class="muted">Not recorded yet. Know them? Use “Report a problem”.</span>`}</span></div>`;
  }

  // ------------------------------------------------------------ hidden gems
  const FAMOUS = /leopold|bademiya|britannia|kyani|mondegar|pop tate|social|starbucks|theobroma|cafe madras|ram ashray|bastian|trishna|gajalee|mahesh lunch|jimmy boy|yazdani|olive|masque|bombay canteen/i;
  function isGem(p) {
    if (!(p.rating >= 4.3) || p.weak || isChain(p) || FAMOUS.test(p.name)) return false;
    const c = costPP(p);
    if (!c.est && c.v > 900) return false;                      // not the fancy, much-talked-about places
    const v = crowdNow(p);
    return v === null || v < 0.78;                               // and not packed right now
  }

  // ------------------------------------------------------------ friends' picks (shared lists you kept)
  const friends = store.get("cf-friends", {});                     // { "Riya": [keys] }
  const friendOf = (p) => Object.keys(friends).filter((n) => (friends[n] || []).includes(p.key));
  const friendTag = (p) => { const f = friendOf(p); return f.length ? `<span class="friend" title="Recommended by ${esc(f.join(", "))}">👥 ${esc(f.slice(0, 2).join(", "))}${f.length > 2 ? " +" + (f.length - 2) : ""}</span>` : ""; };


  // ------------------------------------------------------------ chains (all outlets of a brand)
  const CHAINS = [
    ["McDonald's", "🍔", /^mcdonald/i], ["Burger King", "🍔", /^burger king/i], ["KFC", "🍗", /^kfc\b/i], ["Domino's", "🍕", /^domino/i],
    ["Pizza Hut", "🍕", /^pizza hut/i], ["Subway", "🥪", /^subway\b/i], ["Taco Bell", "🌮", /^taco bell/i], ["Starbucks", "☕", /^starbucks/i],
    ["Cafe Coffee Day", "☕", /^caf[eé] coffee day|^ccd\b/i], ["Third Wave Coffee", "☕", /^third wave/i], ["Barista", "☕", /^barista\b/i],
    ["Chaayos", "🫖", /^chaayos/i], ["Baskin-Robbins", "🍨", /^baskin/i], ["Kailash Parbat", "🍛", /^kailash parbat/i],
    ["Bhagat Tarachand", "🍛", /^bhagat tarachand/i], ["Jumbo King", "🍔", /^jumbo king/i], ["Wow! Momo", "🥟", /^wow!? ?momo/i],
    ["Haldiram's", "🍛", /^haldiram/i], ["Theobroma", "🍰", /^theobroma/i],
    ["Monginis", "🎂", /^monginis/i], ["Merwans", "🧁", /merwan/i], ["Birdy's", "🍰", /^birdy/i], ["Ribbons & Balloons", "🎂", /^ribbons/i],
    ["Candies", "🥪", /^candies\b/i], ["Grandmama's Cafe", "☕", /^grandmama/i], ["Blue Tokai", "☕", /^blue tokai/i], ["Tea Villa", "🫖", /^tea villa/i],
    ["Natural Ice Cream", "🍨", /^natural'?s?\b/i], ["The Belgian Waffle Co.", "🧇", /^(the )?belgian waffle/i], ["Bachelorr's", "🥤", /^bachelorr?'?s/i],
    ["Havmor", "🍨", /^havmor/i], ["Giani's", "🍨", /^giani/i], ["Love & Cheesecake", "🍰", /love (&|and) cheesecake/i], ["Keventers", "🥤", /^keventers/i],
    ["Mad Over Donuts", "🍩", /^mad over donuts/i], ["Shiv Sagar", "🍛", /^shiv ?sagar/i], ["Sukh Sagar", "🍛", /^sukh ?sagar/i],
    ["Cream Centre", "🍛", /^cream cent(re|er)/i], ["Prashant Corner", "🍬", /^prashant corner/i], ["Mamledar Misal", "🌶️", /mamledar/i],
    ["Goli Vada Pav", "🍔", /^goli\b/i], ["Tibb's Frankie", "🌯", /^tibb/i], ["Bikanervala", "🍛", /^bikanervala/i], ["Banana Leaf", "🍌", /^banana leaf/i],
    ["Jaffer Bhai's Delhi Darbar", "🍛", /jaffer ?bhai/i], ["Behrouz Biryani", "🍛", /^behrouz/i], ["Faasos", "🌯", /^faasos/i], ["Box8", "🍱", /^box ?8/i],
    ["Charcoal Eats", "🍛", /^charcoal eats/i], ["Copper Chimney", "🍛", /^copper chimney/i], ["Persian Darbar", "🍛", /^persian darbar/i],
    ["Mahesh Lunch Home", "🦀", /^mahesh lunch/i], ["Gajalee", "🐟", /^gajalee/i], ["Popeyes", "🍗", /^popeyes/i], ["Wow! China", "🥡", /^wow!? ?china/i],
    ["Mainland China", "🥡", /^mainland china/i], ["Social", "🍻", /\bsocial$/i], ["Pop Tate's", "🍕", /^pop ?tate/i], ["Barbeque Nation", "🍢", /^barbeque nation/i],
    ["Sigree Global Grill", "🍢", /^sigree/i], ["Chili's", "🌶️", /^chili'?s/i], ["Sbarro", "🍕", /^sbarro/i],
  ];
  state.chain = "";
  const chainRe = (name) => (CHAINS.find(([n]) => n === name) || [])[2];
  function drawChains() {
    $("chainGrid").innerHTML = CHAINS.map(([n, icon, re]) => [n, icon, places.filter((p) => re.test(p.name)).length])
      .filter(([, , c]) => c).sort((a, b) => b[2] - a[2])
      .map(([n, icon, c]) => `<button type="button" class="dish" data-chain="${esc(n)}"><span class="di">${icon}</span><span class="pname">${esc(n)}</span><small class="muted">${c}</small></button>`).join("");
  }
  $("chainGrid").addEventListener("click", (e) => {
    const b = e.target.closest("[data-chain]"); if (!b) return;
    $("chainsDlg").close();
    setArea(null, "", document.querySelector('#quick [data-area=""]'));
    applyDiscover({ chain: b.dataset.chain });
    const pts = visible().map((p) => [p.lat, p.lng]);
    if (pts.length) map.fitBounds(L.latLngBounds(pts).pad(0.05), fitPad(16, { maxZoom: 15 }));
    toast(`${b.dataset.chain}: ${pts.length} outlets`);
  });

  // ------------------------------------------------------------ filter state + visible() hook
  state.dish = ""; state.budget = 0; state.gems = false; state.friendsOnly = false;
  function discoverOk(p) {
    if (state.chain && !chainRe(state.chain).test(p.name)) return false;
    if (state.dish && !dishMatch(p, state.dish)) return false;
    if (state.budget && costPP(p).v > state.budget) return false;
    if (state.gems && !isGem(p)) return false;
    if (state.friendsOnly && !friendOf(p).length) return false;
    if ($("fWifi").checked && !(p.fac & 1)) return false;
    if ($("fOutdoor").checked && !(p.fac & 2)) return false;
    if ($("fPark").checked && !(p.fac & 128)) return false;
    return true;
  }
  function syncDiscoverBanner() {
    const bits = [];
    if (state.mood && !CHIP_MOODS.includes(state.mood)) bits.push(MOODS[state.mood].label);
    if (state.chain) bits.push(`🏷️ ${state.chain}`);
    if (state.dish) bits.push(`${DISHES[state.dish].icon} ${DISHES[state.dish].label}`);
    if (state.budget) bits.push(`💰 up to ₹${state.budget.toLocaleString("en-IN")} a person`);
    if (state.gems) bits.push("💎 Hidden gems");
    if (state.friendsOnly) bits.push("👥 Friends' picks");
    $("discoverBanner").hidden = !bits.length;
    $("discoverText").textContent = bits.join(" · ");
    document.querySelectorAll("[data-tool=gems]").forEach((b) => b.classList.toggle("on", state.gems));
    $("frOnly").hidden = !Object.keys(friends).length;
    $("frOnly").textContent = state.friendsOnly ? "Show everyone's places" : "👥 Show only friends' picks";
  }
  $("discoverClear").addEventListener("click", () => {
    state.dish = ""; state.budget = 0; state.gems = false; state.friendsOnly = false; state.chain = "";
    if (state.mood && !CHIP_MOODS.includes(state.mood)) state.mood = "";
    syncDiscoverBanner(); state.shown = PAGE; render();
  });
  function applyDiscover(patch) {
    Object.assign(state, patch);
    syncDiscoverBanner(); state.shown = PAGE; render();
    if (sheet.mq.matches && sheet.state === "peek") sheet.set("half");
  }
  ["fWifi", "fOutdoor", "fPark"].forEach((id) => $(id).addEventListener("change", () => { state.shown = PAGE; render(); }));

  // URL: ?dish=biryani&budget=300&gems=1&friends=1 (filters in the link, website only)
  function discoverParams(ps) {
    if (state.chain) ps.set("chain", state.chain);
    if (state.dish) ps.set("dish", state.dish);
    if (state.budget) ps.set("budget", state.budget);
    if (state.gems) ps.set("gems", "1");
    if (state.friendsOnly) ps.set("friends", "1");
  }
  function applyDiscoverParams(ps) {
    if (chainRe(ps.get("chain"))) state.chain = ps.get("chain");
    if (DISHES[ps.get("dish")]) state.dish = ps.get("dish");
    const b = parseInt(ps.get("budget"), 10); if (b > 0) state.budget = b;
    if (ps.get("gems") === "1") state.gems = true;
    if (ps.get("friends") === "1" && Object.keys(friends).length) state.friendsOnly = true;
    syncDiscoverBanner();
  }

  // ------------------------------------------------------------ Dish finder
  $("dishGrid").innerHTML = Object.entries(DISHES).map(([k, d]) =>
    `<button type="button" class="dish" data-dish="${k}"><span class="di">${d.icon}</span>${esc(d.label)}</button>`).join("");
  $("dishGrid").addEventListener("click", (e) => {
    const b = e.target.closest("[data-dish]"); if (!b) return;
    $("dishDlg").close(); pickDish(b.dataset.dish);
  });
  function pickDish(key) {
    const n = places.filter((p) => dishMatch(p, key)).length;
    applyDiscover({ dish: key });
    toast(`${DISHES[key].icon} ${n} places for ${DISHES[key].label.toLowerCase()} across the city`);
  }

  // ------------------------------------------------------------ Budget planner
  function budgetResults() {
    const total = Math.max(0, parseInt($("bgTotal").value, 10) || 0), people = Math.max(1, parseInt($("bgPeople").value, 10) || 1);
    const pp = Math.floor(total / people), meal = $("bgMeal").value;
    const mealOk = (p) => meal === "breakfast" ? MOODS.breakfast.test(p)
      : meal === "coffee" ? p.cat === "cafe"
      : meal === "snack" ? /Fast food|Tea|Dessert|Bakery|Food court/.test(p.kind) || p.cat === "cafe"
      : meal === "dinner" ? p.cat === "rest" && (busyAt(p, nowIST().day, 20) !== null)
      : meal === "lunch" ? p.cat === "rest" && (busyAt(p, nowIST().day, 13) !== null) : true;
    const ctr = state.me || map.getCenter();
    const pool = visible().filter((p) => costPP(p).v <= pp && mealOk(p));
    pool.forEach((p) => { p._bd = km(p, ctr); });
    pool.sort((a, b) => rk(b) - rk(a) || (costPP(a).est - costPP(b).est) || a._bd - b._bd);
    return { pp, people, total, pool };
  }
  function drawBudget() {
    const { pp, people, total, pool } = budgetResults();
    $("bgSummary").innerHTML = total ? `₹${total.toLocaleString("en-IN")} for ${people} = <b>₹${pp.toLocaleString("en-IN")} a person</b> · ${pool.length.toLocaleString("en-IN")} places fit${state.areaName ? " in " + esc(state.areaName) : ""}` : "Enter a budget";
    $("bgList").innerHTML = pool.slice(0, 8).map((p) => {
      const c = costPP(p);
      return `<li><button type="button" data-open="${p.key}"><span class="nm">${esc(p.name)}</span>
        <span class="muted">${esc(p.kind)} · ${esc(p.loc === p.sub ? p.sub : p.loc)}${p.rating ? ` · ★ ${p.rating.toFixed(1)}` : ""}</span>
        <span class="bgc">₹${c.v.toLocaleString("en-IN")}/person${c.est ? " (est.)" : ""} · ₹${(c.v * people).toLocaleString("en-IN")} total</span></button></li>`;
    }).join("") || `<li class="muted">Nothing fits yet. Raise the budget or widen the area.</li>`;
  }
  ["bgTotal", "bgPeople", "bgMeal"].forEach((id) => $(id).addEventListener("input", drawBudget));
  $("bgApply").addEventListener("click", () => {
    const { pp } = budgetResults(); $("budgetDlg").close();
    if (pp > 0) applyDiscover({ budget: pp });
  });
  $("bgList").addEventListener("click", (e) => { if (e.target.closest("[data-open]")) $("budgetDlg").close(); });

  // ------------------------------------------------------------ Food Match (describe a craving)
  const CRAVINGS = [
    [/\bspicy|hot|teekha|masala|chatpata\b/, { dishes: ["biryani", "misal", "northindian", "seafood", "chaat"], why: "spicy" }],
    [/\bcheesy|cheese\b/, { dishes: ["pizza", "pasta", "sandwich", "burger"], why: "cheesy" }],
    [/\bsweet|dessert|sugar\b/, { dishes: ["cake", "icecream", "waffle", "dubaichoc"], why: "something sweet" }],
    [/\bhealthy|light|diet|protein|salad\b/, { dishes: ["salad", "juice", "idli"], why: "light / healthy" }],
    [/\bcomfort|homely|ghar ka|simple\b/, { dishes: ["dosa", "thali", "northindian", "irani"], why: "comfort food" }],
    [/\bcrispy|crunchy|fried\b/, { dishes: ["dosa", "vadapav", "friedchicken", "chaat"], why: "crispy" }],
    [/\bcold|chilled|cool\b/, { dishes: ["icecream", "juice", "bubbletea", "cloudcoffee"], why: "something cold" }],
    [/\bquick|fast|on the go|grab\b/, { dishes: ["vadapav", "rolls", "sandwich", "burger"], why: "quick bite" }],
    [/\bstreet( food)?\b/, { dishes: ["vadapav", "pavbhaji", "chaat", "rolls"], why: "street food" }],
    [/\bcaffeine|wake me|energy\b/, { dishes: ["coffee", "filtercoffee", "chai"], why: "caffeine" }],
    [/\bsea|coastal|konkan|malvani\b/, { dishes: ["seafood"], why: "coastal" }],
    [/\bmeaty|meat|non ?veg|chicken|mutton\b/, { dishes: ["kebab", "biryani", "friedchicken", "northindian"], why: "meaty" }],
  ];
  function foodMatch(text) {
    text = deva(text);
    const q = " " + norm(text) + " ";
    const why = [], dishes = new Map(), hard = {};
    const d = findDish(text);
    if (d) { dishes.set(d.key, 3); why.push(DISHES[d.key].label); }
    for (const [re, m] of CRAVINGS) if (re.test(q)) { m.dishes.forEach((k) => dishes.set(k, Math.max(dishes.get(k) || 0, 1.5))); why.push(m.why); }
    // "cafe" / "restaurant" pick the kind of place; generic tags aren't treated as a cuisine.
    if (/\bcafe|cafes|coffee shop\b/.test(q)) { hard.cat = "cafe"; why.push("a cafe"); }
    else if (/\brestaurants?|dinner|lunch\b/.test(q)) { hard.cat = "rest"; why.push("a restaurant"); }
    const GENERIC = /^(cafe|coffee shop|coffee|restaurant|vegetarian|vegetarian only|regional|local|fast food|jain)$/i;
    const cu = allCuisines.find((c) => { const n = norm(c); return !GENERIC.test(c) && n.length > 2 && q.includes(" " + n + " ") && !(d && norm(DISHES[d.key].label).includes(n)); });
    if (cu) why.push(cu);
    let area = null;
    for (const a of areaByLen) { const n = norm(a); if (n.length > 2 && q.includes(" " + n + " ")) { area = a; break; } }
    if (area) why.push("in " + area);
    if (/\bpure ?veg|vegetarian|\bveg\b(?! ?non)/.test(q) && !/non ?veg/.test(q)) { hard.veg = true; why.push("veg"); }
    if (/\bjain\b/.test(q)) { hard.jain = true; why.push("Jain"); }
    if (/\bopen( now)?\b|\bright now\b|\bnow\b/.test(q)) { hard.open = true; why.push("open now"); }
    // Money and group size come from the raw text (norm() drops the ₹ sign).
    // "under 500" = per person; "₹1000 for 4" = a total split four ways.
    const raw = " " + text.toLowerCase().replace(/,(?=\d{3})/g, "") + " ";
    const money = raw.match(/(?:under|below|less than|within|up ?to|max|budget(?: of)?)\s*(?:₹|rs\.?|inr)?\s*(\d{2,6})/) || raw.match(/(?:₹|rs\.?\s?|inr\s?)(\d{2,6})/);
    const pm = raw.match(/(\d{1,2})\s*(?:people|persons|pax|friends|of us)\b/) || raw.match(/\bfor (\d{1,2})\b(?!\s*(?:₹|rs|inr|\d))/);
    const people = pm && +pm[1] >= 1 && +pm[1] <= 20 ? +pm[1] : 0;
    if (money && +money[1] >= 50) {
      hard.budget = Math.floor(+money[1] / (people || 1));
      why.push(`up to ₹${hard.budget}/person${people ? ` (₹${money[1]} for ${people})` : ""}`);
    } else if (/\bcheap|budget|affordable|pocket\b/.test(q)) { hard.budget = 300; why.push("budget-friendly"); }
    const moodHit = Object.entries(MOODS).find(([k]) => (MOOD_WORDS[k] || /$^/).test(q));
    if (moodHit) why.push(MOODS[moodHit[0]].label.replace(/^\S+\s/, ""));
    if (/\bnear (a |the )?(station|metro|train)\b/.test(q)) { hard.station = true; why.push("near a station"); }
    if (/\bwifi|wi-fi\b/.test(q)) { hard.wifi = true; why.push("Wi-Fi"); }
    if (/\boutdoor|outside|open air|terrace|rooftop\b/.test(q)) { hard.outdoor = true; why.push("outdoor seating"); }
    if (/\bparking\b/.test(q)) { hard.parking = true; why.push("parking nearby"); }
    if (/\bquiet|less crowded|not crowded|peaceful|calm\b/.test(q)) { hard.quiet = true; why.push("quiet now"); }

    const ctr = state.me || map.getCenter();
    const inArea = area ? (GROUPS[area.toLowerCase()] ? new Set(GROUPS[area.toLowerCase()].parts) : new Set([area])) : null;
    const scored = [];
    for (const p of places) {
      if (inArea && !(inArea.has(p.zone) || inArea.has(p.sub) || inArea.has(p.loc))) continue;
      if (hard.cat && p.cat !== hard.cat) continue;
      if (hard.veg && !p.pureVeg) continue;
      if (hard.jain && !p.jain) continue;
      if (hard.open && openNow(p.hours) !== true) continue;
      if (hard.budget && costPP(p).v > hard.budget) continue;
      if (hard.station && !nearStation(p)) continue;
      if (hard.wifi && !(p.fac & 1)) continue;
      if (hard.outdoor && !(p.fac & 2)) continue;
      if (hard.parking && !(p.fac & 128)) continue;
      if (hard.quiet) { const v = crowdNow(p); if (v !== null && v >= 0.55) continue; }
      let s = 0;
      const hits = [];
      dishes.forEach((w, k) => { const m = dishMatch(p, k); if (m) { s += w * m; hits.push(DISHES[k].label); } });
      if (cu && p.cuisine.includes(cu)) { s += 3; hits.push(cu); }
      if (moodHit && moodHit[1].test(p)) { s += 2; }
      if ((dishes.size || cu) && !s) continue;                          // asked for food it doesn't serve
      s += (p.weak ? 4.0 : p.rating || 3.6) * 0.8;
      const dist = km(p, ctr);
      s -= area ? 0 : Math.min(3, dist * 0.35);
      scored.push({ p, s, hits, dist });
    }
    scored.sort((a, b) => b.s - a.s);
    return { why: [...new Set(why)], results: scored.slice(0, 8), all: scored, hard, dish: d && d.key, area, cuisine: cu };
  }
  const MOOD_WORDS = { work: /\bwork|study|laptop|wifi\b/, date: /\bdate|romantic|anniversary\b/, celebrate: /\bcelebrat|birthday|party for\b/,
    business: /\bbusiness|client|meeting|office\b/, family: /\bfamily|kids|parents|children\b/, party: /\bparty|drinks|beer|cocktail|pub\b/,
    late: /\blate|midnight|night\b/, breakfast: /\bbreakfast|morning\b/, dessert: /\bdessert\b/, budget: /\bcheap|budget\b/ };
  let lastMatch = null;
  function runFoodMatch() {
    const text = $("fmText").value.trim();
    if (!text) { $("fmOut").innerHTML = ""; return; }
    const m = lastMatch = foodMatch(text);
    $("fmOut").innerHTML = `<p class="muted">Looking for: <b>${esc(m.why.join(" · ") || "anything good nearby")}</b></p>` + (m.results.length
      ? `<ol class="fm">${m.results.map(({ p, hits, dist }) => `<li><button type="button" data-open="${p.key}">
          <span class="nm">${esc(p.name)}</span>
          <span class="muted">${esc(p.kind)} · ${esc(p.loc === p.sub ? p.sub : p.loc)}${p.rating ? ` · ★ ${p.rating.toFixed(1)}` : ""} · ${fmtKm(dist)}</span>
          ${hits.length ? `<span class="why">Matches ${esc([...new Set(hits)].slice(0, 3).join(", "))}</span>` : ""}</button></li>`).join("")}</ol>
        <button type="button" id="fmAll" class="linkbtn">Show all ${m.all.length.toLocaleString("en-IN")} matches on the map</button>`
      : `<p>No match yet. Try fewer conditions, e.g. “spicy veg in Dadar”.</p>`);
  }
  $("fmGo").addEventListener("click", runFoodMatch);
  $("fmText").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); runFoodMatch(); } });
  $("fmExamples").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { $("fmText").value = b.textContent; runFoodMatch(); } });
  $("fmOut").addEventListener("click", (e) => {
    if (e.target.closest("[data-open]")) return $("foodDlg").close();
    if (e.target.id !== "fmAll" || !lastMatch) return;
    const m = lastMatch; $("foodDlg").close();
    if (m.area) showArea(m.area); else if (!state.me) setArea(null, "", document.querySelector('#quick [data-area=""]'));
    $("fVeg").checked = !!m.hard.veg; $("fJain").checked = !!m.hard.jain; $("fOpen").checked = !!m.hard.open; $("fNear").checked = !!m.hard.station;
    $("fWifi").checked = !!m.hard.wifi; $("fOutdoor").checked = !!m.hard.outdoor; $("fPark").checked = !!m.hard.parking;
    if (m.cuisine) { refreshCounts(); if ([...$("cuisine").options].some((o) => o.value === m.cuisine)) $("cuisine").value = m.cuisine; }
    applyDiscover({ dish: m.dish || "", budget: m.hard.budget || 0 });
  });

  // ------------------------------------------------------------ Trending
  // Dishes from 2025–26 coverage (sources in the panel); places from current guides.
  const TRENDING = [
    ["benne", "Benne dosa and ghee podi idli", "Free Press Journal, 2026", "https://www.freepressjournal.in/lifestyle/the-rameshwaram-cafe-to-benne-popular-south-indian-restaurants-mumbai-is-loving-right-now"],
    ["filtercoffee", "Filter coffee (and the viral filter coffee softy)", "Curly Tales, 2026", "https://curlytales.com/discover/this-viral-filter-coffee-softy-has-become-mumbais-new-favourite-treat/"],
    ["matcha", "Matcha", "Hindustan Times, 2026", "https://www.magzter.com/ar/stories/newspaper/Hindustan-Times-Mumbai/INSTA-MADE-ME-EAT-THIS"],
    ["dubaichoc", "Dubai chocolate desserts", "Hindustan Times, 2026", "https://www.magzter.com/ar/stories/newspaper/Hindustan-Times-Mumbai/INSTA-MADE-ME-EAT-THIS"],
    ["cloudcoffee", "Cloud coffee", "Hindustan Times, 2026", "https://www.magzter.com/ar/stories/newspaper/Hindustan-Times-Mumbai/INSTA-MADE-ME-EAT-THIS"],
    ["biryani", "Biryani, India's most-ordered dish", "Swiggy, 2025", "https://www.swiggy.com/corporate/press-release/how-india-swiggyd-2025-a-feast-for-the-fast-the-foodie-and-the-future/"],
    ["burger", "Burgers (no. 2 nationally)", "Swiggy, 2025", "https://www.swiggy.com/corporate/press-release/how-india-swiggyd-2025-a-feast-for-the-fast-the-foodie-and-the-future/"],
    ["dosa", "Dosa and idli for breakfast", "Swiggy, 2025", "https://www.swiggy.com/corporate/press-release/how-india-swiggyd-2025-a-feast-for-the-fast-the-foodie-and-the-future/"],
  ];
  function drawTrending() {
    const ctr = state.me || map.getCenter();
    const where = state.me ? "near you" : "near the map centre";
    const guide = places.filter((p) => p.rating && p.src).map((p) => [km(p, ctr), p]).filter(([d]) => d <= 6)
      .sort((a, b) => rk(b[1]) - rk(a[1]) || a[0] - b[0]).slice(0, 8);
    const item = ([d, p]) => `<li><button type="button" data-open="${p.key}"><span class="nm">${esc(p.name)}</span>
      <span class="muted">★ ${p.rating.toFixed(1)} (${esc(p.ratingSrc)}) · ${esc(p.loc === p.sub ? p.sub : p.loc)} · ${fmtKm(d)}</span></button></li>`;
    $("trendBody").innerHTML = `
      <h3 class="d-sub">Trending dishes</h3>
      <div class="dishrow">${TRENDING.map(([k, label, src, url]) => `<span class="tdish"><button type="button" class="dish" data-dish="${k}"><span class="di">${DISHES[k].icon}</span>${esc(label)}</button><a class="muted small" href="${url}" target="_blank" rel="noopener">${esc(src)}</a></span>`).join("")}</div>
      <h3 class="d-sub">Hot right now ${where}</h3>
      <p class="muted small">Places featured in current food guides and listings (checked November 2026), best rated first.</p>
      <ul class="near">${guide.map(item).join("") || `<li class="muted">None within 6 km. Move the map to a busier area.</li>`}</ul>
      <p><button type="button" class="linkbtn" id="trGems">💎 See hidden gems</button></p>`;
  }
  $("trendBody").addEventListener("click", (e) => {
    const b = e.target.closest("[data-dish]");
    if (b) { $("trendDlg").close(); return pickDish(b.dataset.dish); }
    if (e.target.closest("[data-open]")) $("trendDlg").close();
    if (e.target.id === "trGems") { $("trendDlg").close(); applyDiscover({ gems: true }); }
  });

  // ------------------------------------------------------------ Friends' picks
  function drawFriends() {
    const names = Object.keys(friends);
    $("frName").value = store.get("cf-myname", "");
    $("frList").innerHTML = names.length ? names.map((n) => `<li><span><b>${esc(n)}</b> <span class="muted">· ${friends[n].length} places</span></span>
      <button type="button" class="linkbtn" data-frshow="${esc(n)}">Show</button><button type="button" class="linkbtn" data-frdel="${esc(n)}">Remove</button></li>`).join("")
      : `<li class="muted">No friends' lists yet. When a friend sends you their list, tap “Keep as their picks”.</li>`;
  }
  $("frList").addEventListener("click", (e) => {
    const s = e.target.closest("[data-frshow]"), d = e.target.closest("[data-frdel]");
    if (s) { $("friendsDlg").close(); showSharedList(friends[s.dataset.frshow], s.dataset.frshow); return; }
    if (d) { delete friends[d.dataset.frdel]; store.set("cf-friends", friends); drawFriends(); syncDiscoverBanner(); render(false); }
  });
  $("frOnly").addEventListener("click", () => { $("friendsDlg").close(); applyDiscover({ friendsOnly: !state.friendsOnly }); });
  $("frSave").addEventListener("click", () => { store.set("cf-myname", $("frName").value.trim().slice(0, 30)); toast("Name saved: your shared lists will show it"); });
  $("frShare").addEventListener("click", () => { store.set("cf-myname", $("frName").value.trim().slice(0, 30)); $("friendsDlg").close(); $("shareListBtn").click(); });
  $("listKeep").addEventListener("click", () => { if (state.list) keepFriendList(state.listFrom, [...state.list]); });
  function keepFriendList(name, keys) {
    const n = (name || "A friend").slice(0, 30);
    friends[n] = [...new Set([...(friends[n] || []), ...keys])];
    store.set("cf-friends", friends); syncDiscoverBanner(); render(false);
    toast(`Kept as ${n}'s picks. Turn on 👥 Friends' picks to see them`);
  }


  // ------------------------------------------------------------ Filters panel
  const PANEL_CHECKS = ["fJain", "fNon", "fRated", "fNear", "fWifi", "fOutdoor", "fPark", "fFav"];
  function syncFilterBadge() {
    const n = PANEL_CHECKS.filter((id) => $(id).checked).length + ($("cuisine").value ? 1 : 0) + ($("filterText").value.trim() ? 1 : 0);
    $("nFilters").hidden = !n; $("nFilters").textContent = n;
    $("filtersBtn").classList.toggle("on", n > 0);
  }
  $("filtersBtn").addEventListener("click", () => {
    const open = $("morePanel").hidden;
    $("morePanel").hidden = !open; $("filtersBtn").setAttribute("aria-expanded", open);
  });
  $("filtersReset").addEventListener("click", () => {
    PANEL_CHECKS.forEach((id) => { $(id).checked = false; });
    $("filterText").value = ""; $("cuisine").value = "";
    state.shown = PAGE; render();
  });

  // ------------------------------------------------------------ tools row
  $("tools").addEventListener("click", (e) => {
    const b = e.target.closest("[data-tool]"); if (!b) return;
    const t = b.dataset.tool;
    if (t === "dish") $("dishDlg").showModal();
    else if (t === "chains") { drawChains(); $("chainsDlg").showModal(); }
    else if (t === "match") { $("foodDlg").showModal(); $("fmText").focus(); }
    else if (t === "budget") { drawBudget(); $("budgetDlg").showModal(); }
    else if (t === "trend") { drawTrending(); $("trendDlg").showModal(); }
    else if (t === "gems") applyDiscover({ gems: !state.gems });
    else if (t === "friendlist") { drawFriends(); $("friendsDlg").showModal(); }
  });
  document.querySelectorAll("dialog [data-close]").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));
  syncDiscoverBanner();
