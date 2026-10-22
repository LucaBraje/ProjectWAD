
from sqlalchemy import inspect, text
from app import app, db, Team
import unicodedata
import re


# HISTORICAL BIOGRAPHIES FOR EUROLEAGUE CLUBS
BIOGRAPHIES = {
    "anadolu efes": """
Founded in 1976 as Efes Pilsen, Anadolu Efes is one of Türkiye's most successful basketball clubs. Based in Istanbul, the team has competed in Europe's leading competitions for decades.

Efes won the FIBA Korać Cup in 1996, becoming the first Turkish basketball club to win a major European trophy. The club later won consecutive EuroLeague championships in 2021 and 2022, led by stars including Vasilije Micić and Shane Larkin.
""",

    "as monaco": """
AS Monaco's basketball section was established in 1928. Known as La Roca Team, the club represents Monaco and plays its home games at Salle Gaston Médecin.

Monaco won the EuroCup in 2021 and made its modern EuroLeague debut in the 2021–22 season. The club reached its first EuroLeague Final Four in 2023 and advanced to the championship game in 2025, finishing as runner-up to Fenerbahçe.
""",

    "baskonia": """
Founded in 1959, Baskonia is a professional basketball club based in Vitoria-Gasteiz, Spain. Formerly known under sponsorship names such as TAU Cerámica, it has been a regular competitor in Europe's elite basketball competitions.

Baskonia won the European Cup Winners' Cup in 1996 and reached the EuroLeague championship series in 2001 and the final in 2005. Although it has not won the EuroLeague, it has claimed multiple Spanish league championships.
""",

    "crvena zvezda": """
Founded in 1945, Crvena Zvezda, also known as Red Star Belgrade, is one of Serbia's most historic basketball clubs. The team is famous for its passionate supporters and its rivalry with Partizan.

Crvena Zvezda won the European Cup Winners' Cup in 1974 and has collected numerous Yugoslav, Serbian, and Adriatic League titles. It has competed regularly in the modern EuroLeague since returning to the competition in 2013.
""",

    "dubai": """
Dubai Basketball was established in 2023 as a professional basketball club based in Dubai, United Arab Emirates.

The club began competing in the ABA League in the 2024–25 season and made its EuroLeague debut in 2025–26, becoming the first club from the United Arab Emirates to participate in the competition. Dubai represents a major expansion of top-level European club basketball beyond its traditional geographical base.
""",

    "olimpia milano": """
Founded in 1936, Olimpia Milano is one of Italy's most successful and historic basketball clubs. The Milan-based team has competed under several sponsorship names, including Simmenthal, Tracer, and Armani.

Olimpia Milano has won three European top-tier championships, in 1966, 1987, and 1988. The club also has an extensive record of Italian league championships and reached the modern EuroLeague Final Four in 2021.
""",

    "fc barcelona": """
FC Barcelona's basketball section was founded in 1926. Based in Barcelona, Spain, the club is one of Europe's most recognizable basketball institutions and a long-standing participant in elite European competitions.

Barcelona won its first EuroLeague championship in 2003 and its second in 2010. The club has also won numerous Spanish league and Copa del Rey titles, with legendary players including Juan Carlos Navarro and Pau Gasol.
""",

    "bayern munich": """
FC Bayern Munich's basketball section was established in 1946, although the parent sports club dates back to 1900. Based in Munich, the team has become one of Germany's leading basketball organizations.

Bayern made its modern EuroLeague debut in the 2013–14 season and became a regular participant in the competition. The club has won multiple German championships and reached the EuroLeague playoffs for the first time in 2021.
""",

    "fenerbahce": """
Fenerbahçe's basketball section was founded in 1913 in Istanbul, Türkiye. The club has developed into one of Europe's leading basketball teams, particularly during its modern EuroLeague era.

Under coach Željko Obradović, Fenerbahçe won its first EuroLeague championship in 2017, becoming the first Turkish club to win the modern competition. The club secured its second EuroLeague title in 2025, defeating AS Monaco in the final.
""",

    "hapoel tel aviv": """
Founded in 1935, Hapoel Tel Aviv is one of Israel's historic basketball clubs and a major rival of Maccabi Tel Aviv.

Hapoel has won multiple Israeli championships and domestic cups. The club captured the EuroCup championship in 2025, earning qualification for the EuroLeague and making its debut in the 2025–26 season.
""",

    "asvel": """
Founded in 1948 through the merger of two clubs, ASVEL is based in Villeurbanne, near Lyon, France. The club has historically been one of the most successful teams in French basketball.

ASVEL has won numerous French league championships and has competed in Europe's top basketball competitions across several eras. It returned to the modern EuroLeague in the 2019–20 season and has continued representing French basketball at the highest level.
""",

    "maccabi tel aviv": """
Maccabi Tel Aviv's basketball club was founded in 1932 and has become one of the most decorated teams in European basketball history.

Maccabi has won six European top-tier championships: 1977, 1981, 2001, 2004, 2005, and 2014. The 2001 title came in the FIBA SuproLeague, while the other five came in the European Champions Cup or EuroLeague. The club has also dominated Israeli domestic basketball for decades.
""",

    "olympiacos": """
Olympiacos established its basketball section in 1931 in Piraeus, Greece. It is one of Europe's most successful clubs and shares a famous rivalry with Panathinaikos.

Olympiacos has won four European top-tier championships, in 1997, 2012, 2013, and 2026. The back-to-back titles in 2012 and 2013 were particularly memorable, with Vassilis Spanoulis leading the team during that era.
""",

    "panathinaikos": """
Panathinaikos founded its basketball section in 1919 in Athens, Greece. It is one of Europe's most decorated basketball clubs and maintains an intense rivalry with Olympiacos.

Panathinaikos has won seven European top-tier championships: 1996, 2000, 2002, 2007, 2009, 2011, and 2024. The club enjoyed extraordinary success under coach Željko Obradović and has featured legends such as Dimitris Diamantidis.
""",

    "paris basketball": """
Paris Basketball was founded in 2018 and quickly emerged as an ambitious basketball club in the French capital.

The club won the EuroCup in 2024, earning its first EuroLeague appearance in the 2024–25 season. Despite its relatively short history, Paris rapidly became a competitive force in European basketball and helped strengthen the sport's presence in France's capital.
""",

    "partizan": """
Founded in 1945, Partizan Belgrade is one of Serbia's most historic basketball clubs. The team is famous for developing talented players and for its fierce rivalry with Crvena Zvezda.

Partizan won the European championship in 1992 under young coach Željko Obradović, defeating Joventut Badalona in the final. The club has also won numerous domestic and Adriatic League championships and reached the EuroLeague Final Four in 2010.
""",

    "real madrid": """
Real Madrid's basketball section was founded in 1931 in Madrid, Spain. It is the most successful club in the history of Europe's top-tier basketball competition.

Real Madrid has won eleven European championships: 1964, 1965, 1967, 1968, 1974, 1978, 1980, 1995, 2015, 2018, and 2023. The club has also won numerous Spanish championships and has featured legendary players such as Sergio Llull, Luka Dončić, and Walter Tavares.
""",

    "valencia basket": """
Founded in 1986, Valencia Basket is a professional basketball club based in Valencia, Spain. The club has developed into a regular contender in Spanish and European competitions.

Valencia has won the EuroCup four times, in 2003, 2010, 2014, and 2019. It also captured its first Spanish league championship in 2017. Valencia has participated in several modern EuroLeague seasons, including its return in 2025–26.
""",

    "virtus bologna": """
Virtus Bologna was founded in 1929 and is one of Italy's most historic basketball clubs. Known for its black-and-white identity, the club has a long tradition of domestic and European success.

Virtus won two European top-tier championships, in 1998 and 2001, during an era associated with stars such as Predrag Danilović and Manu Ginóbili. The club also won the EuroCup in 2022, securing its return to the EuroLeague.
""",

    "zalgiris": """
Founded in 1944, Žalgiris Kaunas is Lithuania's most famous basketball club and a central institution in the country's basketball culture.

Žalgiris won the European championship in 1999, defeating Kinder Bologna in the final. The club has also won numerous Lithuanian league titles and reached the modern EuroLeague Final Four in 2018 under coach Šarūnas Jasikevičius.
""",
    "besiktas": """
Beşiktaş's basketball section was founded in 1967 in Istanbul, Türkiye, as part of the Beşiktaş sports club, which was established in 1903.

The club won the Turkish Basketball League championship in 1975 and enjoyed a remarkable 2011–12 season, winning the Turkish League, Turkish Cup, and FIBA EuroChallenge. Beşiktaş has competed in European competitions, including the 2012–13 EuroLeague season, and maintains a strong rivalry with other Istanbul clubs.
""",

}


# MATCH DIFFERENT DATABASE TEAM NAMES

ALIASES = {
    "anadolu efes": [
        "anadolu efes",
        "efes pilsen"
    ],

    "as monaco": [
        "as monaco",
        "monaco"
    ],

    "baskonia": [
        "baskonia",
        "kosner baskonia",
        "tau ceramica"
    ],

    "crvena zvezda": [
        "crvena zvezda",
        "red star"
    ],

    "dubai": [
        "dubai basketball",
        "dubai bc"
    ],

    "olimpia milano": [
        "olimpia milano",
        "olimpia milan",
        "armani olimpia milan",
        "emporio armani",
        "ea7",
        "armani milan"
    ],

    "fc barcelona": [
        "fc barcelona",
        "barcelona",
        "barca"
    ],

    "bayern munich": [
        "fc bayern munich",
        "bayern munich",
        "bayern munchen",
        "bayern"
    ],

    "fenerbahce": [
        "fenerbahce"
    ],

    "hapoel tel aviv": [
        "hapoel ibi tel aviv",
        "hapoel tel aviv"
    ],

    "asvel": [
        "ldlc asvel villeurbanne",
        "asvel",
        "villeurbanne"
    ],

    "maccabi tel aviv": [
        "maccabi rapyd tel aviv",
        "maccabi tel aviv"
    ],

    "olympiacos": [
        "olympiacos",
        "olympiakos"
    ],

    "panathinaikos": [
        "panathinaikos"
    ],

    "paris basketball": [
        "paris basketball"
    ],

    "partizan": [
        "partizan"
    ],

    "real madrid": [
        "real madrid"
    ],

    "valencia basket": [
        "valencia basket",
        "valencia"
    ],

    "virtus bologna": [
        "virtus bologna",
        "virtus segafredo"
    ],

    "zalgiris": [
        "zalgiris"
    ],

    "besiktas": [
        "besiktas",
        "besiktas istanbul"
    ]
}


def normalize_name(name):
    # Remove accents, punctuation, and differences in capitalization
    name = unicodedata.normalize("NFKD", name or "")
    name = "".join(
        character for character in name
        if not unicodedata.combining(character)
    )
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return " ".join(name.split())


def find_biography(team_name):
    normalized = normalize_name(team_name)

    for key, possible_names in ALIASES.items():
        for possible_name in possible_names:
            alias = normalize_name(possible_name)

            if normalized == alias or normalized.startswith(alias + " "):
                return BIOGRAPHIES[key].strip()

    return None


# UPDATE DATABASE
with app.app_context():

    # STEP 1: ADD BIOGRAPHY COLUMN IF NECESSARY
    columns = [
        column["name"]
        for column in inspect(db.engine).get_columns("team")
    ]

    if "biography" not in columns:
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE team ADD COLUMN biography TEXT")
            )

        print("Biography column added successfully!")
    else:
        print("Biography column already exists.")

    # STEP 2: POPULATE TEAM BIOGRAPHIES
    teams = Team.query.all()

    updated = 0
    skipped = 0

    for team in teams:

        # Preserve biographies that already exist
        if team.biography and team.biography.strip():
            print(f"SKIPPED (already filled): {team.name}")
            skipped += 1
            continue

        biography = find_biography(team.name)

        if biography:
            team.biography = biography
            updated += 1
            print(f"UPDATED: {team.name}")
        else:
            skipped += 1
            print(f"NOT FOUND: {team.name}")

    db.session.commit()

    print("\n------------------------------")
    print(f"Total teams: {len(teams)}")
    print(f"Biographies added: {updated}")
    print(f"Skipped/unmatched: {skipped}")
    print("------------------------------")
