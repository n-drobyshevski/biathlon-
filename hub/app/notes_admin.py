"""
Organizer commands for the hub's Bloc-notes (notes.py), run inside the hub:

  docker compose exec hub python notes_admin.py liste             pseudos and notepads
  docker compose exec hub python notes_admin.py mdp <pseudo>      forget the password (notes kept);
                                                                   the next sign-in sets a new one.
                                                                   With scoreboard accounts, reset it
                                                                   in CTFd instead (Admin > Users)
  docker compose exec hub python notes_admin.py supprimer <pseudo>  delete the account, its private
                                                                   notepad and its memberships
  docker compose exec hub python notes_admin.py vider --oui       wipe every account and notepad
                                                                   (between two events)
"""
import sys
import time

import notes


def liste(con):
    players = con.execute("SELECT pseudo, pw_hash IS NULL AS reset, created FROM players ORDER BY pseudo").fetchall()
    print(f"{len(players)} pseudo(s)")
    for p in players:
        when = time.strftime("%d/%m %H:%M", time.localtime(p["created"]))
        print(f"  {p['pseudo']:<24} créé le {when}{'  (mot de passe à redéfinir)' if p['reset'] else ''}")
    pads = con.execute("SELECT p.id, p.name, p.owner, p.shared, length(p.text) AS size, "
                       "(SELECT group_concat(pseudo, ' ') FROM members m WHERE m.pad_id = p.id) AS who "
                       "FROM pads p ORDER BY p.shared DESC, p.id").fetchall()
    shared = [p for p in pads if p["shared"]]
    print(f"{len(shared)} bloc-notes partagé(s), {len(pads) - len(shared)} privé(s)")
    for p in shared:
        print(f"  #{p['id']} {p['name']} (créé par {p['owner']}, {p['size']} caractères) : {p['who']}")


def mdp(con, pseudo):
    found = notes.resolve(pseudo, con)
    if not found:
        print("Pseudo inconnu.")
        return 1
    con.execute("UPDATE players SET pw_hash = NULL WHERE pseudo = ?", (found,))
    if notes.ctfd_base():
        print("Les comptes viennent du tableau des scores : changez le mot de passe dans CTFd (Admin > Users). "
              "Le mot de passe gardé par le hub en secours est effacé.")
    else:
        print("Mot de passe oublié : la prochaine connexion en définit un nouveau.")
    return 0


def supprimer(con, pseudo):
    pseudo = notes.resolve(pseudo, con)
    if not pseudo:
        print("Pseudo inconnu.")
        return 1
    con.execute("BEGIN IMMEDIATE")
    con.execute("DELETE FROM pads WHERE shared = 0 AND owner = ?", (pseudo,))
    for (pid,) in con.execute("SELECT id FROM pads WHERE shared = 1 AND owner = ?", (pseudo,)).fetchall():
        heir = con.execute("SELECT pseudo FROM members WHERE pad_id = ? AND pseudo != ? ORDER BY rowid LIMIT 1",
                           (pid, pseudo)).fetchone()
        if heir:                                 # someone else keeps the shared notepad
            con.execute("UPDATE pads SET owner = ? WHERE id = ?", (heir[0], pid))
        else:
            con.execute("DELETE FROM pads WHERE id = ?", (pid,))
    con.execute("DELETE FROM members WHERE pseudo = ?", (pseudo,))
    con.execute("DELETE FROM statuses WHERE pseudo = ?", (pseudo,))
    con.execute("DELETE FROM players WHERE pseudo = ?", (pseudo,))
    con.execute("COMMIT")
    print(f"{pseudo} supprimé.")
    return 0


def vider(con):
    con.execute("BEGIN IMMEDIATE")
    con.execute("DELETE FROM members")
    con.execute("DELETE FROM statuses")
    con.execute("DELETE FROM pads")
    con.execute("DELETE FROM players")
    con.execute("DELETE FROM meta WHERE key = 'secret'")    # signs everyone out after a restart
    con.execute("COMMIT")
    print("Tout est effacé. Redémarrez le hub pour déconnecter tout le monde : docker compose restart hub")
    return 0


def main(argv):
    if not argv or argv[0] not in ("liste", "mdp", "supprimer", "vider"):
        print(__doc__.strip())
        return 2
    notes.init()
    con = notes.connect()
    try:
        cmd = argv[0]
        if cmd == "liste":
            liste(con)
            return 0
        if cmd in ("mdp", "supprimer"):
            if len(argv) != 2:
                print(f"Usage : python notes_admin.py {cmd} <pseudo>")
                return 2
            return (mdp if cmd == "mdp" else supprimer)(con, argv[1])
        if "--oui" not in argv:
            print("Ceci efface tous les comptes et tous les bloc-notes. Relancez avec --oui pour confirmer.")
            return 2
        return vider(con)
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
