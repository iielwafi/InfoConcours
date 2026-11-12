# -*- coding: utf-8 -*-
"""
Complète uniquement les champs courts des 9 leçons signalées par l'audit.
Sauvegarde SQLite avant toute écriture. Aucun seed, aucune suppression.
À lancer depuis la racine du projet :
    python complete_missing_lesson_fields.py
"""
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

os.environ["AUTO_SEED_CONTENT"] = "0"

from app import app, db, CurriculumLesson, ExerciseAttempt
from curriculum_data import CURRICULUM


# Contenus pédagogiques complémentaires, ciblés sur les champs signalés.
CODE = {
    "Manipuler un système de fichiers avec prudence": """# Examiner avant de modifier
pwd                         # afficher le répertoire courant
ls -la                      # lister les fichiers, y compris cachés
find . -maxdepth 2 -type f  # repérer les fichiers proches

# Créer et copier sans écraser volontairement
mkdir -p sauvegarde
cp -n rapport.txt sauvegarde/rapport.txt

# Vérifier le chemin et les droits avant une action sensible
stat rapport.txt
ls -ld sauvegarde
chmod u+x script.sh         # ajouter l'exécution au propriétaire""",
    "Coder nombres et caractères": """def binaire_vers_decimal(bits):
    \"\"\"Convertit une chaîne binaire non signée en entier.\"\"\"
    if not bits or any(c not in "01" for c in bits):
        raise ValueError("Suite binaire invalide")
    return int(bits, 2)

def intervalle_non_signe(n):
    if n <= 0:
        raise ValueError("Le nombre de bits doit être positif")
    return 0, 2**n - 1

def intervalle_complement_a_deux(n):
    if n <= 0:
        raise ValueError("Le nombre de bits doit être positif")
    return -(2**(n-1)), 2**(n-1) - 1

print(binaire_vers_decimal("00001010"))  # 10
print(intervalle_non_signe(4))           # (0, 15)
print(intervalle_complement_a_deux(4))  # (-8, 7)""",
    "Comparer sans se fier à un seul chiffre": """def acceleration_amdahl(fraction_acceleree, facteur):
    if not 0 <= fraction_acceleree <= 1 or facteur <= 0:
        raise ValueError("Paramètres invalides")
    return 1 / ((1 - fraction_acceleree) +
                fraction_acceleree / facteur)

f = 0.80
s = 4
gain = acceleration_amdahl(f, s)
print(f"Accélération globale : {gain:.2f}")

# Toujours comparer la même tâche et la même métrique :
# durée, débit, consommation ou latence.""",
    "Produire un document accessible et cohérent": """# Procédure de structuration d'un document
1. Appliquer le style « Titre 1 » aux sections principales.
2. Appliquer « Titre 2 » aux sous-sections.
3. Générer la table des matières à partir des styles.
4. Ajouter un texte alternatif utile aux images informatives.
5. Vérifier le contraste, l'ordre de lecture et les liens.
6. Actualiser la table des matières avant l'export.

Exemple de hiérarchie :
Titre 1 : Présentation
    Titre 2 : Objectif
    Titre 2 : Méthode
Titre 1 : Résultats""",
    "Construire des formules recopiables": """# Exemples Excel en français
=A2*$B$1
# A2 est relative; $B$1 est absolue.

=$A2*B$1
# Colonne A figée; ligne 1 figée.

=SI(C2>=10;"Admis";"À revoir")
# Test conditionnel.

=SOMME(D2:D10)
=MOYENNE(D2:D10)

# Après recopie, contrôler les références et tester
# la formule sur une ligne dont le résultat est connu.""",
    "Comprendre couleur et taille d’image": """def taille_brute_octets(largeur, hauteur, bits_par_pixel):
    if min(largeur, hauteur, bits_par_pixel) <= 0:
        raise ValueError("Dimensions et profondeur positives requises")
    return largeur * hauteur * bits_par_pixel / 8

octets = taille_brute_octets(100, 100, 24)
print(f"{octets:.0f} octets")  # 30 000 octets

# Ce calcul ignore les métadonnées et la compression.
# 8 bits par canal × 3 canaux RVB = 24 bits/pixel.""",
    "Numériser un signal audio": """def debit_pcm(frequence_hz, bits_par_echantillon, canaux):
    if min(frequence_hz, bits_par_echantillon, canaux) <= 0:
        raise ValueError("Paramètres positifs requis")
    return frequence_hz * bits_par_echantillon * canaux

debit = debit_pcm(44_100, 16, 1)
print(f"{debit} bits/s")  # 705600 bits/s
print(f"{debit / 8:.0f} octets/s")

# Pour une durée t en secondes :
# taille brute en octets ≈ débit en bits/s × t / 8.""",
}

EXERCISES = {
    "Lire un préfixe CIDR": (
        "On considère l'adresse IPv4 192.168.10.77/26. "
        "1) Donner le masque décimal. 2) Calculer l'adresse réseau. "
        "3) Calculer l'adresse de diffusion. 4) Donner la plage d'adresses "
        "hôtes utilisables et le nombre d'hôtes utilisables.",
        "Un préfixe /26 laisse 6 bits pour les hôtes. Le masque est "
        "255.255.255.192. La taille du bloc dans le dernier octet est "
        "256-192=64. Les sous-réseaux commencent à 0, 64, 128 et 192. "
        "77 appartient au bloc 64–127 : réseau 192.168.10.64, diffusion "
        "192.168.10.127, hôtes utilisables 192.168.10.65 à 192.168.10.126. "
        "Le nombre d'hôtes utilisables est 2^6-2=62."
    ),
    "Distinguer codec et conteneur": (
        "Un fichier vidéo porte l'extension .mp4. Expliquez pourquoi cette "
        "extension ne suffit pas à garantir sa lecture sur tous les appareils. "
        "Précisez le rôle du conteneur, du codec vidéo, du codec audio et "
        "donnez deux vérifications à effectuer en cas de problème de lecture.",
        "MP4 désigne un conteneur : il organise les pistes et les métadonnées. "
        "Il ne désigne pas à lui seul le codec utilisé pour compresser la vidéo "
        "ou l'audio. Deux fichiers .mp4 peuvent donc contenir des codecs "
        "différents. Il faut identifier les codecs des pistes, puis vérifier "
        "que le lecteur et l'appareil les prennent en charge; vérifier aussi "
        "les paramètres comme le profil, la résolution et le débit."
    ),
}

EXTRA_FIELDS = {
    "Coder nombres et caractères": {
        "solution_fr": (
            "Sur n bits non signés, l'intervalle est [0, 2^n−1]. Sur 4 bits, "
            "le maximum vaut 15 (1111₂). En complément à deux sur n bits, "
            "l'intervalle est [−2^(n−1), 2^(n−1)−1]; sur 4 bits, il va de "
            "−8 à 7. Il faut toujours préciser la largeur et le caractère "
            "signé ou non signé. Unicode définit des points de code; UTF-8 "
            "est un encodage qui représente ces points par des séquences "
            "d'un à quatre octets."
        ),
        "revision_fr": (
            "À retenir : 1 octet = 8 bits. Sur n bits non signés : "
            "0 à 2^n−1. En complément à deux : −2^(n−1) à 2^(n−1)−1. "
            "Un dépassement de capacité survient lorsqu'un résultat sort "
            "de l'intervalle représentable. Unicode attribue des points "
            "de code aux caractères; UTF-8 définit leur encodage en octets. "
            "Ne pas confondre caractère, point de code et octet."
        ),
    }
}


def find_source_lessons():
    found = {}
    for subject in CURRICULUM:
        for module in subject["modules"]:
            for chapter in module["chapters"]:
                lesson = chapter["lesson"]
                found[lesson["title"]] = lesson
    return found


def sqlite_path():
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if not uri.startswith("sqlite:///"):
        raise RuntimeError(
            "La base configurée n'est pas SQLite. Arrêt sans modification."
        )
    raw = uri.replace("sqlite:///", "", 1)
    path = Path(raw)
    if not path.is_absolute():
        # Flask-SQLAlchemy résout les chemins SQLite relatifs dans instance/
        path = Path(app.instance_path) / path
    return path.resolve()


def make_backup(path):
    if not path.exists():
        raise FileNotFoundError(f"Base introuvable : {path}")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.stem}_before_missing_fields_{stamp}{path.suffix}")
    # SQLite backup API produit une copie cohérente, même si WAL est actif.
    source = sqlite3.connect(str(path))
    target = sqlite3.connect(str(backup))
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return backup


def main():
    with app.app_context():
        path = sqlite_path()
        backup = make_backup(path)
        source = find_source_lessons()
        updates = []
        missing = []

        # Compter les tentatives avant l'opération pour vérifier leur conservation.
        attempts_before = ExerciseAttempt.query.count()

        for lesson_title, code in CODE.items():
            lesson = CurriculumLesson.query.filter_by(title=lesson_title, published=True).one_or_none()
            if lesson is None:
                missing.append(lesson_title)
                continue
            if len((lesson.code_example or "").strip()) < 80:
                lesson.code_example = code
                updates.append((lesson_title, "code_example"))

        for lesson_title, (exercise, solution) in EXERCISES.items():
            lesson = CurriculumLesson.query.filter_by(title=lesson_title, published=True).one_or_none()
            if lesson is None:
                missing.append(lesson_title)
                continue
            if len((lesson.exercise_fr or "").strip()) < 100:
                lesson.exercise_fr = exercise
                updates.append((lesson_title, "exercise_fr"))
            if len((lesson.solution_fr or "").strip()) < 100:
                lesson.solution_fr = solution
                updates.append((lesson_title, "solution_fr"))

        for lesson_title, fields in EXTRA_FIELDS.items():
            lesson = CurriculumLesson.query.filter_by(title=lesson_title, published=True).one_or_none()
            if lesson is None:
                missing.append(lesson_title)
                continue
            for field, value in fields.items():
                if len((getattr(lesson, field) or "").strip()) < 100:
                    setattr(lesson, field, value)
                    updates.append((lesson_title, field))

        db.session.commit()
        attempts_after = ExerciseAttempt.query.count()

        print("\nMISE À JOUR TERMINÉE")
        print(f"Base : {path}")
        print(f"Sauvegarde : {backup}")
        print(f"Champs complétés : {len(updates)}")
        for title, field in updates:
            print(f"  OK - {title} [{field}]")
        if missing:
            print("Leçons introuvables ou non uniques :")
            for title in sorted(set(missing)):
                print(f"  - {title}")
        print(f"Tentatives avant/après : {attempts_before}/{attempts_after}")
        print("Aucun seed exécuté; aucun exercice, QCM, compte ou progression supprimé.")


if __name__ == "__main__":
    main()
