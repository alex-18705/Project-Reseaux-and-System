# CHECK.md — Vérification V1 du Proxy Réseau C + Python Bridge

## 1. Objectif du document

Ce fichier sert à vérifier si l’implémentation réseau actuelle respecte les exigences minimales d’une version V1 pour le projet :

```text
Python local <-> Proxy C local <-> Proxy C distant <-> Python distant
```

L’architecture actuelle repose sur :

- un proxy C UDP (`proxy_udp.c`) ;
- une API Python (`network_api.py` / `NetworkBridge`) ;
- une communication UDP localhost entre Python et C ;
- une communication UDP LAN entre deux proxys C.

Dans cette version, le proxy C agit principalement comme un relais de paquets UDP. Il ne comprend pas forcément le contenu JSON.

---

## 2. Architecture attendue

### 2.1 Flux général

```text
Python App A
   |
   | UDP localhost
   v
NetworkBridge A
   |
   | 127.0.0.1:py_port
   v
Proxy C A
   |
   | UDP LAN
   v
Proxy C B
   |
   | 127.0.0.1:py_port
   v
NetworkBridge B
   |
   v
Python App B
```

### 2.2 Rôle de chaque composant

| Composant              | Rôle attendu                                                  |
| ---------------------- | ------------------------------------------------------------- |
| `NetworkBridge` Python | Envoyer/recevoir des messages JSON depuis la logique Python   |
| `py_sock` dans C       | Recevoir/envoyer des paquets UDP depuis/vers Python local     |
| `lan_sock` dans C      | Recevoir/envoyer des paquets UDP depuis/vers les pairs réseau |
| `proxy_udp.c`          | Relayer les paquets entre Python et le LAN                    |
| JSON protocol          | Donner un format commun aux messages échangés                 |

---

## 3. Checklist fonctionnelle V1

### 3.1 Communication Python -> C

- [ ] Python crée un socket UDP.
- [ ] Python envoie vers `127.0.0.1:<py_port>`.
- [ ] Le proxy C bind correctement `py_sock` sur `127.0.0.1:<py_port>`.
- [ ] Le proxy C reçoit bien le premier paquet Python.
- [ ] Le proxy C mémorise le port éphémère de Python.
- [ ] Le proxy C affiche un log du type :

```text
[IPC] Client Python attaché sur le port XXXXX
```

### 3.2 Communication C -> Python

- [ ] Le proxy C connaît l’adresse de Python (`py_client_known = 1`).
- [ ] Quand un paquet LAN arrive, le proxy C le forward vers Python.
- [ ] `NetworkBridge._listen_loop()` reçoit le paquet.
- [ ] Le paquet reçu est décodable en UTF-8.
- [ ] Le paquet reçu est un JSON valide.
- [ ] Le message est placé dans `incoming_queue`.
- [ ] `get_updates()` retourne bien les messages reçus.

### 3.3 Communication C -> peer LAN

- [ ] Le proxy C possède un `lan_sock` bindé sur `0.0.0.0:<lan_listen_port>`.
- [ ] En mode client, `remote_ip` est fourni.
- [ ] En mode client, `remote_peer_known = 1` dès le démarrage.
- [ ] En mode serveur, le peer distant doit envoyer au moins un paquet pour être découvert.
- [ ] Le proxy C peut envoyer vers `remote_peer_addr`.
- [ ] Le firewall autorise UDP sur le port LAN choisi.

### 3.4 Communication peer LAN -> C

- [ ] Le peer distant connaît l’IP et le port LAN de ce proxy.
- [ ] Un paquet UDP arrive sur `lan_listen_port`.
- [ ] `lan_to_py_thread()` reçoit ce paquet.
- [ ] Le proxy C mémorise l’adresse du peer distant.
- [ ] Le proxy C affiche un log du type :

```text
[LAN] IP distante découverte : x.x.x.x:port
```

---

## 4. Checklist protocol JSON

### 4.1 Format attendu côté Python

Le message envoyé par `NetworkBridge.send_message()` a actuellement la forme :

```json
{
  "size": 1,
  "dest": "192.168.1.20",
  "dep": null,
  "seq": 1,
  "type": "SYNC_UPDATE",
  "payload": {
    "example": "data"
  }
}
```

À vérifier :

- [ ] Tous les messages possèdent un champ `type`.
- [ ] Tous les messages possèdent un champ `payload`.
- [ ] Les messages importants possèdent un champ `seq`.
- [ ] Le JSON reste inférieur à environ 1400 octets si possible.
- [ ] Le destinataire sait interpréter le même format JSON.

### 4.2 Problème actuel important

Le proxy C actuel ne lit pas les champs JSON :

```text
Le champ "dest" n’est pas utilisé par le proxy C.
Le champ "type" n’est pas utilisé par le proxy C.
Le champ "payload" n’est pas utilisé par le proxy C.
```

Donc le proxy C ne fait pas du routage intelligent. Il fait seulement :

```text
recevoir paquet -> forward vers l’unique peer connu
```

---

## 5. Bugs et risques potentiels dans `proxy_udp.c`

### BUG 1 — Le serveur ne peut pas envoyer si le peer n’a pas encore parlé

En mode serveur, `remote_peer_known = 0`. Donc si Python envoie avant que le peer distant ait envoyé un paquet, le proxy ne sait pas où forwarder.

Code concerné :

```c
if (remote_peer_known) {
    sendto(lan_sock, buffer, n, 0, (struct sockaddr*)&remote_peer_addr, sizeof(remote_peer_addr));
}
```

Risque :

```text
Python envoie un message, mais rien n’arrive au peer.
```

Solution possible :

- fournir `remote_ip` même côté serveur ;
- ajouter un handshake `HELLO` ;
- ajouter une configuration explicite des peers ;
- stocker plusieurs peers dans une table.

---

### BUG 2 — Un seul peer supporté

Le code C ne possède qu’une seule adresse distante :

```c
static struct sockaddr_in remote_peer_addr;
static int remote_peer_known = 0;
```

Risque :

```text
Impossible de gérer plusieurs joueurs/pairs correctement.
```

Solution possible :

- ajouter un `peer_manager` ;
- stocker une liste d’adresses IP/port ;
- utiliser le champ `dest` du JSON pour choisir le peer.

---

### BUG 3 — `dest` côté Python est ignoré par le proxy C

Dans Python :

```python
message = {
    "dest": destination,
    ...
}
```

Mais dans `proxy_udp.c`, le proxy ne parse pas ce champ.

Risque :

```text
Même si Python indique une destination, le proxy C envoie seulement au dernier/unique peer connu.
```

Solution possible :

- parser le JSON côté C ;
- utiliser `dest` pour choisir l’adresse distante ;
- ou supprimer `dest` en V1 si le projet ne supporte qu’un seul peer.

---

### BUG 4 — Calcul incorrect du champ `size`

Dans Python :

```python
"size": len(payload_dict)
```

`len(payload_dict)` donne le nombre de clés du dictionnaire, pas la taille du paquet en octets.

Exemple :

```python
payload_dict = {"message": "bonjour"}
len(payload_dict) == 1
```

Mais la vraie taille en octets est différente.

Risque :

```text
Le champ size est faux et peut induire en erreur si quelqu’un l’utilise pour valider le paquet.
```

Solution possible :

Calculer `size` après sérialisation :

```python
message_without_size = {...}
donnees = json.dumps(message_without_size, separators=(',', ':')).encode('utf-8')
message["size"] = len(donnees)
```

---

### BUG 5 — Champ `dep` toujours `None`

Dans Python :

```python
"dep": None
```

Risque :

```text
Le récepteur ne connaît pas clairement l’adresse logique de l’émetteur.
```

Solution possible :

- remplir `dep` avec l’IP locale ;
- ou utiliser un identifiant logique de joueur ;
- ou supprimer ce champ si inutile en V1.

---

### BUG 6 — `_sender_ip` dans Python ne représente pas le vrai peer distant

Dans `_listen_loop()` :

```python
msg["_sender_ip"] = addr[0]
```

Mais `addr[0]` est normalement `127.0.0.1`, car Python reçoit le paquet depuis le proxy C local, pas directement depuis le peer distant.

Risque :

```text
Python peut croire que le sender est 127.0.0.1 au lieu de l’IP réelle du peer.
```

Solution possible :

- faire ajouter l’IP réelle par le proxy C dans le JSON ;
- ou ne pas utiliser `_sender_ip` pour identifier le peer réel.

---

### BUG 7 — Pas de vérification des erreurs `sendto()` dans C

Le code C appelle :

```c
sendto(...);
```

sans vérifier le retour.

Risque :

```text
Si l’envoi échoue, le programme ne le signale pas.
```

Solution possible :

```c
int sent = sendto(...);
if (sent < 0) {
    perror("sendto");
}
```

---

### BUG 8 — `sender_len` devrait être réinitialisé dans chaque boucle

Actuellement :

```c
socklen_t sender_len = sizeof(sender_addr);
while (1) {
    int n = recvfrom(..., &sender_len);
}
```

Plus robuste :

```c
while (1) {
    sender_len = sizeof(sender_addr);
    int n = recvfrom(..., &sender_len);
}
```

Risque :

```text
Comportement moins robuste sur certaines plateformes.
```

---

### BUG 9 — Race condition entre threads C

Les deux threads accèdent à des variables globales :

```c
py_client_known
remote_peer_known
py_client_addr
remote_peer_addr
```

sans mutex.

Risque :

```text
Lecture/écriture concurrente non protégée.
```

En petit test, cela peut fonctionner. Mais techniquement, ce n’est pas thread-safe.

Solution possible :

- ajouter un mutex ;
- ou remplacer les threads par un `select()` / `poll()` / event loop.

---

### BUG 10 — Pas de fermeture propre du proxy C

Le proxy C boucle indéfiniment :

```c
while (1) {
    sleep(1);
}
```

Risque :

```text
Pas de fermeture propre des sockets.
Pas de WSACleanup sous Windows.
```

Solution possible :

- gérer Ctrl+C ;
- ajouter une variable `running` ;
- fermer les sockets ;
- appeler `WSACleanup()` sous Windows.

---

### BUG 11 — Pas de validation JSON côté C

Le proxy C forwarde les bytes sans vérifier :

- si c’est du JSON ;
- si le champ `type` existe ;
- si le message est valide ;
- si le message est trop grand ;
- si la destination est autorisée.

Risque :

```text
N’importe quel paquet UDP reçu peut être transmis à Python.
```

Solution possible :

- ajouter un `protocol.c` ;
- parser au minimum `type`, `dest`, `seq` ;
- ignorer les messages invalides.

---

### BUG 12 — N’importe qui peut devenir le peer distant

En mode serveur :

```c
remote_peer_addr = sender_addr;
remote_peer_known = 1;
```

Risque :

```text
Le premier paquet UDP reçu détermine le peer.
Un paquet inconnu peut prendre la place attendue.
```

Solution possible :

- vérifier l’IP autorisée ;
- ajouter un message `HELLO` avec token/session id ;
- demander une configuration explicite du peer.

---

### BUG 13 — Risque de fragmentation UDP

Python autorise jusqu’à :

```python
recvfrom(65535)
```

Mais en pratique, un datagramme supérieur à environ 1400 octets peut être fragmenté.

Risque :

```text
Perte de paquets plus fréquente.
JSON incomplet.
Erreur JSONDecodeError.
```

Solution possible :

- garder les messages sous 1400 octets ;
- compresser ou découper les gros messages ;
- éviter d’envoyer tout l’état du jeu trop souvent.

---

### BUG 14 — Le filtre `seq` est global par type, pas par peer

Dans Python :

```python
self._seq_in[msg_type] = seq
```

Risque avec plusieurs peers :

```text
Si peer A envoie SYNC_UPDATE seq=10,
puis peer B envoie SYNC_UPDATE seq=1,
le message de peer B peut être ignoré.
```

Solution possible :

Stocker par peer et par type :

```python
self._seq_in[(peer_id, msg_type)] = seq
```

Pour V1 avec un seul peer, ce bug est moins grave.

---

### BUG 15 — `seq` local peut entrer en conflit entre machines

Chaque machine commence avec :

```python
self._seq_out = 0
```

Risque :

```text
Deux peers peuvent envoyer les mêmes numéros de séquence.
```

Solution possible :

- associer `seq` à un `sender_id` ;
- filtrer par `(sender_id, type)` ;
- ne pas utiliser `seq` globalement.

---

### BUG 16 — Le proxy C est lancé automatiquement mais le chemin est fragile

Dans Python :

```python
proxy_path = os.path.join("network", "proxy_udp.exe")
if not os.path.exists(proxy_path):
    proxy_path = "proxy_udp.exe"
```

Risque :

```text
Si le script est lancé depuis un autre dossier, le proxy C n’est pas trouvé.
```

Solution possible :

Utiliser le chemin absolu basé sur `__file__` :

```python
base_dir = os.path.dirname(os.path.abspath(__file__))
proxy_path = os.path.join(base_dir, "proxy_udp.exe")
```

---

### BUG 17 — `CREATE_NEW_CONSOLE` est Windows-only mais correctement protégé

Code :

```python
creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
```

Ce point est acceptable. Mais attention : sous Linux/macOS, il faut probablement compiler `proxy_udp` sans `.exe`.

Risque :

```text
Le code cherche seulement proxy_udp.exe.
```

Solution possible :

```python
proxy_name = "proxy_udp.exe" if os.name == "nt" else "proxy_udp"
```

---

### BUG 18 — `disconnect()` termine brutalement le proxy C

Dans Python :

```python
self.proxy_process.terminate()
```

Risque :

```text
Le proxy C n’a pas le temps de fermer proprement ses sockets.
```

Solution possible :

- envoyer un message de shutdown au proxy ;
- attendre avec `wait(timeout=...)` ;
- forcer seulement si nécessaire.

---

### BUG 19 — Pas d’accusé de réception

UDP ne garantit pas :

- la livraison ;
- l’ordre ;
- l’absence de duplication.

Le code actuel filtre certains paquets obsolètes, mais ne confirme jamais la réception.

Risque :

```text
Un message important peut être perdu sans que l’application le sache.
```

Solution possible :

- ajouter des messages `ACK` ;
- retransmettre les messages critiques ;
- réserver UDP brut aux updates fréquentes non critiques.

---

### BUG 20 — Pas de distinction claire entre messages fiables et non fiables

Actuellement, tous les messages passent par le même canal UDP.

Risque :

```text
Un message critique comme JOIN, START_GAME, PLAYER_DEAD peut être perdu.
```

Solution possible :

Créer deux catégories :

```text
Messages non critiques : SYNC_UPDATE, POSITION_UPDATE
Messages critiques : JOIN, LEAVE, ATTACK, GAME_OVER, ACK requis
```

---

## 6. Tests minimum à exécuter

### Test 1 — Python parle au proxy C

Objectif : vérifier IPC localhost.

Étapes :

1. Lancer le proxy C.
2. Lancer Python `NetworkBridge.connect()`.
3. Vérifier que le proxy affiche :

```text
[IPC] Client Python attaché sur le port XXXXX
```

Résultat attendu :

```text
Python est bien attaché au proxy C.
```

---

### Test 2 — Proxy client vers proxy serveur

Machine A, serveur :

```bash
./proxy_udp server 5000 6000 6000
```

Machine B, client :

```bash
./proxy_udp <IP_MACHINE_A> 5000 6000 6000
```

Résultat attendu :

```text
Le client connaît immédiatement le serveur.
Le serveur découvre le client après réception du premier paquet LAN.
```

---

### Test 3 — Python A vers Python B

Objectif : vérifier le chemin complet.

```text
Python A -> Proxy C A -> Proxy C B -> Python B
```

Résultat attendu côté Python B :

```text
get_updates() retourne le message envoyé par Python A.
```

---

### Test 4 — Python B vers Python A

Objectif : vérifier le chemin retour.

```text
Python B -> Proxy C B -> Proxy C A -> Python A
```

Résultat attendu côté Python A :

```text
get_updates() retourne le message envoyé par Python B.
```

---

### Test 5 — Message JSON invalide

Envoyer un paquet non JSON vers le proxy ou vers Python.

Résultat attendu :

```text
NetworkBridge ignore le paquet et ne crash pas.
```

---

### Test 6 — Gros message

Envoyer un payload supérieur à 1400 octets.

Résultat attendu :

```text
NetworkBridge affiche un warning MTU.
Le projet doit décider si ce cas est autorisé ou non.
```

---

### Test 7 — Réordonnancement `SYNC_UPDATE`

Envoyer :

```text
SYNC_UPDATE seq=2
SYNC_UPDATE seq=1
```

Résultat attendu :

```text
seq=2 accepté.
seq=1 ignoré.
```

---

## 7. Critères d’acceptation V1

La version V1 peut être considérée acceptable si :

- [ ] Python peut envoyer un JSON au proxy C.
- [ ] Le proxy C peut forwarder ce JSON au proxy distant.
- [ ] Le proxy distant peut forwarder ce JSON au Python distant.
- [ ] Le chemin inverse fonctionne aussi.
- [ ] Les ports sont configurables.
- [ ] Le programme fonctionne sur au moins deux machines du même LAN.
- [ ] Les erreurs JSON côté Python ne crashent pas le programme.
- [ ] Les messages trop grands sont au moins détectés.
- [ ] Le rôle de l’IPC est clairement expliqué dans le rapport.
- [ ] Les limites de V1 sont documentées.

---

## 8. Limites acceptables pour une V1 simple

Ces limites peuvent être acceptables si elles sont clairement expliquées :

- un seul peer supporté ;
- pas de vraie fiabilité UDP ;
- pas d’ACK ;
- pas de retransmission ;
- pas de routage multi-peer ;
- proxy C qui ne parse pas encore le JSON ;
- découverte simple du peer par premier paquet reçu.

Mais ces limites doivent être indiquées dans le rapport comme limites de V1.

---

## 9. Améliorations prioritaires recommandées

### Priorité 1 — Corriger les problèmes bloquants

- [ ] Corriger le champ `size` côté Python.
- [ ] Ne pas considérer `_sender_ip = 127.0.0.1` comme l’IP réelle du peer.
- [ ] Ajouter des logs d’erreur pour `sendto()` côté C.
- [ ] Réinitialiser `sender_len` à chaque `recvfrom()`.
- [ ] Clarifier le mode serveur/client et le premier paquet `HELLO`.

### Priorité 2 — Rendre le projet plus propre

- [ ] Ajouter un petit protocole : `HELLO`, `DATA`, `ACK`, `ERROR`.
- [ ] Ajouter un `peer_id` ou `sender_id` dans les messages.
- [ ] Stocker les numéros de séquence par peer.
- [ ] Ajouter un fichier `protocol.c` si le C doit comprendre le JSON.
- [ ] Ajouter un fichier `peer_manager.c` si plusieurs peers sont nécessaires.

### Priorité 3 — Préparer une version plus avancée

- [ ] Gestion multi-peer.
- [ ] Heartbeat / timeout.
- [ ] ACK pour messages critiques.
- [ ] Reconnexion propre.
- [ ] Fermeture propre du proxy C.
- [ ] Tests automatisés.

---

## 10. Conclusion

L’implémentation actuelle est cohérente pour une V1 de type relais UDP simple :

```text
Python <-> Proxy C <-> Peer
```

Cependant, elle ne doit pas être présentée comme une architecture réseau complète. Elle doit être décrite comme :

```text
Un proxy UDP minimal qui relaie les datagrammes entre Python local et un peer réseau.
```

Les principaux points faibles actuels sont :

1. un seul peer supporté ;
2. pas de routage basé sur `dest` ;
3. pas de parsing JSON côté C ;
4. pas de fiabilité UDP ;
5. champ `size` incorrect ;
6. `_sender_ip` trompeur côté Python ;
7. découverte de peer fragile ;
8. absence de vraie fermeture propre.

Pour la V1, cela peut suffire si les tests démontrent clairement que le chemin complet fonctionne dans les deux sens.
 
---

## 11. Test local 3 joueurs

Objectif : verifier rapidement que 3 instances online peuvent tourner sur la meme machine.

Commande depuis la racine du projet :

```bash
python network/test_three_players.py
```

Resultat attendu :

```text
[CHECK] player1_host: OK
[CHECK] player2_join: OK
[CHECK] player3_join: OK
[RESULT] OK: les 3 joueurs voient chacun 2 armees distantes.
```

Ce test lance :

- 1 host sur `py_port=5000`, `lan_port=6000` ;
- 1 joiner sur `py_port=5001`, `lan_port=6001`, `remote_port=6000` ;
- 1 joiner sur `py_port=5002`, `lan_port=6002`, `remote_port=6000`.

Pour tester avec l'affichage Pygame, lancer les 3 commandes online manuellement dans 3 terminaux et ajouter `--pygame`.
