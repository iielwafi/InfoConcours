"""Authored, chapter-specific teaching material for the eight-subject academy.

Each record adds a worked method and three distinct examples. Existing seed
records are enriched only when their original text has not been edited.
"""

PHASE8_DETAILS = {
"Données, conditions et itérations": {
"objectives": ["Écrire un algorithme avec des entrées, traitements et sorties explicites.", "Justifier les bornes d’une boucle et vérifier les cas limites."],
"terms": ["Une variable est une case logique associée à un nom et à une valeur courante; une affectation remplace cette valeur.", "Une condition est une expression booléenne; une boucle répète un bloc selon un nombre fixé ou une condition d’arrêt."],
"sections": ["Commencer par le contrat : préciser ce que l’algorithme reçoit, ce qu’il doit produire et les contraintes sur les données. Une bonne description sépare saisie, calcul et affichage. Pour un maximum, il faut décider comment traiter une entrée vide et si des égalités sont possibles avant de choisir l’algorithme.", "L’affectation se lit de droite à gauche : on calcule l’expression puis on mémorise le résultat. Dans une condition SI/SINON, une seule branche est exécutée selon la valeur vraie ou fausse du test. Une boucle POUR convient lorsque les répétitions sont dénombrables; TANT QUE convient lorsque la fin dépend des données, à condition de faire progresser l’état vers l’arrêt.", "Une trace est une exécution manuelle structurée. Écrire une ligne par opération, avec les variables pertinentes, fait apparaître les erreurs d’ordre et de mise à jour. Une boucle correcte possède une initialisation, une condition, une transformation qui progresse et un résultat lisible après la terminaison."],
"examples": ["Maximum : pour [4, 9, 2], initialiser m à 4, comparer 9 puis 2; m vaut successivement 4, 9, 9. Le résultat est 9.", "Moyenne : lire n notes, accumuler somme et effectif, puis calculer somme/effectif seulement si l’effectif est positif; n=0 doit produire un message défini.", "Validation d’âge : relire tant que l’âge est négatif; la saisie 12 termine la boucle et satisfait la contrainte. Une condition de lecture qui ne change jamais peut boucler indéfiniment."],
"demo": "Pour compter les notes au moins égales à 10, initialiser compteur à 0; parcourir chaque note; si note ≥ 10, incrémenter compteur; afficher compteur après le parcours. Sur [8, 10, 13], le compteur évolue 0, 1, 2 et la sortie vaut 2.",
"review": ["Entrée vide et valeur minimale", "Valeur exactement sur la borne", "Une valeur au-dessus de la borne", "Condition qui devient fausse", "Variable mise à jour à chaque tour"]},
"Boucles imbriquées et invariants": {
"objectives": ["Déterminer les tours exécutés par des boucles à bornes inclusives ou exclusives.", "Énoncer un invariant vérifiable avant et après une itération."],
"terms": ["Un invariant de boucle est une propriété vraie à l’initialisation et conservée par chaque itération; il aide à relier l’état courant au résultat visé.", "Dans des boucles imbriquées, la boucle interne repart généralement de son initialisation à chaque nouveau tour externe."],
"sections": ["Pour une boucle allant de a à b inclus par pas de 1, le nombre de valeurs est b−a+1 lorsque b≥a. Pour un pas de taille k, compter les termes réellement atteints; ne pas appliquer mécaniquement la formule si la borne n’est pas divisible par k.", "Si une boucle externe a n tours et l’interne m tours pour chacun, le corps s’exécute n×m fois. Si la taille interne dépend de i, sommer les tours plutôt que multiplier deux bornes; par exemple 1+2+…+n vaut n(n+1)/2.", "Pour prouver un invariant, montrer qu’il est vrai avant le premier tour, qu’un tour le conserve, puis interpréter l’invariant à la sortie. Une boucle qui ne modifie pas la variable de contrôle peut ne jamais terminer; un pas de signe incompatible avec la condition peut aussi l’éloigner de la sortie."],
"examples": ["i de 0 à 5 inclus fait 6 tours; j de 1 à 2 fait 2 tours par i, soit 12 affichages.", "Pour afficher un triangle de n lignes d’étoiles, la ligne i affiche i symboles : le total est 1+…+n = n(n+1)/2.", "Dans une recherche de minimum, après k éléments traités, l’invariant ‘m est le minimum des k premiers’ permet de conclure lorsque k atteint n."],
"demo": "Trace i=1..3 et j=1..i : pour i=1, un tour; i=2, deux; i=3, trois. Total 6. L’invariant de la boucle interne est que les j premières positions de la ligne i ont été affichées; à sa fin, la ligne contient exactement i symboles.",
"review": ["Bornes inclusives ou exclusives", "Réinitialisation de la variable interne", "Pas de boucle et sens de progression", "Taille fixe ou dépendante", "Invariant initial, conservé puis interprété"]},
"Tableaux, recherches et tris": {
"objectives": ["Écrire un parcours qui respecte les indices valides.", "Choisir une recherche adaptée à l’ordre et au nombre de requêtes."],
"terms": ["Un tableau est une séquence indexée; selon le langage, les indices commencent à 0 ou à 1. Pour n éléments à partir de 0, le dernier indice est n−1.", "La recherche séquentielle examine les éléments jusqu’à trouver la cible ou atteindre la fin; la dichotomie exige un ordre trié et maintient un intervalle candidat."],
"sections": ["Dans un parcours, l’indice doit rester dans l’intervalle valide. Pour un tableau de longueur n indexé à partir de 0, la condition usuelle est i<n, et non i≤n. La recherche séquentielle fonctionne même sans tri et a un coût O(n) au pire.", "La dichotomie compare la cible à l’élément médian. Si la cible est plus petite, conserver la moitié gauche; si elle est plus grande, conserver la droite. L’intervalle doit rétrécir à chaque tour. Le nombre de comparaisons croît comme O(log n), mais les données doivent être triées et l’accès au milieu efficace.", "Un tri coûte du temps et parfois de la mémoire. Si une seule recherche est faite, le tri peut coûter plus qu’il n’économise. Pour de nombreuses recherches dans des données qui changent peu, le tri préalable peut être rentable. Il faut aussi définir le comportement avec doublons et la position renvoyée."],
"examples": ["Dans [2, 5, 8, 11, 15, 20, 24], chercher 15 : milieu 11, aller à droite; nouveau milieu 20, aller à gauche; trouver 15.", "Dans [7, 3, 9], rechercher 3 par séquentiel examine 7 puis 3; la dichotomie n’est pas valide avant tri.", "Sur un tableau vide, la recherche renvoie ‘absent’ sans tenter d’accéder à l’indice 0; ce cas détecte une erreur fréquente de borne."],
"demo": "Recherche séquentielle : i=0; tant que i<n et T[i]≠x, augmenter i. À la sortie, si i<n alors x se trouve en T[i], sinon il est absent. Pour [4, 6, 9] et x=9, les comparaisons se font aux indices 0, 1 puis 2.",
"review": ["Longueur n et dernier indice n−1", "Tableau trié avant dichotomie", "Mise à jour cohérente de gauche et droite", "Cible absente", "Coût du tri compris dans le choix"]},
"Récursivité, piles et complexité": {
"objectives": ["Écrire une relation récursive avec cas de base et argument qui se rapproche de ce cas.", "Simuler une pile ou une file et estimer un ordre de croissance simple."],
"terms": ["Un appel récursif est un appel de fonction depuis cette même fonction; les appels non terminés occupent des cadres dans la pile d’exécution.", "Une pile retire le dernier élément ajouté (LIFO); une file retire le premier ajouté (FIFO). O(g(n)) décrit une croissance asymptotique, pas un temps exact."],
"sections": ["Une définition récursive doit couvrir les cas de base et réduire strictement la taille du problème. Pour factorielle, fact(0)=1 et fact(n)=n×fact(n−1) pour n>0. Les entrées négatives doivent être refusées ou traitées, sans quoi la réduction n’atteint pas le cas de base.", "À l’appel, paramètres et point de reprise sont empilés; au retour, les résultats se combinent dans l’ordre inverse. La profondeur d’appels détermine la mémoire de pile. Une version itérative peut éviter une grande profondeur, même si les deux méthodes calculent le même résultat.", "Pour estimer le coût, compter les opérations dominantes en fonction de n. Une boucle simple sur n éléments donne O(n); deux boucles complètes imbriquées donnent O(n²); diviser la taille par deux donne O(log n). On ignore les constantes pour comparer les tendances, pas pour prédire une durée précise."],
"examples": ["fact(4) appelle fact(4), fact(3), fact(2), fact(1), fact(0), puis remonte vers 24.", "Une pile reçoit A puis B; retirer renvoie B. Une file reçoit A puis B; retirer renvoie A.", "Pour n=1000, un parcours linéaire peut examiner environ 1000 éléments; une recherche dichotomique en examine environ 10, sous réserve du tri préalable."],
"demo": "Pour somme(n)=1+…+n : définir somme(0)=0; sinon somme(n)=n+somme(n−1). Pour n=3, la descente est 3+somme(2), 2+somme(1), 1+somme(0), puis les retours donnent 1, 3, 6. La profondeur est proportionnelle à n.",
"review": ["Cas de base atteignable", "Taille réduite à chaque appel", "Ordre d’empilement et de retour", "Pile/file distinguées", "Complexité exprimée en fonction de n"]},
"Types, contrôle et fonctions": {
"objectives": ["Choisir types et contrats de fonction explicites.", "Écrire des fonctions testables avec des retours et des erreurs maîtrisés."],
"terms": ["Un paramètre est une donnée reçue par une fonction; une valeur retournée est le résultat transmis à l’appelant. Afficher avec print ne remplace pas return.", "Une précondition précise ce qui doit être vrai à l’appel; une postcondition décrit le résultat garanti si l’appel réussit."],
"sections": ["Choisir un type selon le domaine : entier pour un effectif, booléen pour un état, chaîne pour un identifiant textuel, liste pour une séquence modifiable. Un type flottant ne représente pas exactement toutes les fractions décimales; pour des montants, une représentation décimale adaptée peut être nécessaire.", "Une fonction claire fait une tâche cohérente, reçoit ses dépendances en paramètres et renvoie un résultat. Documenter les unités, les valeurs acceptées et les exceptions évite les contrats implicites. Les noms doivent exprimer la responsabilité plutôt qu’un détail d’implémentation.", "Valider aux frontières du programme : conversion, domaine numérique et cas vide. Intercepter une exception attendue, telle que ValueError lors d’une conversion utilisateur, mais ne pas masquer toutes les exceptions avec un bloc trop large."],
"examples": ["moyenne([10, 14, 16]) renvoie 40/3; la liste vide est rejetée explicitement pour éviter la division par zéro.", "Une fonction aire_rectangle(longueur, largeur) vérifie des dimensions non négatives puis renvoie leur produit, sans afficher le résultat elle-même.", "La chaîne ‘007’ peut être un identifiant et doit rester chaîne si les zéros initiaux ont du sens; la convertir en entier la transforme en 7."],
"demo": "Définir moyenne(notes) : vérifier que notes n’est pas vide; vérifier que chaque note respecte [0,20]; calculer somme(notes)/len(notes); retourner le nombre. Tester [10,14] → 12, [20] → 20 et [] → erreur documentée.",
"review": ["Type cohérent avec le sens", "Paramètres et retour explicites", "Valeur vide ou hors domaine traitée", "Exceptions attendues seulement", "Tests liés au contrat"]},
"Collections, fichiers et erreurs": {
"objectives": ["Sélectionner une collection selon l’ordre, l’unicité et l’accès souhaités.", "Lire un fichier et traiter les erreurs de saisie sans perdre de données."],
"terms": ["Une liste conserve un ordre et peut être modifiée; un tuple est ordonné et immuable; un dictionnaire associe une clé à une valeur; un ensemble conserve des éléments uniques.", "Une exception signale une situation qui empêche l’opération normale; la clause finally ou le gestionnaire with assure la libération de ressources."],
"sections": ["Choisir une structure par les opérations dominantes. Une liste convient à une séquence, un dictionnaire à une recherche par clé, un ensemble à l’appartenance et à l’élimination de doublons. Les dictionnaires exigent des clés uniques; une nouvelle affectation à la même clé remplace l’ancienne valeur.", "Ouvrir les fichiers avec with garantit la fermeture après lecture même si une erreur arrive. Préciser l’encodage pour le texte, distinguer ligne vide et fin de fichier, et ne pas supposer que le fichier existe ou que le format est correct.", "Une erreur de données prévisible doit produire un message utile et permettre une reprise lorsque c’est raisonnable. Ne pas intercepter indistinctement toute exception : cela peut cacher un défaut du programme. Valider puis transformer les données avec une stratégie annoncée."],
"examples": ["Compter des mots : dictionnaire fréquence; pour chaque mot normalisé, faire fréquence[mot]=fréquence.get(mot,0)+1.", "Retirer les doublons d’une liste sans perdre l’ordre peut se faire en parcourant et en ajoutant seulement les éléments jamais vus, tout en gardant un ensemble des éléments rencontrés.", "Lire un fichier CSV avec encodage UTF-8 dans un bloc with; si le fichier est absent, signaler le chemin attendu sans imprimer de fausse réussite."],
"demo": "Lire des entiers depuis une ligne : découper sur les espaces; convertir chaque élément dans un try limité à ValueError; rejeter la ligne entière si une valeur est invalide. La politique ‘tout ou rien’ évite un résultat partiel silencieux.",
"review": ["Ordre et doublons nécessaires ?", "Clé de dictionnaire stable ?", "Fichier fermé automatiquement ?", "Encodage et format explicités ?", "Exception attendue distinguée du défaut"]},
"Classes et objets": {
"objectives": ["Distinguer la définition d’une classe de ses instances.", "Protéger les invariants et choisir entre composition et héritage."],
"terms": ["Une classe définit une forme d’état et des opérations; une instance est un objet concret avec ses propres valeurs d’attributs.", "L’encapsulation protège un invariant par l’interface publique; la composition construit un objet à partir d’autres objets, tandis que l’héritage exprime une spécialisation de type."],
"sections": ["Décrire d’abord les responsabilités : quelles données appartiennent à l’objet et quelles opérations doivent rester cohérentes ensemble ? Un constructeur établit l’état initial valide. Les méthodes modifient l’état en maintenant les invariants.", "L’encapsulation n’est pas simplement rendre un attribut ‘privé’; c’est éviter que tout appelant puisse placer l’objet dans un état incohérent. En Python, la convention de nommage et les propriétés aident, mais il faut surtout définir un contrat et vérifier les entrées.", "N’utiliser l’héritage que si chaque sous-type peut remplacer le type parent sans casser son contrat. Si l’objet ‘contient’ un autre rôle ou service, la composition est généralement plus claire. La redéfinition de méthode doit préserver le sens attendu et peut appeler super() lorsque cela respecte le contrat."],
"examples": ["Compte : solde initial ≥0; deposer refuse un montant ≤0; retirer refuse un montant supérieur au solde; chaque opération maintient solde≥0.", "Une classe Élève peut contenir une liste de Résultats; les résultats sont des objets composés, sans faire hériter Élève de Résultat.", "Si Carré hérite de Rectangle mais que modifier largeur change la hauteur, il viole les attentes d’un rectangle mutable; une classe Forme avec aire() peut être une abstraction plus sûre."],
"demo": "Modéliser un compte : constructeur contrôle solde initial; retirer(montant) vérifie montant positif et solde suffisant; il ne modifie le solde qu’après les contrôles; le test confirme que solde avant = solde après + montant retiré.",
"review": ["Responsabilité de la classe claire", "Invariant établi au constructeur", "Méthodes qui préservent l’état", "Héritage justifié par une relation ‘est un’", "Composition envisagée avant hiérarchie profonde"]},
"Tests et débogage": {
"objectives": ["Concevoir des tests nominaux, limites et erreurs à partir d’un contrat.", "Localiser un défaut par reproduction minimale et observation d’état."],
"terms": ["Un cas de test associe une entrée, un résultat attendu et une observation réelle; une assertion exprime une propriété à vérifier.", "Un test de régression conserve un cas qui échouait avant une correction afin de détecter le retour du même défaut."],
"sections": ["Construire les tests depuis les classes d’équivalence et frontières du contrat, et non seulement depuis les lignes du code. Pour une recherche, tester cible présente et absente, tableau vide, singleton, extrémités et doublons selon la spécification.", "Quand un test échoue, lire le message et réduire l’entrée jusqu’au plus petit cas reproductible. Comparer attendu et observé à chaque étape et formuler une hypothèse précise; changer une seule cause à la fois.", "La correction fonctionnelle signifie que le programme respecte le contrat. La performance concerne le temps ou la mémoire pour une charge donnée. Optimiser d’abord une solution correcte et mesurée; une amélioration supposée peut compliquer le code sans bénéfice."],
"examples": ["max([]) doit soit retourner une valeur définie par contrat, soit lever une erreur annoncée; le test de liste vide rend la décision explicite.", "Pour convertir une note, tester ‘12’ (nominal), ‘0’ et ‘20’ (bornes), ‘21’ (hors domaine), et ‘abc’ (type invalide).", "Une recherche dichotomique qui échoue sur [2,4] avec cible 4 peut être réduite à ce seul tableau pour examiner le calcul du milieu et la mise à jour de borne."],
"demo": "Pour diagnostiquer un décompte erroné : écrire l’entrée minimale, calculer le résultat attendu à la main, tracer la variable compteur après chaque élément, localiser la première divergence, corriger, puis garder le cas comme test automatique.",
"review": ["Résultat attendu calculable indépendamment", "Cas nominal et limites", "Défaut reproductible minimal", "Première divergence repérée", "Test de régression ajouté"]},
"Entités, relations et contraintes": {
"objectives": ["Transformer les besoins en entités, attributs, associations et cardinalités.", "Choisir clés et contraintes pour empêcher les références incohérentes."],
"terms": ["Une clé primaire identifie une ligne; une clé étrangère référence une clé candidate d’une autre table et impose l’intégrité référentielle.", "Une relation plusieurs-à-plusieurs est représentée par une table d’association, souvent dotée d’une clé composée et d’attributs propres à l’association."],
"sections": ["Lire les règles de gestion avant de dessiner les tables. Les noms importants ne sont pas tous des entités : une caractéristique simple peut être attribut, tandis qu’un concept avec identité, cycle de vie ou relations propres mérite souvent sa table.", "Déterminer les cardinalités minimale et maximale dans chaque sens. Si un étudiant suit plusieurs cours et qu’un cours accueille plusieurs étudiants, créer Inscription(etudiant_id, cours_id, date). La date appartient à l’inscription, pas nécessairement à l’étudiant ni au cours.", "Ajouter les contraintes là où elles protègent réellement le modèle : NOT NULL pour une valeur obligatoire, UNIQUE pour une unicité métier, CHECK pour un domaine simple, FK pour les références. Choisir suppression en cascade ou restriction selon la conservation attendue."],
"examples": ["Client(id, nom) et Commande(id, client_id, date); client_id référence Client et une commande ne peut pointer vers un client absent.", "Étudiant–Cours est plusieurs-à-plusieurs; Inscription possède une contrainte UNIQUE(etudiant_id,cours_id) si une seule inscription active est permise.", "Une ligne de commande a quantité et prix_unitaire au moment de la vente; ces faits décrivent la ligne de commande, même si le produit change de prix plus tard."],
"demo": "Besoin ‘un enseignant peut donner plusieurs cours et un cours peut avoir plusieurs enseignants’ : créer Enseignant, Cours, Affectation(enseignant_id,cours_id,année); faire des deux identifiants une clé composée si une seule affectation par paire et année est autorisée.",
"review": ["Identités de ligne explicites", "Cardinalités écrites dans les deux sens", "Association pour M:N", "Clés étrangères sans orphelins", "Contraintes déduites des règles métier"]},
"Normalisation et qualité": {
"objectives": ["Repérer les dépendances fonctionnelles et les anomalies dues aux répétitions.", "Proposer une décomposition qui conserve les faits nécessaires."],
"terms": ["X→Y signifie que dans les lignes valides, une même valeur de X détermine une seule valeur de Y.", "Une anomalie d’insertion, de modification ou de suppression apparaît lorsqu’un même fait est stocké dans plusieurs endroits dépendants."],
"sections": ["La normalisation examine la signification des attributs, pas seulement la forme visuelle d’une table. Dans Produit(id, nom, categorie_id, categorie_nom), si categorie_id détermine categorie_nom, ce nom est répété dans chaque produit de la catégorie.", "Séparer les faits indépendants réduit les anomalies : Produit référence Catégorie, et le nom de catégorie apparaît une fois. La jointure reconstitue les informations. Vérifier que les clés et dépendances métier sont respectées après décomposition.", "La troisième forme normale est souvent présentée comme l’absence de dépendances transitives inappropriées des attributs non-clés sur la clé; la définition formelle s’appuie sur les dépendances fonctionnelles. Il faut éviter la sur-normalisation qui rend les requêtes inutilement complexes, tout en justifiant toute dénormalisation par des besoins mesurés."],
"examples": ["Dans Commande(id, client_id, client_nom), client_id→client_nom; si le nom change, plusieurs commandes doivent être mises à jour.", "Dans une relation d’inscription, (étudiant_id,cours_id)→date_inscription si la règle garantit une inscription unique par paire.", "Supprimer le dernier produit d’une catégorie ne doit pas faire disparaître le seul enregistrement de la catégorie; séparer Catégorie évite cette anomalie."],
"demo": "Repérer la dépendance client_id→client_nom; créer Client(client_id, client_nom) et Commande(commande_id, client_id); conserver client_id comme FK; comparer les lignes avant/après jointure pour s’assurer qu’aucune commande n’est perdue.",
"review": ["Dépendances métier explicites", "Attributs descriptifs de la bonne clé", "Anomalies concrètes identifiées", "Jointure sans perte de faits", "Dénormalisation justifiée par mesure"]},
"SQL : filtrer et joindre": {
"objectives": ["Écrire SELECT avec filtre, tri, regroupement et jointure non ambiguë.", "Prédire les effets de NULL, WHERE, GROUP BY et HAVING."],
"terms": ["WHERE filtre les lignes d’entrée; HAVING filtre les groupes après agrégation.", "Une jointure combine des lignes selon une condition; une jointure mal définie peut créer un produit cartésien."],
"sections": ["L’ordre logique simplifié est FROM/JOIN, WHERE, GROUP BY, HAVING, SELECT, ORDER BY. Les filtres sur colonnes de ligne vont généralement dans WHERE; les conditions sur COUNT/SUM après regroupement vont dans HAVING.", "Toujours qualifier les colonnes partagées par plusieurs tables et nommer les tables avec des alias lisibles. Pour préserver des lignes sans correspondance, choisir LEFT JOIN en connaissance de cause; placer une condition de table droite dans WHERE peut annuler l’effet de conservation.", "NULL n’est ni zéro ni chaîne vide. Utiliser IS NULL/IS NOT NULL et comprendre la logique à trois valeurs. COUNT(colonne) ignore les NULL, tandis que COUNT(*) compte les lignes."],
"examples": ["SELECT cours_id, COUNT(*) FROM Inscription WHERE annee=2026 GROUP BY cours_id HAVING COUNT(*)>=10; renvoie les cours ayant au moins dix inscriptions cette année.", "SELECT c.titre, e.nom FROM Cours c JOIN EnseignantCours ec ON ec.cours_id=c.id JOIN Enseignant e ON e.id=ec.enseignant_id; relie explicitement les clés.", "Pour conserver les cours sans inscription : Cours LEFT JOIN Inscription. Compter Inscription.id plutôt que COUNT(*) pour obtenir zéro sur les lignes sans correspondance."],
"demo": "Table Inscription(cours_id, etudiant_id, annee). Pour compter les inscrits 2026 : filtrer annee dans WHERE, regrouper par cours_id, calculer COUNT(*), puis filtrer COUNT(*)≥10 avec HAVING; ORDER BY effectif DESC classe le résultat.",
"review": ["Jointure PK–FK explicite", "WHERE avant agrégation", "HAVING après agrégation", "NULL testé par IS NULL", "COUNT adapté aux lignes conservées"]},
"Transactions et index": {
"objectives": ["Relier chaque propriété ACID à un risque concret.", "Évaluer les bénéfices et coûts d’un index sur une requête réelle."],
"terms": ["COMMIT rend les modifications d’une transaction durables; ROLLBACK annule les modifications non validées.", "Un index est une structure auxiliaire organisée pour accélérer certains accès; la base doit aussi le maintenir lors des écritures."],
"sections": ["Atomicité : toutes les étapes d’un transfert réussissent ou aucune. Cohérence : les contraintes restent vraies. Isolation : opérations concurrentes ne produisent pas un état interdit. Durabilité : après validation, le résultat survit selon les garanties du système.", "Un index sur une colonne filtrée ou utilisée comme clé de jointure peut réduire les lignes examinées. Un index composite est ordonné selon son préfixe; l’ordre des colonnes compte. Le moteur et les statistiques déterminent le plan réellement choisi.", "Chaque index coûte stockage, maintenance et parfois ralentit INSERT/UPDATE/DELETE. Éviter d’indexer toutes les colonnes par principe; observer les requêtes dominantes et le plan d’exécution sur une charge représentative."],
"examples": ["Transfert de 100 : débiter A et créditer B dans une transaction; si le crédit échoue, ROLLBACK annule le débit.", "Un index sur Inscription(cours_id) peut aider une requête de comptage par cours, mais doit être confirmé par le plan et la taille.", "Une table fortement mise à jour avec peu de recherches peut subir un coût net d’index; retirer un index inutilisé peut améliorer les écritures."],
"demo": "BEGIN; vérifier le solde; débiter le compte source; créditer la cible; vérifier les contraintes; COMMIT uniquement si toutes les opérations réussissent, sinon ROLLBACK. En production, la vérification et le débit doivent être protégés contre concurrence selon le SGBD.",
"review": ["Début, validation ou annulation visibles", "Règles d’intégrité maintenues", "Isolation évaluée pour concurrence", "Requête et index liés", "Coûts d’écriture et stockage considérés"]},
"Processus et ordonnancement": {
"objectives": ["Décrire les états d’un processus et ses transitions liées aux événements.", "Calculer attente et réponse sur une trace d’ordonnancement simple."],
"terms": ["Un programme est un ensemble d’instructions stocké; un processus est une exécution avec état, ressources et contexte; un thread est un flux d’exécution au sein d’un processus.", "Le quantum est la durée maximale d’exécution accordée à un processus dans une rotation Round Robin."],
"sections": ["Les états usuels sont prêt, en exécution et bloqué/en attente, avec parfois terminé. Une fin d’E/S fait passer un processus bloqué vers prêt; le répartiteur peut ensuite l’exécuter. Un processus prêt attend le processeur mais peut progresser dès qu’il l’obtient.", "FCFS exécute dans l’ordre d’arrivée et peut faire attendre longtemps les petits travaux derrière un grand. Round Robin partage le processeur par quantum; un quantum trop grand ressemble à FCFS, un quantum trop petit multiplie les changements de contexte.", "Comparer les politiques avec les mêmes arrivées et durées. Le temps de réponse mesure le délai jusqu’à la première exécution; le temps d’attente additionne les périodes en file prête. L’équité et le débit peuvent entrer en tension."],
"examples": ["P1=4 unités, P2=2 unités, arrivés ensemble: FCFS P1 puis P2 donne attente 0 et 4; l’ordre doit être annoncé.", "Round Robin q=2 sur P1=5, P2=3 : P1(2), P2(2), P1(2), P2(1), P1(1); la file tourne tant qu’il reste du travail.", "Un processus attendant le disque est bloqué, non prêt; exécuter un autre processus évite de laisser le CPU inactif."],
"demo": "Tracer une table temps/CPU/file pour q=2; après chaque quantum, retirer le processus fini ou remettre le restant en queue. Calculer pour chaque processus premier démarrage et achèvement; attente = temps d’achèvement − arrivée − durée CPU.",
"review": ["État associé à la cause", "Ordre d’arrivée spécifié", "Quantum appliqué correctement", "Changement de contexte distingué du travail utile", "Métrique calculée depuis la trace"]},
"Mémoire virtuelle": {
"objectives": ["Traduire une adresse logique en page et déplacement.", "Expliquer le traitement d’un défaut de page et son coût."],
"terms": ["Une page est un bloc d’espace logique; un cadre est un bloc de RAM de même taille.", "Un défaut de page survient lorsqu’une référence vise une page non résidente; le système doit la rendre disponible avant la reprise."],
"sections": ["Pour une taille de page puissance de deux, les bits faibles de l’adresse forment le déplacement; les bits hauts donnent le numéro de page. La table de pages associe une page logique à un cadre physique et des attributs de protection.", "La traduction conserve le déplacement : adresse physique = numéro de cadre × taille de page + déplacement. Un TLB mémorise certaines traductions pour éviter une consultation complète de table à chaque accès.", "Si la page manque, le processeur déclenche une exception contrôlée. Le système choisit éventuellement une victime, écrit une page modifiée si nécessaire, lit la page depuis le stockage, met à jour les tables puis relance l’instruction. Cette opération est bien plus lente qu’un accès RAM."],
"examples": ["Taille de page 4096 octets, adresse logique 9000 : page 2 et déplacement 808 (9000=2×4096+808).", "Si page 2 est dans cadre 7, adresse physique = 7×4096+808 = 29 480.", "Une boucle parcourant une très grande mémoire avec peu de cadres peut provoquer beaucoup de défauts si elle saute entre des pages éloignées."],
"demo": "Décomposer 0x2345 avec pages de 4 Kio : les 12 bits bas sont le déplacement (0x345=837), les bits hauts donnent la page (0x2). Consulter la table; si page 2 → cadre 7, l’adresse physique concatène cadre 7 et déplacement 0x345.",
"review": ["Taille de page en octets", "Page et déplacement séparés", "Déplacement conservé", "Défaut distingué d’une faute mémoire illégale", "Coût disque par rapport à RAM"]},
"Fichiers, permissions et commandes": {
"objectives": ["Résoudre un chemin relatif depuis le répertoire courant.", "Lire les permissions usuelles et choisir une commande prudente."],
"terms": ["Un chemin absolu part de la racine; un chemin relatif est résolu depuis le répertoire courant.", "Sur Unix, r, w et x désignent lecture, écriture et traversée/exécution selon le type d’objet, pour propriétaire, groupe et autres."],
"sections": ["Un chemin est une suite de composants séparés par /. ‘.’ désigne le répertoire courant et ‘..’ son parent. Toujours vérifier le répertoire courant avant une commande qui modifie ou supprime des fichiers.", "Sur un répertoire, x autorise la traversée/recherche du nom et r permet d’énumérer ses entrées; la permission w combinée à x permet généralement de créer/supprimer des entrées. Une permission d’exécution sur un fichier autorise son lancement si le système et le format le permettent.", "Les commandes d’inspection comme pwd, ls -l et stat précèdent une modification. Utiliser des chemins explicites, commencer par une portée limitée, et ne pas employer récursivement une suppression sans vérifier la cible."],
"examples": ["Depuis /home/samira/projet, ./notes.txt désigne /home/samira/projet/notes.txt; ../partage/liste.txt remonte d’un niveau.", "chmod 640 rapport.txt donne rw- au propriétaire, r-- au groupe, aucun droit aux autres (si les bits sont interprétés en octal standard).", "Un script nécessite lecture et traversée de son chemin pour être exécuté; un fichier exécutable dans un répertoire inaccessible reste inaccessible."],
"demo": "Avant de copier un fichier: pwd; ls -l source; vérifier le chemin destination; créer un répertoire cible si nécessaire; copier; relire ls -l cible et comparer taille/date. Chaque étape confirme le périmètre avant d’agir.",
"review": ["Répertoire courant connu", "Chemin relatif résolu correctement", "Droits répertoire vs fichier distingués", "Portée de commande vérifiée", "Effet destructif contrôlé"]},
"Sécurité et sauvegardes": {
"objectives": ["Appliquer moindre privilège et distinguer authentification/autorisation.", "Définir une sauvegarde restaurable et vérifier son résultat."],
"terms": ["L’authentification établit l’identité déclarée; l’autorisation détermine les actions permises à cette identité.", "Une sauvegarde est une copie récupérable d’un état; sa validité se démontre par des tests de restauration, pas par sa seule existence."],
"sections": ["Attribuer les droits nécessaires, pour la durée nécessaire. Séparer compte administrateur et compte courant limite l’impact d’une erreur. Les permissions doivent être revues après changement de rôle ou départ d’un utilisateur.", "Une sauvegarde répond à un scénario: erreur humaine, panne de support, chiffrement malveillant ou perte de site. Une copie sur le même disque ne protège pas contre sa défaillance; garder des versions et une copie séparée selon les contraintes.", "Définir fréquence, durée de conservation, responsable et objectif de reprise. Restaurer périodiquement dans un environnement distinct, vérifier intégrité et accès, et consigner la procédure. Une sauvegarde jamais testée peut être incomplète ou inutilisable."],
"examples": ["Un enseignant peut consulter les copies de ses classes mais n’a pas besoin de modifier les comptes administrateurs.", "Une sauvegarde quotidienne plus une copie séparée hebdomadaire protège mieux d’une panne locale qu’une seconde copie dans le même dossier.", "Restaurer un échantillon dans une base temporaire et comparer nombre de comptes/enregistrements vérifie le processus sans toucher au service actif."],
"demo": "Plan de restauration: créer une cible temporaire; vérifier la somme de contrôle du fichier sauvegardé; restaurer sans écraser la source; ouvrir l’application; contrôler tables et accès; mesurer la durée; documenter les écarts avant de valider la procédure.",
"review": ["Compte et droits minimum", "Menace et objectif de reprise définis", "Copies séparées et versionnées", "Restauration réellement testée", "Source active protégée pendant le test"]},
"Modèles en couches": {
"objectives": ["Associer service et protocole à une couche sans confondre modèle et implémentation.", "Suivre encapsulation de données entre application et support physique."],
"terms": ["Un protocole décrit des règles d’échange entre entités homologues; une couche fournit un service à la couche supérieure.", "Encapsulation ajoute des informations de contrôle autour des données; décapsulation les retire à la réception."],
"sections": ["Le modèle OSI distingue sept fonctions (physique, liaison, réseau, transport, session, présentation, application) pour raisonner; TCP/IP regroupe ces fonctions en un nombre de couches différent. Les correspondances sont utiles mais ne sont pas toujours exactes terme à terme.", "Le routeur examine l’adresse réseau d’un paquet IP; le commutateur Ethernet utilise l’adresse MAC sur le réseau local; les ports TCP/UDP dirigent vers une application de transport. Une adresse n’a de sens qu’avec le contexte de la couche.", "À l’émission, application produit des données, transport ajoute ports et éventuellement contrôle, IP ajoute adresses logiques, liaison crée une trame locale, puis le média transmet des bits. Chaque routeur retire/renouvelle l’encapsulation liaison tout en acheminant le paquet IP."],
"examples": ["Une requête HTTPS circule dans TCP (ou un transport moderne équivalent selon le protocole), puis IP et Ethernet/Wi‑Fi sur un réseau local.", "Le paquet IP traverse plusieurs routeurs; l’adresse MAC de la trame change à chaque lien, tandis que les adresses IP source/destination restent en principe celles des extrémités hors traduction.", "Un câble défectueux relève du niveau physique; une adresse IP mal configurée relève de la configuration réseau, même si l’utilisateur voit dans les deux cas une page inaccessible."],
"demo": "Suivre l’envoi d’un fichier: application forme le contenu; transport le segmente; IP choisit destination logique; liaison construit une trame pour le prochain saut; le routeur reçoit, examine IP et émet une nouvelle trame vers le saut suivant.",
"review": ["Trame, paquet, segment différenciés", "MAC locale vs IP routable", "Ports identifient un point de transport", "Encapsulation par couche", "Un modèle n’est pas un protocole unique"]},
"IPv4 et sous-réseaux": {
"objectives": ["Calculer réseau, diffusion et intervalle hôte pour préfixes simples.", "Vérifier si deux adresses appartiennent au même sous-réseau."],
"terms": ["Un préfixe CIDR /p fixe les p premiers bits pour la partie réseau; les bits restants identifient l’hôte dans le sous-réseau.", "L’adresse réseau a les bits hôtes à 0; l’adresse de diffusion IPv4 conventionnelle a les bits hôtes à 1."],
"sections": ["IPv4 contient 32 bits, écrits en quatre octets décimaux. Le masque /24 a 24 bits à 1 puis 8 à 0, soit 255.255.255.0. Pour d’autres préfixes, le masque peut couper un octet; raisonner en binaire ou par blocs évite les devinettes.", "Pour un sous-réseau conventionnel avec h bits hôtes, il y a 2^h adresses au total, souvent 2^h−2 hôtes utilisables, sauf préfixes particuliers et conventions modernes. Les adresses réseau/diffusion ne s’attribuent pas comme hôtes dans ce modèle classique.", "Deux hôtes sont dans le même sous-réseau si l’application du même masque donne le même identifiant réseau. Le plan doit prévoir nombre d’hôtes, passerelle, plages réservées et absence de chevauchement."],
"examples": ["192.168.1.37/24 → réseau 192.168.1.0, diffusion 192.168.1.255, hôtes classiques .1 à .254.", "10.4.7.129/25 : blocs de 128 dans le dernier octet; l’adresse appartient au réseau 10.4.7.128/25.", "Deux machines 192.168.1.20/24 et 192.168.2.20/24 sont sur des réseaux différents malgré le même dernier octet."],
"demo": "Pour 192.168.1.77/26, /26 laisse 6 bits hôtes et donne des blocs de 64 : 0–63, 64–127, 128–191, 192–255. 77 est dans 64–127; réseau .64, diffusion .127, hôtes classiques .65–.126.",
"review": ["Préfixe entre 0 et 32", "Masque/bloque calculé", "Adresse réseau et diffusion distinctes", "Nombre d’hôtes selon convention", "Même masque utilisé pour comparer"]},
"TCP, UDP et ports": {
"objectives": ["Comparer les garanties de transport de TCP et UDP selon un besoin.", "Interpréter adresse IP, port source/destination et socket."],
"terms": ["TCP fournit un flux d’octets fiable et ordonné pour une connexion; il ne conserve pas les frontières de messages de l’application.", "UDP transmet des datagrammes sans garantie intégrée de livraison, ordre ou retransmission; les applications peuvent ajouter leurs propres mécanismes."],
"sections": ["IP achemine des paquets entre réseaux, sans assurer seul un échange applicatif complet. TCP utilise numéros de séquence, accusés de réception, retransmission et contrôle de congestion; ces mécanismes apportent fiabilité au prix d’état et parfois latence.", "UDP expose une interface datagramme légère. Une application temps réel peut tolérer des pertes ponctuelles plutôt que retarder les données suivantes; elle doit décider si elle ajoute correction, contrôle ou retransmission.", "Un port identifie un endpoint de transport sur un hôte; IP identifie l’interface/adresse réseau. Le couple protocole, adresse IP et port distingue les flux. Les numéros ‘bien connus’ sont des conventions d’usage, pas une preuve qu’un service répond effectivement."],
"examples": ["Un transfert de fichier doit détecter pertes et rétablir l’ordre, donc utilise souvent TCP ou un protocole fournissant ces garanties.", "Une communication vocale peut préférer faible latence; une perte d’un fragment sonore peut être moins nuisible qu’une retransmission tardive.", "Deux connexions Web d’un même ordinateur partagent souvent un serveur/port destination, mais possèdent des ports source distincts."],
"demo": "Pour expliquer une connexion, noter IP_source:port_source → IP_destination:port_destination et le protocole. Le serveur reçoit sur son port d’écoute; le système utilise le tuple pour remettre les segments au bon socket.",
"review": ["Fiabilité nécessaire ou délai prioritaire", "Flux TCP vs datagrammes UDP", "Port n’est pas une adresse IP", "Frontières de messages gérées par l’application", "Port seul ne prouve pas accessibilité"]},
"DNS, DHCP et Web": {
"objectives": ["Décrire les principales étapes d’une résolution DNS et d’une visite HTTPS.", "Distinguer configuration DHCP, résolution de nom et chiffrement TLS."],
"terms": ["DNS interroge une hiérarchie distribuée d’enregistrements; le résolveur récursif peut mettre ses réponses en cache pendant leur durée de vie.", "DHCP attribue ou communique des paramètres réseau tels qu’adresse, passerelle et serveurs DNS; HTTPS transporte HTTP dans une connexion protégée par TLS."],
"sections": ["Lors d’une résolution, le client interroge généralement un résolveur configuré. Celui-ci répond depuis son cache ou poursuit la recherche via les serveurs DNS pertinents. Une réponse A/AAAA associe le nom à une adresse IPv4/IPv6; d’autres types existent.", "DHCP permet à un hôte de découvrir un serveur puis négocier une configuration, souvent adresse, masque, passerelle et DNS. Une panne DNS ne signifie donc pas forcément que le client n’a pas d’adresse; l’adresse peut être obtenue mais les noms ne se résolvent pas.", "Une visite HTTPS résout le nom, établit le transport, négocie TLS et vérifie le certificat pour le nom demandé selon la chaîne de confiance; ensuite la requête HTTP est protégée. TLS chiffre et protège l’intégrité du canal et authentifie le serveur sous les conditions du certificat; il ne garantit pas que le site est honnête."],
"examples": ["Un ordinateur a une adresse valide par DHCP mais un mauvais DNS : accéder par IP peut fonctionner alors que le nom échoue.", "Un cache DNS peut conserver une ancienne réponse jusqu’à expiration TTL; changer la configuration n’est pas toujours visible immédiatement partout.", "HTTPS protège les identifiants en transit contre l’écoute locale, mais ne protège pas d’un mot de passe réutilisé ou d’un site frauduleux."],
"demo": "Diagnostic par étapes : vérifier l’adresse et la passerelle reçues; tester connectivité IP; demander la résolution du nom; tester le nom; enfin vérifier HTTPS/certificat. Chaque test localise une couche différente au lieu de conclure immédiatement ‘Internet en panne’.",
"review": ["DHCP configure l’hôte", "DNS résout des noms", "HTTPS = HTTP protégé par TLS", "Cache et TTL expliquent la durée", "Certificat vérifié pour le bon nom"]},
"Cycle d’exécution et composants CPU": {
"objectives": ["Associer ALU, registres et unité de contrôle à leurs rôles.", "Tracer les étapes recherche, décodage et exécution d’une instruction simple."],
"terms": ["Un registre est un stockage très rapide de faible capacité dans le processeur; le compteur ordinal désigne la prochaine instruction selon l’architecture.", "L’ALU effectue opérations arithmétiques/logiques; l’unité de contrôle orchestre les étapes et signaux."],
"sections": ["Une instruction possède un codage défini par l’architecture : opération, registres ou adresses selon le jeu d’instructions. Le processeur doit obtenir ce code, l’interpréter et activer les ressources nécessaires.", "Dans le cycle pédagogique recherche–décodage–exécution, la recherche lit l’instruction, le décodage identifie l’opération et les opérandes, puis l’exécution calcule ou transfère une valeur. Certaines instructions impliquent mémoire ou plusieurs étapes; les processeurs modernes chevauchent les phases.", "Les bus transportent des informations : bus de données pour les valeurs, bus d’adresses pour sélectionner une position, signaux de contrôle pour coordonner lecture/écriture. Les architectures réelles intègrent caches et mécanismes plus complexes, mais ce modèle aide à suivre le trajet d’une instruction."],
"examples": ["ADD R1,R2,R3 peut calculer R2+R3 dans l’ALU puis écrire le résultat dans R1.", "LOAD R1,[A] lit une donnée à l’adresse A en mémoire/cache et la place dans un registre; l’instruction et la donnée sont deux lectures différentes.", "Une comparaison SUB ou instruction dédiée met des indicateurs; une branche conditionnelle utilise ces indicateurs pour modifier le flot d’exécution."],
"demo": "Pour ADD R1,R2,R3 : le compteur ordinal indique l’instruction; elle est chargée; le décodeur identifie ADD et les registres; les valeurs R2/R3 alimentent l’ALU; résultat écrit dans R1; compteur ordinal avance sauf contrôle de branchement.",
"review": ["Contrôle orchestre, ALU calcule", "Registres contiennent opérandes/résultats", "Instruction et données distinguées", "Bus d’adresse vs données", "Cycle pédagogique simplifié annoncé"]},
"Hiérarchie mémoire": {
"objectives": ["Comparer registres, caches, RAM et stockage par vitesse, capacité et persistance.", "Expliquer localité temporelle/spatiale et effet sur un accès."],
"terms": ["La localité temporelle signifie qu’une donnée récemment utilisée a une probabilité d’être réutilisée bientôt.", "La localité spatiale signifie que des adresses voisines ont une probabilité d’être consultées ensemble."],
"sections": ["Les niveaux proches du CPU sont généralement rapides et chers par bit, donc petits; les niveaux éloignés sont plus vastes et persistants, mais plus lents. Cette hiérarchie évite de traiter chaque accès au stockage comme un accès registre.", "Le cache garde des blocs récents/probables. Un accès peut être un succès (hit) ou un défaut (miss); un défaut entraîne la récupération du bloc depuis un niveau inférieur. Le taux de succès, le coût du défaut et le motif d’accès influencent la performance.", "La RAM est volatile; SSD/HDD sont des supports de stockage non volatils sous fonctionnement normal. Cache et RAM ne remplacent pas une sauvegarde, car ils ne sont pas des copies durables contre panne ou suppression."],
"examples": ["Parcours séquentiel d’un tableau lit des éléments voisins et bénéficie de la localité spatiale.", "Une boucle réutilisant le même compteur bénéficie de localité temporelle; si compteur reste dans un registre, il peut ne pas solliciter la RAM à chaque fois.", "Après coupure, contenu RAM perdu; fichier sauvegardé sur SSD persiste normalement, mais une panne du SSD nécessite une autre copie."],
"demo": "Comparer deux parcours matriciels : si les éléments d’une ligne sont contigus en mémoire, parcourir d’abord les colonnes de cette ligne exploite mieux la localité. Le nombre de calculs est similaire, mais les défauts cache peuvent varier.",
"review": ["Capacité et latence séparées", "Volatile/persistant distingués", "Hit et miss définis", "Localité reliée au motif d’accès", "Cache n’est pas sauvegarde"]},
"Représentation des nombres": {
"objectives": ["Convertir des nombres binaires sur une largeur définie.", "Calculer l’intervalle et interpréter un débordement en complément à deux."],
"terms": ["Avec n bits non signés, l’intervalle est de 0 à 2^n−1; chaque position pèse une puissance de deux.", "Sur n bits en complément à deux, l’intervalle est −2^(n−1) à 2^(n−1)−1; le motif de bits dépend de la largeur fixée."],
"sections": ["La valeur binaire se calcule par somme des bits pondérés : b_k2^k. Pour convertir un décimal positif, divisions successives par 2 donnent les restes lus de bas en haut. Toujours préciser la largeur et le caractère signé/non signé.", "En complément à deux, un motif dont le bit de poids fort vaut 1 représente une valeur négative. Pour obtenir −x sur n bits : inverser les bits de x puis ajouter 1; les opérations restent modulaires sur la largeur et peuvent déborder.", "Le stockage de caractères dépend d’un encodage. Unicode attribue des points de code; UTF‑8 les encode en un à quatre octets selon le caractère. Le nombre de caractères n’est donc pas toujours égal au nombre d’octets."],
"examples": ["10110₂ = 16+4+2 = 22₁₀.", "Sur 4 bits non signés, 15+1 produit 0000 avec retenue perdue; 16 n’est pas représentable et le calcul déborde.", "Sur 8 bits, 00000101 représente +5; son opposé en complément à deux est 11111011, soit −5."],
"demo": "Calculer −6 sur 8 bits : +6=00000110; inversion=11111001; ajouter 1 donne 11111010. Vérifier poids signé −128+64+32+16+8+2=−6.",
"review": ["Largeur n précisée", "Signé/non signé annoncé", "Poids 2^i appliqués", "Complément à deux = inversion + 1", "Débordement jugé dans l’intervalle"]},
"Mesure des performances": {
"objectives": ["Distinguer fréquence d’horloge, temps d’exécution, débit et latence.", "Appliquer la loi d’Amdahl à une fraction accélérée."],
"terms": ["La latence mesure le délai d’une opération; le débit mesure le nombre d’opérations terminées par unité de temps.", "La loi d’Amdahl borne le gain total quand une partie du travail reste inchangée."],
"sections": ["La fréquence compte des cycles par seconde; le temps CPU dépend aussi des cycles nécessaires par instruction, du nombre d’instructions et des attentes mémoire/E/S. GHz seul ne suffit donc pas à comparer deux machines.", "Fixer la charge, les entrées, les conditions d’exécution et la métrique. Un benchmark utile est reproductible, représentatif et répété; distinguer temps total, CPU, débit et temps de réponse.", "Si fraction f est accélérée d’un facteur s, gain global = 1/((1−f)+f/s). Même accélérer infiniment la partie f ne peut dépasser 1/(1−f). Cette limite explique pourquoi l’optimisation du petit segment peut produire peu d’effet."],
"examples": ["Si 80% du temps est accéléré ×4 : gain = 1/(0,2+0,8/4)=2,5.", "Si 90% d’un programme est parallélisé à l’infini, gain maximal =1/0,1=10, non infini.", "Une machine peut avoir faible latence pour une requête mais débit moindre sous forte concurrence; les deux mesures répondent à des questions différentes."],
"demo": "Identifier la fraction optimisée f=0,6 et facteur s=3; temps normalisé restant =0,4+0,6/3=0,6; accélération =1/0,6≈1,67. Vérifier la borne infinie 1/(1−0,6)=2,5.",
"review": ["Charge de travail identique", "Métrique correctement nommée", "Fréquence n’est pas performance seule", "Formule d’Amdahl appliquée", "Borne séquentielle mentionnée"]},
"Documents structurés": {
"objectives": ["Créer une hiérarchie de styles sémantique et générer une table des matières.", "Contrôler lisibilité, navigation clavier et textes alternatifs."],
"terms": ["Un style associe une fonction de structure à une mise en forme cohérente; un titre hiérarchique est différent d’un texte simplement agrandi.", "Un texte alternatif décrit le rôle ou l’information d’une image pour les lecteurs qui ne la voient pas."],
"sections": ["Planifier les niveaux : titre du document, sections, sous-sections. Appliquer les styles intégrés plutôt que formater chaque ligne séparément; les modifications globales et la navigation deviennent fiables.", "Insérer une table des matières à partir des styles de titre, puis l’actualiser après modifications. Utiliser des listes réelles et des tableaux seulement pour des données tabulaires; vérifier ordre de lecture et contrastes.", "Pour une image informative, écrire un texte alternatif bref qui transmet l’information pertinente; une image décorative peut être marquée comme telle selon l’outil. Exporter en PDF ne garantit pas automatiquement une structure accessible : vérifier le document final."],
"examples": ["Rapport de stage : Titre 1 pour ‘Méthode’, Titre 2 pour ‘Échantillon’; créer puis actualiser la table des matières.", "Pour un schéma de réseau, un texte alternatif peut dire ‘Routeur relie le réseau local à Internet’; ne pas répéter la légende si elle suffit.", "Un tableau comparant protocoles a une ligne d’en-têtes clairement définie; utiliser des cellules fusionnées seulement si la structure demeure compréhensible."],
"demo": "Créer un rapport : appliquer Titre 1/2; choisir corps lisible; insérer légendes; générer table des matières; parcourir les titres au clavier; vérifier liens et alternatives; exporter puis ouvrir le PDF pour contrôler pagination et ordre.",
"review": ["Styles sémantiques utilisés", "Table des matières actualisée", "Images porteuses décrites", "Tableaux tabulaires", "Export contrôlé dans le lecteur cible"]},
"Formules et références": {
"objectives": ["Prévoir le déplacement d’une référence relative, absolue ou mixte lors d’une recopie.", "Vérifier une formule avec des données dont le résultat est calculable à la main."],
"terms": ["A1 est relative; $A$1 fige colonne et ligne; $A1 fige la colonne; A$1 fige la ligne.", "Une formule est une expression recalculée par le tableur; une erreur affichée peut signaler référence invalide, type ou division par zéro."],
"sections": ["Avant de recopier, repérer les entrées par ligne et les paramètres fixes. Une formule de remise peut utiliser une cellule de taux absolue et une quantité relative. Le symbole $ fixe la coordonnée lors du déplacement.", "Les fonctions comme SOMME, MOYENNE et SI facilitent les calculs; nom et séparateurs dépendent de langue/version. Vérifier si l’outil attend virgule ou point-virgule et ne pas confondre texte numérique et nombre.", "Contrôler une formule sur petit jeu de données, sur zéro, valeur limite, cellule vide et erreur attendue. Protéger les cellules de formule dans un document partagé et documenter les unités."],
"examples": ["Montant en A2, taux en B1 : =A2*$B$1; recopiée vers A3, devient =A3*$B$1.", "Tableau à double entrée : formule =$A2*B$1 fixe la colonne A pour l’étiquette ligne et la ligne 1 pour l’en-tête colonne.", "=SI(C2>=10;\"Admis\";\"À revoir\") classe une note; tester 9, 10 et une cellule vide pour comprendre la politique."],
"demo": "Pour calculer TTC : mettre le taux en B1=20%; prix HT en A2:A4; saisir =A2*(1+$B$1), recopier vers le bas; contrôler 100→120; modifier le taux à 10% et vérifier que toutes les lignes se recalculent.",
"review": ["Cellules d’entrée et paramètres identifiés", "$ placé sur bonnes lignes/colonnes", "Séparateur et noms de fonction vérifiés", "Bornes testées indépendamment", "Unités et cellules de formule visibles"]},
"Analyse de données": {
"objectives": ["Nettoyer types, doublons et valeurs manquantes avant agrégation.", "Choisir une mesure et une échelle graphique adaptées à la question."],
"terms": ["Une agrégation résume plusieurs lignes (somme, compte, moyenne); son interprétation dépend du périmètre retenu.", "Un tableau croisé dynamique regroupe les observations selon des dimensions et calcule des mesures résumées."],
"sections": ["Préparer un jeu de données rectangulaire : une observation par ligne, une variable par colonne, en-têtes uniques, types homogènes. Repérer doublons, codes mal saisis, valeurs manquantes et unités incohérentes avant de calculer.", "Traduire la question en dimension et mesure : ‘quantité par mois et catégorie’ exige une date/mois, une catégorie et une quantité. Distinguer moyenne et médiane lorsque les valeurs extrêmes sont importantes; toujours documenter le dénominateur.", "Un graphique devrait montrer unité, période, source et périmètre. Une échelle tronquée peut exagérer une différence; un axe partant de zéro n’est pas toujours nécessaire pour chaque type, mais tout choix doit être signalé et honnête."],
"examples": ["Données de ventes : normaliser dates au même format et montants en même devise avant somme mensuelle.", "Un tableau croisé ‘lignes=mois, colonnes=catégorie, valeurs=somme des quantités’ répond à une question de volume et non de chiffre d’affaires.", "Si une moyenne de 10 masque neuf valeurs 1 et une valeur 91, afficher aussi médiane ou distribution pour révéler la dispersion."],
"demo": "Avant un tableau croisé : filtrer les lignes invalides selon une règle documentée; compter lignes et doublons; actualiser la source; regrouper par mois; comparer le total des agrégats au total source pour repérer des lignes omises.",
"review": ["Ligne = observation", "Types et unités homogènes", "Périmètre/dénominateur explicites", "Agrégat répond à la question", "Graphique ne masque pas la variation"]},
"Présentations et partage": {
"objectives": ["Construire une progression de diapositives avec une idée principale par écran.", "Vérifier lisibilité, compatibilité, droits et accessibilité avant partage."],
"terms": ["La charge cognitive est l’effort mental nécessaire pour traiter l’information; une diapositive dense peut concurrencer la parole.", "Un média lié dépend du fichier source externe; un média incorporé est stocké dans le fichier de présentation, avec un poids plus élevé."],
"sections": ["Commencer par le public, l’objectif et la durée; organiser en question, explication, exemple et synthèse. Un titre informatif annonce le point de la diapositive et aide à suivre le fil.", "Utiliser contraste, taille de police adaptée à la projection, alignements stables et visuels lisibles. Un graphique doit garder légende et unités; une animation n’est utile que si elle clarifie une étape.", "Avant partage, vérifier fichiers liés, polices, codecs, droits d’image et confidentialité des notes. Exporter en PDF pour figer un rendu peut réduire l’interactivité; garder une source modifiable si le destinataire doit adapter."],
"examples": ["Pour enseigner la recherche dichotomique : une diapo montre le tableau, la borne gauche/droite et la comparaison médiane; révéler une étape à la fois.", "Remplacer un paragraphe de 90 mots par un schéma et trois libellés; garder le raisonnement détaillé dans les notes du présentateur.", "Tester le diaporama sur l’ordinateur de la salle avec projecteur : couleurs, vidéos, liens et polices peuvent varier."],
"demo": "Planifier 6 minutes : annoncer objectif; présenter problème; développer trois étapes avec exemples; donner une courte question; conclure par trois idées. Vérifier le temps avec répétition, pas seulement avec le nombre de diapositives.",
"review": ["Public et objectif définis", "Titre exprimant l’idée", "Une idée principale par écran", "Ressources et polices testées", "Droits et notes confidentielles contrôlés"]},
"Formats matriciels et vectoriels": {
"objectives": ["Choisir un format selon le contenu, la transparence, l’édition et le support.", "Calculer un ordre de grandeur du poids brut d’une image matricielle."],
"terms": ["Une image matricielle échantillonne la scène en pixels; une image vectorielle décrit des formes géométriques.", "La résolution spatiale décrit le détail par unité de longueur dans un contexte de sortie; dimensions en pixels ne déterminent pas seules la taille imprimée."],
"sections": ["JPEG compresse généralement avec perte et convient souvent aux photographies; réenregistrer plusieurs fois peut accumuler des artefacts. PNG conserve exactement les pixels compressés et prend en charge la transparence, ce qui convient à des graphismes; SVG décrit des tracés et se redimensionne sans pixellisation.", "Une image brute approximative pèse largeur×hauteur×bits_par_pixel/8, hors en-têtes. Le fichier réel dépend du format, du contenu, métadonnées et compression. Un fond uniforme se compresse autrement qu’une texture détaillée.", "Pour imprimer, considérer dimensions en pixels et résolution visée; pour écran, considérer pixels affichés et densité. Convertir en vectoriel ne recrée pas les détails d’une photo déjà matricielle."],
"examples": ["Photo 1920×1080 distribuée en JPEG de qualité adaptée; inspecter les artefacts avant publication.", "Logo avec aplats et transparence exporté en SVG si plateforme le supporte; PNG transparent si compatibilité simple prioritaire.", "Image 100×100 en 24 bits : 100×100×24/8=30 000 octets bruts environ, avant compression et métadonnées."],
"demo": "Choisir pour une affiche : demander si le visuel est photo ou logo; si photo, conserver une source haute résolution et exporter JPEG; si logo, garder source vectorielle et tester SVG/PNG aux tailles finales; vérifier poids et netteté.",
"review": ["Photo ou dessin géométrique identifié", "Perte de qualité acceptable ?", "Transparence nécessaire ?", "Dimensions et résolution distinguées", "Compatibilité du format vérifiée"]},
"Couleurs et compression": {
"objectives": ["Convertir profondeur de couleur et dimensions en taille brute approximative.", "Choisir compression et espace colorimétrique selon écran ou impression."],
"terms": ["RVB mélange lumière rouge, verte et bleue; CMJN représente des encres soustractives et la gamme imprimable diffère de celle d’un écran.", "Une compression sans perte permet de récupérer exactement les données encodées; avec perte, certaines informations sont supprimées."],
"sections": ["À 8 bits par canal RVB, chaque pixel porte 24 bits, soit 3 octets avant alpha, en-tête et compression. Ajouter un canal alpha peut porter le brut à 32 bits/pixel.", "Les espaces colorimétriques définissent comment les valeurs correspondent à des couleurs; deux écrans ou profils différents peuvent rendre différemment les mêmes nombres. Convertir RVB en CMJN peut déplacer les couleurs hors gamme.", "La compression sans perte réduit les répétitions sans altérer les valeurs restaurées; la compression avec perte exploite des limites perceptuelles, mais peut créer blocs, halos ou bandes. Préserver une source non destructive avant export final."],
"examples": ["800×600 en 24 bits : 800×600×3=1 440 000 octets bruts (hors en-tête), soit environ 1,44 Mo décimaux.", "Une image destinée à l’écran reste généralement préparée en RVB; pour impression, demander le profil et les consignes de l’imprimeur.", "Un diagramme avec texte net peut souffrir d’artefacts JPEG; PNG sans perte garde mieux les contours, tandis qu’une photo se compresse souvent efficacement en JPEG."],
"demo": "Comparer deux exports du même visuel : garder dimensions, vérifier qualité à 100%, mesurer taille et observer contours/dégradés; sélectionner la plus petite version qui garde lisibilité requise.",
"review": ["Profondeur exprimée par canal ou pixel", "Bits convertis en octets", "Brut différent du fichier compressé", "RVB/CMJN selon sortie", "Perte observée sur contours et dégradés"]},
"Échantillonnage sonore": {
"objectives": ["Expliquer la mesure temporelle et la quantification d’un signal.", "Calculer le débit PCM selon fréquence, profondeur et nombre de canaux."],
"terms": ["La fréquence d’échantillonnage indique le nombre de mesures par seconde; la profondeur en bits détermine le nombre de niveaux de quantification.", "Le débit PCM brut est fréquence × bits par échantillon × nombre de canaux, en bits par seconde."],
"sections": ["Un signal analogique varie continûment; le convertisseur prélève des valeurs à intervalles réguliers, puis quantifie chaque valeur. Une fréquence trop faible ne représente pas correctement les variations rapides; le théorème de Nyquist donne une condition idéale, tandis que les systèmes pratiques utilisent filtres et marges.", "La profondeur augmente les niveaux possibles et réduit le pas de quantification; elle n’augmente pas la fréquence de mesure. Le nombre de canaux distingue mono, stéréo et autres configurations.", "Le débit brut n’est pas le poids final si compression ou en-têtes sont utilisés. Pour une durée en secondes, taille brute approximative = débit×durée/8 octets; convertir en décimal ou binaire en annonçant la convention."],
"examples": ["48 000×16×2=1 536 000 bit/s pour PCM stéréo 16 bits, soit 192 000 octets/s environ.", "Une minute à 705 600 bit/s représente 42 336 000 bits, soit 5 292 000 octets bruts avant en-tête.", "Augmenter la profondeur de 16 à 24 bits augmente le débit PCM d’un facteur 1,5 si fréquence et canaux restent identiques."],
"demo": "Pour mono 44,1 kHz, 16 bits, 10 s : 44 100×16×1=705 600 bit/s; multiplier par 10 et diviser par 8 donne 882 000 octets bruts. Indiquer que la compression et métadonnées modifient le fichier réel.",
"review": ["Fréquence en échantillons/s", "Profondeur en bits/échantillon", "Canaux comptés", "Débit en bits/s", "Durée et division par 8 pour octets"]},
"Codecs, conteneurs et vidéo": {
"objectives": ["Distinguer codec, flux et conteneur à partir d’un fichier multimédia.", "Estimer les facteurs qui déterminent taille et qualité vidéo."],
"terms": ["Un codec encode/décode un flux audio ou vidéo et peut appliquer une compression avec ou sans perte.", "Un conteneur regroupe une ou plusieurs pistes et métadonnées; l’extension ne détermine pas à elle seule les codecs présents."],
"sections": ["Un fichier MP4 peut contenir vidéo H.264 et audio AAC, mais un autre MP4 peut intégrer d’autres codecs. Le lecteur doit prendre en charge le conteneur, les codecs et leurs profils.", "La résolution détermine le nombre de pixels par image; la cadence, les images par seconde; le débit, les bits moyens par seconde. Mouvement complexe, bruit et scènes détaillées demandent souvent davantage de bits pour une qualité comparable.", "Une compression avec perte peut créer blocs, contours bruités et détails effacés. Tester sur scènes représentatives et appareils cibles; préserver le fichier source pour une nouvelle exportation."],
"examples": ["Deux fichiers .mp4 ne sont pas nécessairement lisibles par le même ancien appareil si leurs codecs diffèrent.", "1920×1080 à 60 images/s demande généralement plus de débit qu’une scène fixe en 640×360 à 24 images/s, à réglage comparable.", "Un fichier contenant vidéo sans audio reste un conteneur avec une piste; l’extension ne garantit pas qu’une piste sonore existe."],
"demo": "Diagnostiquer un fichier illisible : inspecter conteneur, codec vidéo/audio, résolution, profil, débit et appareil; ne pas conclure à partir de l’extension. Si besoin, réencoder la piste avec un codec pris en charge en conservant l’original.",
"review": ["Extension, conteneur, codec distingués", "Pistes audio/vidéo inspectées", "Résolution et cadence annoncées", "Débit relié à qualité et taille", "Source conservée avant réencodage"]},
}

CODE_EXAMPLES = {
"Données, conditions et itérations": '''def compter_admis(notes):
    compteur = 0
    for note in notes:
        if note >= 10:
            compteur += 1
    return compteur

print(compter_admis([8, 10, 13]))  # 2''',
"Boucles imbriquées et invariants": '''for i in range(1, 4):
    for j in range(1, i + 1):
        print("*", end="")
    print()
# *
# **
# ***''',
"Tableaux, recherches et tris": '''def rechercher(tab, cible):
    i = 0
    while i < len(tab) and tab[i] != cible:
        i += 1
    return i if i < len(tab) else -1

print(rechercher([4, 6, 9], 9))  # 2''',
"Récursivité, piles et complexité": '''def somme(n):
    if n < 0:
        raise ValueError("n doit être positif ou nul")
    if n == 0:
        return 0
    return n + somme(n - 1)

print(somme(3))  # 6''',
"Types, contrôle et fonctions": '''def moyenne(notes):
    if not notes:
        raise ValueError("La liste de notes est vide")
    if any(not 0 <= note <= 20 for note in notes):
        raise ValueError("Chaque note doit être entre 0 et 20")
    return sum(notes) / len(notes)

print(moyenne([10, 14, 16]))  # 13.333333333333334''',
"Collections, fichiers et erreurs": '''from collections import Counter

with open("mots.txt", encoding="utf-8") as fichier:
    mots = fichier.read().lower().split()
frequences = Counter(mots)
print(frequences["réseau"])''',
"Classes et objets": '''class Compte:
    def __init__(self, solde=0):
        if solde < 0:
            raise ValueError("Solde initial négatif")
        self._solde = solde

    def retirer(self, montant):
        if montant <= 0 or montant > self._solde:
            return False
        self._solde -= montant
        return True''',
"Tests et débogage": '''def rechercher(tab, cible):
    for i, valeur in enumerate(tab):
        if valeur == cible:
            return i
    return -1

assert rechercher([], 4) == -1
assert rechercher([4], 4) == 0
assert rechercher([2, 5, 8], 8) == 2''',
"Entités, relations et contraintes": '''CREATE TABLE Cours (
    id INTEGER PRIMARY KEY,
    titre TEXT NOT NULL UNIQUE
);
CREATE TABLE Inscription (
    etudiant_id INTEGER NOT NULL,
    cours_id INTEGER NOT NULL REFERENCES Cours(id),
    annee INTEGER NOT NULL,
    PRIMARY KEY (etudiant_id, cours_id, annee)
);''',
"Normalisation et qualité": '''CREATE TABLE Categorie (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL UNIQUE
);
CREATE TABLE Produit (
    id INTEGER PRIMARY KEY,
    nom TEXT NOT NULL,
    categorie_id INTEGER NOT NULL REFERENCES Categorie(id)
);''',
"SQL : filtrer et joindre": '''CREATE TABLE Cours(id INTEGER PRIMARY KEY, titre TEXT NOT NULL);
CREATE TABLE Inscription(cours_id INTEGER NOT NULL, etudiant_id INTEGER NOT NULL, annee INTEGER NOT NULL);
INSERT INTO Cours VALUES (1, 'Réseaux');
INSERT INTO Inscription VALUES (1, 1, 2026), (1, 2, 2026), (1, 3, 2026);
SELECT c.titre, COUNT(i.etudiant_id) AS effectif
FROM Cours AS c
JOIN Inscription AS i ON i.cours_id = c.id
WHERE i.annee = 2026
GROUP BY c.id, c.titre
HAVING COUNT(i.etudiant_id) >= 3
ORDER BY effectif DESC;
-- Résultat : Réseaux | 3''',
"Transactions et index": '''CREATE TABLE Compte(id INTEGER PRIMARY KEY, solde INTEGER CHECK(solde >= 0));
INSERT INTO Compte VALUES (1, 500), (2, 200);
BEGIN;
UPDATE Compte SET solde = solde - 100 WHERE id = 1;
UPDATE Compte SET solde = solde + 100 WHERE id = 2;
COMMIT;
CREATE INDEX ix_compte_solde ON Compte(solde);
SELECT id, solde FROM Compte ORDER BY id;
-- Résultat : (1, 400), (2, 300)''',
}

WHY_IT_MATTERS = {
"Données, conditions et itérations": "Ces constructions sont le vocabulaire de base pour décrire une procédure reproductible et montrer précisément comment une réponse est calculée.",
"Boucles imbriquées et invariants": "Le comptage et les invariants permettent de prévoir la durée d’un algorithme et de justifier qu’il produit le résultat annoncé.",
"Tableaux, recherches et tris": "Les recherches dans des séquences apparaissent dans les traitements de listes, fichiers et banques de données; le choix de méthode change fortement à grande échelle.",
"Récursivité, piles et complexité": "Les appels, structures de parcours et ordres de croissance aident à comparer des solutions et à détecter les limites de mémoire ou de temps.",
"Types, contrôle et fonctions": "Des fonctions aux contrats clairs rendent un programme réutilisable, vérifiable et plus sûr face à des saisies inattendues.",
"Collections, fichiers et erreurs": "Les programmes réels doivent organiser des données et les lire depuis des supports où format, accès et erreurs ne sont jamais garantis.",
"Classes et objets": "La modélisation objet aide à rassembler état et règles métier lorsque plusieurs opérations doivent préserver les mêmes invariants.",
"Tests et débogage": "Une démarche de test rend les défauts reproductibles et évite qu’une modification correcte en apparence casse un cas déjà maîtrisé.",
"Entités, relations et contraintes": "Un modèle relationnel explicite évite les références incohérentes et permet de répondre aux besoins par des requêtes fiables.",
"Normalisation et qualité": "La normalisation rend les mises à jour cohérentes et réduit les contradictions lorsque les faits évoluent.",
"SQL : filtrer et joindre": "Les requêtes structurent l’accès aux données et leurs clauses déterminent quelles lignes et quels groupes apparaissent dans le résultat.",
"Transactions et index": "Les transactions protègent les opérations composées; les index équilibrent rapidité de lecture, espace et coût d’écriture.",
"Processus et ordonnancement": "L’ordonnancement explique pourquoi plusieurs programmes progressent sur une machine et comment équité et réactivité se négocient.",
"Mémoire virtuelle": "La traduction d’adresses permet l’isolation et le partage contrôlé de la mémoire, au prix de délais importants lors des défauts de page.",
"Fichiers, permissions et commandes": "La maîtrise des chemins et permissions est nécessaire pour administrer un poste sans exposer ni détruire des fichiers par erreur.",
"Sécurité et sauvegardes": "La disponibilité d’un système dépend autant de droits limités que de copies dont la restauration a réellement été testée.",
"Modèles en couches": "Les couches facilitent le diagnostic: une panne de lien, d’adressage, de transport ou d’application demande des vérifications différentes.",
"IPv4 et sous-réseaux": "Le sous-réseautage permet d’attribuer des plages cohérentes, de dimensionner les réseaux et d’identifier les destinations locales.",
"TCP, UDP et ports": "Les applications choisissent des compromis entre ordre, fiabilité, latence et débit en s’appuyant sur les services de transport.",
"DNS, DHCP et Web": "Ces services configurent un hôte, traduisent des noms et protègent les échanges Web; les distinguer accélère le diagnostic réseau.",
"Cycle d’exécution et composants CPU": "Suivre les données entre registres, ALU, mémoire et contrôle relie le code exécuté aux opérations matérielles.",
"Hiérarchie mémoire": "La localité et la hiérarchie expliquent pourquoi le même calcul peut avoir des performances très différentes selon l’ordre d’accès.",
"Représentation des nombres": "La largeur et l’encodage déterminent quelles valeurs une machine peut représenter sans ambiguïté ni débordement.",
"Mesure des performances": "Une comparaison mesurée évite de confondre fréquence, débit et temps d’attente et permet de prévoir les limites d’une optimisation.",
"Documents structurés": "Une structure sémantique facilite la navigation, les changements globaux et l’accès du document à des lecteurs variés.",
"Formules et références": "Les références pilotent le comportement des formules lorsqu’elles sont recopiées, et une erreur peut fausser des décisions réelles.",
"Analyse de données": "Nettoyage, agrégation et visualisation conditionnent la validité des conclusions tirées d’un tableau de données.",
"Présentations et partage": "Un support efficace rend une idée enseignable et lisible au lieu de concurrencer l’explication par une masse de texte.",
"Formats matriciels et vectoriels": "Le bon format préserve netteté, transparence et compatibilité tout en évitant des fichiers inutilement lourds.",
"Couleurs et compression": "La couleur et la compression influencent à la fois l’apparence, le poids et la fidélité d’un média selon son support.",
"Échantillonnage sonore": "La numérisation transforme un signal continu en données mesurables; ses paramètres déterminent fidélité et débit.",
"Codecs, conteneurs et vidéo": "Distinguer flux et conteneur résout des problèmes de compatibilité et aide à choisir un compromis de taille et de qualité.",
}
