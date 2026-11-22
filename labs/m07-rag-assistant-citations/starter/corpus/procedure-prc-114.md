---
titre: PRC-114 Redémarrage du serveur de facturation
version: 2026-01
statut: en vigueur
droits: tous
---
# PRC-114 Redémarrage du serveur de facturation

## Préalables
Avant tout redémarrage, obtenez l'accord du responsable d'exploitation. Prévenez l'astreinte applicative au poste 4410. Vérifiez qu'aucun traitement de facturation n'est en cours dans la console d'ordonnancement.

## Étapes
Arrêtez le service de facturation depuis la console d'administration. Attendez la fin de l'écriture des journaux, puis redémarrez le serveur. Relancez le service et vérifiez que la page d'état affiche le statut vert.

## Après le redémarrage
Consignez l'intervention dans le journal d'exploitation avec l'heure de début, l'heure de fin et le nom de la personne qui a donné son accord. En cas d'échec, ouvrez un incident de priorité 2.
