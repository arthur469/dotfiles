# Bureau 43PR personnalisé

Les modules natifs sont conservés. Dans Paramètres → BAR, CPU, RAM et GPU ont chacun leur activation et leur emplacement. Un appui long déplace un module ; le rapprocher d’une autre bulle les regroupe. Les commandes START/CENTER/END rétablissent un ancrage automatique.

La disposition libre sur l’écran est facultative et désactivée par défaut. Une fois activée, les mêmes bulles se déplacent dans les deux directions. Le seul mode de regroupement est Auto, activable/désactivable : déposer près du haut, du bas, de la gauche ou de la droite d’un module détermine la nouvelle cellule. Une seconde rangée permet un carré. Glisser la bordure ou le fond d’une bulle déplace le groupe entier. Les voisins libèrent la place pendant le geste. Les bulles évitent leurs voisines et restent dans les limites de l’écran ; une résolution trop petite peut manquer de place. En disposition libre, « Reserve screen space » active une mosaïque native autour des bulles : les fenêtres se réorganisent automatiquement, et une flottante qui les recouvre est déplacée ou, si nécessaire, réduite. Désactiver cette option autorise la superposition et rétablit la disposition précédente. Le redimensionnement manuel des tuiles n’est pas disponible dans cette mosaïque automatique.

## Fenêtres

- Open apps reste le module d’origine : replier/déplier, taille des icônes et longueur visible réglables ; la liste défile. Les icônes des fenêtres réduites sont grises, les autres gardent leurs couleurs.
- Super+Tab reste le carrousel ; Alt+Tab change directement de fenêtre.
- Super+O règle le bureau courant ; Super+Maj+O règle uniquement la fenêtre sélectionnée. « Suivre le bureau » retire l’exception. L’exception suit cette fenêtre pendant sa vie et disparaît à sa fermeture. Le plein écran du compositeur comme celui demandé par une vidéo reste toujours opaque. Brave reste opaque indépendamment du bureau. La sélection dans le menu suit aussi le survol de la souris.
- Super+Espace bascule la fenêtre flottante. L’option « flottantes rapides » remet une fenêtre créée ainsi en mosaïque lorsqu’on la déplace avec Super+clic ; les boîtes de dialogue ne sont pas concernées.
- Super+Maj+touche de la rangée des chiffres déplace la fenêtre vers un autre bureau ; Super+touche sélectionne ce bureau. Par exemple : sélectionner Brave, Super+Maj+é (touche physique 2) l’envoie sur le bureau 2 sans y aller ; Super+é ouvre ensuite ce bureau. Les positions physiques sont utilisées pour respecter AZERTY et QWERTY.
- Super+M réduit normalement ; Super+Ctrl+M choisit ou crée un groupe de fenêtres réduites. La création d’un groupe active cette option. Les groupes réutilisent Open apps ; retirer un groupe conserve ses fenêtres dans les réduites ordinaires.
- L’option Super+glisser vers Open apps permet de réduire une fenêtre en la déposant sur ce module ou sur un groupe. Elle reste désactivée par défaut. À l’inverse, maintenir Super puis glisser l’icône d’une fenêtre réduite depuis Open apps la restaure en flottante à l’endroit du relâchement, dans les limites de l’écran.

## Consommation et luminosité

Un clic sur CPU/RAM/GPU ouvre la liste des processus. Le tri initial affiche les plus consommateurs. Le survol et la confirmation figent la liste. Tous les processus peuvent être parcourus par défilement, sans bouton Pause. Sortir la souris conserve le défilement ; fermer et rouvrir le panneau le réinitialise. Le tri par nom reste disponible pendant le survol. La croix demande confirmation avant SIGTERM ; une seconde action permet de forcer SIGKILL. Les processus essentiels et ceux d’un autre utilisateur sont protégés. L’identité de démarrage et un pidfd empêchent de viser un PID réutilisé.

Le module Luminosité et les touches dédiées utilisent le rétroéclairage ou DDC/CI pour l’écran concerné. La molette sur l’icône de luminosité règle la valeur ; un clic ouvre les paramètres d’affichage et leur curseur de luminosité. Les retours visuels utilisent la carte native du volume, verticale ou horizontale suivant la barre. Sur un écran qui ne prend pas DDC/CI en charge, une mesure indisponible ne représente pas une luminosité de zéro.

Les notifications, le menu d’alimentation et le volume s’ouvrent vers l’intérieur près de leur bouton. Les notifications courtes restent au moins six secondes ; un délai nul reste persistant. Le calendrier utilise la langue LC_TIME/LANG de la session. Une traduction complète de tous les anciens menus 43PR reste un chantier distinct.

## Maintenance

Les fonds animés passent par hyprquickpaper, mpvpaper et le restaurateur natif 43PR. OpenWallpaper et le second module de fenêtres réduites sont retirés. Vérifier la version locale et ses réglages avant toute nouvelle extension. Le dossier de migration contient diagnostics, essais, sauvegardes et contributions préparées ; ne pas publier les archives personnelles.
