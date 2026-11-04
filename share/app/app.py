#!/usr/bin/env python3
"""
Intranet DécaFlop — DécaFlop's intranet site with the internal document library.
Its own container, not a challenge: players log in with the crew account the
staff portal (challenge 01) hands out, then browse department folders to find
the evidence files instead of downloading them from the hub.

Pages: home (internal news + recent activity), Documents (the library), file
search, staff directory (annuaire), recent activity, help. The look comes from
the shared intranet chrome (intranet.py + static/intranet.css).

- Files are read from HANDOUT_DIR (docker-compose mounts handouts/dist there,
  read-only) and served byte-for-byte through an explicit path -> filename map.
  Nothing outside that map is downloadable; there is no path traversal.
- Mundane text files are generated inline as decoys; they hold no clues.
- The search is a plain, case- and accent-insensitive substring match over the
  names in that map (no database, no templates). The query is only ever shown
  html-escaped, inside the search field. Sort and filter parameters are
  whitelisted and never echoed.
"""
import csv
import hmac
import mimetypes
import io
import json
import os
import sys
import time
import unicodedata
import uuid
import zipfile
from html import escape as esc
from urllib.parse import quote, urlencode

from flask import Flask, Response, abort, redirect, request, send_from_directory, session

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # sibling intranet.py
import capture  # noqa: E402
import fab  # noqa: E402
import intranet  # noqa: E402
from intranet import icon  # noqa: E402

HANDOUT_DIR = os.environ.get("HANDOUT_DIR", "/handouts")
SHARE_USER = os.environ.get("SHARE_USER", "equipe-it")
SHARE_PASSWORD = os.environ.get("SHARE_PASSWORD", "transition2026")

app = Flask(__name__)
app.secret_key = os.environ.get("SHARE_SECRET_KEY") or os.urandom(32)
# Offline every service shares the Pi's host, and browsers ignore ports for
# cookies: under Flask's default name "session" the intranet's login and the
# scoreboard's (CTFd also uses "session") would keep replacing each other.
app.config["SESSION_COOKIE_NAME"] = "intranet_session"

PRODUCT = "Intranet DécaFlop 16.0.4351"
SITE = "Intranet DécaFlop"
LAST_LOGIN = "01/11/2026 à 22:41 depuis 10.20.0.14"


def html(page, status=200):
    return Response(page, status=status, mimetype="text/html")


def fr_size(n):
    size = float(n)
    for unit in ("o", "Ko", "Mo"):
        if size < 1024 or unit == "Mo":
            return f"{size:.0f} {unit}" if unit == "o" else (f"{size:.1f} {unit}").replace(".", ",")
        size /= 1024


def fr_dt(when, sep=" "):
    """'2026-11-01 09:12' -> '01/11/2026 09:12'."""
    d, t = when.split()
    y, m, day = d.split("-")
    return f"{day}/{m}/{y}{sep}{t}"


# --------------------------------------------------------------------------
# Content model. Each file: path (segments, last = filename), kind (icon),
# type, author, when ('YYYY-MM-DD HH:MM'), version, description, and either a
# handout 'source' (served from HANDOUT_DIR) or decoy 'text' (generated).
# --------------------------------------------------------------------------
DEPT_ORDER = ["Direction de course", "Chronométrage", "Arbitrage", "Basis SAP", "IT",
              "Logistique", "Communication"]
DEPT_DESC = {
    "Direction de course": "Organisation de la finale, réunions, dossier incident",
    "Chronométrage": "Captures et documents de la cabine de chronométrage",
    "Arbitrage": "Jury, consignes et pièces remises par les arbitres",
    "Basis SAP": "Administration du système SAP DFlop ERP (DFL)",
    "IT": "Outils, procédures et sauvegardes de l'équipe IT",
    "Logistique": "Bénévoles, matériel, plans d'accès",
    "Communication": "Presse et visuels de l'événement",
}


def ev(path, kind, typ, who, when, ver, desc=""):
    return {"path": path, "name": path[-1], "source": path[-1], "kind": kind, "type": typ,
            "who": who, "when": when, "ver": ver, "desc": desc, "decoy": False}


def decoy(path, kind, typ, who, when, ver, text, desc=""):
    return {"path": path, "name": path[-1], "source": None, "kind": kind, "type": typ,
            "who": who, "when": when, "ver": ver, "desc": desc, "decoy": True, "text": text}


def blank(path, kind, typ, who, when, ver="1.0", text="", desc=""):
    """Smoke: an office file, image or system leftover that is empty (or a few
    bytes). Not text/CSV, so it shows "Aperçu non disponible" and downloads
    as-is with its own media type."""
    return decoy(path, kind, typ, who, when, ver, text, desc)


# Kinds without a viewer of their own borrow an existing icon.
KIND_ICON = {"doc": "page", "pdf": "page", "ppt": "page", "xls": "csv", "png": "img",
             "psd": "img", "sys": "txt"}


def icon_of(f):
    return KIND_ICON.get(f["kind"], f["kind"])


_LISEZMOI = ("Dossier d'outils de l'equipe IT d'urgence.\n\n"
             "- wordlist.txt : petite liste de mots utilisee pour les tests.\n\n"
             "Merci de ne rien supprimer sans prevenir l'astreinte IT (poste 300).\n"
             "Ce dossier est partage avec toute l'equipe evenement.\n")
_PLANNING = ("Planning des benevoles - week-end de la finale\n"
             "=============================================\n\n"
             "Samedi\n"
             "  07h00-12h00  Accueil / dossards      8 benevoles\n"
             "  09h00-15h00  Ravitaillement velo     6 benevoles\n"
             "  10h00-16h00  Point d'eau course      5 benevoles\n\n"
             "Dimanche\n"
             "  06h30-13h00  Parc a velos            6 benevoles\n"
             "  08h00-17h00  Village partenaires     4 benevoles\n\n"
             "Contact logistique : poste 118. Pensez a emporter de l'eau.\n")
_NOTE_PARCOURS = ("Note parcours - rappel organisation\n"
                  "-----------------------------------\n\n"
                  "Les trois boucles course longent le port. Balisage pose la veille,\n"
                  "retire le dimanche soir. Navettes spectateurs toutes les 15 minutes\n"
                  "depuis le centre-ville.\n\n"
                  "Rien a signaler cote parcours. Document de travail, non contractuel.\n")
_CONSIGNES = ("Consignes jury - rappel\n"
              "-----------------------\n\n"
              "- Casque attache avant de toucher le velo.\n"
              "- Drafting interdit : 1 minute de penalite.\n"
              "- Combinaison autorisee si l'eau est sous 22 C.\n\n"
              "Pour toute reclamation, voir la direction de course (bureau de course).\n")
_NOTES_BASIS = ("Notes Basis - SAP DFlop ERP (DFL / mandant 001)\n"
                "===============================================\n\n"
                "Rappels pour l'equipe, a trier apres la finale :\n\n"
                "- Moniteur du gateway SAP accessible sur le reseau staff (port 8014).\n"
                "  A verifier : les ACL reginfo/secinfo sont restees sur les valeurs\n"
                "  par defaut depuis l'installation.\n"
                "- Les rapports maison (dont l'export des resultats) sont dans le\n"
                "  dossier 'Basis SAP / Developpements'. Rappel : ne pas laisser de\n"
                "  jeton en dur dans le code.\n"
                "- L'export de la table USR02 est archive dans 'Basis SAP / Exports'.\n\n"
                "Document de travail interne, sans valeur officielle. Ne pas diffuser.\n")
_CR_SECU = ("Compte rendu - reunion securite du 27/10/2026\n"
            "=============================================\n\n"
            "Presents : C. Dumont (direction de course), H. Martin, S. Lambert (arbitrage),\n"
            "E. Roux (logistique), N. Petit (DSI), poste de secours (Croix-Blanche).\n\n"
            "1. Natation : 2 bateaux + 4 kayaks. Bouee de rappel a 750 m.\n"
            "   Report possible de 30 min si brouillard sur le port.\n"
            "2. Velo : fermeture des routes 7h30-12h30, arretes prefectoraux recus.\n"
            "3. Course : 3 points d'eau, 1 poste de secours mobile.\n"
            "4. Radios : 24 postes, canal 3 pour la direction, canal 5 pour la logistique.\n"
            "5. Meteo : 14 C prevus, eau a 17 C (combinaison autorisee).\n\n"
            "Prochaine reunion : briefing general samedi 18h00, salle B.\n")
_RADIOS = ("id;modele;canal;affecte_a;etat\n"
           "R01;TK-3401;3;Direction de course;OK\n"
           "R02;TK-3401;3;Direction de course;OK\n"
           "R03;TK-3401;3;Bureau de course;OK\n"
           "R04;TK-3401;4;Arbitrage - natation;OK\n"
           "R05;TK-3401;4;Arbitrage - velo;batterie faible\n"
           "R06;TK-3401;4;Arbitrage - course;OK\n"
           "R07;TK-3401;5;Logistique - parc a velos;OK\n"
           "R08;TK-3401;5;Logistique - ravitaillement;OK\n"
           "R09;TK-3401;5;Logistique - village;antenne a remplacer\n"
           "R10;TK-3401;6;Cabine de chronometrage;OK\n"
           "R11;TK-3401;6;Poste de secours;OK\n"
           "R12;TK-3401;6;IT - astreinte;OK\n")
_POLITIQUE = ("Politique de mots de passe - rappel DSI (oct. 2026)\n"
              "==================================================\n\n"
              "- 12 caracteres minimum, dont une majuscule et un chiffre.\n"
              "- Renouvellement tous les 90 jours, pas de reutilisation des 5 derniers.\n"
              "- Un compte = une personne. Les comptes d'equipe sont temporaires et\n"
              "  desactives apres l'evenement.\n"
              "- Ne pas cocher \"memoriser\" dans les outils installes sur les portables\n"
              "  partages.\n"
              "- Verrouillez votre poste (Windows + L) des que vous le quittez.\n\n"
              "Questions : astreinte IT, poste 300.\n")
_POINTS = ("Points de chronometrage - finale 2026\n"
           "=====================================\n\n"
           "P0  Depart natation (ponton du port)           km  0,0\n"
           "P1  Sortie de l'eau / entree parc              km  1,5\n"
           "P2  Sortie T1                                  km  1,6\n"
           "P3  Velo - mi-parcours (rond-point des Iles)   km 21,6\n"
           "P4  Entree T2                                  km 41,6\n"
           "P5  Course - fin de boucle 2                   km 48,3\n"
           "P6  Arrivee (quai d'honneur)                   km 51,6\n\n"
           "Tapis poses le samedi a 16h00. Verification croisee avec les puces le\n"
           "dimanche a 6h30.\n")
_COMMUNIQUE = ("COMMUNIQUE DE PRESSE - projet v3 (ne pas diffuser avant validation)\n\n"
               "DecaFlop, partenaire titre du Championnat regional de triathlon\n\n"
               "Dimanche, 412 athletes sont attendus sur le port pour la finale du\n"
               "championnat regional. DecaFlop equipe les benevoles et tient un village\n"
               "partenaires de 8h a 17h, avec un atelier de reglage velo gratuit.\n\n"
               "Contact presse : service marketing, poste 120.\n")
_BADGES = ("Commande de badges - finale 2026\n"
           "================================\n\n"
           "Benevoles ............ 46\n"
           "Arbitres ............. 12\n"
           "Chronometrage ........  6\n"
           "Secours .............. 14\n"
           "Presse ...............  9\n"
           "Partenaires .......... 20\n"
           "IT ...................  4\n\n"
           "Livraison prevue vendredi au bureau de course. Pochettes et tours de cou\n"
           "en stock (carton 3, local logistique).\n")

_ODJ_BRIEFING = ("Briefing general - samedi 18h00, salle B\n"
                 "========================================\n\n"
                 "1. Mot de la direction de course (C. Dumont)        5 min\n"
                 "2. Securite et secours (Croix-Blanche)              10 min\n"
                 "3. Parcours et fermetures de routes (H. Martin)     10 min\n"
                 "4. Chronometrage et resultats (L. Eriksen)          5 min\n"
                 "5. Benevoles : postes et horaires (E. Roux)         10 min\n"
                 "6. Questions                                        10 min\n\n"
                 "Merci d'arriver 10 minutes avant. Badge obligatoire.\n")
_CR_PARTENAIRES = ("Compte rendu - point partenaires du 21/10/2026\n"
                   "==============================================\n\n"
                   "- DecaFlop : village de 8h a 17h, atelier velo, 400 gourdes offertes.\n"
                   "- Mairie : prete 120 barrieres et le podium du quai d'honneur.\n"
                   "- Radio locale : direct de 9h a 11h depuis l'arrivee.\n\n"
                   "A faire : valider le plan du village avant le 30/10 (logistique).\n")
_CABLAGE = ("Tapis de chronometrage - cablage\n"
            "================================\n\n"
            "Chaque tapis : 1 boitier + 1 rallonge 25 m + 1 batterie de secours.\n"
            "P0 a P2 : alimentation depuis la cabine. P3 a P6 : groupes electrogenes.\n"
            "Test de lecture des puces samedi 16h30 avec 3 puces temoin.\n\n"
            "En cas de coupure : noter les dossards a la main (feuilles dans le bac bleu).\n")
_LISEZMOI_CAPTURES = ("Captures reseau de la cabine de chronometrage.\n\n"
                      "Deposees par l'equipe IT d'urgence. Merci de ne pas modifier les\n"
                      "fichiers : travaillez sur une copie.\n")
_PENALITES = "dossard;nom;discipline;motif;minutes;arbitre;heure\n"
_WIFI_INVITES = ("Wi-Fi invites - village partenaires\n"
                 "===================================\n\n"
                 "Reseau : DECAFLOP-INVITES\n"
                 "Acces  : portail captif, code journalier remis a l'accueil du village.\n\n"
                 "Ce reseau ne donne acces a aucun outil interne. Le Wi-Fi staff\n"
                 "(DECAFLOP-TIMING) est reserve a la cabine de chronometrage.\n")
_ASTREINTE = ("Checklist astreinte IT - jour de course\n"
              "=======================================\n\n"
              "[ ] 6h00  Allumer les bornes Wi-Fi du PC course et du village\n"
              "[ ] 6h15  Verifier l'imprimante PRN-VIL-02 (certificats)\n"
              "[ ] 6h30  Test radio canal 6 avec la cabine\n"
              "[ ] 7h00  Sauvegarde des postes du bureau de course\n"
              "[ ] 12h00 Point avec la direction de course\n"
              "[ ] 17h00 Recuperer les portables d'equipe\n")
_RAVITO = ("Ravitaillement - liste de courses\n"
           "=================================\n\n"
           "- Eau plate : 1 200 L\n"
           "- Boisson isotonique : 300 L\n"
           "- Bananes : 40 kg\n"
           "- Oranges : 25 kg\n"
           "- Gels : 6 cartons (offerts par DecaFlop)\n"
           "- Gobelets compostables : 5 000\n")
_ACCREDITATIONS = ("media;journaliste;type;arrivee\n"
                   "Le Littoral Sport;A. Perrin;ecrit;samedi\n"
                   "Radio Cote Ouest;M. Lefebvre;radio;dimanche\n"
                   "TriMag;J. Bernard;photo;dimanche\n"
                   "France Region;equipe 2 pers.;video;dimanche\n")
_TRANSPORTS = ("Ordres de transport - octobre 2026 (DFL)\n"
               "========================================\n\n"
               "DFLK900412  T. Girard   Ecran de saisie des inscriptions     importe\n"
               "DFLK900415  T. Girard   Correctif calcul des categories     importe\n"
               "DFLK900420  M. Sorensen Mise a jour des roles staff         importe\n"
               "DFLK900427  T. Girard   Export des resultats (RFC)          importe\n\n"
               "Prochaine fenetre de transport : apres la finale.\n")
_LOCK_PLANNING = "Elodie Roux" + " " * 40
_DESKTOP_INI = "[.ShellClassInfo]\r\nLocalizedResourceName=Bureau\r\n"

FILES = [
    ev(("Chronométrage", "Captures", "timing_booth.pcap"), "pcap", "Capture réseau (PCAP)",
       "Équipe IT d'urgence", "2026-11-01 22:14", "1.0", "Capture du Wi-Fi staff, cabine de chronométrage"),
    ev(("Arbitrage", "Pièces", "referee_usb.img"), "img", "Image disque brute",
       "Arbitrage", "2026-11-01 20:03", "1.0", "Image de la clé USB retrouvée en cabine"),
    ev(("Basis SAP", "Exports", "SAP_USR02_export.csv"), "csv", "Feuille CSV",
       "Basis SAP", "2026-11-01 09:12", "1.0", "Export de la table USR02 (mandant 001)"),
    ev(("Basis SAP", "Exports", "sap_hint.txt"), "txt", "Document texte",
       "Basis SAP", "2026-11-01 09:15", "1.2", "Note d'accompagnement de l'export"),
    ev(("IT", "Outils", "wordlist.txt"), "txt", "Document texte",
       "Équipe IT d'urgence", "2026-10-31 17:40", "2.1", "Liste de mots"),
    ev(("Direction de course", "Dossier incident", "case_file.zip"), "zip", "Archive ZIP (chiffrée)",
       "Direction de course", "2026-11-02 08:05", "1.0", "Pièces du dossier incident"),
    ev(("IT", "Sauvegardes postes", "portable-equipe-03", "dflop_erp.sap"), "sap", "Raccourci SAP GUI",
       "Équipe IT d'urgence", "2026-10-30 11:20", "1.0", "Sauvegarde du bureau du portable 03"),
    ev(("Basis SAP", "Développements", "ZDFLOP_RESULT_EXPORT.abap"), "abap", "Source ABAP",
       "Basis SAP", "2026-10-28 16:48", "3.4", "Rapport d'export des résultats (RFC)"),
    # --- mundane decoys (generated text, no clues) ---
    # A Basis working note that casually names the SAP gateway monitor (:8014,
    # challenge 14) and the ABAP dev folder — service names only, no secrets.
    decoy(("Basis SAP", "notes_basis.txt"), "txt", "Note interne", "Basis SAP",
          "2026-10-29 15:12", "1.3", _NOTES_BASIS, "Notes de l'équipe Basis"),
    decoy(("IT", "Outils", "LISEZ-MOI.txt"), "txt", "Note interne", "Équipe IT d'urgence",
          "2026-10-31 17:41", "1.0", _LISEZMOI),
    decoy(("IT", "Procédures", "politique_mots_de_passe.txt"), "txt", "Note interne", "Nicolas Petit",
          "2026-10-20 10:02", "4.0", _POLITIQUE, "Rappel de la DSI"),
    decoy(("Logistique", "Bénévoles", "planning_benevoles.txt"), "txt", "Note interne", "Élodie Roux",
          "2026-10-28 14:05", "1.6", _PLANNING),
    decoy(("Logistique", "Bénévoles", "commande_badges.txt"), "txt", "Note interne", "Élodie Roux",
          "2026-10-23 11:47", "1.1", _BADGES),
    decoy(("Logistique", "Matériel", "inventaire_radios.csv"), "csv", "Feuille CSV", "Logistique",
          "2026-10-29 18:30", "2.0", _RADIOS, "Affectation des radios"),
    decoy(("Direction de course", "Dossier incident", "note_parcours.txt"), "txt", "Note interne",
          "Direction de course", "2026-10-30 10:22", "1.0", _NOTE_PARCOURS),
    decoy(("Direction de course", "Réunions", "CR_reunion_securite_2026-10-27.txt"), "txt",
          "Compte rendu", "Hugo Martin", "2026-10-27 19:10", "1.0", _CR_SECU),
    decoy(("Chronométrage", "Parcours", "points_chronometrage.txt"), "txt", "Note interne",
          "Lars Eriksen", "2026-10-26 09:44", "1.2", _POINTS),
    decoy(("Arbitrage", "Pièces", "consignes_jury.txt"), "txt", "Note interne", "Sophie Lambert",
          "2026-10-29 09:30", "1.0", _CONSIGNES),
    decoy(("Communication", "Presse", "communique_finale_2026_v3.txt"), "txt", "Communiqué (projet)",
          "Camille Fontaine", "2026-10-30 16:25", "0.3", _COMMUNIQUE),
    # --- more smoke: short mundane notes, empty office files, system leftovers ---
    decoy(("Direction de course", "Réunions", "ordre_du_jour_briefing_samedi.txt"), "txt",
          "Note interne", "Claire Dumont", "2026-10-31 09:05", "1.1", _ODJ_BRIEFING),
    decoy(("Direction de course", "Réunions", "CR_point_partenaires_2026-10-21.txt"), "txt",
          "Compte rendu", "Hugo Martin", "2026-10-21 18:40", "1.0", _CR_PARTENAIRES),
    blank(("Direction de course", "Réunions", "plan_secours_v2.docx"), "doc", "Document Word",
          "Hugo Martin", "2026-10-25 11:02", "2.0"),
    blank(("Direction de course", "Archives 2025", "bilan_finale_2025.pdf"), "pdf", "Document PDF",
          "Claire Dumont", "2025-11-12 15:30"),
    blank(("Direction de course", "Archives 2025", "resultats_finale_2025.xlsx"), "xls",
          "Classeur Excel", "Bureau de course", "2025-11-03 10:14"),
    decoy(("Chronométrage", "Captures", "LISEZ-MOI.txt"), "txt", "Note interne",
          "Équipe IT d'urgence", "2026-11-01 22:20", "1.0", _LISEZMOI_CAPTURES),
    decoy(("Chronométrage", "Parcours", "cablage_tapis.txt"), "txt", "Note interne",
          "Jan Kowalski", "2026-10-30 14:12", "1.0", _CABLAGE),
    blank(("Chronométrage", "Parcours", "plan_parcours_velo.pdf"), "pdf", "Document PDF",
          "Lars Eriksen", "2026-10-24 08:55", "3.0"),
    decoy(("Arbitrage", "Pièces", "feuille_penalites_vierge.csv"), "csv", "Feuille CSV",
          "Karim Benali", "2026-10-31 07:30", "1.0", _PENALITES, "Modèle à remplir"),
    blank(("Arbitrage", "Pièces", "reglement_2026.pdf"), "pdf", "Document PDF",
          "Sophie Lambert", "2026-09-15 17:00", "2026"),
    decoy(("IT", "Procédures", "wifi_invites_village.txt"), "txt", "Note interne",
          "Nicolas Petit", "2026-10-29 12:10", "1.0", _WIFI_INVITES),
    decoy(("IT", "Procédures", "checklist_astreinte.txt"), "txt", "Note interne",
          "Astreinte IT", "2026-10-30 19:45", "1.2", _ASTREINTE),
    blank(("IT", "Procédures", "Nouveau document texte.txt"), "txt", "Document texte",
          "Astreinte IT", "2026-10-31 23:58"),
    blank(("IT", "Sauvegardes postes", "portable-equipe-02", "desktop.ini"), "sys",
          "Paramètres de dossier", "Équipe IT d'urgence", "2026-10-30 11:18", text=_DESKTOP_INI),
    decoy(("Basis SAP", "Transports", "ordres_transport_oct.txt"), "txt", "Note interne",
          "Thomas Girard", "2026-10-28 17:02", "1.0", _TRANSPORTS),
    decoy(("Logistique", "Matériel", "liste_courses_ravito.txt"), "txt", "Note interne",
          "Logistique", "2026-10-27 10:20", "1.3", _RAVITO),
    blank(("Logistique", "Matériel", "devis_location_barrieres.pdf"), "pdf", "Document PDF",
          "Logistique", "2026-10-16 09:41"),
    decoy(("Logistique", "Matériel", "Copie de inventaire_radios.csv"), "csv", "Feuille CSV",
          "Logistique", "2026-10-29 18:32", "2.0", _RADIOS),
    blank(("Logistique", "Bénévoles", "~$planning_benevoles.xlsx"), "xls", "Fichier temporaire",
          "Élodie Roux", "2026-11-01 08:12", text=_LOCK_PLANNING),
    blank(("Logistique", "Bénévoles", "fiches_postes_benevoles.docx"), "doc", "Document Word",
          "Élodie Roux", "2026-10-26 16:03", "1.4"),
    decoy(("Communication", "Presse", "accreditations_presse.csv"), "csv", "Feuille CSV",
          "Camille Fontaine", "2026-10-30 11:15", "1.1", _ACCREDITATIONS),
    blank(("Communication", "Visuels", "affiche_finale_2026_HD.psd"), "psd", "Fichier Photoshop",
          "Camille Fontaine", "2026-10-12 14:44", "4.0"),
    blank(("Communication", "Visuels", "logo_decaflop_noir.png"), "png", "Image PNG",
          "Service marketing", "2026-03-02 10:00"),
    blank(("Communication", "Visuels", "Thumbs.db"), "sys", "Fichier système",
          "Service marketing", "2026-10-12 14:50"),
    blank(("Communication", "Presse", "presentation_partenaires.pptx"), "ppt", "Présentation PowerPoint",
          "Julien Moreau", "2026-10-20 18:22", "1.2"),
]
FILES_BY_PATH = {f["path"]: f for f in FILES}
# Folders that exist but hold nothing yet.
EMPTY_FOLDERS = [("IT", "Sauvegardes postes", "portable-equipe-01"),
                 ("Arbitrage", "Réclamations"), ("Logistique", "Plans"),
                 ("Communication", "Réseaux sociaux")]


def build_tree():
    root = {"name": "Documents", "path": (), "children": {}, "files": []}

    def ensure(segs):
        node = root
        for i, s in enumerate(segs):
            node = node["children"].setdefault(
                s, {"name": s, "path": tuple(segs[:i + 1]), "children": {}, "files": []})
        return node
    for f in FILES:
        ensure(f["path"][:-1])["files"].append(f)
    for p in EMPTY_FOLDERS:
        ensure(p)
    return root


TREE = build_tree()


def child_folders(node):
    kids = list(node["children"].values())
    if node["path"] == ():
        kids.sort(key=lambda n: DEPT_ORDER.index(n["name"]) if n["name"] in DEPT_ORDER else 99)
    else:
        kids.sort(key=lambda n: n["name"].lower())
    return kids


def get_node(segs):
    node = TREE
    for s in segs:
        node = node["children"].get(s)
        if node is None:
            return None
    return node


def descendant_files(node):
    out = list(node["files"])
    for c in node["children"].values():
        out += descendant_files(c)
    return out


def latest(node):
    fs = descendant_files(node)
    return max(fs, key=lambda f: f["when"]) if fs else None


def folder_href(path):
    return "/documents" if not path else "/d/" + "/".join(quote(s) for s in path)


def download_href(f):
    return "/telecharger/" + "/".join(quote(s) for s in f["path"])


def preview_href(f):
    return "/apercu/" + "/".join(quote(s) for s in f["path"])


def details_href(f):
    return folder_href(f["path"][:-1]) + "?f=" + quote(f["name"])


def is_available(f):
    if f["decoy"]:
        return True
    return os.path.isfile(os.path.join(HANDOUT_DIR, f["source"]))


def size_bytes(f):
    if f["decoy"]:
        return len(f["text"].encode("utf-8"))
    p = os.path.join(HANDOUT_DIR, f["source"])
    return os.path.getsize(p) if os.path.isfile(p) else None


def file_size(f):
    n = size_bytes(f)
    return fr_size(n) if n is not None else None


def elements_label(n):
    return str(n) + (" élément" if n == 1 else " éléments")


def fold(s):
    """Lower-case, accent-free form used for matching."""
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


# --------------------------------------------------------------------------
# Chrome
# --------------------------------------------------------------------------
def display_user():
    u = session.get("user", SHARE_USER)
    return "Équipe IT d'urgence" if u == "equipe-it" else u


TOPNAV = [("/", "Accueil"), ("/documents", "Documents"), ("/annuaire", "Annuaire"),
          ("/activite", "Activité récente")]


def quick_launch(current_section, current_path=()):
    def a(href, label, on):
        return f'<a href="{href}"{intranet.CUR if on else ""}>{esc(label)}</a>'
    depts = "".join(
        f'<li>{a(folder_href(d["path"]), d["name"], current_path[:1] == d["path"])}</li>'
        for d in child_folders(TREE))
    return ('<ul>'
            f'<li>{a("/", "Accueil", current_section == "home")}</li>'
            f'<li>{a("/documents", "Documents", current_section == "docs" and not current_path)}'
            f'<ul>{depts}</ul></li>'
            f'<li>{a("/annuaire", "Annuaire", current_section == "dir")}</li>'
            f'<li>{a("/activite", "Activité récente", current_section == "activity")}</li>'
            f'<li>{a("/aide", "Aide", current_section == "help")}</li>'
            '</ul>')


def page(title, section, body, current_path=(), q=""):
    suite_on = {"home": "news", "docs": "docs", "dir": "dir"}.get(section)
    top_on = {"home": "/", "docs": "/documents", "dir": "/annuaire", "activity": "/activite"}.get(section)
    topnav = [(h, lbl, h == top_on) for h, lbl in TOPNAV]
    return intranet.page(
        title + " - " + SITE, body, app="intranet", site_title=SITE, site_href="/", logo="DF",
        topnav=topnav, quick=quick_launch(section, current_path),
        tabs=("Parcourir", "Page"), tabs_right=("Partager", "Suivre"),
        search=intranet.search_box("/recherche", "Rechercher sur ce site", q),
        user=display_user(), logout="/logout", suite_on=suite_on, product=PRODUCT,
        foot_extra="Dernière connexion le " + LAST_LOGIN)


# --------------------------------------------------------------------------
# Auth (the login is not a puzzle — the staff portal hands out the account).
# No lockout on wrong passwords: players just retry.
# --------------------------------------------------------------------------
def _bare_login(u):
    """Accept DECAFLOP\\user and user@decaflop.local as well as user."""
    u = u.strip()
    if "\\" in u and u.split("\\", 1)[0].lower() == "decaflop":
        u = u.split("\\", 1)[1]
    if u.lower().endswith("@decaflop.local"):
        u = u[: -len("@decaflop.local")]
    return u


@app.before_request
def require_login():
    if request.endpoint in ("login", "logout", "static"):
        return None
    if not session.get("ok"):
        return redirect("/login")
    return None


def login_page(error="", status=200, user=""):
    err = f'<p class="status err" role="alert">{esc(error)}</p>' if error else ""
    body = (intranet.head("Connexion - Intranet DécaFlop") +
            '<div class="signin"><div class="art" aria-hidden="true"><b>DÉCA<i>FLOP</i></b>'
            '<span>Intranet du réseau staff</span></div>'
            '<div class="pane"><div class="wordmark">DÉCA<i>FLOP</i></div>'
            '<h1>Connexion</h1><p>Connectez-vous avec votre compte DécaFlop.</p>'
            '<form method="post" action="/login">' + err +
            '<label for="u">Identifiant</label>'
            f'<input class="in" id="u" name="identifiant" value="{esc(user)}" placeholder="DECAFLOP\\identifiant" '
            'autocomplete="username" autocapitalize="none" spellcheck="false">'
            '<label for="p">Mot de passe</label>'
            '<input class="in" id="p" name="motdepasse" type="password" autocomplete="current-password">'
            '<button class="btn" type="submit">Connexion</button></form>'
            '<small>Accès réservé au personnel DécaFlop et aux prestataires autorisés. Les connexions '
            'sont journalisées conformément à la charte informatique.</small>'
            '<small>Mot de passe oublié ? Appelez l\'assistance au poste 300.</small>'
            '<div class="ft">© 2026 DécaFlop, Direction des Systèmes d\'Information</div>'
            '</div></div></body></html>')
    return html(body, status)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("ok"):
            return redirect("/")
        return login_page()
    raw = request.form.get("identifiant", "")
    u = _bare_login(raw)
    p = request.form.get("motdepasse", "")
    if hmac.compare_digest(u, SHARE_USER) and hmac.compare_digest(p, SHARE_PASSWORD):
        session.clear()
        session["ok"] = True
        session["user"] = SHARE_USER
        return redirect("/")
    return login_page("Identifiant ou mot de passe incorrect.", 401, raw)


# Out of the story: the game's floating shortcuts (fab.py) on every HTML page,
# the login page included, so a player can always get back to the hub and the
# site. A logged-in visit also sets the cookie that shows the intranet button
# on the hub and the site (kept after logout: it marks a first access).
@app.after_request
def shortcuts(resp):
    if session.get("ok") and not fab.intranet_unlocked():
        fab.mark_intranet(resp)
    # inject() leaves pages without </body> (redirects) alone; downloads are not HTML.
    if resp.mimetype == "text/html" and not resp.direct_passthrough and not resp.is_streamed:
        resp.set_data(fab.inject(resp.get_data(as_text=True), fab.render("share", fab.default_urls())))
    return resp


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/login")


# --------------------------------------------------------------------------
# Home, activity, help
# --------------------------------------------------------------------------
NEWS = [
    ("Cellule de crise activée après un incident sur la liste de départ", "Direction de course",
     "2026-11-02 07:40",
     "Une anomalie a été détectée sur la liste de départ de la finale. L'équipe IT d'urgence a accès "
     "au partage pour l'enquête. Merci de ne rien supprimer ni déplacer dans "
     "<a href=\"/d/Direction%20de%20course/Dossier%20incident\">Direction de course / Dossier incident</a>."),
    ("Maintenance du système SAP DFL samedi 7 novembre de 22 h à 2 h", "Basis SAP", "2026-10-29 15:30",
     "Le système DFL (mandant 001) sera indisponible pendant l'application du support package de "
     "novembre. Les saisies de résultats doivent être terminées avant 21 h 30."),
    ("Plan de circulation et navettes pour la finale", "Logistique", "2026-10-28 12:10",
     "Navettes depuis le centre-ville toutes les 15 minutes à partir de 6 h. Parking staff P3, badge "
     "obligatoire. Le planning des bénévoles est dans "
     "<a href=\"/d/Logistique/B%C3%A9n%C3%A9voles\">Logistique / Bénévoles</a>."),
    ("Rappel sur la politique de mots de passe", "Direction des Systèmes d'Information", "2026-10-20 10:05",
     "Les comptes d'équipe créés pour l'événement seront désactivés le lundi suivant la finale. "
     "Le rappel complet est dans <a href=\"/d/IT/Proc%C3%A9dures\">IT / Procédures</a>."),
]


def activity_items(limit=None):
    fs = sorted(FILES, key=lambda f: f["when"], reverse=True)
    if limit:
        fs = fs[:limit]
    out = []
    for f in fs:
        verb = "a ajouté" if f["ver"] in ("1.0", "0.1") else "a modifié"
        folder = f["path"][:-1]
        out.append(f'<li>{icon(icon_of(f))}<div><a href="{preview_href(f)}">'
                   f'{esc(f["name"])}</a><small>{esc(f["who"])} {verb} ce fichier le {fr_dt(f["when"], " à ")}, '
                   f'dans {esc(" / ".join(folder))}</small></div></li>')
    return '<ul class="feed">' + "".join(out) + '</ul>'


@app.get("/")
def root():
    news = "".join(
        f'<li><h3>{esc(t)}</h3><p class="by">{esc(who)}, le {fr_dt(when, " à ")}</p><p>{text}</p></li>'
        for t, who, when, text in NEWS)
    apps = "".join(
        f'<li><a href="{esc(intranet.app_url(k))}">{esc(intranet.APPS[k][1])}</a></li>'
        for k in intranet.ORDER if k != "intranet")
    body = ('<h1 class="h1">Accueil</h1>'
            '<div class="cols"><div>'
            f'<section class="wp"><h2>Annonces</h2><ul class="news">{news}</ul></section>'
            f'<section class="wp"><h2>Activité récente</h2>{activity_items(6)}'
            '<p style="margin-top:8px"><a href="/activite">Toute l\'activité</a></p></section>'
            '</div><div>'
            '<section class="wp"><h2>Liens rapides</h2><ul class="links">'
            '<li><a href="/documents">Documents</a></li><li><a href="/annuaire">Annuaire</a></li>'
            f'<li><a href="/aide">Aide et assistance</a></li>{apps}</ul></section>'
            '<section class="wp"><h2>Ma session</h2><dl class="kv">'
            f'<dt>Compte</dt><dd>{esc(session.get("user", SHARE_USER))}</dd>'
            '<dt>Droits</dt><dd>Lecture (bibliothèque Documents)</dd>'
            f'<dt>Dernière connexion</dt><dd>{LAST_LOGIN}</dd>'
            '<dt>Session</dt><dd>Expire après 30 min d\'inactivité</dd></dl></section>'
            '</div></div>')
    return html(page("Accueil", "home", body))


@app.get("/activite")
def activity():
    body = ('<h1 class="h1">Activité récente</h1>'
            '<p class="lead mute">Fichiers ajoutés ou modifiés dans la bibliothèque Documents.</p>' +
            activity_items())
    return html(page("Activité récente", "activity", body))


@app.get("/aide")
def help_page():
    body = ('<h1 class="h1">Aide et assistance</h1>'
            '<div class="cols"><div>'
            '<section class="wp"><h2>Charte informatique (extrait)</h2><ul>'
            '<li>Les documents du partage sont internes. Ne les copiez pas sur un support personnel.</li>'
            '<li>Un compte est attribué à une personne ou à une équipe nommée ; ne le prêtez pas.</li>'
            '<li>Les accès sont journalisés et peuvent être contrôlés par la DSI.</li>'
            '<li>Signalez toute anomalie à l\'astreinte IT.</li></ul></section>'
            '<section class="wp"><h2>Navigateurs pris en charge</h2>'
            '<p>Microsoft Edge, Firefox ESR et Chrome (versions maintenues). Une résolution de 1280 x 1024 '
            'ou plus est conseillée.</p></section>'
            '</div><div>'
            '<section class="wp"><h2>Contacts</h2><dl class="kv">'
            '<dt>Astreinte IT</dt><dd>Poste 300 (24 h/24 pendant l\'événement)</dd>'
            '<dt>DSI</dt><dd>Poste 301</dd>'
            '<dt>Bureau de course</dt><dd>Poste 214</dd>'
            '<dt>Logistique</dt><dd>Poste 118</dd></dl>'
            '<p style="margin-top:10px"><a href="/annuaire">Voir l\'annuaire complet</a></p></section>'
            '</div></div>')
    return html(page("Aide", "help", body))


# --------------------------------------------------------------------------
# Directory (annuaire): static, no logins shown.
# --------------------------------------------------------------------------
PEOPLE = [
    ("Claire Dumont", "Directrice de course", "Direction de course", "201", "PC course"),
    ("Hugo Martin", "Adjoint à la direction de course", "Direction de course", "202", "PC course"),
    ("Bureau de course", "Accueil des concurrents", "Direction de course", "214", "Mairie, salle B"),
    ("Lars Eriksen", "Chef chronométreur", "Chronométrage", "230", "Cabine de chronométrage"),
    ("Jan Kowalski", "Opérateur chronométrage", "Chronométrage", "231", "Cabine de chronométrage"),
    ("Sophie Lambert", "Arbitre principale", "Arbitrage", "240", "Tente jury"),
    ("Karim Benali", "Juge arbitre", "Arbitrage", "241", "Tente jury"),
    ("Astreinte IT", "Support pendant l'événement", "DSI", "300", "PC course"),
    ("Nicolas Petit", "Responsable DSI", "DSI", "301", "Siège, bât. A"),
    ("Équipe IT d'urgence", "Cellule de crise", "DSI", "305", "PC course"),
    ("Mette Sorensen", "Administratrice SAP Basis", "Basis SAP", "310", "Siège, bât. A"),
    ("Thomas Girard", "Développeur ABAP", "Basis SAP", "311", "Siège, bât. A"),
    ("Logistique", "Standard logistique", "Logistique", "118", "Village"),
    ("Élodie Roux", "Responsable bénévoles", "Logistique", "119", "Village"),
    ("Service marketing", "Presse et partenariats", "Marketing", "120", "Siège, bât. C"),
    ("Camille Fontaine", "Chargée de communication", "Marketing", "121", "Siège, bât. C"),
    ("Julien Moreau", "Responsable partenariat triathlon", "Marketing", "130", "Siège, bât. C"),
]
SERVICES = sorted({p[2] for p in PEOPLE}, key=fold)


@app.get("/annuaire")
def directory():
    svc = request.args.get("service", "")
    if svc not in SERVICES:
        svc = ""
    rows = [p for p in PEOPLE if not svc or p[2] == svc]
    opts = '<option value="">Tous les services</option>' + "".join(
        f'<option{" selected" if s == svc else ""}>{esc(s)}</option>' for s in SERVICES)
    trs = "".join(
        f'<tr><td class="ty">{icon("user")}</td><td><b style="font-weight:600">{esc(n)}</b>'
        f'<span class="meta">{esc(fn)}, {esc(s)}, poste {esc(ph)}</span></td>'
        f'<td class="hide-sm">{esc(fn)}</td><td class="hide-sm">{esc(s)}</td>'
        f'<td class="num">{esc(ph)}</td><td class="hide-sm">{esc(b)}</td></tr>'
        for n, fn, s, ph, b in rows)
    body = ('<h1 class="h1">Annuaire</h1>'
            '<form class="views" method="get" action="/annuaire">'
            '<label for="svc">Service</label><select id="svc" name="service" class="in" '
            'style="width:auto;height:24px;padding:0 4px">' + opts + '</select>'
            '<button class="btn sec" type="submit" style="min-width:0;padding:2px 10px">Filtrer</button>'
            f'<span class="mute" style="margin-left:auto">{len(rows)} contact(s)</span></form>'
            '<table class="list"><thead><tr><th class="ty"></th><th>Nom</th><th class="hide-sm">Fonction</th>'
            '<th class="hide-sm">Service</th><th style="width:70px">Poste</th><th class="hide-sm">Bureau</th></tr>'
            '</thead><tbody>' + trs + '</tbody></table>'
            '<p class="mute" style="margin-top:10px;font-size:12px">Pour joindre un poste interne, composez le '
            'numéro à 3 chiffres depuis un téléphone du réseau staff.</p>')
    return html(page("Annuaire", "dir", body))


# --------------------------------------------------------------------------
# Documents
# --------------------------------------------------------------------------
SORTS = {"nom": lambda f: fold(f["name"]), "date": lambda f: f["when"],
         "taille": lambda f: size_bytes(f) or 0}


def sort_args():
    tri = request.args.get("tri", "nom")
    ordre = request.args.get("ordre", "asc")
    if tri not in SORTS:
        tri = "nom"
    if ordre not in ("asc", "desc"):
        ordre = "asc"
    return tri, ordre


def qs(**kw):
    kw = {k: v for k, v in kw.items() if v}
    return ("?" + urlencode(kw)) if kw else ""


def sort_link(label, key, tri, ordre):
    if key == tri:
        nxt = "desc" if ordre == "asc" else "asc"
        arrow = " ↑" if ordre == "asc" else " ↓"
    else:
        nxt, arrow = "asc", ""
    href = qs(tri=None if key == "nom" and nxt == "asc" else key, ordre=None if nxt == "asc" else nxt)
    return f'<a href="{href or "?"}">{label}{arrow}</a>'


def folder_row(sub):
    cnt = len(sub["children"]) + len(sub["files"])
    last = latest(sub)
    when = fr_dt(last["when"]) if last else ""
    who = esc(last["who"]) if last else ""
    return (f'<tr><td class="ck"></td><td class="ty">{icon("folder")}</td>'
            f'<td><a href="{folder_href(sub["path"])}">{esc(sub["name"])}</a>'
            f'<span class="meta">{elements_label(cnt)}{", modifié le " + when if when else ""}</span></td>'
            f'<td class="c-date num">{when}</td><td class="c-who">{who}</td>'
            f'<td class="c-size">{elements_label(cnt)}</td><td class="c-ver"></td></tr>')


SEL = ' class="sel"'


def file_row(f, selected, tri, ordre):
    sel = f["name"] == selected
    size = file_size(f)
    sizecell = (f'<td class="c-size num">{size}</td>' if size is not None
                else '<td class="c-size na">pas encore disponible</td>')
    meta = (f'{size}, {esc(f["who"])}, le {fr_dt(f["when"], " à ")}' if size is not None
            else f'pas encore disponible, {esc(f["who"])}')
    href = qs(f=f["name"], tri=tri if tri != "nom" else None, ordre=ordre if ordre != "asc" else None)
    return (f'<tr{SEL if sel else ""}><td class="ck"><a href="{href}" title="Sélectionner">'
            f'{"✓" if sel else "○"}</a></td>'
            f'<td class="ty">{icon(icon_of(f), f["type"])}</td>'
            f'<td><a href="{preview_href(f)}">{esc(f["name"])}</a>'
            f'<a class="dots" href="{href}" title="Afficher les détails" aria-label="Détails de {esc(f["name"])}">'
            f'...</a><span class="meta">{meta}</span></td>'
            f'<td class="c-date num">{fr_dt(f["when"])}</td><td class="c-who">{esc(f["who"])}</td>'
            f'{sizecell}<td class="c-ver num">{esc(f["ver"])}</td></tr>')


def callout(f, row):
    avail = is_available(f)
    size = file_size(f) or "Non disponible"
    link = request.host_url.rstrip("/") + download_href(f)
    acts = (f'<a href="{preview_href(f)}">Ouvrir</a><a href="{download_href(f)}">Télécharger</a>' if avail
            else '<span class="off">Pas encore disponible</span>')
    peek = ""
    if avail and f["kind"] in TEXT_KINDS | {"csv"}:
        lines = as_text(read_bytes(f, 4096)).splitlines()[:PEEK_LINES]
        peek = (f'<a class="peek" href="{preview_href(f)}" title="Ouvrir l\'aperçu">'
                f'<pre>{esc(chr(10).join(lines))}</pre></a>')
    meta = [("Type", esc(f["type"])), ("Taille", size), ("Version", esc(f["ver"]))]
    if f["desc"]:
        meta.append(("Description", esc(f["desc"])))
    meta.append(("Emplacement", esc("Documents / " + " / ".join(f["path"][:-1]))))
    dl = "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in meta)
    return (f'<aside class="callout" id="details" style="--row:{row}" aria-label="Détails du fichier">'
            f'<h2>{esc(f["name"])}</h2>'
            f'<p>Modifié le {fr_dt(f["when"], " à ")} par {esc(f["who"])}</p>'
            f'{peek}<dl>{dl}</dl><div class="link" title="{esc(link)}">{esc(link)}</div>'
            f'<div class="acts">{acts}</div></aside>')


@app.get("/documents")
def documents():
    rows = "".join(
        f'<tr><td class="ty">{icon("folder")}</td><td><a href="{folder_href(d["path"])}">{esc(d["name"])}</a>'
        f'<span class="meta">{esc(DEPT_DESC.get(d["name"], ""))}</span></td>'
        f'<td class="hide-sm">{esc(DEPT_DESC.get(d["name"], ""))}</td>'
        f'<td class="c-date num">{fr_dt(latest(d)["when"]) if latest(d) else ""}</td>'
        f'<td class="c-items">{elements_label(len(d["children"]) + len(d["files"]))}</td></tr>'
        for d in child_folders(TREE))
    body = ('<h1 class="h1">Documents</h1>'
            + views_bar() +
            '<table class="list"><thead><tr><th class="ty"></th><th>Nom</th><th class="hide-sm">Description</th>'
            '<th class="c-date">Modifié</th><th class="c-items">Contenu</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            f'<div class="pager">Éléments 1 à {len(child_folders(TREE))}</div>')
    return html(page("Documents", "docs", body))


def views_bar():
    return ('<div class="views"><a href="/documents" aria-current="page">Tous les documents</a>'
            '<a href="/activite">Modifiés récemment</a>' +
            intranet.search_box("/recherche", "Rechercher un fichier", cls="find") + '</div>')


@app.get("/d/<path:subpath>")
def folder(subpath):
    segs = tuple(s for s in subpath.split("/") if s)
    node = get_node(segs)
    if node is None or node["path"] == ():
        abort(404)
    selected = request.args.get("f", "")
    tri, ordre = sort_args()
    files = sorted(node["files"], key=SORTS[tri], reverse=(ordre == "desc"))
    subs = child_folders(node)
    rows = [folder_row(s) for s in subs] + [file_row(f, selected, tri, ordre) for f in files]
    head_row = ('<tr><th class="ck">✓</th><th class="ty"></th>'
                f'<th>{sort_link("Nom", "nom", tri, ordre)}</th>'
                f'<th class="c-date">{sort_link("Modifié", "date", tri, ordre)}</th>'
                '<th class="c-who">Modifié par</th>'
                f'<th class="c-size">{sort_link("Taille du fichier", "taille", tri, ordre)}</th>'
                '<th class="c-ver">Version</th></tr>')
    table = ('<table class="list"><thead>' + head_row + '</thead><tbody>' + "".join(rows) +
             '</tbody></table>')
    if not rows:
        table = '<p class="empty">Ce dossier est vide.</p>'
    else:
        table += f'<div class="pager">Éléments 1 à {len(rows)}</div>'
    sel = next((f for f in files if f["name"] == selected), None)
    if sel is not None:
        work = ('<div class="work"><div style="min-width:0">' + table + '</div>' +
                callout(sel, len(subs) + files.index(sel)) + '</div>')
    else:
        work = table
    crumbs = ['<a href="/documents">Documents</a>']
    for i, s in enumerate(segs):
        crumbs.append(esc(s) if i == len(segs) - 1 else f'<a href="{folder_href(segs[:i + 1])}">{esc(s)}</a>')
    body = ('<h1 class="h1">' + '<span class="sep">›</span>'.join(crumbs) + '</h1>' + views_bar() + work)
    return html(page(node["name"], "docs", body, current_path=node["path"]))


@app.get("/recherche")
def search():
    q = request.args.get("q", "")[:100].strip()
    hits = []
    if q:
        needle = fold(q)
        for f in FILES:
            hay = fold(" ".join(f["path"]) + " " + f["desc"] + " " + f["type"])
            if needle in hay:
                hits.append(f)
        hits.sort(key=lambda f: f["when"], reverse=True)
    if not q:
        result = '<p class="empty">Saisissez un nom de fichier, de dossier ou un type de document.</p>'
    elif not hits:
        result = '<p class="empty">Aucun résultat. Vérifiez l\'orthographe ou essayez un autre terme.</p>'
    else:
        trs = "".join(
            f'<tr><td class="ty">{icon(icon_of(f), f["type"])}</td>'
            f'<td><a href="{preview_href(f)}">{esc(f["name"])}</a>'
            f'<span class="meta">{esc(" / ".join(f["path"][:-1]))}, le {fr_dt(f["when"], " à ")}</span></td>'
            f'<td class="hide-sm"><a href="{folder_href(f["path"][:-1])}">'
            f'{esc(" / ".join(f["path"][:-1]))}</a></td>'
            f'<td class="c-date num">{fr_dt(f["when"])}</td>'
            f'<td class="c-size num">{file_size(f) or ""}</td></tr>'
            for f in hits)
        result = ('<table class="list"><thead><tr><th class="ty"></th><th>Nom</th>'
                  '<th class="hide-sm">Emplacement</th><th class="c-date">Modifié</th>'
                  f'<th class="c-size">Taille</th></tr></thead><tbody>{trs}</tbody></table>')
    count = f'{len(hits)} résultat(s)' if q else ""
    body = ('<h1 class="h1">Recherche</h1>'
            '<form class="views" role="search" method="get" action="/recherche">'
            '<label class="sr" for="rq">Rechercher</label>'
            f'<input class="in" id="rq" name="q" value="{esc(q)}" placeholder="Rechercher dans Documents" '
            'style="max-width:360px;height:26px">'
            '<button class="btn" type="submit" style="min-width:0;padding:3px 14px">Rechercher</button>'
            f'<span class="mute" style="margin-left:auto">{count}</span></form>' + result)
    return html(page("Recherche", "docs", body))


# --------------------------------------------------------------------------
# File viewer (read-only preview, like the Office Web Apps viewer)
# --------------------------------------------------------------------------
TEXT_KINDS = {"txt", "abap", "sap"}
PREVIEW_BYTES = 1_000_000
PREVIEW_LINES = 2000
PREVIEW_ROWS = 500
GRID_SPARE_COLS = 10
GRID_MIN_ROWS = 30
PEEK_LINES = 7


def read_bytes(f, limit=PREVIEW_BYTES):
    """The file's first `limit` bytes (None if the handout is missing)."""
    if f["decoy"]:
        return f["text"].encode("utf-8")[:limit]
    p = os.path.join(HANDOUT_DIR, f["source"])
    if not os.path.isfile(p):
        return None
    with open(p, "rb") as fh:
        return fh.read(limit)


def as_text(data):
    if data is None:
        return ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def cut_note(shown, total, unit):
    if shown >= total:
        return ""
    return (f'<p class="vcut">Aperçu limité aux {shown} premières {unit}. '
            'Téléchargez le fichier pour le consulter en entier.</p>')


def text_view(f, data):
    lines = as_text(data).splitlines() or [""]
    rows = "".join(f'<span class="l">{esc(line)}</span>' for line in lines[:PREVIEW_LINES])
    return (cut_note(min(len(lines), PREVIEW_LINES), len(lines), "lignes") +
            f'<div class="sheet"><pre class="code">{rows}</pre></div>')


def col_name(i):
    out = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        out = chr(65 + r) + out
    return out


def csv_view(f, data):
    text = as_text(data)
    first = text.split("\n", 1)[0]
    delim = ";" if first.count(";") > first.count(",") else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    shown = rows[:PREVIEW_ROWS]
    # like a spreadsheet, the grid carries on past the data with empty cells
    ncol = max((len(r) for r in shown), default=1) + GRID_SPARE_COLS
    shown = shown + [[]] * max(GRID_MIN_ROWS - len(shown), 0)
    head = '<tr><th class="corner"></th>' + "".join(f"<th>{col_name(i)}</th>" for i in range(ncol)) + "</tr>"
    body = "".join(f"<tr><th>{n}</th>" + "".join(f"<td>{esc(c)}</td>" for c in r + [""] * (ncol - len(r)))
                   + "</tr>" for n, r in enumerate(shown, 1))
    # The static grid is the fallback; static/classeur.js reads the same rows from
    # #csv-data and turns #csv-sheet into the sortable, filterable "Classeur".
    return (cut_note(min(len(rows), PREVIEW_ROWS), len(rows), "lignes") +
            f'<div class="sheet wide" id="csv-sheet"><div class="gridwrap"><table class="grid"><thead>{head}</thead>'
            f'<tbody>{body}</tbody></table></div></div>' + csv_data(rows[:PREVIEW_ROWS], len(rows)))


def csv_data(rows, total):
    """The rows as JSON for classeur.js. Cells are file content: <, > and & are
    escaped so nothing in a cell can close the script element."""
    data = json.dumps({"rows": rows, "total": total, "cut": total > len(rows)}, ensure_ascii=False)
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f'<script type="application/json" id="csv-data">{data}</script>'


CLASSEUR_CSS = '<link rel="stylesheet" href="/static/classeur.css">'
CLASSEUR_JS = '<script src="/static/classeur.js" defer></script>'


def zip_view(f, data):
    try:
        entries = zipfile.ZipFile(io.BytesIO(data)).infolist()
    except zipfile.BadZipFile:
        return no_preview(f)
    locked = any(e.flag_bits & 1 for e in entries)
    trs = "".join(
        f'<tr><td class="ty">{icon("folder" if e.is_dir() else "txt")}</td><td>{esc(e.filename)}</td>'
        f'<td class="c-size num">{"" if e.is_dir() else fr_size(e.file_size)}</td>'
        f'<td class="c-ver">{"Oui" if e.flag_bits & 1 else "Non"}</td></tr>' for e in entries)
    note = ('<p class="status">Archive protégée par un mot de passe. Téléchargez-la pour l\'extraire.</p>'
            if locked else "")
    return (f'<div class="sheet pad">{note}<table class="list"><thead><tr><th class="ty"></th><th>Nom</th>'
            '<th class="c-size">Taille</th><th class="c-ver">Chiffré</th></tr></thead>'
            f'<tbody>{trs}</tbody></table>'
            f'<div class="pager">{elements_label(len(entries))} dans l\'archive</div></div>')


def no_preview(f, missing=False):
    if missing:
        title, text, act = ("Fichier pas encore disponible",
                            "Ce fichier est en cours de dépôt sur le partage. Réessayez dans quelques minutes.",
                            "")
    else:
        title = "Aperçu non disponible"
        text = (f"Les fichiers de type {esc(f['type'])} ne peuvent pas être affichés dans le navigateur. "
                "Téléchargez le fichier pour l'ouvrir avec l'application adaptée.")
        act = f'<a class="btn" href="{download_href(f)}">Télécharger</a>'
    return (f'<div class="sheet nopv">{icon(icon_of(f))}<h2>{title}</h2><p>{text}</p>{act}</div>')


# Files that are genuine, spoiler-level hints (not decoys). The first time a
# player opens one in a session, a warning stands in front of the content so a
# curious click does not spoil the search.
SPOILER_PATHS = {("Basis SAP", "Exports", "sap_hint.txt")}


def is_spoiler(f):
    return f["path"] in SPOILER_PATHS


def hint_warning(f):
    """Interstitial shown before a real hint is revealed."""
    return (
        '<div class="sheet nopv hint-warn">' + icon("txt") +
        '<h2>Ceci est un véritable indice</h2>'
        '<p>Ce fichier n\'est pas un leurre : il contient un vrai indice pour '
        'l\'épreuve. Ne l\'ouvrez que si vous êtes vraiment bloqué et que vous '
        'n\'avez plus aucune piste. Le consulter trop tôt vous gâchera la '
        'recherche.</p>'
        f'<a class="btn" href="{preview_href(f)}?vu=1">Afficher quand même l\'indice</a>'
        f'<a class="btn sec" href="{folder_href(f["path"][:-1])}">Revenir au dossier</a>'
        '</div>')


CAPTURE_CSS = '<link rel="stylesheet" href="/static/capture.css">'
PCAP_PREVIEW_BYTES = 5_000_000


def viewer_page(f, content, wide=False, classeur=False, css=""):
    folder = f["path"][:-1]
    crumbs = ['<a href="/documents">Documents</a>'] + [
        f'<a href="{folder_href(folder[:i + 1])}">{esc(s)}</a>' for i, s in enumerate(folder)]
    size = file_size(f)
    meta = (f'Version {esc(f["ver"])}, modifié le {fr_dt(f["when"], " à ")} par {esc(f["who"])}'
            + (f", {size}" if size else ""))
    dl = (f'<a href="{download_href(f)}">Télécharger</a>' if is_available(f)
          else '<span class="off">Télécharger</span>')
    bar = (f'<div class="vbar"><div class="vname">{icon(icon_of(f), f["type"])}<div>'
           f'<h1>{esc(f["name"])}</h1><small>{" / ".join(crumbs)}</small></div></div>'
           f'<nav class="vacts" aria-label="Fichier">{dl}<a href="{details_href(f)}">Détails</a>'
           f'<a class="x" href="{folder_href(folder)}" title="Fermer l\'aperçu">Fermer</a></nav></div>')
    head = intranet.head(f'{f["name"]} - {SITE}')
    if classeur:                       # interactive CSV preview (static/classeur.*)
        css += CLASSEUR_CSS
    if css:
        head = head.replace("</head>", css + "</head>", 1)
    return (head + intranet.SPRITE +
            intranet.suite("intranet", "docs", display_user(), "/logout") + bar +
            f'<main class="viewer{" wide" if wide else ""}" id="main"><p class="vmeta">{meta}</p>{content}</main>'
            + (CLASSEUR_JS if classeur else "") + '</body></html>')


@app.get("/apercu/<path:filepath>")
def preview(filepath):
    f = FILES_BY_PATH.get(tuple(s for s in filepath.split("/") if s))
    if f is None:
        abort(404)
    if is_spoiler(f):
        if request.args.get("vu") == "1":
            session["hint_vu"] = True
        if not session.get("hint_vu"):
            return html(viewer_page(f, hint_warning(f)))
    data = read_bytes(f)
    if data is None:
        content = no_preview(f, missing=True)
    elif f["kind"] in TEXT_KINDS:
        content = text_view(f, data)
    elif f["kind"] == "csv":
        content = csv_view(f, data)
    elif f["kind"] == "zip":
        content = zip_view(f, read_bytes(f, 50_000_000))
    elif f["kind"] == "pcap":           # packet list + layers of the clicked packet (capture.py)
        content = capture.view(read_bytes(f, PCAP_PREVIEW_BYTES), request.args.get("p", ""), preview_href(f))
        return html(viewer_page(f, content, wide=True, css=CAPTURE_CSS))
    else:
        content = no_preview(f)
    grid = f["kind"] == "csv" and data is not None
    return html(viewer_page(f, content, wide=grid, classeur=grid))


@app.get("/telecharger/<path:filepath>")
def download(filepath):
    segs = tuple(s for s in filepath.split("/") if s)
    f = FILES_BY_PATH.get(segs)
    if f is None:
        abort(404)
    if f["decoy"]:
        if f["kind"] in TEXT_KINDS | {"csv"}:
            mime = "text/plain; charset=utf-8"
        else:                                   # empty office file, image, system file
            mime = mimetypes.guess_type(f["name"])[0] or "application/octet-stream"
        return Response(f["text"], mimetype=mime,
                        headers={"Content-Disposition": 'attachment; filename="' + f["name"] + '"'})
    if not os.path.isfile(os.path.join(HANDOUT_DIR, f["source"])):
        abort(404)
    return send_from_directory(HANDOUT_DIR, f["source"], as_attachment=True)


@app.errorhandler(404)
def not_found(_e):
    if not session.get("ok"):
        return redirect("/login")
    body = ('<h1 class="h1">Désolé, cette page est introuvable.</h1>'
            '<p class="lead">Le dossier ou le fichier demandé n\'existe pas ou a été déplacé.</p>'
            '<p><a href="/documents">Retour à la bibliothèque Documents</a></p>'
            '<dl class="kv" style="margin-top:22px;color:var(--mute)">'
            f'<dt>ID de corrélation</dt><dd><code>{uuid.uuid4()}</code></dd>'
            f'<dt>Date et heure</dt><dd>{time.strftime("%d/%m/%Y %H:%M:%S")}</dd></dl>')
    return html(page("Introuvable", "docs", body), 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
