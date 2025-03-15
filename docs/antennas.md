Fabrication et Connexion d’une Antenne pour un Réseau Maillé Raspberry Pi (AirNet PCTamalou)

Objectif

Construire une antenne Wi-Fi (omnidirectionnelle ou directionnelle) pour ton Raspberry Pi (modèles 3, 4 ou 5), parfaitement adaptée au réseau maillé AirNet PCTamalou avec BATMAN-adv.

On va tout détailler : les bases électriques, la fabrication pas à pas, la connexion au Pi, et les tests, pour booster la portée (100m à 15 km selon config), stabiliser le réseau, et garder un coût mini (~10-25€). Que tu sois en ville ou à la campagne, ce guide est ton plan sans faille !

Matériel Nécessaire (Check-List Complète)

Avant de commencer, rassemble tout ça – rien de compliqué, tout se trouve en ligne (Amazon, eBay) ou chez un brico du coin :

    Raspberry Pi (3, 4 ou 5) : Avec Wi-Fi intégré (chip BCM43438 ou mieux). 35-70€ neuf, ~20€ d’occase sur Leboncoin.
    Fil de cuivre ou aluminium : 1-2 mm de diamètre, rigide (genre fil électrique dénudé). 1m suffit (~2-5€).
    Câble coaxial U.FL : Court (10-20 cm), 50 ohms, ex. : RG-178 ou RG-316. ~5€ sur eBay ("U.FL to RP-SMA").
    Connecteur U.FL : Petit connecteur pour le Pi (optionnel si câble déjà équipé). ~2-3€ (lot de 5 sur AliExpress).
    Plaque PCB vierge ou feuille métal : Pour réflecteur Yagi, 10x10 cm max. ~5€ (PCB chez électronicien) ou récup (boîte conserve).
    Base non conductrice : Plastique/bois pour fixer dipôle (ex. : vieux jouet ou planchette). Gratuit si récup.
    Fer à souder : 15-25W, pointe fine (~10-15€ chez Castorama).
    Soudure : Étain-plomb ou sans plomb, 0.8-1 mm (~5€, rouleau 100g).

    Outils :
        Pince coupante : Pour fil (~5€).
        Multimètre : Basique (~10€, test continuité/tension).
        Perceuse : Mini (ou perceuse main), foret 1-2 mm (~10€ ou prêt voisin).
        Colle époxy : Fixation solide (~5€, tube 2 composants).

    Optionnel (comparaison) : Antenne Yagi 2.4 GHz (~15-20€, 5-10 dBi, RP-SMA).

    Extras : Loupe (3-5€, bijoutier) + lunettes sécurité (2€) pour soudure propre.

Coût total : 10-25€ (DIY), 30-50€ (avec antenne achetée).

Étape 1 : Comprendre les Bases Électriques et Électroniques (Pas de Panique !)

Avant de couper ou souder, capte ces notions – c’est simple et ça évite les boulettes :

    Fréquence et Longueur d’Onde

        Le Wi-Fi du Pi est à 2.4 GHz (canaux 1-13, on utilisera canal 1 par défaut).
            Calcul : Longueur d’onde (λ) = vitesse lumière (300 000 000 m/s) ÷ fréquence (2 400 000 000 Hz) = 12.5 cm.

        Pourquoi ça compte ? Ton antenne doit matcher cette taille :
            λ/2 (dipôle) = 6.25 cm total.
            λ/4 (par segment) = 3.125 cm.
                Astuce : Mesure avec une règle précise (métal, pas plastique qui s’étire).

    Impédance
        Le Wi-Fi du Pi veut 50 ohms entre antenne et circuit.
        Si mismatch (ex. : mauvais câble), signal rebondit = perte de portée.
            Solution : Câble coaxial 50 ohms (RG-178, pas du RG-58 à 75 ohms).
                Test : Multimètre en mode "continuité" (bip) pour vérifier connexions.

    Gain et Directivité
        Omnidirectionnelle (dipôle) : Rayonne partout autour (360° horizontal), gain ~2-5 dBi. Parfait pour couverture large (maison, quartier).
            Directionnelle (Yagi) : Focale dans une direction, gain ~8-15 dBi. Idéal pour viser un nœud loin (village voisin).
                Exemple : 2 dBi = 100m, 10 dBi = 1-5 km (selon obstacles).

    Puissance
        Le Pi sort 20 dBm max (100 mW).
        Loi (Europe) : EIRP (puissance + gain) ≤ 30 dBm.
            Ex. : 20 dBm + 10 dBi = 30 dBm (OK).
            Si plus (ampli RF), illégal sans licence – on reste clean ici.

        Astuce : Antenne booste portée, pas puissance émise.

Étape 2 : Choisir et Fabriquer l’Antenne (Pas à Pas)

On te donne deux options : dipôle omnidirectionnel (base simple) ou Yagi directionnel (option portée). Suis chaque étape, c’est du gâteau si tu lis bien !

Option 1 : Antenne Dipôle Omnidirectionnelle (λ/2)

Quand ? Pour couverture large (100m-1 km selon obstacles).

    Matériaux :

        Fil cuivre/aluminium (6.25 cm total).
        Câble coaxial U.FL (10-20 cm).
        Base plastique/bois (5x5 cm).

    Fabrication :

        Coupe le fil :
            Prends ton fil (1-2 mm).
            Mesure 6.25 cm avec règle métal (pas de ciseaux tordus, pince coupante nette).
            Coupe pile au milieu = 2 segments de 3.125 cm.
            Astuce : Lime les bouts (papier verre) pour enlever bavures.

        Prépare le coaxial :
            Dénude 1 cm à l’extrémité (couteau précis ou cutter).
            Sépare âme (fil central) et blindage (tresse autour).

            Torsade blindage pour qu’il tienne.

        Soudure :
            Chauffe fer (5 min, 300-350°C).
            Étame fil et coaxial : petite goutte soudure sur chaque bout, attends 2s, retire fer.
            Soude âme à un segment (3.125 cm).
            Soude blindage à l’autre segment (3.125 cm).

            Schéma mental :

            [Âme coaxiale] ---- [Fil 3.125 cm] (haut)
                               |
            [Blindage coax] ---- [Fil 3.125 cm] (bas)

            Sécurité : Pas de soudure qui touche âme ET blindage = court-circuit !

        Fixation :
            Colle (époxy) les deux segments verticalement sur base plastique.
            Laisse 1-2 mm entre soudure âme/blindage (pas de contact).
            Attends 10 min (époxy sèche).

    Vérification :
        Multimètre en "continuité" (bip) :
            Âme → fil haut = bip.
            Blindage → fil bas = bip.
            Âme → blindage = silence (sinon, refais soudure).

        Erreur : "Bip partout ? Court-circuit. Détache, refais propre."

    Résultat : Antenne verticale, 6.25 cm, rayonne partout, gain ~2-5 dBi.

Option 2 : Antenne Yagi Directionnelle (5 Éléments)

Quand ? Pour longue portée (1-15 km, viser un nœud précis).

    Matériaux :
        Fil cuivre/aluminium (total ~33 cm).
        Plaque métal/PCB (10x10 cm, réflecteur).
        Tige plastique (15-20 cm, ex. : règle ou tube PVC).
        Câble coaxial U.FL (10-20 cm).

    Fabrication :

        Coupe les éléments :
            Réflecteur : 10 cm (plaque ou fil plat).
            Dipôle : 6.25 cm (comme ci-dessus, 2 x 3.125 cm).
            Directeurs : 5.8 cm (D1), 5.6 cm (D2), 5.4 cm (D3).
            Astuce : Étiquette chaque morceau (papier collant) pour pas mélanger.

        Monte sur tige :
            Prends tige plastique (20 cm).
            Marque positions au stylo :
                0 cm : Réflecteur.
                3 cm : Dipôle (point soudure).
                5.5 cm : D1.
                8 cm : D2.
                10.5 cm : D3.
            Perce petits trous (foret 1-2 mm) à chaque marque.
            Passe fils dans trous, fixe avec colle époxy (sèche 10 min).

        Soudure dipôle :
            Comme dipôle simple : âme → fil haut (3.125 cm), blindage → fil bas (3.125 cm).
            Centre à 3 cm sur tige.

            Schéma mental :

            [10 cm Réflecteur] --- [6.25 cm Dipôle] --- [5.8 cm D1] --- [5.6 cm D2] --- [5.4 cm D3]

        Fixe réflecteur :
            Colle plaque métal à 0 cm (isolée du dipôle, pas de contact électrique).

        Alignement :
            Tous éléments parallèles, bien droits (règle pour vérifier).

    Vérification :
        Multimètre :
            Âme → fil haut dipôle = bip.
            Blindage → fil bas dipôle = bip.
            Âme → réflecteur = silence (sinon, isole mieux).

        Erreur : "Mauvais gain ? Mesures fausses. Recoupe précis."

    Résultat : Antenne Yagi, 20 cm long, gain ~8-10 dBi, directionnelle (vise cible).

Étape 3 : Connecter l’Antenne au Raspberry Pi (Hardware Time !)

Le Pi a une antenne interne (PCB). On va la bypasser pour brancher la nôtre. Attention, c’est délicat mais faisable !

Pour Raspberry Pi 3

    Localisation :
        Retourne le Pi (côté verso, sans coque).
        Près du chip Wi-Fi (petit carré métal), vois une trace PCB en zigzag (antenne interne).
        À côté, un pad J13 : deux petits trous (U.FL prêt).
        Photo mentale : J13 = cercle central (âme) + anneau autour (masse).

    Modification :
        Soude U.FL :
            Prends connecteur U.FL (minuscule !).
            Chauffe fer (300°C, 5 min).
            Étame U.FL : goutte soudure sur pin central + masse.
            Pose U.FL sur J13 :
                Pin central → trou central.
                Masse (côtés) → anneau.
            Soude rapide (2-3s par point, loupe aide).

        Option hardcore :
            Coupe trace PCB interne (zigzag) avec cutter précis.
            Gratte juste assez (1 mm) pour couper, pas plus (sinon circuit HS).
            Astuce : Teste Wi-Fi avant/après (voir config).

    Branchement :
        Clique câble coaxial U.FL sur J13 (pousse fort, "clic").
        Autre bout va à ton antenne (dipôle/Yagi).

    Vérif :
        Multimètre :
            Âme U.FL → fil haut = bip.
            Masse → fil bas = bip.
            Âme → masse = silence.

        Erreur : "Wi-Fi mort ? Soudure HS ou court-circuit. Refais propre."

Pour Raspberry Pi 4/5

    Localisation :
        Haut gauche (face dessus), sous blindage métal (Wi-Fi).
        Retire blindage (pince fine, soulève délicat).
        Vois antenne PCB (petite boucle) + ligne fine vers module Wi-Fi.
        Pas de J13, faut souder direct sur ligne.

    Modification :

        Soude U.FL :
            Trouve ligne antenne (trace fine entre module et PCB interne).
            Gratte 1 mm (cutter) pour exposer cuivre.
            Étame : goutte soudure sur ligne + masse proche (point GND).

            Soude U.FL :
                Pin central → ligne.
                Masse → GND (blindage ou vis proche).
            Loupe + fer fin obligatoire (sinon, massacre assuré).

        Coupe interne :
            Gratte trace vers antenne PCB (1 mm après U.FL).
            Teste avant/après.

    Branchement :
        Clique câble U.FL sur connecteur soudé.
        Relie à antenne DIY.

    Vérif :
        Multimètre : Comme Pi 3.
        Erreur : "Pas de signal ? Soudure loupée ou trace mal coupée."

Précautions (Sérieux !)

    Fer 15-25W, pointe fine (pas 60W qui fond tout).
    Loupe + lumière (LED) pour voir micro-soudures.
    Teste continuité avant d’allumer (court-circuit grille le Pi).
    Travaille sur tapis antistatique ou bois (pas métal).

Étape 4 : Configuration Logicielle (Facile !)

Ton antenne est prête, faut dire au Pi de l’utiliser.

    Vérifie Wi-Fi :

        Branche Pi, ouvre terminal (SSH ou écran).

        iwconfig :
            Sortie : wlan0 IEEE 802.11 ... Mode:Managed.
            Si vide : "Antenne mal branchée ou Pi grillé. Teste câble."

    Mode Ad-Hoc :

        sudo iwconfig wlan0 mode ad-hoc (active IBSS).
        sudo iwconfig wlan0 channel 1 essid "AirNetMesh" (rejoins réseau).

        Vérifie : iwconfig wlan0 → Mode:Ad-Hoc ESSID:"AirNetMesh".

        Erreur : "Command failed ? Carte incompatible ou sudo oublié."

    BATMAN-adv :

        Installe : sudo apt install batman-adv batctl -y (~5 min).

        Configure :

        sudo modprobe batman-adv
        sudo batctl if add wlan0
        sudo ifconfig bat0 up
        Test : batctl n (liste voisins mesh).
        Erreur : "bat0 absent ? Vérifiez iw dev ou relancez."

Étape 5 : Tests et Optimisation (T’es un Pro !)

Vérifie que ça marche et booste si besoin.

    Portée :

        sudo iwlist wlan0 scan : Liste réseaux détectés.
        Compare avant (antenne interne) vs après (DIY).
        Attendu : Plus de signaux ou RSSI plus fort (-50 dBm vs -80 dBm).
        Erreur : "Rien ? Antenne mal soudée ou portée bloquée (mur)."

    Débit :

        Deux Pi sur AirNet :
            Pi 1 : iperf -s (serveur).
            Pi 2 : iperf -c 10.13.37.X (client, IP du Pi 1).

        Résultat : ~10-20 Mbps (dipôle), ~5-15 Mbps (Yagi loin).

        Erreur : "0 Mbps ? Nœuds hors portée ou BATMAN HS."

    Ajustements :

        Yagi : Oriente pile vers nœud cible (boussole ou essai-erreur).
        Puissance : sudo iwconfig wlan0 txpower 20 (max légal).
        Ampli RF : Option (~20€), mais attention lois (EIRP ≤ 30 dBm).

Bonus : Astuces AirNet PCTamalou (Pro Tips !)

    Solaire : Panneau 5V/10W (~15€) + câble USB = autonomie outdoor (6h soleil = 24h).
    Furtivité : Canaux 1, 6, 11 (moins saturés), iwconfig wlan0 txpower 10 (moins détectable).
    Échelle : Nœuds Yagi en étoile (3-4 nœuds, 120° chacun) = village couvert.
