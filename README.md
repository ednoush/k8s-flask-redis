# k8s-redis-flask

Ce projet permet de déployer une application multi-tiers (API Flask + Redis) sur Kubernetes en appliquant les bonnes pratiques de sécurité.
Ce projet a été réalisé dans le cadre de ma préparation à la certification CKAD (formation KodeKloud).

---

## Objectif du projet

Ce projet démontre, de façon concrète et vérifiable, la maîtrise du cycle complet de déploiement d'une application sur Kubernetes : conteneurisation, orchestration, configuration, sécurité, réseau et gestion des ressources.

L'application est volontairement simple. Son rôle n'est pas de porter une logique métier complexe, mais de servir de support vivant pour vérifier que chaque brique Kubernetes mise en place fonctionne réellement.

---

## Architecture

```
                 Utilisateur
                      │
                      ▼
      Service NodePort « portofolio-app-service »   ← seul point d'entrée externe
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
    Pod API       Pod API       Pod API              Deployment : 3 réplicas
        └─────────────┼─────────────┘
                      ▼
      Service ClusterIP « redis-service »            ← nom stable, jamais d'IP de Pod en dur
                      │
                      ▼
                  Pod Redis                          Deployment : 1 réplica

  Injectés dans les Pods : ConfigMap « map-api », Secret « file-secret »,
  ServiceAccount « my-service-account » (RBAC), SecurityContext non root.
```

---

## Stack technique

| Composant | Choix |
|---|---|
| Langage et framework | Python 3.13, Flask |
| Base de données | Redis |
| Conteneurisation | Docker |
| Orchestration | Kubernetes (cluster de laboratoire) |
| Registre d'images | Docker Hub : `ednoush01/portofolio-app:v1` |

---

## Contenu du dépôt

| Fichier | Rôle |
|---|---|
| `main.py` | Code de l'API Flask |
| `requirements.txt` | Dépendances Python |
| `dockerfile-portofolio.dockerfile` | Construction de l'image de l'application |
| `ns-deployment.yml` | Namespaces `dev` et `prod` |
| `configmap.yaml` | ConfigMap `map-api` (configuration non sensible) et Secret `file-secret` |
| `svc-role.yml` | ServiceAccount dédié et RoleBinding |
| `Deployment-web-app.yml` | Deployments de l'API (3 réplicas) et de Redis (1 réplica) |
| `svc-cluster-IP.yml` | Service NodePort de l'API et Service ClusterIP de Redis |

---

## Points d'accès de l'API

| Route | Rôle |
|---|---|
| `GET /` | Informations générales et nom du Pod qui a traité la requête |
| `GET /healthz` | Vérification de la connexion à Redis, utilisable par les sondes Kubernetes |
| `GET /count` | Lecture du compteur de visites stocké dans Redis |
| `POST /count` | Incrémentation du compteur de visites |
| `GET /items` | Liste des éléments stockés |
| `POST /items` | Ajout d'un élément (JSON : `{"item": "..."}`) |

Le nom du Pod renvoyé par `GET /` permet de constater la répartition de charge entre les trois réplicas.

---

## Sécurité appliquée

- **Exécution sans privilèges root** : un `securityContext` (`runAsUser` / `runAsGroup`) est appliqué aux deux Deployments.
- **Configuration externalisée** : les variables non sensibles sont dans un ConfigMap, le mot de passe Redis dans un Secret. Chaque variable est injectée individuellement avec `valueFrom` pour garder un contrôle précis sur ce que reçoit chaque conteneur.
- **Identité dédiée** : l'application utilise son propre ServiceAccount, distinct du compte par défaut, avec des droits limités par RBAC selon le principe du moindre privilège.
- **Ressources maîtrisées** : des `requests` et `limits` CPU et mémoire sont définis, pour éviter qu'un conteneur ne consomme toutes les ressources du nœud.
- **Aucun secret réel dans le dépôt** : la valeur du Secret est vide dans `configmap.yaml` et doit être renseignée au moment du déploiement.

---

## Déploiement

**1. Construire et publier l'image**

```bash
docker build -f dockerfile-portofolio.dockerfile -t <utilisateur>/portofolio-app:v1 .
docker push <utilisateur>/portofolio-app:v1
```

**2. Créer les namespaces**

```bash
kubectl apply -f ns-deployment.yml
```

**3. Appliquer la configuration et la sécurité, puis les charges de travail**

```bash
kubectl apply -f configmap.yaml
kubectl apply -f svc-role.yml
kubectl apply -f Deployment-web-app.yml
kubectl apply -f svc-cluster-IP.yml
```

L'ordre a une raison : les Pods lisent le ConfigMap, le Secret et le ServiceAccount au démarrage. Ces objets doivent donc exister avant les Deployments.

**4. Vérifier l'état des Pods et trouver le port exposé**

```bash
kubectl get pods -n dev
kubectl get svc -n dev
```

**5. Tester l'API**

```bash
curl http://<IP_DU_NŒUD>:<NODEPORT>/
curl http://<IP_DU_NŒUD>:<NODEPORT>/healthz
```

---

## Tests réalisés

- Stabilité des Pods vérifiée : statut `Running`, aucun redémarrage.
- Test de bout en bout de l'API avec `curl` sur le NodePort, connexion à Redis confirmée.
- Vérification des endpoints du Service Redis pour confirmer qu'il cible le bon Pod.
- Test de connexion TCP depuis un Pod de l'API vers le Service ClusterIP de Redis.
- Vérification de l'injection des variables du ConfigMap (`APP_NAME` visible dans la réponse de l'API).
- Vérification du `securityContext` avec `kubectl exec ... -- id`.
- Validation de la syntaxe des manifestes avec `kubectl apply --dry-run=client`.
---

## Difficultés rencontrées et solutions

| Problème | Solution |
|---|---|
| Avertissement Docker `JSONArgsRecommended` | Passage à la forme « exec » pour l'instruction `CMD` |
| Bloc `resources` sans effet | Correction de l'indentation YAML : le bloc doit être une propriété du conteneur |
| RoleBinding sans effet | Création du Role manquant, vérifiée avec `kubectl get roles` |

---

## Pistes d'amélioration

- Ajouter des sondes `livenessProbe` et `readinessProbe` sur `/healthz`.
- Utiliser une version précise de l'image Redis plutôt que `latest`.
- Répliquer la configuration complète dans le namespace `prod`.
- Remplacer le NodePort par un Ingress pour un accès externe plus propre.
- Lancer l'API avec Gunicorn déjà présent dans les dépendances plutôt qu'avec le serveur de développement de Flask.

---

