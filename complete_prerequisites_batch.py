"""Complete short prerequisites for InfoConcours lessons without touching learner progress.
Run from project root: python complete_prerequisites_batch.py
"""
from __future__ import annotations
import os, shutil, sqlite3
from datetime import datetime
from pathlib import Path

os.environ["AUTO_SEED_CONTENT"] = "0"

from app import create_app, db, CurriculumLesson, CurriculumChapter, CurriculumModule, CurriculumSubject

EXPECTED_DB = "infoconcours-phase8-dev.db"
PREREQUISITES = {
    "Parcourir et rechercher dans une séquence": "Savoir déclarer une variable, utiliser une boucle, comparer deux valeurs et manipuler une séquence d’éléments. Connaître les indices et la notion de condition d’arrêt.",
    "Décomposer un problème et analyser son coût": "Savoir lire un algorithme, identifier ses entrées et sorties, suivre une boucle et effectuer des opérations arithmétiques simples. Connaître les notions de variable, instruction et comparaison.",
    "Écrire des fonctions fiables": "Connaître les variables, les types de base, les conditions et les boucles en Python. Savoir lire un appel de fonction et distinguer une valeur retournée d’un affichage.",
    "Organiser les données en collections": "Maîtriser les variables, les types numériques et chaînes de caractères, les conditions, les boucles et les fonctions simples en Python. Savoir parcourir une séquence.",
    "Modéliser avec la programmation orientée objet": "Savoir écrire et appeler une fonction Python, utiliser des variables et des collections, et comprendre la différence entre une donnée et une opération qui la traite.",
    "Vérifier un programme par des tests": "Savoir écrire une fonction Python avec des paramètres et une valeur de retour. Connaître les conditions, les exceptions simples et les types de données usuels.",
    "Réduire les anomalies de données": "Connaître les tables, les lignes, les colonnes, les clés primaires et étrangères ainsi que les relations entre tables. Savoir lire un schéma relationnel simple.",
    "Construire une requête SQL lisible": "Connaître le modèle relationnel, les tables, les colonnes, les clés et les types de données. Maîtriser les opérations de sélection, filtrage et tri dans un tableau de données.",
    "Garantir cohérence et accès efficaces": "Savoir écrire une requête SELECT avec WHERE et JOIN. Connaître les clés primaires, les clés étrangères, les contraintes d’intégrité et le rôle général d’un index.",
    "Partager le processeur": "Connaître le rôle d’un système d’exploitation, la notion de processus et la différence entre programme et processus. Comprendre qu’un processeur exécute des instructions.",
    "Comprendre mémoire et pagination": "Connaître les notions de processus, mémoire vive, adresse et système d’exploitation. Savoir distinguer mémoire principale et stockage secondaire.",
    "Manipuler un système de fichiers avec prudence": "Savoir utiliser les notions de fichier, dossier, chemin absolu et chemin relatif. Connaître les opérations de création, lecture, copie, déplacement et suppression.",
    "Protéger disponibilité et accès": "Connaître les comptes utilisateurs, les groupes, les fichiers, les permissions et les processus. Comprendre les notions de sauvegarde, panne et mise à jour.",
    "Situer les protocoles dans les couches réseau": "Connaître les notions de réseau, hôte, adresse IP, paquet et communication client-serveur. Savoir distinguer une application d’un équipement réseau.",
    "Lire un préfixe CIDR": "Connaître l’écriture binaire, les octets et la structure générale d’une adresse IPv4. Savoir effectuer des divisions par puissances de deux et comprendre le rôle d’un masque.",
    "Choisir un transport selon le besoin": "Connaître les adresses IP, les ports et le modèle client-serveur. Comprendre qu’une application échange des données à travers le réseau.",
    "Suivre la résolution d’un nom et une requête Web": "Connaître les notions d’adresse IP, de nom de domaine, de client, de serveur et de protocole. Savoir distinguer une requête et une réponse.",
    "Suivre une instruction dans le processeur": "Connaître les notions de programme, instruction, processeur, mémoire et registre. Savoir qu’une instruction peut être décodée puis exécutée.",
    "Comparer cache, RAM et stockage": "Connaître les unités de capacité (octet, Ko, Mo, Go), la notion de mémoire et la différence entre données temporaires et données conservées.",
    "Coder nombres et caractères": "Connaître les systèmes décimal et binaire, les puissances de deux et les unités d’information. Savoir effectuer une conversion simple entre bases.",
    "Comparer sans se fier à un seul chiffre": "Connaître les unités de fréquence, de durée et de capacité, ainsi que les notions de processeur, mémoire et stockage. Savoir interpréter une mesure avec son unité.",
    "Produire un document accessible et cohérent": "Savoir utiliser un traitement de texte, saisir et organiser des paragraphes, appliquer une mise en forme et enregistrer un document.",
    "Construire des formules recopiables": "Connaître les cellules, lignes, colonnes et références d’une feuille de calcul. Savoir saisir une formule simple et effectuer les quatre opérations.",
    "Résumer des données sans les déformer": "Savoir organiser des données dans un tableau, reconnaître les lignes et colonnes, calculer somme, moyenne et effectif, et lire un graphique simple.",
    "Préparer un support pédagogique clair": "Savoir structurer un document ou une présentation, hiérarchiser les titres, choisir des visuels lisibles et adapter le contenu au public visé.",
    "Choisir un format d’image": "Connaître les notions de fichier, extension, pixel, résolution et compression. Savoir distinguer une image matricielle d’une image vectorielle.",
    "Comprendre couleur et taille d’image": "Connaître les pixels, la résolution, les dimensions et les principaux formats d’image. Comprendre les notions de couleur et de profondeur de codage.",
    "Numériser un signal audio": "Connaître les notions de signal, fréquence et amplitude. Savoir qu’un son analogique varie continûment et qu’un ordinateur manipule des valeurs numériques.",
    "Distinguer codec et conteneur": "Connaître les notions de fichier audio/vidéo, compression, format et extension. Comprendre la différence entre les données multimédias et leur emballage."
}

def main():
    app = create_app()
    with app.app_context():
        uri = app.config["SQLALCHEMY_DATABASE_URI"]
        if not uri.startswith("sqlite:///"):
            raise SystemExit("STOP : la base configurée n'est pas SQLite.")
        db_path = Path(app.instance_path) / uri.split("sqlite:///", 1)[1]
        if db_path.name != EXPECTED_DB or db_path.parent.name != "instance" or not db_path.exists():
            raise SystemExit(f"STOP : base inattendue ou introuvable : {db_path}")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = db_path.with_name(f"{db_path.stem}_before_prerequisites_{stamp}.db")
        shutil.copy2(db_path, backup)

        changed = []
        missing = []
        for lesson in CurriculumLesson.query.all():
            title = (lesson.title or "").strip()
            target = PREREQUISITES.get(title)
            if not target:
                continue
            current = (lesson.prerequisites_fr or "").strip()
            if len(current) < 90:
                lesson.prerequisites_fr = target
                changed.append(title)
        for title in PREREQUISITES:
            if not CurriculumLesson.query.filter_by(title=title).first():
                missing.append(title)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        print("MISE A JOUR TERMINEE")
        print(f"Base : {db_path}")
        print(f"Sauvegarde : {backup}")
        print(f"Prérequis complétés : {len(changed)}")
        for title in changed:
            print(f"  OK - {title}")
        if missing:
            print("Titres non trouvés : " + " ; ".join(missing))
        print("Aucun exercice, QCM, tentative, compte ou progression n'a été modifié.")

if __name__ == "__main__":
    main()
