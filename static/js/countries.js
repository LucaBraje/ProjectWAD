 cletountryCodeByName = new Map();

function normalizeCountryName(name) {
    return name
        .trim()
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[.'’]/g, "")
        .replace(/\s+/g, " ");
}

async function loadCountryCodes() {
    try {
        const response = await fetch(
            "https://cdn.jsdelivr.net/npm/country-list@2.3.0/countries.json"
        );

        if (!response.ok) {
            throw new Error("Could not load country codes.");
        }

        const countries = await response.json();

        countries.forEach(country => {
            countryCodeByName.set(
                normalizeCountryName(country.name),
                country.code.toLowerCase()
            );
        });

        // Alternative names that may appear in your CSV.
    const aliases = {
           // Subnational Flags (UK Nations)
    "england": "gb-eng",
        };

        Object.entries(aliases).forEach(([name, code]) => {
            countryCodeByName.set(normalizeCountryName(name), code);
        });

        console.log(`Loaded ${countries.length} country entries.`);
    } catch (error) {
        console.error("Country code loading error:", error);
    }
}

function getFlagUrl(countryName) {
    if (!countryName) return null;

    const name = normalizeCountryName(countryName);

      const aliases = {
           // Subnational Flags (UK Nations)
    "england": "gb-eng",
    "scotland": "gb-sct",
    "wales": "gb-wls",
    "northern ireland": "gb-nir",

    // North America & Caribbean
    "united states of america": "us",
    "united states": "us",
    "usa": "us",
    "canada": "ca",
    "mexico": "mx",
    "antigua and barbuda": "ag",
    "bahamas": "bs",
    "barbados": "bb",
    "cuba": "cu",
    "dominica": "dm",
    "dominican republic": "do",
    "grenada": "gd",
    "haiti": "ht",
    "jamaica": "jm",
    "saint kitts and nevis": "kn",
    "saint lucia": "lc",
    "saint vincent and the grenadines": "vc",
    "trinidad and tobago": "tt",

    // Europe
    "albania": "al",
    "andorra": "ad",
    "austria": "at",
    "belarus": "by",
    "belgium": "be",
    "bosnia and herzegovina": "ba",
    "bosnia": "ba",
    "bulgaria": "bg",
    "croatia": "hr",
    "cyprus": "cy",
    "czech republic": "cz",
    "czechia": "cz",
    "denmark": "dk",
    "estonia": "ee",
    "finland": "fi",
    "france": "fr",
    "germany": "de",
    "greece": "gr",
    "hungary": "hu",
    "iceland": "is",
    "ireland": "ie",
    "italy": "it",
    "kosovo": "xk",
    "latvia": "lv",
    "liechtenstein": "li",
    "lithuania": "lt",
    "luxembourg": "lu",
    "malta": "mt",
    "moldova": "md",
    "monaco": "mc",
    "montenegro": "me",
    "netherlands": "nl",
    "holland": "nl",
    "north macedonia": "mk",
    "macedonia": "mk",
    "norway": "no",
    "poland": "pl",
    "portugal": "pt",
    "romania": "ro",
    "russia": "ru",
    "san marino": "sm",
    "serbia": "rs",
    "slovakia": "sk",
    "slovenia": "si",
    "spain": "es",
    "sweden": "se",
    "switzerland": "ch",
    "ukraine": "ua",
    "united kingdom": "gb",
    "uk": "gb",
    "great britain": "gb",
    "vatican city": "va",

    // Middle East & Asia
    "afghanistan": "af",
    "armenia": "am",
    "azerbaijan": "az",
    "bahrain": "bh",
    "bangladesh": "bd",
    "bhutan": "bt",
    "brunei": "bn",
    "cambodia": "kh",
    "china": "cn",
    "georgia": "ge",
    "india": "in",
    "indonesia": "id",
    "iran": "ir",
    "iraq": "iq",
    "israel": "il",
    "japan": "jp",
    "jordan": "jo",
    "kazakhstan": "kz",
    "kuwait": "kw",
    "kyrgyzstan": "kg",
    "laos": "la",
    "lebanon": "lb",
    "malaysia": "my",
    "maldives": "mv",
    "mongolia": "mn",
    "myanmar": "mm",
    "burma": "mm",
    "nepal": "np",
    "north korea": "kp",
    "south korea": "kr",
    "korea": "kr",
    "oman": "om",
    "pakistan": "pk",
    "palestine": "ps",
    "philippines": "ph",
    "qatar": "qa",
    "saudi arabia": "sa",
    "singapore": "sg",
    "sri lanka": "lk",
    "syria": "sy",
    "taiwan": "tw",
    "tajikistan": "tj",
    "thailand": "th",
    "timor-leste": "tl",
    "east timor": "tl",
    "turkey": "tr",
    "turkiye": "tr",
    "turkmenistan": "tm",
    "united arab emirates": "ae",
    "uae": "ae",
    "uzbekistan": "uz",
    "vietnam": "vn",
    "yemen": "ye",

    // South America
    "argentina": "ar",
    "bolivia": "bo",
    "brazil": "br",
    "chile": "cl",
    "colombia": "co",
    "ecuador": "ec",
    "guyana": "gy",
    "paraguay": "py",
    "peru": "pe",
    "suriname": "sr",
    "uruguay": "uy",
    "venezuela": "ve",

    // Central America
    "belize": "bz",
    "costa rica": "cr",
    "el salvador": "sv",
    "guatemala": "gt",
    "honduras": "hn",
    "nicaragua": "ni",
    "panama": "pa",

    // Africa
    "algeria": "dz",
    "angola": "ao",
    "benin": "bj",
    "botswana": "bw",
    "burkina faso": "bf",
    "burundi": "bi",
    "cabo verde": "cv",
    "cape verde": "cv",
    "cameroon": "cm",
    "central african republic": "cf",
    "chad": "td",
    "comoros": "km",
    "congo": "cg",
    "democratic republic of the congo": "cd",
    "dr congo": "cd",
    "djibouti": "dj",
    "egypt": "eg",
    "equatorial guinea": "gq",
    "eritrea": "er",
    "eswatini": "sz",
    "swaziland": "sz",
    "ethiopia": "et",
    "gabon": "ga",
    "gambia": "gm",
    "ghana": "gh",
    "guinea": "gn",
    "guinea-bissau": "gw",
    "ivory coast": "ci",
    "cote d'ivoire": "ci",
    "kenya": "ke",
    "lesotho": "ls",
    "liberia": "lr",
    "libya": "ly",
    "madagascar": "mg",
    "malawi": "mw",
    "mali": "ml",
    "mauritania": "mr",
    "mauritius": "mu",
    "morocco": "ma",
    "mozambique": "mz",
    "namibia": "na",
    "niger": "ne",
    "nigeria": "ng",
    "rwanda": "rw",
    "sao tome and principe": "st",
    "senegal": "sn",
    "seychelles": "sc",
    "sierra leone": "sl",
    "somalia": "so",
    "south africa": "za",
    "south sudan": "ss",
    "sudan": "sd",
    "tanzania": "tz",
    "togo": "tg",
    "tunisia": "tn",
    "uganda": "ug",
    "zambia": "zm",
    "zimbabwe": "zw",

    // Oceania
    "australia": "au",
    "fiji": "fj",
    "kiribati": "ki",
    "marshall islands": "mh",
    "micronesia": "fm",
    "nauru": "nr",
    "new zealand": "nz",
    "palau": "pw",
    "papua new guinea": "pg",
    "samoa": "ws",
    "solomon islands": "sb",
    "tonga": "to",
    "tuvalu": "tv",
    "vanuatu": "vu"
        };
    const code = aliases[name] || countryCodeByName.get(name);

    console.log("FLAG DEBUG:", countryName, "=>", code);

    return code ? `https://flagcdn.com/${code}.svg` : null;
}

