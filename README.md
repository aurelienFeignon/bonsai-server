# Bonsai Server

Serveur LLM Docker autonome, compatible OpenAI, réutilisable par Dedale ou une
autre application. La configuration testée utilise Bonsai 27B **1-bit Q1_0** sur
GPU NVIDIA : 4096 tokens, un slot et environ 4 Gio de VRAM sur RTX 5070. Il s'agit
de la famille historique Bonsai, distincte de Bonsai 2.

## Démarrer

Prérequis : Linux x64, Docker Compose avec accès GPU NVIDIA et Python 3 pour les
scripts de préparation. Aucun Python ni CUDA n'est installé sur l'hôte par ce projet.

```bash
git clone https://github.com/aurelienFeignon/bonsai-server.git
cd bonsai-server
python3 scripts/setup.py
python3 scripts/download-model.py
docker compose up -d --build --wait
python3 scripts/smoke.py
```

`setup.py` crée `.env` à partir de `.env.example`, génère une clé si nécessaire
et préserve les valeurs existantes. La clé n'est pas affichée. `.env` et `models/`
sont exclus de Git et du contexte Docker. Les poids sont montés en lecture seule.
Le téléchargement est reprenable et vérifie la révision, la taille et le SHA-256
avant d'activer le fichier. Un modèle existant avec un checksum différent n'est
jamais écrasé automatiquement.

API : `http://127.0.0.1:53110/v1`. La clé `BONSAI_API_KEY` est obligatoire pour les
appels du modèle. Le port hôte est configurable ; le port interne reste 53110.

## Passer des paramètres

Modifier `.env` pour conserver les réglages, puis recréer le conteneur :

```bash
docker compose up -d --force-recreate --wait
```

Ou passer une valeur ponctuelle :

```bash
BONSAI_CTX_SIZE=2048 BONSAI_TEMPERATURE=0.2 docker compose up -d --force-recreate --wait
BONSAI_CTX_SIZE=2048 python3 scripts/smoke.py
# Retour aux valeurs de .env :
docker compose up -d --force-recreate --wait
```

| Paramètres | Rôle / défaut |
| --- | --- |
| `MODEL_REPO`, `MODEL_REVISION`, `MODEL_FILE`, `MODEL_SHA256`, `MODEL_SIZE_BYTES` | Source HF et intégrité du modèle ; relancer le téléchargement après modification |
| `MODEL_DIR`, `BONSAI_MODEL_ALIAS` | Dossier des poids et identifiant annoncé par l'API |
| `BONSAI_CTX_SIZE`, `BONSAI_PARALLEL` | Contexte total 4096, un slot ; le contexte disponible par requête est réparti entre les slots |
| `BONSAI_GPU_ID`, `BONSAI_GPU_LAYERS` | GPU 0, 999 couches pour tout décharger sur GPU ; 0 couche laisse les calculs sur CPU mais le profil réserve toujours un GPU NVIDIA |
| `BONSAI_BATCH_SIZE`, `BONSAI_UBATCH_SIZE` | Batch et microbatch 128 |
| `BONSAI_THREADS`, `BONSAI_CPU_LIMIT`, `BONSAI_RAM_LIMIT` | 4 threads, 4 CPU, 8g de RAM ; ces limites ne plafonnent pas la VRAM |
| `BONSAI_FLASH_ATTN`, `BONSAI_CACHE_TYPE_K`, `BONSAI_CACHE_TYPE_V` | Flash attention `on`, cache KV `f16` |
| `BONSAI_JINJA`, `BONSAI_CHAT_TEMPLATE` | `false`, `chatml` : voie texte qualifiée pour le JSON |
| `BONSAI_REASONING`, `BONSAI_REASONING_BUDGET`, `BONSAI_REASONING_FORMAT` | `off`, 0, `deepseek` ; le raisonnement et les outils restent non qualifiés |
| `BONSAI_CONTEXT_SHIFT` | `false` : refus d'un contexte trop long au lieu de déplacer le début |
| `BONSAI_TEMPERATURE`, `BONSAI_TOP_P`, `BONSAI_TOP_K`, `BONSAI_MIN_P`, `BONSAI_MAX_TOKENS` | Défauts serveur 0.1 / 0.95 / 20 / 0.05 / 600 |
| `BONSAI_BIND`, `BONSAI_PORT`, `BONSAI_NETWORK` | `127.0.0.1`, 53110, réseau Docker `bonsai-llm` |
| `BONSAI_CORS_ORIGINS`, `BONSAI_API_KEY` | Origines autorisées et clé locale |
| `CUDA_BASE_IMAGE`, `LLAMA_RELEASE`, `LLAMA_CUDA_VERSION`, `LLAMA_ARCHIVE_SHA256` | Versions de build ; changer ensemble release/variante CUDA/empreinte, puis reconstruire l'image |

Les variables du shell priment sur `.env`. Les scripts de préparation lisent des
valeurs littérales, sans exécuter de shell ni développer `${...}`. Les valeurs
avec espaces doivent être entre guillemets. Les valeurs par défaut du serveur
(température, nombre de tokens, etc.) peuvent être remplacées par chaque requête
compatible OpenAI ; Dedale envoie notamment ses propres budgets.

Les options natives non listées peuvent être ajoutées comme arguments, sans
`eval` et sans découpage d'une chaîne `EXTRA_ARGS` :

```bash
docker compose stop bonsai
docker compose run --rm --service-ports --use-aliases bonsai --ctx-size 2048 --temp 0.2
# Après arrêt de cette commande :
docker compose up -d --wait
```

Les arguments explicites arrivent après ceux construits depuis l'environnement.
Conserver le port interne 53110 et l'écoute 0.0.0.0, utilisés par Docker et le
healthcheck. Changer le port public avec `BONSAI_PORT`. Pour libérer la VRAM :
`docker compose stop bonsai`.

## Connecter Dedale

Le réseau est créé au démarrage du serveur. Son alias DNS est `bonsai`.
Dedale y rattache uniquement son API ; PostgreSQL et ses autres services restent
sur son réseau habituel.

```bash
cd /opt/dedale
BONSAI_SERVER_DIR="$HOME/bonsai-server" ./scripts/download-bonsai.sh
# .env Dedale : COMPOSE_FILE=docker-compose.yml:docker-compose.semantic.yml:docker-compose.bonsai.yml
docker compose up -d --no-deps api
python3 scripts/qualify-bonsai.py
```

Le script de compatibilité synchronise la clé, le nom du réseau et l'alias du
modèle dans le `.env` local de Dedale, sans les afficher. Relancer cette étape
si ces trois paramètres changent. Les autres applications peuvent utiliser le
même réseau externe ou l'API sur le port hôte avec leur propre client.

Démarrer le serveur avant l'API Dedale. Les projets ont des cycles de vie
indépendants : arrêter Dedale n'arrête plus Bonsai. Pour supprimer le réseau
avec `docker compose down`, détacher d'abord ses consommateurs ; préférer `stop`
pour libérer seulement la mémoire GPU.

## Vérifications et limites

```bash
python3 -m unittest discover -s tests -v
python3 scripts/smoke.py
```

Cinq tests hors ligne vérifient la priorité de configuration, la préservation de
la clé et des réglages, les chemins de modèles et le contrôle d'intégrité.
Le test HTTP vérifie l'authentification, l'identité du modèle, le contexte et les
slots effectifs, puis une génération JSON. Les contextes 2048 et 4096 ont été
vérifiés sur le serveur réel, ainsi que deux slots avec partage du contexte. Le RAG Dedale reste fonctionnel après extraction.

Seuls les réglages de base sont qualifiés : les autres choix de modèle, cache
KV, raisonnement, contexte et parallélisme demandent une vérification sur le
matériel cible. La mémoire augmente avec les paramètres ; 4 Gio n'est pas une
limite garantie. La qualité du modèle 1-bit reste imparfaite (répétitions,
français maladroit ou faits hors sujet). Les références résolubles ne prouvent
pas automatiquement chaque affirmation. Vision, outils et charge ne sont pas
qualifiés par ces tests textuels.

## Provenance

Poids : [prism-ml/Bonsai-27B-gguf](https://huggingface.co/prism-ml/Bonsai-27B-gguf),
révision `f10afb355f104535e3e3e98cf7ab7795c72bd292` ; fiche Apache-2.0.
Runtime : [PrismML llama.cpp](https://github.com/PrismML-Eng/llama.cpp/releases/tag/prism-b10777-e3de715),
release `prism-b10777-e3de715`, Linux CUDA 12.8.
Démo de référence : [Bonsai-demo](https://github.com/PrismML-Eng/Bonsai-demo),
commit examiné `db871ea96bffff5ce5609873c412b75d7cd5ba3c`.
Les fichiers `.env.example` et `Dockerfile` fixent les empreintes des poids et du
runtime. Leurs licences respectives restent applicables.
