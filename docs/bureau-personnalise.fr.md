# Bureau 43PR personnalisé

[English](desktop-extensions.en.md)

Les modules natifs sont conservés. Dans Paramètres → BAR, CPU, RAM et GPU ont chacun leur activation et leur emplacement. Un appui long déplace un module ; le rapprocher d’une autre bulle les regroupe. Les commandes START/CENTER/END rétablissent un ancrage automatique.

La disposition libre sur l’écran est facultative. Le seul regroupement est Auto, activable/désactivable : déposer dans une bulle près du haut, du bas, de la gauche ou de la droite d’un module détermine sa cellule. Cela permet rangées, colonnes et carrés. Glisser le fond ou la bordure déplace tout le groupe ; le déposer dans un autre groupe les fusionne. Pendant un glissement avec le bouton gauche enfoncé, le clic droit tourne la disposition de 90° ; les icônes et textes restent droits. Un appui long relâché sans déplacement ne modifie rien. Les guides aimantent les bords et centres proches. Les bulles conservent seulement 3 pixels logiques de marge intérieure par côté. Leur contour de sélection accentué apparaît pendant l’appui maintenu sans augmenter leur largeur.

Les voisins libèrent la place pendant le geste. Une expansion Open apps déplace temporairement ses voisins ; replier restaure leurs positions, sauf déplacement volontaire entre-temps. Si la place manque, la longueur d’Open apps diminue et le défilement permet toujours de parcourir les applications. Une configuration trop dense pour l’écran peut nécessiter une taille d’icônes ou une échelle plus petite.

« Reserve screen space » réserve uniquement les rectangles visibles et l’espacement « Edge margin ». L’extension Hyprland facultative conserve l’arbre de mosaïque natif : l’ordre des fenêtres, les échanges et le redimensionnement restent disponibles ; les fenêtres qui rencontrent une bulle réduisent leur rectangle visible. Désactiver la réservation restaure leur géométrie native et autorise la superposition. La disposition libre ne remplace plus le gestionnaire de mosaïque. Le plugin est compilé pour la version exacte de Hyprland ; après changement de version, le reconstruire explicitement avec `.config/hypr/plugins/bubble-reserve/build.sh` dans le dépôt. Sans binaire compatible, la barre normale conserve l’exclusion standard ; la réservation intérieure des bulles libres n’est pas disponible.

## Fenêtres

- Open apps reste le module d’origine : replier/déplier, taille des icônes et longueur visible réglables ; la liste défile. Les fenêtres réduites apparaissent en premier, sans mélanger leur ordre avec celui des fenêtres ouvertes. Les icônes des fenêtres réduites sont grises, les autres gardent leurs couleurs.
- Super+Tab reste le carrousel ; Alt+Tab change directement de fenêtre.
- Super+O règle le bureau courant ; Super+Maj+O règle uniquement la fenêtre sélectionnée. « Suivre le bureau » retire l’exception. L’exception suit cette fenêtre pendant sa vie et disparaît à sa fermeture. Le plein écran du compositeur comme celui demandé par une vidéo reste toujours opaque. Brave est réglable comme les autres fenêtres hors plein écran. La glissière native va de 40 à 100 %, par pas de 1 %, à la souris, à la molette ou au clavier. Échap annule l’aperçu en cours. Ctrl+Super+O retire toutes les exceptions existantes, y compris sur les autres bureaux ; chaque fenêtre retrouve la valeur de son propre bureau. Le clic gauche du module Opacité ouvre sa section dans Display des paramètres 43PR. Le survol et la molette conservent la carte de contrôle native orientée comme la barre. La molette sur son icône ou sa glissière règle le bureau par pas de 1 %. Le clic droit déverrouille toutes les fenêtres. Les raccourcis conservent le panneau d’opacité dédié : sa molette fonctionne partout sur la sortie où il est ouvert, sans faire défiler l’application dessous. Cliquer son icône règle le périmètre sélectionné à 40 %.
- Super+Espace bascule la fenêtre flottante. L’option « flottantes rapides » remet une fenêtre créée ainsi en mosaïque lorsqu’on la déplace avec Super+clic ; les boîtes de dialogue ne sont pas concernées.
- Super+Maj+touche de la rangée des chiffres déplace la fenêtre vers un autre bureau ; Super+touche sélectionne ce bureau. Par exemple : sélectionner Brave, Super+Maj+é (touche physique 2) l’envoie sur le bureau 2 sans y aller ; Super+é ouvre ensuite ce bureau. Les positions physiques sont utilisées pour respecter AZERTY et QWERTY.
- Super+M réduit normalement ; Super+Ctrl+M choisit ou crée un groupe de fenêtres réduites. La création d’un groupe active cette option. Les groupes réutilisent Open apps ; retirer un groupe conserve ses fenêtres dans les réduites ordinaires.
- L’option Super+glisser vers Open apps permet de réduire une fenêtre en la déposant sur ce module ou sur un groupe. Elle reste désactivée par défaut. À l’inverse, maintenir Super puis glisser l’icône d’une fenêtre réduite depuis Open apps la restaure en flottante à l’endroit du relâchement, dans les limites de l’écran.

## Consommation et luminosité

Un clic sur CPU/RAM/GPU ouvre la liste des processus. Le tri initial affiche les plus consommateurs. Le survol et la confirmation figent la liste. Tous les processus peuvent être parcourus par défilement, sans bouton Pause. Sortir la souris conserve le défilement ; fermer et rouvrir le panneau le réinitialise. Le tri par nom reste disponible pendant le survol. Les processus sont regroupés par application : l’en-tête additionne leur consommation et se déplie pour voir chaque processus. La croix d’en-tête vise le groupe ; celle d’un enfant vise ce seul processus. La confirmation apparaît près de la ligne sélectionnée. La croix demande confirmation avant SIGTERM ; une seconde action permet de forcer SIGKILL. Les processus essentiels et ceux d’un autre utilisateur sont protégés. L’identité de démarrage et un pidfd empêchent de viser un PID réutilisé.

Le module Luminosité et les touches dédiées utilisent le rétroéclairage ou DDC/CI pour l’écran concerné. La molette sur l’icône de luminosité utilise le même pas que celle du son et fusionne les changements rapides en une écriture après 280 ms de pause. Le nombre affiché suit immédiatement la demande. Un clic droit passe à 0 %, puis un second retrouve la dernière valeur choisie, indépendamment pour chaque écran, pendant la session. Un clic gauche ouvre les paramètres d’affichage et leur curseur de luminosité. Les retours visuels utilisent la carte native du volume, verticale ou horizontale suivant la barre. Sur un écran qui ne prend pas DDC/CI en charge, une mesure indisponible ne représente pas une luminosité de zéro.

Les notifications, le menu d’alimentation et le volume s’ouvrent vers l’intérieur près de leur bouton. Les notifications courtes restent au moins six secondes ; un délai nul reste persistant. Le calendrier utilise la langue LC_TIME/LANG de la session. Une traduction complète de tous les anciens menus 43PR reste un chantier distinct.

## Fichiers

Super+E et l’ouverture des dossiers utilisent Thunar. « Choisir des fichiers » est le sélecteur GTK des applications qui passent par le portail ; ce choix est explicite. Ctrl+O reste géré par l’application active : certaines utilisent leur propre boîte de dialogue.

## Maintenance

Les fonds animés passent par hyprquickpaper, mpvpaper et le restaurateur natif 43PR. Un seul lecteur est partagé entre les bureaux ; aucun lecteur distinct ne tourne pour les bureaux invisibles. L’option native auto-pause suspend le décodage lorsque le fond est caché, et le reprend lorsqu’il redevient visible. Le mode nuit impose une pause du fond, sans toucher à YouTube ni aux tâches. Le mode jour retire cette pause et reprend explicitement Hardware Sync AI en conservant ses appareils sélectionnés. Les routines personnelles restent séparées de l’image vierge. OpenWallpaper et le second module de fenêtres réduites sont retirés. Vérifier la version locale et ses réglages avant toute nouvelle extension. Le dossier de migration contient diagnostics, essais, sauvegardes et contributions préparées ; ne pas publier les archives personnelles.

Le code de ces extensions a été développé avec l’assistance d’OpenAI Codex, puis validé par les essais consignés dans le projet de migration. Les contributions amont restent séparées et soumises aux règles et politiques IA de chaque projet.


## Ajustements du 27 octobre

Maintenir le bouton gauche sur un module et tourner la molette règle uniquement son opacité, de 40 à 100 %, par pas de 1 %. Sur le fond ou le bord d’une bulle, le même geste règle le fond et tous ses boutons à la même valeur, sans double multiplication. Un bouton peut ensuite être réglé séparément. Changer de groupe lui fait prendre l’opacité du groupe d’arrivée ; le détacher conserve sa valeur. Une glissière affiche la valeur pendant le geste. Paramètres → Display → Opacité permet de tout rétablir si un bouton est devenu difficile à voir.

Le réglage Edge margin s’applique aux quatre côtés du cadre et à l’écart des fenêtres autour des bulles. La marge intérieure reste de trois pixels logiques. La poignée supérieure des paramètres se déplace en maintenant sa partie libre, à côté des trois boutons d’ancrage. Le sélecteur de bureaux suit la rotation locale de son groupe.

L’ouverture ou le repli d’Open apps garde l’ordre des groupes dans leur bande. Le glissement reste animé ; le relâchement applique directement la position finale. Les tailles extrêmes restent limitées par l’espace disponible.

La fermeture du groupe Steam vise aussi son processus principal : fermer uniquement un sous-processus supervisé peut toujours entraîner sa relance par Steam. Le réglage de réservation envoie une seule taille finale aux applications. Le double curseur de redimensionnement propre au client Steam reste à confirmer visuellement ; aucune règle globale de curseur n’a été imposée.

Les commandes IPC `notifications night true` et `notifications night false` coupent toutes les alertes pour la nuit puis restaurent le choix précédent. L’historique reste conservé. Un changement manuel de Ne pas déranger quitte ce contrôle temporaire. Les routines personnelles qui appellent ces commandes restent hors de l’image vierge.

Le fond `Odysseus-Terminal-ASCII.mp4` est une extraction vidéo de l’effet ASCII du thème Terminal, sans interface ni données. Il est sélectionnable dans le sélecteur 43PR et utilise son moteur unique, sa pause selon la visibilité et son mode nuit. Aucune vidéo distincte ne tourne par bureau caché.

Pour le défaut Bluetooth au démarrage de Quickshell 0.3.2, `scripts/wait-bluetooth.py` attend au maximum huit secondes que BlueZ soit joignable ; il ne met pas l’adaptateur sous tension. Le service utilisateur peut l’appeler par `ExecStartPre=/usr/bin/python3 %h/.config/quickshell/scripts/wait-bluetooth.py`. Il s’agit d’un contournement au démarrage ; un arrêt ultérieur de BlueZ peut encore nécessiter un redémarrage de Quickshell. Défaut amont suivi dans https://github.com/quickshell-mirror/quickshell/issues/1201.


Maintien du clic gauche + **Ctrl + molette** : taille du composant, de 50 à 200 % de sa taille normale dans la barre, par pas de 5 %. Sur le fond d’un groupe, le geste conserve les proportions entre ses composants. La molette sans Ctrl reste dédiée à l’opacité (40–100 %, pas de 1 %). Les dimensions du bouton, les zones de clic, les ancrages des panneaux et l’espace réservé aux fenêtres suivent cette taille. Open apps conserve son budget et son défilement. Le retour global aux tailles normales est disponible par `qs ipc call bar resetSizes` ou la réinitialisation des réglages Bar.

Les pictogrammes seuls partagent une boîte carrée de référence de 16 pixels logiques à l’échelle normale. Leur dessin visible est ajusté proportionnellement et centré dans chaque bouton, y compris pour les caractères Unicode supplémentaires ; la taille personnelle du module reste appliquée ensuite. Le compteur des notifications reste un badge dans le coin ; il ne doit pas déplacer la cloche. Les rotations depuis le contenu d’un module conservent l’orientation au relâchement et le point de prise en main ; les zones de clic suivent les positions libres.

Configs → Keybinds affiche aussi Super+Tab / Super+Maj+Tab, Alt+Tab, l’opacité de la fenêtre, sa réinitialisation, les commandes des fenêtres réduites et les gestes Super+souris. Les combinaisons fixes sont en lecture seule, comme les commandes de bureaux natives ; les commandes d’opacité dérivées suivent la touche Opacity modifiable. Les actions rapides utilisent le même identifiant `kb_qa` que Lua. Les valeurs de secours réservent Super+L au verrouillage et Print / Maj+Print aux captures de zone / écran complet.

Le pont natif 0.2 ou suivant est nécessaire pour détecter Ctrl hors du clavier de la barre. Après une mise à jour des sources du plugin, le reconstruire explicitement avec son script build.sh, même si la version de Hyprland est inchangée. Les tailles de curseur X11 et Hyprcursor suivent maintenant la même valeur de session.
