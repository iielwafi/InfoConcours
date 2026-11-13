export type CuratedFrenchVideo = {
  lessonTitle: string;
  title: string;
  channel: string;
  videoId: string;
  description: string;
};

/**
 * Curated YouTube suggestions for the 32-lesson curriculum.
 * Every item was matched to a French-language video result during research.
 * Imports are deliberately pending: an administrator must open, verify and publish each one.
 */
export const CURATED_FRENCH_VIDEOS: CuratedFrenchVideo[] = [
  {
    lessonTitle: "Écrire et tracer un algorithme",
    title: "Algorithmes 2 : écrire avec le pseudo-code ou un diagramme de flux",
    channel: "Pierre Huguet",
    videoId: "DKuy4SFLiuE",
    description: "Introduction à l’écriture d’un algorithme en pseudo-code et à sa représentation par diagramme de flux."
  },
  {
    lessonTitle: "Raisonner sur les répétitions",
    title: "Formation Python #2 : Les bases — variables, boucles, fonctions et bonnes pratiques",
    channel: "ItSkillsMaker",
    videoId: "UTkEDUl4atY",
    description: "Rappels sur les variables, les boucles for/while et les fonctions, avec une progression pour débutants."
  },
  {
    lessonTitle: "Parcourir et rechercher dans une séquence",
    title: "La recherche dichotomique — NSI Terminale",
    channel: "Clément Latek",
    videoId: "EbPJjKYqXr8",
    description: "Recherche exhaustive et recherche dichotomique dans un tableau trié, avec script Python et comparaison du nombre d’opérations."
  },
  {
    lessonTitle: "Décomposer un problème et analyser son coût",
    title: "Introduction à l’analyse de complexité algorithmique — Notation grand O",
    channel: "Ingécodeur",
    videoId: "0fmfnXAPLdA",
    description: "Notion de complexité temporelle, nombre d’opérations, notation grand O et comparaison des ordres de grandeur."
  },
  {
    lessonTitle: "Écrire des fonctions fiables",
    title: "Fonctions Python — Maîtrisez les fonctions en Python",
    channel: "MaxCode",
    videoId: "9XQuZAtcans",
    description: "Création et utilisation des fonctions, paramètres, arguments nommés, valeurs par défaut et portée des variables."
  },
  {
    lessonTitle: "Organiser les données en collections",
    title: "Formation Python #3 : Structures de données essentielles",
    channel: "ItSkillsMaker",
    videoId: "iVGk7DJD0cc",
    description: "Présentation pratique des listes, dictionnaires, tuples et ensembles, avec critères de choix."
  },
  {
    lessonTitle: "Modéliser avec la programmation orientée objet",
    title: "Programmation orientée objet — Introduction",
    channel: "Programming With HAIRIBI",
    videoId: "IPNkfaQFjr4",
    description: "Introduction à la POO, aux classes et objets, à l’encapsulation, à l’héritage et au polymorphisme."
  },
  {
    lessonTitle: "Vérifier un programme par des tests",
    title: "Introduction aux tests unitaires avec la bibliothèque Unittest en Python",
    channel: "Donald Programmer",
    videoId: "cLG3KBVY3CA",
    description: "Pourquoi tester un programme, structurer des tests unitaires et les exécuter avec unittest."
  },
  {
    lessonTitle: "Passer d’un besoin à un modèle relationnel",
    title: "Cours Modèle Relationnel et MCD",
    channel: "E mds",
    videoId: "VFHVNA8xgK0",
    description: "Conception d’une base relationnelle, MCD, MLD, entités, associations, cardinalités et clés."
  },
  {
    lessonTitle: "Réduire les anomalies de données",
    title: "Maîtriser la normalisation des bases de données : 1FN, 2FN, 3FN",
    channel: "Yves Programmeur",
    videoId: "6bLRBNBhNCI",
    description: "Normalisation relationnelle et formes normales pour limiter les redondances et anomalies de mise à jour."
  },
  {
    lessonTitle: "Construire une requête SQL lisible",
    title: "Apprenez la commande SELECT en SQL de A à Z",
    channel: "Gickel OKABI | AntalaSchool",
    videoId: "TPhkdwMNvlU",
    description: "SELECT, WHERE, ORDER BY, DISTINCT, LIMIT, fonctions d’agrégation, GROUP BY et HAVING."
  },
  {
    lessonTitle: "Garantir cohérence et accès efficaces",
    title: "SQL pour débutants — Jointures, sous-requêtes et vues",
    channel: "LeCoinStat",
    videoId: "g9yC8pcdRFc",
    description: "Jointures INNER/LEFT/RIGHT, relations entre tables, sous-requêtes et vues pour exploiter les données."
  },
  {
    lessonTitle: "Partager le processeur",
    title: "Scheduling de processus — Systèmes d’exploitation",
    channel: "Mokaddem Mostéfa",
    videoId: "wdk1_iVP4aE",
    description: "Ordonnancement FCFS, SJF, priorité et Round Robin, diagrammes de Gantt et calcul des temps d’attente."
  },
  {
    lessonTitle: "Comprendre mémoire et pagination",
    title: "Mémoire virtuelle 1",
    channel: "Mokaddem Mostéfa",
    videoId: "bG1eeKhnkUk",
    description: "Mémoire virtuelle, pagination, segmentation, tables de pages, swap et défauts de page."
  },
  {
    lessonTitle: "Manipuler un système de fichiers avec prudence",
    title: "Apprendre chmod et chown — 3 exercices Linux pour débutants",
    channel: "Wael Tech School",
    videoId: "TNelX5gZhmA",
    description: "Permissions de lecture, écriture et exécution, droits utilisateur/groupe/autres et commandes chmod/chown."
  },
  {
    lessonTitle: "Protéger disponibilité et accès",
    title: "MasterClass cybersécurité — Disponibilité, intégrité, confidentialité et traçabilité",
    channel: "Yelentic",
    videoId: "KRnbOoww1pE",
    description: "Piliers de sécurité CIA, disponibilité des services, intégrité, confidentialité, contrôle des accès et traçabilité."
  },
  {
    lessonTitle: "Situer les protocoles dans les couches réseau",
    title: "Comprendre les modèles OSI et TCP/IP",
    channel: "Cookie connecté",
    videoId: "26jazyc7VNk",
    description: "Couches OSI et TCP/IP, encapsulation, unités de données, commutateurs et routeurs."
  },
  {
    lessonTitle: "Lire un préfixe CIDR",
    title: "Réseaux : adresse IP et masques de sous-réseaux",
    channel: "Ludovic Guérin — Cours de SI",
    videoId: "RnpSaDSSjR4",
    description: "Adressage IPv4, masque de sous-réseau, plages d’adresses et calculs de sous-réseaux."
  },
  {
    lessonTitle: "Choisir un transport selon le besoin",
    title: "Cours Réseaux — Étude de TCP, UDP et la notion de port",
    channel: "Moustapha Fall — Formation Réseau IP",
    videoId: "Up44zrox_HI",
    description: "Différences entre TCP et UDP, rôle des ports et choix du protocole de transport."
  },
  {
    lessonTitle: "Suivre la résolution d’un nom et une requête Web",
    title: "Introduction à la gestion DHCP et DNS",
    channel: "WEWANTCODE",
    videoId: "r-s_oKc_cQU",
    description: "Introduction aux rôles du DNS et du DHCP dans un réseau et à leur utilisation pour gérer les postes clients."
  },
  {
    lessonTitle: "Suivre une instruction dans le processeur",
    title: "Étapes d’exécution d’une instruction par le processeur",
    channel: "MEHDI.ma20",
    videoId: "NxqS44Op1YU",
    description: "Cycle d’exécution d’une instruction, CPU, registres, unité de contrôle, ALU, bus et architecture de Von Neumann."
  },
  {
    lessonTitle: "Coder nombres et caractères",
    title: "Codage de l’information : binaire et hexadécimal",
    channel: "Stefan Maurer",
    videoId: "znIvv1lUoWo",
    description: "Conversions décimal/binaire et décimal/hexadécimal, représentation des textes et codage des couleurs."
  },
  {
    lessonTitle: "Produire un document accessible et cohérent",
    title: "Créer une table des matières automatique — styles et numérotation des titres dans Word",
    channel: "Thom Reo — Cours & Tutos",
    videoId: "71645Z8g7rY",
    description: "Styles de titres, hiérarchie du document, numérotation automatique et table des matières."
  },
  {
    lessonTitle: "Construire des formules recopiables",
    title: "Formation Excel : références relatives et absolues et premiers calculs",
    channel: "Tintin Digital",
    videoId: "BmWw2yza3PQ",
    description: "Références relatives, absolues et mixtes, symbole dollar et recopie de formules sans décaler les cellules fixes."
  },
  {
    lessonTitle: "Résumer des données sans les déformer",
    title: "Excel — Maîtriser les tableaux croisés dynamiques",
    channel: "Axel Formateur Excel",
    videoId: "1v-mibStd80",
    description: "Créer un tableau croisé dynamique, résumer, filtrer, agréger et extraire des données."
  },
  {
    lessonTitle: "Préparer un support pédagogique clair",
    title: "PowerPoint — Tuto simple pour faire une présentation efficace",
    channel: "WizAide",
    videoId: "iOxHd3xZB3I",
    description: "Structure des diapositives, lisibilité, choix visuels, animations et préparation d’une présentation orale."
  },
  {
    lessonTitle: "Numériser un signal audio",
    title: "De l’analogique vers le numérique",
    channel: "Ressource pédagogique BTS SNIR",
    videoId: "wQUQk5QG630",
    description: "Numérisation d’un signal analogique et bases de l’échantillonnage et de la quantification d’un signal acoustique."
  },
  {
    lessonTitle: "Distinguer codec et conteneur",
    title: "Les codecs vidéo : le mystère de la compression",
    channel: "Itsmecedlu",
    videoId: "1KmYni-MePs",
    description: "Rôle des codecs de compression vidéo, H.264, H.265/HEVC, ProRes et compromis entre taille et qualité."
  }
];

export const MISSING_FRENCH_VIDEO_LESSONS = [
  "Comparer cache, RAM et stockage",
  "Comparer sans se fier à un seul chiffre",
  "Choisir un format d’image",
  "Comprendre couleur et taille d’image",
] as const;
