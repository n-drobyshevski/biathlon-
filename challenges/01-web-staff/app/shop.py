"""
DécaFlop public storefront for challenge 01 (decor only: nothing here is part
of the challenge). The challenge itself (robots.txt + the staff portal) lives
in app.py.

The site follows the layout of a large sports retailer: announcement bar,
header with search, product rails, filterable category pages and detailed
product pages. It is read-only on purpose. Online sales are "suspended during
the race", so there is no cart, account or checkout to poke at, and the only
form is the search box, which never echoes what was typed. Filter and sort
parameters are mapped to known values and never echoed either.
"""
import os
import zlib
from html import escape
from urllib.parse import urlencode

from flask import Blueprint, Response, abort, request, send_from_directory

from packshots import DRAW, packshot, ui

shop = Blueprint("shop", __name__)
NB = "\u00a0"   # non-breaking space (French typography, prices)
CUR = ' aria-current="page"'
ON = ' aria-current="true"'


# --------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------
CATEGORIES = {
    "natation": ("Natation", "Lunettes, bonnets, combinaisons et matériel d'entraînement pour la piscine "
                 "et l'eau libre."),
    "velo": ("Vélo", "Vélos de chrono, casques, bidons et tout ce qu'il faut pour réparer au bord de la route."),
    "course-a-pied": ("Course à pied", "Chaussures, montres GPS et accessoires pour les dix derniers kilomètres."),
}
BRANDS = {"nageflop": "Nageflop", "pedalo": "Pédalo", "bofbof": "Bofbof", "runflop": "Runflop"}
BRAND_SLUG = {v: k for k, v in BRANDS.items()}


def P(cat, brand, title, price, was, rating, reviews, badge, ref, colors, sizes, na, desc,
      points, specs, revs, qa):
    return dict(cat=cat, brand=brand, title=title, price=price, was=was, rating=rating, reviews=reviews,
                badge=badge, ref=ref, colors=colors, sizes=sizes, na=set(na), desc=desc, points=points,
                specs=specs, revs=revs, qa=qa)


TU = ["TU"]   # taille unique

PRODUCTS = {
    # ------------------------------------------------------------ natation
    "lunettes-natation": P(
        "natation", "Nageflop", "Lunettes de natation anti-buée verres teintés", "14,99", "", 3.9, 1048, "low",
        "8 553 902", [("Bleu", "#2f7fd6"), ("Fumé", "#4a4f5c"), ("Miroir doré", "#c99b2d")], TU, [],
        "Des verres teintés pour nager face au soleil levant et un joint souple qui tient sans serrer. "
        "La sangle double se règle en quelques secondes, même avec un bonnet.",
        [("Vision", "Verres teintés anti-UV, adaptés à l'eau libre par temps clair."),
         ("Étanchéité", "Joints en silicone souple sur tout le contour de l'œil."),
         ("Réglage", "Sangle double et pont de nez interchangeable, trois tailles fournies.")],
        [("Verres", "Polycarbonate teinté, traitement anti-buée"), ("Joints", "Silicone"),
         ("Sangle", "Double, en silicone, réglage par boucle"), ("Pont de nez", "3 tailles fournies"),
         ("Étui", "Inclus"), ("Garantie", "2 ans")],
        [(4, "Bonne vision en extérieur", "Je les utilise au lac le matin, les verres teintés font vraiment la "
          "différence. L'anti-buée tient une petite heure, ensuite il faut rincer.", "Camille", "19/09/2026",
          "Nage en eau libre"),
         (3, "Correctes pour le prix", "Elles prennent un peu l'eau si la sangle n'est pas assez serrée. Une fois "
          "bien réglées, rien à redire pour l'entraînement.", "Thomas", "03/08/2026", "Piscine")],
        ("Peut-on les porter par-dessus des lunettes de vue ?",
         "Non, ce modèle se porte directement sur le visage. Des verres correcteurs adaptables peuvent être "
         "commandés en magasin.")),
    "bonnet-silicone": P(
        "natation", "Nageflop", "Bonnet de bain en silicone haute visibilité", "6,99", "", 4.5, 212, None,
        "8 553 127", [("Jaune fluo", "#f2e600"), ("Orange", "#ff7a1a"), ("Rose", "#ff5fa2")], TU, [],
        "Un bonnet épais et très coloré pour être repéré facilement par les bateaux de sécurité en eau "
        "libre. Le silicone ne tire pas les cheveux et garde la chaleur.",
        [("Visibilité", "Coloris fluo repérable de loin, même avec du clapot."),
         ("Confort", "Silicone épais qui ne tire pas les cheveux."),
         ("Chaleur", "Limite la perte de chaleur par la tête dans une eau fraîche.")],
        [("Matière", "Silicone 100 %"), ("Épaisseur", "0,8 mm"), ("Taille", "Unique, adulte"),
         ("Entretien", "Rincer à l'eau claire et sécher à l'ombre"), ("Garantie", "2 ans")],
        [(5, "Indestructible", "Trois saisons de piscine et toujours comme neuf. Il se met facilement, même "
          "avec les cheveux longs.", "Léa", "28/09/2026", "Piscine"),
         (4, "Bien visible", "Imposé par mon club pour l'eau libre. Un peu chaud en été, mais c'est le but en "
          "octobre.", "Marc", "11/10/2026", "Nage en eau libre")],
        ("Le bonnet est-il accepté en compétition ?",
         "Oui. Lors des épreuves officielles, l'organisation fournit un bonnet de couleur imposée à porter "
         "par-dessus.")),
    "combinaison-tri-500": P(
        "natation", "Nageflop", "Combinaison néoprène de triathlon Tri 500 homme", "199,99", "249,99", 4.3, 96,
        None, "8 571 234", [("Noir et bleu", "#1a1d24"), ("Noir et menthe", "#22352c")],
        ["XS", "S", "M", "L", "XL", "XXL"], ["XXL"],
        "Une combinaison en néoprène de 5 mm sur le torse et les cuisses pour garder les jambes en surface, "
        "avec des épaules en 2 mm pour une rotation complète. La fermeture dorsale à cordon permet de "
        "l'enlever vite en transition.",
        [("Flottabilité", "Néoprène de 5 mm sur le torse et les cuisses pour garder les jambes en surface."),
         ("Transition rapide", "Fermeture dorsale à cordon et chevilles coupées pour l'enlever en quelques "
          "secondes."),
         ("Liberté d'épaules", "Panneaux de 2 mm sous les bras pour une rotation complète.")],
        [("Épaisseur", "5 mm torse et cuisses, 2 mm épaules et bras"), ("Fermeture", "Dorsale, à cordon"),
         ("Température de l'eau", "De 14 à 22 °C"), ("Doublure", "Jersey intérieur"),
         ("Conformité", "Règlement fédéral des épreuves avec combinaison"), ("Garantie", "2 ans")],
        [(5, "Très bonne flottabilité", "Utilisée pour deux triathlons distance M. On flotte très bien et elle "
          "s'enlève vite en transition. Prendre sa taille habituelle.", "Julien", "14/09/2026", "Triathlon"),
         (4, "Bon rapport qualité-prix", "Un peu serrée aux épaules les premières sorties, ça s'assouplit "
          "ensuite. Attention aux ongles en l'enfilant.", "Sandrine", "02/08/2026", "Triathlon")],
        ("Quelle taille choisir quand on est entre deux tailles ?",
         "Prenez la plus petite. Le néoprène se détend un peu à l'usage. Le guide des tailles indique le poids "
         "et la taille conseillés.")),
    "pull-buoy": P(
        "natation", "Nageflop", "Pull-buoy en mousse pour l'entraînement des bras", "9,99", "", 4.6, 157, "new",
        "8 612 045", [("Bleu et noir", "#3643ba")], TU, [],
        "Calé entre les cuisses, il maintient les jambes à la surface pour travailler uniquement les bras. "
        "La mousse EVA reste ferme et ne se gorge pas d'eau.",
        [("Travail des bras", "Isole le haut du corps pour progresser sur la traction."),
         ("Tenue", "Forme en huit qui reste en place entre les cuisses."),
         ("Durabilité", "Mousse EVA fermée qui ne prend pas l'eau.")],
        [("Matière", "Mousse EVA"), ("Dimensions", "23 x 14 x 9 cm"), ("Poids", "110 g"), ("Garantie", "2 ans")],
        [(5, "Indispensable", "Je l'utilise à chaque séance de piscine. Il ne glisse pas et la mousse n'a pas "
          "bougé en un an.", "Hugo", "06/10/2026", "Piscine"),
         (4, "Simple et efficace", "Un peu gros pour mon petit gabarit au début, on s'y habitue vite.", "Inès",
          "21/07/2026", "Piscine")],
        ("Peut-on l'utiliser comme planche ?",
         "Oui, pour les éducatifs de jambes, même s'il porte moins qu'une planche classique.")),
    "sac-etanche-30l": P(
        "natation", "Nageflop", "Sac étanche de triathlon 30 L avec bretelle", "24,99", "29,99", 4.4, 73, None,
        "8 598 310", [("Bleu", "#3643ba"), ("Noir", "#1d2129")], TU, [],
        "Un sac à fermeture enroulable pour garder les affaires au sec au bord de l'eau et au parc à vélos. "
        "La bretelle se règle et se retire.",
        [("Étanche", "Fermeture enroulable sur trois tours et soudures étanches."),
         ("Pratique", "Bretelle réglable et amovible, poignée sur le dessus."),
         ("Visible", "Bande réfléchissante pour le retrouver au parc à vélos.")],
        [("Volume", "30 litres"), ("Matière", "PVC enduit"), ("Fermeture", "Enroulable, boucle clipsable"),
         ("Poids", "480 g"), ("Garantie", "2 ans")],
        [(5, "Tout reste au sec", "Testé sous une grosse averse au parc à vélos, rien n'a pris l'eau. La "
          "bretelle est confortable.", "Nathalie", "15/09/2026", "Triathlon"),
         (4, "Bon sac", "Le volume est juste pour une combinaison et des chaussures, mais ça passe.", "Olivier",
          "30/08/2026", "Triathlon")],
        ("Le sac flotte-t-il ?",
         "Fermé avec de l'air à l'intérieur, oui. Il n'est pas conçu pour être tracté en nageant.")),
    # ----------------------------------------------------------------- vélo
    "velo-chrono-race-900": P(
        "velo", "Pédalo", "Vélo de chrono Race 900 aluminium, prolongateurs réglables", "1 299,00", "1 499,00",
        4.1, 212, None, "8 604 117", [("Bleu", "#3643ba")], ["S", "M", "L", "XL"], ["XL"],
        "Un cadre en aluminium aux formes aérodynamiques, des prolongateurs réglables et une transmission "
        "2 x 11 vitesses. Livré avec une roue arrière lenticulaire pour les épreuves contre la montre.",
        [("Aérodynamisme", "Tubes profilés et roue arrière lenticulaire."),
         ("Position", "Prolongateurs et repose-bras réglables en hauteur et en largeur."),
         ("Transmission", "2 x 11 vitesses, plateaux 53/39 et cassette 11-28.")],
        [("Cadre", "Aluminium 6061, câbles internes"), ("Fourche", "Carbone"), ("Transmission", "2 x 11 vitesses"),
         ("Roues", "Arrière lenticulaire, avant jante de 60 mm"), ("Poids", "9,4 kg en taille M"),
         ("Garantie", "5 ans sur le cadre, 2 ans sur les composants")],
        [(4, "Très bon premier vélo de chrono", "La position se trouve facilement grâce au réglage des "
          "prolongateurs. Un peu lourd en montée mais très stable sur le plat.", "Antoine", "09/09/2026",
          "Triathlon"),
         (5, "Gros gain de vitesse", "Deux km/h de mieux sur mon parcours habituel. Faites régler la position en "
          "magasin, ça vaut le coup.", "Pauline", "17/08/2026", "Contre-la-montre")],
        ("La roue lenticulaire est-elle autorisée partout ?",
         "Elle est autorisée en triathlon sans aspiration-abri. Par vent fort, l'organisation peut l'interdire, "
         "prévoyez alors une roue arrière à rayons.")),
    "casque-aero": P(
        "velo", "Pédalo", "Casque aéro de triathlon à visière magnétique", "89,99", "", 4.0, 57, None,
        "8 604 522", [("Blanc et bleu", "#f2f3f7"), ("Noir", "#1d2129")], ["S-M", "M-L"], [],
        "Un profil allongé pour gagner quelques secondes en position et une visière magnétique qui se clipse "
        "d'une main. La molette arrière ajuste le tour de tête.",
        [("Profil aéro", "Queue courte qui reste efficace même tête baissée."),
         ("Visière", "Magnétique, se retire et se remet d'une main en transition."),
         ("Ventilation", "Deux entrées d'air frontales pour les journées chaudes.")],
        [("Tours de tête", "S-M de 53 à 57 cm, M-L de 57 à 61 cm"), ("Poids", "340 g en taille M-L"),
         ("Visière", "Polycarbonate, fixation magnétique"), ("Norme", "EN 1078"), ("Garantie", "2 ans")],
        [(4, "Visière très pratique", "Elle se met en place toute seule grâce aux aimants. Un peu chaud au-delà "
          "de 28 degrés.", "Romain", "25/08/2026", "Triathlon"),
         (4, "Bon casque", "Il taille un peu petit, j'ai pris M-L pour 57 cm de tour de tête.", "Élise",
          "12/07/2026", "Contre-la-montre")],
        ("La visière est-elle compatible avec des lunettes de vue ?",
         "Avec des montures fines, oui, la visière se porte par-dessus. Essayez-le en magasin avec vos "
         "lunettes.")),
    "bidon-750": P(
        "velo", "Bofbof", "Bidon de vélo 750 ml à valve anti-fuite", "4,99", "6,99", 3.9, 87, None, "8 590 731",
        [("Translucide", "#d8e4f0"), ("Bleu", "#3643ba"), ("Noir", "#1d2129")], TU, [],
        "Un bidon souple sans BPA avec une valve à débit rapide utilisable d'une main en roulant. Le bouchon "
        "se dévisse en entier pour le nettoyage.",
        [("Débit rapide", "Valve qui s'ouvre avec les dents et se referme seule."),
         ("Prise en main", "Corps souple avec une zone de préhension marquée."),
         ("Entretien", "Passe au lave-vaisselle, bouchon démontable.")],
        [("Contenance", "750 ml"), ("Matière", "Polyéthylène sans BPA"), ("Valve", "Anti-fuite, débit rapide"),
         ("Compatibilité", "Porte-bidons standards"), ("Garantie", "2 ans")],
        [(4, "Fait le job", "Pas de fuite dans le sac et la valve est facile à utiliser en roulant.", "Kevin",
          "02/10/2026", "Vélo de route"),
         (3, "Goût de plastique au début", "Il faut le laver deux ou trois fois avant que le goût disparaisse. "
          "Sinon rien à dire.", "Marion", "18/06/2026", "VTT")],
        ("Peut-on y mettre une boisson chaude ?",
         "Non, ce bidon est prévu pour des boissons froides ou à température ambiante.")),
    "kit-reparation": P(
        "velo", "Pédalo", "Kit de réparation crevaison avec démonte-pneus", "7,99", "", 4.5, 241, None,
        "8 590 118", [("Noir", "#1d2129")], TU, [],
        "Tout pour réparer une chambre à air au bord de la route, dans une pochette qui se glisse sous la "
        "selle ou dans la poche du maillot.",
        [("Complet", "Deux démonte-pneus, six rustines, de la colle et du papier abrasif."),
         ("Compact", "Pochette zippée de la taille d'une carte postale."),
         ("Solide", "Démonte-pneus en nylon renforcé qui ne marquent pas les jantes.")],
        [("Contenu", "2 démonte-pneus, 6 rustines, 1 tube de colle, 1 abrasif"), ("Dimensions", "14 x 9 x 3 cm"),
         ("Poids", "55 g"), ("Garantie", "2 ans")],
        [(5, "A sauvé ma sortie", "Crevaison à 40 km de chez moi, réparée en dix minutes. Les démonte-pneus sont "
          "solides.", "Bruno", "27/09/2026", "Vélo de route"),
         (4, "Pratique", "La colle sèche vite une fois ouverte, pensez à la changer chaque saison.", "Claire",
          "14/05/2026", "Vélotaf")],
        ("Le kit convient-il aux pneus tubeless ?",
         "Non, il est prévu pour les chambres à air. Pour le tubeless, demandez un kit de mèches à l'atelier.")),
    "gants-velo": P(
        "velo", "Pédalo", "Gants de vélo courts Road 500", "14,99", "", 4.2, 64, "last", "8 604 903",
        [("Noir", "#1d2129"), ("Bleu", "#3643ba")], ["XS", "S", "M", "L", "XL"], ["XS"],
        "Des gants courts avec une paume rembourrée pour limiter les fourmillements sur les longues sorties. "
        "Le dos en maille respire.",
        [("Confort", "Mousse sous la paume aux points d'appui."), ("Respirant", "Dos en maille aérée."),
         ("Pratique", "Tirettes entre les doigts pour les retirer facilement.")],
        [("Paume", "Synthétique, mousse de 4 mm"), ("Dos", "Maille polyester"),
         ("Fermeture", "Patte auto-agrippante"), ("Entretien", "Lavable en machine à 30 °C"),
         ("Garantie", "2 ans")],
        [(4, "Bons gants d'été", "Confortables et la paume amortit bien. La taille correspond au guide.",
          "Stéphane", "08/08/2026", "Vélo de route"),
         (5, "Parfaits pour le triathlon", "Je les enfile en roulant après la transition, ils tiennent bien.",
          "Aurélie", "10/09/2026", "Triathlon")],
        ("Peut-on utiliser un téléphone sans les retirer ?",
         "Oui, ces gants courts laissent le bout des doigts libre.")),
    # ------------------------------------------------------- course à pied
    "chaussures-lacage-rapide": P(
        "course-a-pied", "Runflop", "Chaussures de running à laçage rapide Tri Speed", "59,99", "", 4.6, 33, None,
        "8 611 270", [("Bleu", "#3643ba"), ("Gris", "#9aa0aa")],
        ["39", "40", "41", "42", "43", "44", "45", "46"], ["39", "46"],
        "Des lacets élastiques à serrage rapide pour enfiler les chaussures en quelques secondes au parc à "
        "vélos, une semelle amortissante et une tirette au talon.",
        [("Laçage rapide", "Lacets élastiques et bloqueur, pas de nœud à faire."),
         ("Amorti", "Semelle intermédiaire en mousse EVA, drop de 8 mm."),
         ("Sans chaussettes", "Intérieur doux et sans couture pour courir pieds nus.")],
        [("Drop", "8 mm"), ("Poids", "255 g en pointure 42"), ("Tige", "Maille respirante"),
         ("Semelle", "EVA et caoutchouc"), ("Usage", "Route, entraînement et compétition"), ("Garantie", "2 ans")],
        [(5, "Gain de temps en transition", "Je les mets en dix secondes. Confortables sans chaussettes sur "
          "10 km.", "Mathieu", "22/09/2026", "Triathlon"),
         (4, "Bon amorti", "Elles taillent normalement. Un peu justes en largeur pour mes pieds.", "Sophie",
          "05/09/2026", "Course sur route")],
        ("Peut-on remplacer les lacets élastiques par des lacets classiques ?",
         "Oui, les œillets sont standards. Les lacets classiques sont vendus séparément.")),
    "montre-gps": P(
        "course-a-pied", "Runflop", "Montre GPS multisport Tri 200", "79,99", "99,99", 4.2, 140, None, "8 611 845",
        [("Noir", "#1d2129")], TU, [],
        "Un mode triathlon qui enchaîne natation, vélo et course d'une seule pression, avec les temps de "
        "transition. L'autonomie atteint 12 heures en GPS.",
        [("Multisport", "Passage d'une discipline à l'autre d'un appui sur le bouton."),
         ("Autonomie", "12 heures en GPS, 10 jours en mode montre."),
         ("Étanche", "Jusqu'à 50 mètres, comptage des longueurs en piscine.")],
        [("GPS", "Oui"), ("Autonomie", "12 h en GPS, 10 jours en mode montre"), ("Étanchéité", "50 m"),
         ("Écran", "Rond, lisible en plein soleil"), ("Bracelet", "Silicone, 22 mm"), ("Garantie", "2 ans")],
        [(4, "Simple et fiable", "Le mode triathlon fonctionne bien et les transitions sont séparées. "
          "L'application est basique.", "Damien", "16/09/2026", "Triathlon"),
         (4, "Très bien pour débuter", "Le GPS met parfois une minute à capter en ville.", "Laura", "29/07/2026",
          "Course sur route")],
        ("La montre mesure-t-elle la fréquence cardiaque ?",
         "Oui, au poignet. Une ceinture cardio peut être ajoutée pour plus de précision en natation.")),
    "ceinture-dossard": P(
        "course-a-pied", "Runflop", "Ceinture porte-dossard avec attaches pour gels", "9,99", "", 4.7, 301, None,
        "8 611 402", [("Noir", "#1d2129"), ("Bleu", "#3643ba")], TU, [],
        "Fixez votre dossard sans épingles et tournez-le dans le dos pour la partie vélo. Trois passants "
        "accueillent des gels énergétiques.",
        [("Sans épingles", "Deux attaches tiennent le dossard sans le déchirer."),
         ("Transition", "Se clipse en une seconde à la sortie du parc à vélos."),
         ("Ravitaillement", "Trois passants élastiques pour les gels.")],
        [("Tour de taille", "Réglable de 65 à 120 cm"), ("Matière", "Élastique polyester"),
         ("Attaches", "2 pour le dossard, 3 pour les gels"), ("Poids", "35 g"), ("Garantie", "2 ans")],
        [(5, "Indispensable en triathlon", "Plus besoin d'épingles et le dossard tourne facilement. Les passants "
          "tiennent bien les gels.", "Fabien", "13/09/2026", "Triathlon"),
         (5, "Parfait", "Légère, on l'oublie pendant la course.", "Céline", "04/10/2026", "Trail")],
        ("Le dossard peut-il se déchirer avec les attaches ?",
         "Non, les attaches passent dans les trous prévus du dossard. Deux œillets adhésifs sont fournis pour "
         "les dossards sans trous.")),
    "casquette-running": P(
        "course-a-pied", "Runflop", "Casquette de running légère et respirante", "9,99", "", 4.3, 88, "last",
        "8 611 633", [("Blanc", "#f2f3f7"), ("Bleu", "#3643ba")], TU, [],
        "Une casquette légère avec des panneaux en maille pour évacuer la chaleur et une visière souple qui "
        "se range dans une poche.",
        [("Respirante", "Panneaux latéraux en maille."), ("Légère", "45 g, visière souple."),
         ("Réglable", "Bande élastique et boucle à l'arrière.")],
        [("Matière", "Polyester recyclé"), ("Poids", "45 g"), ("Tour de tête", "Réglable de 54 à 60 cm"),
         ("Entretien", "Lavage à la main"), ("Garantie", "2 ans")],
        [(4, "Légère", "On ne la sent pas en courant et elle sèche vite.", "Yann", "21/08/2026",
          "Course sur route"),
         (5, "Top par temps chaud", "Je la mouille aux ravitaillements, elle garde la tête au frais.", "Amandine",
          "06/07/2026", "Triathlon")],
        ("La casquette passe-t-elle en machine ?",
         "Un lavage à la main à l'eau froide est conseillé pour ne pas déformer la visière.")),
    "gels-energetiques": P(
        "course-a-pied", "Bofbof", "Gels énergétiques goût citron, lot de 4", "5,99", "", 4.1, 52, "new",
        "8 590 977", [("Citron", "#f2e600")], TU, [],
        "Quatre gels de 32 g à prendre pendant l'effort, avec une texture liquide qui s'avale sans eau. Chaque "
        "gel apporte 22 g de glucides.",
        [("Énergie", "22 g de glucides par gel."), ("Texture", "Liquide, se prend sans eau."),
         ("Format", "Sachet avec encoche, s'ouvre d'une main.")],
        [("Contenu", "4 gels de 32 g"), ("Glucides", "22 g par gel"), ("Sodium", "50 mg par gel"),
         ("Goût", "Citron"), ("Conservation", "À l'abri de la chaleur")],
        [(4, "Bon goût", "Pas trop sucré, il passe bien même en fin de course.", "Nicolas", "18/09/2026",
          "Triathlon"),
         (4, "Pratique", "L'encoche s'ouvre bien avec des mains mouillées.", "Emma", "01/10/2026", "Trail")],
        ("Combien de gels prévoir sur un triathlon distance olympique ?",
         "En général un gel toutes les 40 à 45 minutes à partir de la partie vélo. Testez toujours à "
         "l'entraînement avant la course.")),
}

# Product type, used for the menu and the breadcrumb.
KIND = {"lunettes-natation": "Lunettes", "bonnet-silicone": "Bonnets", "combinaison-tri-500": "Combinaisons",
        "pull-buoy": "Pull-buoys", "sac-etanche-30l": "Sacs étanches", "velo-chrono-race-900": "Vélos de chrono",
        "casque-aero": "Casques", "bidon-750": "Bidons", "kit-reparation": "Réparation", "gants-velo": "Gants",
        "chaussures-lacage-rapide": "Chaussures", "montre-gps": "Montres GPS",
        "ceinture-dossard": "Ceintures porte-dossard", "casquette-running": "Casquettes",
        "gels-energetiques": "Nutrition"}

DRAW_OK = set(DRAW)   # every catalogue product has a drawing (checked by the tests)

HOME_DEALS = ["combinaison-tri-500", "velo-chrono-race-900", "lunettes-natation", "montre-gps",
              "sac-etanche-30l", "bidon-750"]
RACE_DAY = ["ceinture-dossard", "chaussures-lacage-rapide", "gels-energetiques", "casquette-running"]
FINAL_KIT = ["combinaison-tri-500", "velo-chrono-race-900", "casque-aero", "ceinture-dossard",
             "chaussures-lacage-rapide"]

STORES = [
    ("stade", "DécaFlop Stade", "2 allée du Stade",
     [("Du lundi au samedi", "9 h à 20 h"), ("Dimanche", "9 h à 13 h")],
     ["Atelier vélo", "Location de vélos", "Retrait des commandes"]),
    ("centre-ville", "DécaFlop Centre-ville", "14 rue du Port",
     [("Du lundi au samedi", "10 h à 19 h"), ("Dimanche", "10 h à 13 h")],
     ["Retrait des commandes", "Essayage des combinaisons"]),
    ("destockage", "DécaFlop Déstockage", "Parking du Stade, entrée nord",
     [("Du vendredi au dimanche", "9 h à 18 h")],
     ["Fins de séries", "Matériel de location d'occasion"]),
]
STOCK_PATTERNS = [
    [("ok", "En stock"), ("low", "Plus que 2"), ("out", "Rupture")],
    [("ok", "En stock"), ("ok", "En stock"), ("low", "Plus que 1")],
    [("low", "Plus que 3"), ("ok", "En stock"), ("out", "Rupture")],
]


def num(price):
    return float(price.replace(" ", "").replace(NB, "").replace(",", "."))


def pct_off(p):
    return round((1 - num(p["price"]) / num(p["was"])) * 100) if p["was"] else 0


def stock(slug):
    return STOCK_PATTERNS[zlib.crc32(slug.encode()) % len(STOCK_PATTERNS)]


# --------------------------------------------------------------------------
# Small builders
# --------------------------------------------------------------------------
def fr(text):
    """French typography: non-breaking spaces inside « » and before : ? !"""
    for a, b in (("« ", "«" + NB), (" »", NB + "»"), (" :", NB + ":"), (" ?", NB + "?"), (" !", NB + "!")):
        text = text.replace(a, b)
    return text


def html(page, status=200):
    return Response(page, status=status, mimetype="text/html")


def euros(s):
    return s.replace(" ", NB) + NB + "€"


def rating_txt(r):
    return f"{r:.1f}".replace(".", ",")


def stars(r, count=None, plain=False):
    pct = f"{r / 5 * 100:.0f}%"
    txt = ""
    if not plain:
        txt = f"<b>{rating_txt(r)}</b>"
        if count is not None:
            txt += f" ({count:,})".replace(",", NB)
    return (f'<span class="stars"><span class="s" style="--p:{pct}" role="img" '
            f'aria-label="Note de {rating_txt(r)} sur 5"></span>{txt}</span>')


def price_block(p):
    old = ""
    if p["was"]:
        old = f'<s>{euros(p["was"])}</s><span class="off">-{pct_off(p)}{NB}%</span>'
    return f'<div class="price"><b>{euros(p["price"])}</b>{old}</div>'


BADGES = {"new": ("new", "Nouveau"), "low": ("low", "Prix bas"), "last": ("last", "Dernière chance")}


def badge(p):
    if p["was"]:
        return f'<span class="badge sale">-{pct_off(p)}{NB}%</span>'
    if p["badge"]:
        cls, label = BADGES[p["badge"]]
        return f'<span class="badge {cls}">{label}</span>'
    return ""


def card(slug):
    p = PRODUCTS[slug]
    dots = "".join(f'<i style="--c:{c}"></i>' for _n, c in p["colors"][:3])
    more = f'<span>{len(p["colors"])} coloris</span>' if len(p["colors"]) > 1 else ""
    return (f'<a class="card" href="/produit/{slug}"><div class="ph">{packshot(slug)}{badge(p)}</div>'
            f'<div class="cb"><span class="brand">{p["brand"]}</span><span class="t">{p["title"]}</span>'
            f'{stars(p["rating"], p["reviews"])}{price_block(p)}<div class="swatches">{dots}{more}</div>'
            '<span class="pick">Retrait gratuit en magasin</span></div></a>')


def crumbs(*items):
    parts = [f'<a href="{h}">{t}</a>' if h else f"<span>{t}</span>" for h, t in items]
    return ('<nav class="crumb" aria-label="Fil d\'Ariane">' +
            '<span class="sep" aria-hidden="true"></span>'.join(parts) + "</nav>")


def page_head(title, text="", items=()):
    return (f'<section class="page-hd"><div class="in">{crumbs(("/", "Accueil"), *items, (None, title))}'
            f'<h1>{title}</h1>{"<p>" + text + "</p>" if text else ""}</div></section>')


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------
SUBNAV = [("/natation", "Natation"), ("/velo", "Vélo"), ("/course-a-pied", "Course à pied"),
          ("/triathlon", "Triathlon"), ("/location", "Location"), ("/atelier", "Atelier vélo"),
          ("/magasins", "Magasins")]


def mega_menu():
    cols = []
    for cat, (name, _i) in CATEGORIES.items():
        items = "".join(f'<li><a href="/produit/{s}">{KIND[s]}</a></li>'
                        for s, p in PRODUCTS.items() if p["cat"] == cat)
        cols.append(f'<div><h3>{name}</h3><ul><li><a href="/{cat}">Tout le rayon {name.lower()}</a></li>'
                    f'{items}</ul></div>')
    cols.append('<div><h3>Services et infos</h3><ul><li><a href="/triathlon">Le championnat</a></li>'
                '<li><a href="/location">Location de vélos</a></li><li><a href="/atelier">Atelier vélo</a></li>'
                '<li><a href="/destockage">Déstockage</a></li><li><a href="/magasins">Nos magasins</a></li>'
                '<li><a href="/aide">Aide et contact</a></li></ul></div>')
    return ('<details class="mega"><summary>' + ui("menu", 18) + '<span class="lbl">Tous les sports</span>'
            '</summary><div class="mega-panel"><div class="in">' + "".join(cols) + '</div></div></details>')


def footer():
    cols = [
        ("Aide", [("/aide#commande", "Suivi de commande"), ("/aide#retours", "Retours et échanges"),
                  ("/aide#garantie", "Garantie"), ("/aide#tailles", "Guide des tailles"),
                  ("/aide#contact", "Nous contacter")]),
        ("Services", [("/location", "Location de vélos"), ("/atelier", "Atelier vélo"),
                      ("/aide#retrait", "Retrait en magasin"), ("/destockage", "Déstockage")]),
        ("Magasins", [(f"/magasins#{k}", n) for k, n, *_r in STORES]),
        ("Entreprise", [("/actualites", "Actualités"), ("/presse", "Espace presse"),
                        ("/recrutement", "Recrutement"), ("/triathlon", "Sponsoring triathlon")]),
    ]
    c = "".join(f'<div><h3>{t}</h3><ul>' + "".join(f'<li><a href="{h}">{x}</a></li>' for h, x in items) +
                '</ul></div>' for t, items in cols)
    return ('<section class="reassure" aria-label="Nos engagements"><ul>'
            f'<li>{ui("store")}<div><b>Retrait gratuit</b><span>Dans nos 3 magasins, prêt en 1 h</span></div></li>'
            f'<li>{ui("return")}<div><b>Retours sous 30 jours</b><span>En magasin, avec le ticket</span></div></li>'
            f'<li>{ui("shield")}<div><b>Garantie 2 ans</b><span>5 ans sur les cadres de vélo</span></div></li>'
            f'<li>{ui("card")}<div><b>Paiement sécurisé</b><span>Carte bancaire et chèque-cadeau</span></div></li>'
            '</ul></section>'
            '<footer class="foot"><div class="in cols">' + c +
            '<div><h3>Service client</h3><p class="tel">0 800 FLOP FLOP</p>'
            '<p style="margin:0">Du lundi au vendredi, de 9 h à 18 h. Service et appel gratuits.</p>'
            '<div class="pay"><span>CB</span><span>VISA</span><span>Mastercard</span><span>PayPal</span>'
            '<span>Chèque-cadeau</span></div></div></div>'
            '<div class="legal"><div class="in"><span>© 2026 DécaFlop SAS</span>'
            '<nav aria-label="Informations légales">'
            '<a href="/informations-legales#mentions">Mentions légales</a>'
            '<a href="/informations-legales#cgv">Conditions générales de vente</a>'
            '<a href="/informations-legales#cookies">Cookies</a>'
            '<a href="/informations-legales#accessibilite">Accessibilité partiellement conforme</a>'
            '</nav></div></div></footer>')


def layout(title, body, current="", notice=""):
    sub = "".join(f'<li><a href="{h}"{CUR if h == current else ""}>{label}</a></li>' for h, label in SUBNAV)
    deal_cur = CUR if current == "/destockage" else ""
    sub += f'<li><a class="deal" href="/destockage"{deal_cur}>Déstockage</a></li>'
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><link rel="stylesheet" href="/static/decaflop.css"></head><body>
<a class="skip" href="#main">Aller au contenu</a>
<div class="promo"><div class="in"><span>Retrait gratuit en magasin en 1 h</span><span>Retours sous 30 jours</span>
<span>Garantie 2 ans sur tout le matériel</span><span>Finale régionale de triathlon dimanche.
<a href="/triathlon">Voir le programme</a></span></div></div>
<header class="hd"><div class="in">
{mega_menu()}
<a class="mark" href="/">DÉCA<i>FLOP</i><small>sport pour (presque) tous</small></a>
<form class="search" action="/" role="search">{ui("search", 20)}<input name="q" aria-label="Rechercher"
 placeholder="Rechercher un produit, un sport, une marque"><button type="submit">Rechercher</button></form>
<nav class="acct" aria-label="Mon espace">
<a href="/magasins">{ui("pin")}<span class="lbl">Magasins</span></a>
<a href="/compte">{ui("user")}<span class="lbl">Mon compte</span></a>
<a href="/panier">{ui("bag")}<span class="count">0</span><span class="lbl">Panier</span></a>
</nav></div></header>
<nav class="subnav" aria-label="Rayons"><ul>{sub}</ul></nav>
{notice}
<main id="main">{body}</main>
{footer()}
</body></html>"""


# --------------------------------------------------------------------------
# Press / news media. The poster (02) and the race photo (03) are built into
# handouts/dist and mounted read-only at HANDOUT_DIR (see docker-compose). Only
# these two files are ever served, byte-for-byte. The stego trailer and the
# EXIF must survive, so nothing here re-encodes or resizes them.
# --------------------------------------------------------------------------
HANDOUT_DIR = os.environ.get("HANDOUT_DIR", "/handouts")
MEDIA = {"decaflop_poster.png", "transition_shot.jpg"}


def media_available(name):
    return os.path.isfile(os.path.join(HANDOUT_DIR, name))


# Actualités: three short posts, newest first. The race-eve post shows a photo
# the event crew shared and links its full-size original. Like on many event
# sites, nothing strips the metadata.
NEWS = [
    {"slug": "parc-a-velos-pret", "date": "1 novembre 2026",
     "title": "Le parc à vélos est prêt pour la finale", "photo": True,
     "lede": "À la veille de la finale, la zone de transition a pris ses quartiers au "
             "bord de la plage. Tout est en place pour le grand jour.",
     "body": [
        "Les barrières aux couleurs de DécaFlop sont montées, les râteliers alignés et "
        "numérotés : demain matin, chaque finaliste y déposera son vélo avant le départ "
        "de la natation.",
        "Nos équipes ont passé la journée sur place pour que la transition se fasse sans "
        "accroc. Un stand de réparation DécaFlop restera ouvert tout le week-end, à deux "
        "pas du parc à vélos.",
        "Rendez-vous demain dès 7 h pour l'ouverture du parc. Et d'ici là, partagez "
        "l'affiche de la finale autour de vous !",
     ]},
    {"slug": "navettes-spectateurs", "date": "30 octobre 2026",
     "title": "Des navettes gratuites pour les spectateurs", "photo": False,
     "lede": "Pour venir encourager les finalistes sans galérer à se garer, des navettes "
             "relient le centre-ville au stade tout le week-end.",
     "body": [
        "Les navettes partent du centre-ville toutes les 15 minutes, de 6 h 30 à 17 h, et "
        "déposent les spectateurs à l'entrée du village partenaires.",
        "Un parking vélo surveillé est installé près du stade pour celles et ceux qui "
        "préfèrent venir sur deux roues. L'accès au site reste gratuit.",
        "Besoin d'un dernier accessoire avant la course ? Nos trois magasins sont ouverts "
        "tout le week-end.",
     ]},
    {"slug": "magasins-ouverts-week-end", "date": "27 octobre 2026",
     "title": "Nos trois magasins ouverts tout le week-end", "photo": False,
     "lede": "Combinaison qui fuit, lacet cassé, bidon oublié. Nos magasins restent "
             "ouverts pour parer aux imprévus d'avant-course.",
     "body": [
        "Les magasins DécaFlop Stade, Centre-ville et Déstockage gardent leurs portes "
        "ouvertes tout le week-end de la finale, avec des horaires élargis.",
        "L'atelier vélo du magasin Stade assure les réglages de dernière minute et la "
        "location de vélos de chrono, casque inclus, sur présentation d'une pièce "
        "d'identité.",
        "Un conseil d'avant-course ? Nos vendeurs, souvent pratiquants eux-mêmes, sont "
        "là pour ça.",
     ]},
]
NEWS_BY_SLUG = {p["slug"]: p for p in NEWS}


# --------------------------------------------------------------------------
# Home
# --------------------------------------------------------------------------
SEARCH_NOTICE = ('<div class="in notice-wrap"><p class="notice" role="status">La recherche en ligne est '
                 'indisponible pendant la compétition. Nos vendeurs vous renseignent en magasin.</p></div>')

SCHEDULE = [("7 h 00", "Ouverture du parc à vélos", "Transition"), ("8 h 30", "Départ finale femmes", "Plage"),
            ("10 h 30", "Départ finale hommes", "Plage"), ("15 h 00", "Podium", "Grand chapiteau")]


def news_card(p):
    return (f'<a class="news" href="/actualites/{p["slug"]}"><span class="date">{p["date"]}</span>'
            f'<b>{p["title"]}</b><p>{p["lede"]}</p><span class="more">Lire l\'article</span></a>')


@shop.get("/")
def home():
    notice = SEARCH_NOTICE if "q" in request.args else ""
    hero_ink = dict(ink="#ffffff", paper="#3643ba")
    sports = [("/natation", "Natation", "lunettes-natation"), ("/velo", "Vélo", "velo-chrono-race-900"),
              ("/course-a-pied", "Course à pied", "chaussures-lacage-rapide"),
              ("/triathlon", "Triathlon", "combinaison-tri-500"), ("/location", "Location", "casque-aero"),
              ("/destockage", "Déstockage", "etiquette")]
    sp = "".join(f'<li><a href="{h}"><span class="c">{packshot(art)}</span>{n}</a></li>' for h, n, art in sports)
    sched = "".join(f"<tr><td>{t}</td><td>{w}</td><td>{l}</td></tr>" for t, w, l in SCHEDULE)
    body = f"""<section class="hero"><div class="in">
 <div><span class="eyebrow">Sponsor titre du Championnat régional</span>
  <h1>Prêts pour la finale{NB}?</h1>
  <p>Combinaisons, vélos de chrono et tout le petit matériel de transition. Retrait gratuit en magasin, prêt en 1 h.</p>
  <div class="ctas"><a class="btn light" href="/triathlon#equipement">L'équipement triathlon</a>
   <a class="btn ghost" href="/triathlon">Programme de la course</a></div></div>
 <div class="art" aria-hidden="true"><span class="disc"></span>
  <span class="a1">{packshot("velo-chrono-race-900", **hero_ink)}</span>
  <span class="a2">{packshot("combinaison-tri-500", **hero_ink)}</span>
  <span class="a3">{packshot("lunettes-natation", **hero_ink)}</span></div>
</div></section>
<section class="sec"><div class="in"><div class="sec-hd"><h2>Nos sports</h2></div><ul class="sports">{sp}</ul></div></section>
<section class="sec grey"><div class="in"><div class="sec-hd"><h2>Prix bas sur l'équipement de course</h2>
 <a href="/destockage">Tout voir</a></div><div class="rail">{"".join(card(s) for s in HOME_DEALS)}</div></div></section>
<section class="sec"><div class="in"><div class="services">
 <a class="service" href="/aide#retrait">{ui("store", 40)}<div><b>Retrait en 1 h</b><span>Réservez en ligne, retirez en magasin le jour même.</span></div></a>
 <a class="service" href="/location">{ui("bike", 40)}<div><b>Location de vélos</b><span>Vélos de chrono réglés à votre taille, casque inclus.</span></div></a>
 <a class="service" href="/atelier">{ui("wrench", 40)}<div><b>Atelier vélo</b><span>Révision express avant la course, sans rendez-vous.</span></div></a>
 <a class="service" href="/destockage">{ui("tag", 40)}<div><b>Déstockage</b><span>Fins de séries et matériel de location d'occasion.</span></div></a>
</div></div></section>
<section class="sec grey"><div class="in event">
 <div><span class="kicker">Championnat régional de triathlon</span><h2>La finale, c'est dimanche</h2>
  <p>1,5 km de natation, 40 km de vélo et 10 km de course à pied. DécaFlop est sponsor titre de l'édition 2026
   et tient un stand de réparation au parc à vélos.</p>
  <a class="btn" href="/triathlon">Le championnat</a></div>
 <div class="sched"><table>{sched}</table></div>
</div></section>
<section class="sec"><div class="in"><div class="sec-hd"><h2>Pour le jour de la course</h2>
 <a href="/course-a-pied">Tout le rayon course à pied</a></div>
 <div class="grid">{"".join(card(s) for s in RACE_DAY)}</div></div></section>
<section class="sec grey"><div class="in"><div class="sec-hd"><h2>Actualités</h2>
 <a href="/actualites">Toutes les actualités</a></div>
 <div class="news-list">{"".join(news_card(p) for p in NEWS)}</div></div></section>"""
    return html(layout("DécaFlop, sponsor du Championnat régional de triathlon", fr(body), notice=notice))


# --------------------------------------------------------------------------
# Category pages (filters and sort are links; values are whitelisted)
# --------------------------------------------------------------------------
PRICE_BANDS = {"moins-20": ("Moins de 20 €", lambda v: v < 20),
               "20-100": ("De 20 à 100 €", lambda v: 20 <= v <= 100),
               "plus-100": ("Plus de 100 €", lambda v: v > 100)}
NOTES = {"4": ("4 étoiles et plus", 4.0), "3": ("3 étoiles et plus", 3.0)}
SORTS = {"pertinence": "Pertinence", "prix-croissant": "Prix croissant", "prix-decroissant": "Prix décroissant",
         "note": "Meilleures notes"}


def read_filters():
    a = request.args
    return {"marque": a.get("marque") if a.get("marque") in BRANDS else None,
            "prix": a.get("prix") if a.get("prix") in PRICE_BANDS else None,
            "note": a.get("note") if a.get("note") in NOTES else None,
            "tri": a.get("tri") if a.get("tri") in SORTS else "pertinence"}


def matches(slug, f, skip=None):
    p = PRODUCTS[slug]
    if f["marque"] and skip != "marque" and BRAND_SLUG[p["brand"]] != f["marque"]:
        return False
    if f["prix"] and skip != "prix" and not PRICE_BANDS[f["prix"]][1](num(p["price"])):
        return False
    if f["note"] and skip != "note" and p["rating"] < NOTES[f["note"]][1]:
        return False
    return True


def sort_slugs(slugs, tri):
    if tri == "prix-croissant":
        return sorted(slugs, key=lambda s: num(PRODUCTS[s]["price"]))
    if tri == "prix-decroissant":
        return sorted(slugs, key=lambda s: -num(PRODUCTS[s]["price"]))
    if tri == "note":
        return sorted(slugs, key=lambda s: -PRODUCTS[s]["rating"])
    return list(slugs)


def link(path, f, **changes):
    g = dict(f)
    g.update(changes)
    params = [(k, g[k]) for k in ("marque", "prix", "note", "tri") if g.get(k) and not (k == "tri" and
                                                                                       g[k] == "pertinence")]
    return escape(path + ("?" + urlencode(params) if params else ""))


def facets(path, slugs, f):
    def block(title, key, options):
        lis = []
        for value, label in options:
            n = sum(1 for s in slugs if matches(s, {**f, key: value}))
            on = f[key] == value
            if not n and not on:
                lis.append(f'<li><span class="dim"><span>{label}</span><small>0</small></span></li>')
                continue
            href = link(path, f, **{key: None if on else value})
            cur = ON if on else ""
            lis.append(f'<li><a href="{href}"{cur}><span>{label}</span><small>{n}</small></a></li>')
        return f'<div class="facet"><h3>{title}</h3><ul>{"".join(lis)}</ul></div>'
    brands = sorted({BRAND_SLUG[PRODUCTS[s]["brand"]] for s in slugs}, key=lambda b: BRANDS[b])
    return (block("Marque", "marque", [(b, BRANDS[b]) for b in brands]) +
            block("Prix", "prix", [(k, v[0]) for k, v in PRICE_BANDS.items()]) +
            block("Note des clients", "note", [(k, v[0]) for k, v in NOTES.items()]))


def listing(title, intro, slugs, path, current):
    f = read_filters()
    shown = sort_slugs([s for s in slugs if matches(s, f)], f["tri"])
    count = f"{len(shown)} produit{'s' if len(shown) > 1 else ''}"
    sort = "".join(f'<a href="{link(path, f, tri=k)}"{ON if f["tri"] == k else ""}>{v}</a>' for k, v in SORTS.items())
    chips = []
    if f["marque"]:
        chips.append(f'<a href="{link(path, f, marque=None)}">{BRANDS[f["marque"]]}</a>')
    if f["prix"]:
        chips.append(f'<a href="{link(path, f, prix=None)}">{PRICE_BANDS[f["prix"]][0]}</a>')
    if f["note"]:
        chips.append(f'<a href="{link(path, f, note=None)}">{NOTES[f["note"]][0]}</a>')
    if chips:
        chips.append(f'<a class="clear" href="{link(path, f, marque=None, prix=None, note=None)}">Tout effacer</a>')
    chips_html = f'<div class="chips">{"".join(chips)}</div>' if chips else ""
    fac = facets(path, slugs, f)
    grid = (f'<div class="grid three">{"".join(card(s) for s in shown)}</div>' if shown else
            '<p class="empty">Aucun produit ne correspond à ces filtres.</p>')
    active = sum(1 for k in ("marque", "prix", "note") if f[k])
    body = f"""<div class="in">
{crumbs(("/", "Accueil"), (None, title))}
<div class="plp-hd"><h1>{title}</h1><p>{intro}</p></div>
<div class="plp"><aside class="filters" aria-label="Filtres"><h2>Filtrer</h2>{fac}</aside>
<div><details class="mfilters"><summary>Filtrer{f" ({active})" if active else ""}</summary><div class="filters">{fac}</div></details>
 <div class="toolbar"><span class="count">{count}</span><div class="sort"><span>Trier par</span>{sort}</div></div>
 {chips_html}{grid}</div></div>
</div>"""
    return html(layout(f"{title} - DécaFlop", fr(body), current=current))


@shop.get("/<any(natation, velo, 'course-a-pied'):cat>")
def category(cat):
    name, intro = CATEGORIES[cat]
    slugs = [s for s, p in PRODUCTS.items() if p["cat"] == cat]
    return listing(name, intro, slugs, f"/{cat}", f"/{cat}")


@shop.get("/destockage")
def clearance():
    slugs = [s for s, p in PRODUCTS.items() if p["was"] or p["badge"] in ("last", "low")]
    return listing("Déstockage", "Prix barrés, fins de séries et derniers stocks, dans la limite des quantités "
                   "disponibles.", slugs, "/destockage", "/destockage")


# --------------------------------------------------------------------------
# Product page
# --------------------------------------------------------------------------
NA = ' class="na"'
VIEWS = [None, (70, 70, 260, 260), (40, 150, 200, 200), (160, 150, 200, 200)]


def distribution(r, n):
    # Skewed toward 5 stars with a small 1-star tail, like real review counts.
    w = {k: 2.71828 ** (-((k - (r + 0.4)) ** 2) / 1.4) + (0.03 if k == 1 else 0) for k in range(1, 6)}
    tot = sum(w.values())
    counts = {k: int(n * v / tot) for k, v in w.items()}
    counts[max(w, key=w.get)] += n - sum(counts.values())
    return counts


@shop.get("/produit/<slug>")
def product(slug):
    if slug not in PRODUCTS:
        abort(404)
    p = PRODUCTS[slug]
    cat_name = CATEGORIES[p["cat"]][0]
    st = stock(slug)
    pickup = next((STORES[i][1] for i, (k, _t) in enumerate(st) if k == "ok"), STORES[0][1])
    # gallery: CSS-only view switcher (radio + label), no script
    radios = "".join(f'<input class="sr" type="radio" name="vue" id="vue{i}"{" checked" if i == 0 else ""}>'
                     for i in range(len(VIEWS)))
    thumbs = "".join(f'<label for="vue{i}" title="Vue {i + 1}">{packshot(slug, crop=c)}</label>'
                     for i, c in enumerate(VIEWS))
    views = "".join(f'<div class="view v{i}">{packshot(slug, crop=c, label=p["title"] if i == 0 else "")}</div>'
                    for i, c in enumerate(VIEWS))
    if p["sizes"] == TU:
        sizes = '<p class="tu">Taille unique</p>'
    else:
        sizes = '<div class="opts">' + "".join(
            f'<label{NA if s in p["na"] else ""}><input type="radio" name="taille" '
            f'value="{s}"{" disabled" if s in p["na"] else ""}><span class="sz">{s}</span></label>'
            for s in p["sizes"]) + '</div>'
    guide = '<a href="/aide#tailles">Guide des tailles</a>' if p["sizes"] != TU else ""
    colors = "".join(f'<label title="{n}"><input type="radio" name="coloris"{" checked" if i == 0 else ""}>'
                     f'<span class="sw"><i style="--c:{c}"></i></span><span class="sr">{n}</span></label>'
                     for i, (n, c) in enumerate(p["colors"]))
    points = "".join(f"<li><b>{t}</b><span>{d}</span></li>" for t, d in p["points"])
    specs = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in p["specs"])
    dist = distribution(p["rating"], p["reviews"])
    bars = "".join(f'<li><span>{k} étoile{"s" if k > 1 else ""}</span><span class="bar"><i style="--w:'
                   f'{dist[k] / p["reviews"] * 100:.0f}%"></i></span><span>{dist[k]}</span></li>'
                   for k in range(5, 0, -1))
    revs = "".join(f'<article class="review">{stars(s, plain=True)}<h3>{t}</h3><p>{txt}</p>'
                   f'<p class="by"><span>{who}, le {d}</span><span>{use}</span><span class="ver">Acheteur vérifié</span></p></article>'
                   for s, t, txt, who, d, use in p["revs"])
    q, a = p["qa"]
    stock_list = "".join(f'<li><span>{STORES[i][1]}</span><span class="st {k}">{t}</span></li>'
                         for i, (k, t) in enumerate(st))
    related = [s for s, x in PRODUCTS.items() if x["cat"] == p["cat"] and s != slug][:4]
    rc = f"{p['reviews']:,}".replace(",", NB)
    body = f"""<div class="in">
{crumbs(("/", "Accueil"), (f"/{p['cat']}", cat_name), (None, KIND[slug]))}
<div class="pdp">
 <div class="gallery">{radios}<div class="thumbs">{thumbs}</div><div class="main-ph">{views}{badge(p)}</div></div>
 <div class="buy">
  <span class="brand"><a href="/{p['cat']}?marque={BRAND_SLUG[p['brand']]}">{p["brand"]}</a></span>
  <h1>{p["title"]}</h1>
  <div class="meta">{stars(p["rating"])}<a href="#avis">{rc} avis</a><span>Réf. {p["ref"].replace(" ", NB)}</span></div>
  {price_block(p)}<p class="vat">Prix TTC, éco-participation incluse.</p>
  <fieldset class="opt"><legend>Coloris <span>{len(p["colors"])} au choix</span></legend><div class="opts">{colors}</div></fieldset>
  <fieldset class="opt"><legend>Taille {guide}</legend>{sizes}</fieldset>
  <div class="hold"><b>Vente en ligne suspendue pendant la compétition.</b> Réservez l'article dans l'un de nos
   magasins, il vous attend à l'accueil.</div>
  <div class="cta"><span class="btn wide off" aria-disabled="true">Ajouter au panier</span>
   <a class="btn wide line" href="#magasins">Réserver en magasin</a></div>
  <div class="deliv">
   <div>{ui("store")}<p><b>Retrait en magasin</b><span>Gratuit. </span><span class="ok">Disponible aujourd'hui à {pickup}</span></p></div>
   <div>{ui("truck")}<p><b>Livraison à domicile</b><span>Reprend le lundi 9 novembre</span></p></div>
  </div>
  <ul class="trust"><li>{ui("return")}Retours sous 30 jours</li><li>{ui("shield")}Garantie 2 ans</li><li>{ui("card")}Paiement sécurisé</li></ul>
 </div>
</div></div>
<nav class="tabs" aria-label="Sections de la fiche"><div class="in"><ul>
 <li><a href="#points-forts">Points forts</a></li><li><a href="#caracteristiques">Caractéristiques</a></li>
 <li><a href="#avis">Avis ({rc})</a></li><li><a href="#questions">Questions</a></li>
 <li><a href="#magasins">Disponibilité</a></li></ul></div></nav>
<div class="in">
<section class="pd-sec" id="points-forts"><h2>Points forts</h2><p class="desc">{p["desc"]}</p><ul class="highlights">{points}</ul></section>
<section class="pd-sec" id="caracteristiques"><h2>Caractéristiques</h2><table class="specs"><tbody>
 <tr><th>Marque</th><td>{p["brand"]}</td></tr><tr><th>Référence</th><td>{p["ref"].replace(" ", NB)}</td></tr>{specs}</tbody></table></section>
<section class="pd-sec" id="avis"><h2>Avis clients</h2><div class="reviews">
 <div><div class="avg">{rating_txt(p["rating"])}<small>/5</small></div>{stars(p["rating"], plain=True)}
  <p class="small mute">{rc} avis publiés sur les trois dernières années</p><ul class="dist">{bars}</ul></div>
 <div>{revs}</div></div></section>
<section class="pd-sec" id="questions"><h2>Questions et réponses</h2><dl class="qa"><dt>{q}</dt>
 <dd>{a}<small>Réponse de l'équipe DécaFlop</small></dd></dl></section>
<section class="pd-sec" id="magasins"><h2>Disponibilité en magasin</h2><ul class="stock">{stock_list}</ul>
 <p class="small mute" style="margin-top:10px">Stock indicatif, mis à jour toutes les heures. <a href="/magasins">Horaires et adresses</a></p></section>
</div>
<section class="sec grey"><div class="in"><div class="sec-hd"><h2>Les clients ont aussi consulté</h2>
 <a href="/{p['cat']}">Tout le rayon {cat_name.lower()}</a></div>
 <div class="grid">{"".join(card(s) for s in related)}</div></div></section>"""
    return html(layout(f"{p['title']} - DécaFlop", fr(body), current=f"/{p['cat']}"))


# --------------------------------------------------------------------------
# Championship, stores, help, services
# --------------------------------------------------------------------------
@shop.get("/triathlon")
def championship():
    legs = "".join(
        f'<div class="panel"><div class="leg-art">{packshot(art)}</div><h2>{name}<span class="dist-tag">{dist}</span></h2>'
        f'<p>{text}</p></div>'
        for art, name, dist, text in [
            ("lunettes-natation", "Natation", "1,5 km", "Départ en vagues depuis la plage, deux boucles balisées par des bouées jaunes."),
            ("velo-chrono-race-900", "Vélo", "40 km", "Quatre tours d'un circuit fermé à la circulation. Aspiration-abri interdite."),
            ("chaussures-lacage-rapide", "Course à pied", "10 km", "Trois boucles le long du port, arrivée devant le grand chapiteau."),
        ])
    prog = "".join(f"<tr><td>{t}</td><td>{w}</td></tr>" for t, w in [
        ("6 h 30", "Retrait des dossards et des puces"), ("7 h 00", "Ouverture du parc à vélos"),
        ("8 h 15", "Briefing des athlètes"), ("8 h 30", "Départ finale femmes"), ("10 h 30", "Départ finale hommes"),
        ("13 h 30", "Fermeture du parc à vélos"), ("15 h 00", "Podium et remise des prix")])
    body = f"""{page_head("Championnat régional de triathlon", "Deux finales, trois disciplines et un seul parc à vélos. DécaFlop est fier d'être sponsor titre de l'édition 2026.")}
<section class="sec"><div class="in"><div class="sec-hd"><h2>Le format, distance olympique</h2></div>
 <div class="cols3 legs">{legs}</div></div></section>
<section class="sec grey"><div class="in cols2">
 <div class="panel"><h2>Programme complet</h2><table class="std"><tbody>{prog}</tbody></table></div>
 <div class="panel"><h2>Règlement en bref</h2><ul class="ticks">
  <li>Puce de chronométrage obligatoire, portée à la cheville gauche.</li>
  <li>Casque attaché avant de toucher le vélo et jusqu'à l'avoir reposé.</li>
  <li>Aspiration-abri interdite sur la partie vélo, sous peine d'une minute de pénalité.</li>
  <li>Combinaison autorisée si l'eau est sous 22 °C.</li></ul>
  <p class="small mute" style="margin-top:12px">Les résultats officiels seront publiés ici après la course.</p></div>
</div></section>
<section class="sec" id="equipement"><div class="in"><div class="sec-hd"><h2>L'équipement de la finale</h2>
 <a href="/natation">Voir les rayons</a></div><div class="grid">{"".join(card(s) for s in FINAL_KIT[:4])}</div></div></section>
<section class="sec grey"><div class="in"><div class="sec-hd"><h2>Venir en spectateur</h2></div><div class="cols2">
 <div class="panel"><h2>Accès</h2><p>Navettes gratuites depuis le centre-ville toutes les 15 minutes. Parking vélo
  surveillé près du stade.</p></div>
 <div class="panel"><h2>Sur place</h2><p>Écran géant au grand chapiteau, village partenaires et stand de réparation
  DécaFlop ouvert toute la journée.</p></div></div>
 <p class="small mute" style="margin:16px 0 0">Médias et supporters, l'affiche officielle de la finale est à
  télécharger dans notre <a href="/presse">espace presse</a>.</p>
</div></section>"""
    return html(layout("Le championnat - DécaFlop", fr(body), current="/triathlon"))


@shop.get("/magasins")
def stores():
    cards = "".join(
        f'<div class="store-card" id="{key}"><h2>{name}</h2><span class="open">Ouvert tout le week-end de la finale</span>'
        f'<p class="li">{ui("pin", 20)}<span>{addr}</span></p>'
        f'<table class="hours"><tbody>{"".join(f"<tr><th>{d}</th><td>{h}</td></tr>" for d, h in hours)}</tbody></table>'
        f'<ul class="tags">{"".join(f"<li>{s}</li>" for s in services)}</ul></div>'
        for key, name, addr, hours, services in STORES)
    body = f"""{page_head("Nos magasins", "Trois magasins autour du stade, tous ouverts pendant le week-end de course avec des horaires élargis.")}
<section class="sec"><div class="in"><div class="cols3">{cards}</div>
<p class="small mute" style="margin-top:18px">Service client au 0 800 FLOP FLOP, du lundi au vendredi de 9 h à 18 h.</p></div></section>"""
    return html(layout("Magasins - DécaFlop", fr(body), current="/magasins"))


FAQ = [
    ("commande", "Où en est ma commande ?",
     "Les commandes passées avant la compétition sont livrées en magasin. Vous recevez un SMS dès qu'elles "
     "sont prêtes, avec votre numéro de retrait."),
    ("retrait", "Comment fonctionne le retrait en magasin ?",
     "Réservez l'article en magasin ou par téléphone, il est mis de côté à l'accueil pendant 48 h. Le retrait "
     "est gratuit dans nos trois magasins."),
    ("retours", "Comment retourner un article ?",
     "Rapportez-le dans n'importe quel magasin sous 30 jours avec votre ticket. Les articles portés pendant une "
     "course ne sont pas repris."),
    ("garantie", "Que couvre la garantie ?",
     "Deux ans sur tout le matériel et cinq ans sur les cadres de vélo. L'usure normale des pneus, plaquettes "
     "et lacets n'est pas couverte."),
    ("location", "Puis-je louer un vélo pour la course ?",
     "Oui, au magasin Stade, sur présentation d'une pièce d'identité. Le vélo est réglé à votre taille et le "
     "casque est inclus."),
]
SIZE_WETSUIT = [("XS", "160 à 168 cm", "55 à 62 kg"), ("S", "166 à 174 cm", "60 à 68 kg"),
                ("M", "172 à 180 cm", "67 à 76 kg"), ("L", "178 à 186 cm", "75 à 85 kg"),
                ("XL", "184 à 192 cm", "84 à 95 kg"), ("XXL", "190 à 198 cm", "94 à 105 kg")]
SIZE_SHOES = [("39", "24,6 cm"), ("40", "25,2 cm"), ("41", "25,9 cm"), ("42", "26,5 cm"), ("43", "27,2 cm"),
              ("44", "27,8 cm"), ("45", "28,5 cm"), ("46", "29,1 cm")]


@shop.get("/aide")
def help_page():
    items = "".join(f'<details class="faq" id="{k}"><summary>{q}</summary><p>{a}</p></details>' for k, q, a in FAQ)
    wet = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in SIZE_WETSUIT)
    shoes = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in SIZE_SHOES)
    body = f"""{page_head("Aide et contact", "Les réponses aux questions les plus fréquentes, le guide des tailles et nos contacts.")}
<section class="sec"><div class="in cols2"><div>{items}</div>
 <div class="panel" id="contact"><h2>Nous contacter</h2><p class="tel-dark">0 800 FLOP FLOP</p>
  <p>Du lundi au vendredi, de 9 h à 18 h. Service et appel gratuits.</p>
  <a class="btn" href="/magasins">Trouver un magasin</a></div>
</div></section>
<section class="sec grey" id="tailles"><div class="in"><div class="sec-hd"><h2>Guide des tailles</h2></div><div class="cols2">
 <div class="panel"><h2>Combinaisons néoprène</h2><table class="std"><thead><tr><th>Taille</th><th>Hauteur</th><th>Poids</th></tr></thead>
  <tbody>{wet}</tbody></table></div>
 <div class="panel"><h2>Chaussures de running</h2><table class="std"><thead><tr><th>Pointure</th><th>Longueur du pied</th></tr></thead>
  <tbody>{shoes}</tbody></table><p class="small mute" style="margin-top:10px">Mesurez votre pied le soir, en appui, talon contre un mur.</p></div>
</div></div></section>"""
    return html(layout("Aide - DécaFlop", fr(body)))


@shop.get("/location")
def rental():
    rows = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in [
        ("Vélo de chrono Race 900", "35 €", "60 €"), ("Vélo de route aluminium", "25 €", "40 €"),
        ("Paire de roues aéro", "20 €", "35 €"), ("Combinaison néoprène", "15 €", "25 €")])
    body = f"""{page_head("Location de vélos", "Louez votre vélo de chrono ou votre combinaison pour la finale. Le matériel est révisé, réglé à votre taille et prêt à rouler.")}
<section class="sec"><div class="in cols2">
 <div class="panel"><h2>Tarifs</h2><table class="std"><thead><tr><th>Matériel</th><th>1 jour</th><th>Week-end</th></tr></thead>
  <tbody>{rows}</tbody></table><p class="small mute" style="margin-top:10px">Casque inclus avec chaque vélo. Caution par empreinte bancaire.</p></div>
 <div class="panel"><h2>Comment ça marche</h2><ul class="ticks">
  <li>Réservation au magasin DécaFlop Stade ou par téléphone.</li>
  <li>Retrait la veille de la course à partir de 14 h, avec une pièce d'identité.</li>
  <li>Réglage de la selle et des prolongateurs sur place par l'atelier.</li>
  <li>Retour le dimanche avant 18 h au stand DécaFlop du parc à vélos.</li></ul>
  <p style="margin-top:14px"><a class="btn" href="/magasins#stade">Voir le magasin Stade</a></p></div>
</div></section>"""
    return html(layout("Location de vélos - DécaFlop", fr(body), current="/location"))


@shop.get("/atelier")
def workshop():
    rows = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in [
        ("Révision express avant course", "19 €"), ("Réglage des dérailleurs", "12 €"),
        ("Réglage des freins", "10 €"), ("Remplacement d'un pneu, hors pièce", "8 €"),
        ("Montage de prolongateurs", "15 €"), ("Étude de position simplifiée", "39 €")])
    body = f"""{page_head("Atelier vélo", "Nos mécaniciens préparent votre vélo pour la course, sans rendez-vous, au magasin Stade et au stand du parc à vélos.")}
<section class="sec"><div class="in cols2">
 <div class="panel"><h2>Prestations</h2><table class="std"><thead><tr><th>Prestation</th><th>Prix</th></tr></thead>
  <tbody>{rows}</tbody></table></div>
 <div class="panel"><h2>Le week-end de la finale</h2><p>L'atelier du magasin Stade est ouvert samedi de 9 h à 20 h.
  Dimanche, un stand de réparation est installé à côté du parc à vélos de 6 h 30 à 15 h.</p>
  <p>Les réparations de moins de 15 minutes sont faites pendant que vous attendez.</p>
  <a class="btn" href="/magasins#stade">Voir le magasin Stade</a></div>
</div></section>"""
    return html(layout("Atelier vélo - DécaFlop", fr(body), current="/atelier"))


@shop.get("/recrutement")
def careers():
    values = "".join(f'<div class="panel"><h2>{t}</h2><p>{d}</p></div>' for t, d in [
        ("Sport", "Une heure de sport par semaine sur votre temps de travail, et du matériel prêté pour essayer."),
        ("Proximité", "Des conseils de pratiquant à pratiquant, en magasin comme au bord de la course."),
        ("Responsabilité", "Chaque vendeur gère son rayon, de la commande à la mise en avant."),
    ])
    jobs = "".join(f'<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td></tr>' for a, b, c in [
        ("Vendeur sports nautiques", "DécaFlop Centre-ville", "CDI, temps plein"),
        ("Technicien atelier cycle", "DécaFlop Stade", "CDI, temps plein"),
        ("Préparateur de commandes", "DécaFlop Déstockage", "CDD de 6 mois")])
    body = f"""{page_head("Rejoignez nos équipes", "Vendeurs, mécaniciens, préparateurs. Nous recrutons des sportifs qui aiment conseiller.")}
<section class="sec"><div class="in"><div class="sec-hd"><h2>Nos valeurs</h2></div><div class="cols3">{values}</div></div></section>
<section class="sec grey"><div class="in"><div class="sec-hd"><h2>Offres d'emploi</h2></div>
 <div class="panel"><table class="std"><thead><tr><th>Poste</th><th>Magasin</th><th>Contrat</th></tr></thead><tbody>{jobs}</tbody></table>
 <p class="small mute" style="margin-top:12px">Déposez votre CV à l'accueil du magasin concerné.</p></div></div></section>"""
    return html(layout("Recrutement - DécaFlop", fr(body)))


@shop.get("/compte")
def account():
    body = f"""{page_head("Mon compte")}
<section class="sec"><div class="in"><div class="panel narrow"><h2>Espace client indisponible</h2>
 <p>L'espace client est fermé pendant la compétition. Vos commandes et vos factures restent consultables en
  magasin, sur présentation d'une pièce d'identité.</p>
 <div class="btns"><a class="btn" href="/magasins">Trouver un magasin</a><a class="btn line" href="/aide#commande">Suivi de commande</a></div>
</div></div></section>"""
    return html(layout("Mon compte - DécaFlop", fr(body)))


@shop.get("/panier")
def cart():
    body = f"""{page_head("Mon panier")}
<section class="sec"><div class="in"><div class="panel narrow"><h2>Votre panier est vide</h2>
 <p>La vente en ligne est suspendue pendant la compétition. Réservez vos articles en magasin, ils vous attendent
  à l'accueil.</p>
 <div class="btns"><a class="btn" href="/">Continuer mes achats</a><a class="btn line" href="/magasins">Nos magasins</a></div>
</div></div></section>"""
    return html(layout("Mon panier - DécaFlop", fr(body)))


@shop.get("/informations-legales")
def legal():
    body = f"""{page_head("Informations légales")}
<section class="sec"><div class="in legal-text">
 <h2 id="mentions">Mentions légales</h2>
 <p>Le site est édité par DécaFlop SAS, société par actions simplifiée dont le siège est situé 2 allée du Stade.
  Directeur de la publication, le président de DécaFlop SAS. Contact par le service client au 0 800 FLOP FLOP.</p>
 <h2 id="cgv">Conditions générales de vente</h2>
 <p>Pendant la compétition, la vente en ligne est suspendue. Les articles réservés sont payés et retirés en
  magasin. Les prix affichés sont en euros, toutes taxes comprises. Les retours sont acceptés sous 30 jours avec
  le ticket de caisse, dans n'importe lequel de nos magasins.</p>
 <h2 id="cookies">Cookies</h2>
 <p>Ce site n'utilise que des cookies techniques nécessaires à son fonctionnement. Aucun cookie publicitaire ni de
  mesure d'audience n'est déposé.</p>
 <h2 id="accessibilite">Accessibilité</h2>
 <p>Le site est partiellement conforme au référentiel général d'amélioration de l'accessibilité. Un audit
  complet est prévu en 2027. Pour signaler un problème, contactez le service client.</p>
</div></section>"""
    return html(layout("Informations légales - DécaFlop", fr(body)))


# --------------------------------------------------------------------------
# Press and news
# --------------------------------------------------------------------------
@shop.get("/medias/<name>")
def media(name):
    # Serve ONLY the two press/news files, exactly as built (no re-encoding, so
    # the appended ZIP and the EXIF survive). Anything else, a traversal attempt
    # or a file that isn't built yet falls through to the French 404.
    if name not in MEDIA or not media_available(name):
        abort(404)
    return send_from_directory(HANDOUT_DIR, name)


@shop.get("/presse")
def press():
    if media_available("decaflop_poster.png"):
        art = ('<img class="poster" src="/medias/decaflop_poster.png" '
               'alt="Affiche officielle du Championnat régional de triathlon 2026">')
        dl = ('<a class="btn" href="/medias/decaflop_poster.png" download>'
              "Télécharger l'affiche (PNG)</a>")
    else:
        art = ('<div class="poster missing" role="img" '
               'aria-label="Affiche officielle (bientôt disponible)">'
               "<span>Affiche officielle<br>bientôt disponible</span></div>")
        dl = ('<span class="btn off" aria-disabled="true">'
              "Affiche bientôt disponible</span>")
    body = f"""{page_head("Espace presse", "L'affiche officielle du Championnat régional de triathlon 2026, à partager sans modération.")}
<section class="sec"><div class="in press">
 <div class="press-art">{art}</div>
 <div class="press-txt">
  <h2>Affiche officielle</h2>
  <p>Notre affiche de la finale est libre de partage. Imprimez-la, affichez-la,
     postez-la. Partagez-la partout !</p>
  {dl}
  <p class="small mute" style="margin:14px 0 0">Format PNG, prête à imprimer.</p>
  <div class="panel" style="margin-top:22px">
   <h2>Contact presse</h2>
   <p style="margin:0">Service marketing et communication DécaFlop<br>
    Poste 120, ou <a href="/aide#contact">nous contacter</a></p>
  </div>
 </div>
</div></section>"""
    return html(layout("Espace presse - DécaFlop", fr(body)))


@shop.get("/actualites")
def news_list():
    body = f"""{page_head("Actualités", "Les nouvelles de DécaFlop et du Championnat régional de triathlon.")}
<section class="sec"><div class="in"><div class="news-list">{"".join(news_card(p) for p in NEWS)}</div></div></section>"""
    return html(layout("Actualités - DécaFlop", fr(body)))


@shop.get("/actualites/<slug>")
def news_post(slug):
    p = NEWS_BY_SLUG.get(slug)
    if not p:
        abort(404)
    if p["photo"] and media_available("transition_shot.jpg"):
        figure = """<figure class="news-photo">
 <img src="/medias/transition_shot.jpg" alt="La zone de transition de la finale, en soirée">
 <figcaption>Photo : équipe DécaFlop. <a href="/medias/transition_shot.jpg">Voir l'original</a></figcaption>
</figure>"""
    elif p["photo"]:
        figure = ('<div class="news-photo missing" role="img" aria-label="Photo '
                  '(bientôt disponible)"><span>Photo bientôt disponible</span></div>')
    else:
        figure = ""
    paras = "".join(f"<p>{t}</p>" for t in p["body"])
    body = f"""<article class="in post">
 {crumbs(("/", "Accueil"), ("/actualites", "Actualités"), (None, p['title']))}
 <span class="date">{p['date']}</span>
 <h1>{p['title']}</h1>
 <p class="lede">{p['lede']}</p>
 {figure}
 {paras}
 <p class="back"><a href="/actualites">Toutes les actualités</a></p>
</article>"""
    return html(layout(f"{p['title']} - DécaFlop", fr(body)))
