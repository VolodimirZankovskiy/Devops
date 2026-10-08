# Лабораторна робота №3 — Kubernetes: покроковий runbook

Ці команди виконуються на твоїй машині (не тут) — потрібні встановлені
Docker, minikube і kubectl. Нижче — усі кроки завдання по порядку, із
командами і поясненням, що саме кожна з них показує.

Образи публікуються **локально, без реєстру** — через
`minikube image load`, тому в маніфестах `imagePullPolicy: Never`.

---

## 1. Підготувати образ застосунку (2 версії)

У корені проєкту (де лежать `services/api` і `services/stats` з лаби №1):

```bash
# версія 1.0.0
docker build -t taskmanager-api:1.0.0 ./services/api
docker build -t taskmanager-stats:1.0.0 ./services/stats
```

Зроби малу видиму зміну для версії 1.1.0 — наприклад, онови
`description` у Swagger-шаблоні `services/api/app.py` з
`"CRUD API для управління задачами (Лаб. робота №1, DevOps)."` на щось
із позначкою "v1.1" — це дасть видиму різницю під час rolling update:

```bash
docker build -t taskmanager-api:1.1.0 ./services/api
docker build -t taskmanager-stats:1.1.0 ./services/stats
```

Перевір, що обидва теги є:
```bash
docker images | findstr taskmanager
```

---

## 2. Розгорнути локальний кластер

```bash
minikube start --driver=docker
kubectl get nodes                       # стан вузла
kubectl get pods -n kube-system         # системні поди
minikube addons enable metrics-server
minikube addons enable ingress
minikube addons list                    # перевірити, що обидва enabled
```

Завантаж обидві версії обох образів у кластер (без push у реєстр):

```bash
minikube image load taskmanager-api:1.0.0
minikube image load taskmanager-api:1.1.0
minikube image load taskmanager-stats:1.0.0
minikube image load taskmanager-stats:1.1.0
minikube image ls | Select-String taskmanager
```

---

## 3. Namespace

Вже описаний у `k8s/00-namespace.yaml` (`taskmanager`). Якщо викладач
просить назвати його твоїм прізвищем — заміни `name:` у цьому файлі
одним рядком перед деплоєм.

---

## 4. Маніфести — що лежить у `k8s/`

| Файл | Об'єкт | Що демонструє |
|---|---|---|
| `00-namespace.yaml` | Namespace | ізоляція проєкту |
| `01-configmap.yaml` | ConfigMap | `MONGO_DB`, `LOG_LEVEL` — 2 нечутливі параметри |
| `02-secret.yaml` | Secret | облікові дані Mongo + готовий `MONGO_URI` |
| `03-mongo-pvc.yaml` | PVC | постійне сховище для БД |
| `04-mongo-deployment.yaml` | Deployment | Mongo, 1 репліка, читає креденшли з Secret |
| `05-mongo-service.yaml` | Service (ClusterIP) | доступ до Mongo всередині кластера |
| `06-api-deployment.yaml` | Deployment | api, **2 репліки**, requests/limits, liveness/readiness на `/health` |
| `07-api-service.yaml` | Service (NodePort) | доступ до api з хоста (порт 30500) |
| `08-stats-deployment.yaml` | Deployment | stats, 2 репліки, ті самі проби |
| `09-stats-service.yaml` | Service (ClusterIP) | доступ до stats всередині кластера |
| `10-ingress.yaml` | Ingress | маршрутизація `/api/...` → сервіс api через nginx |

---

## 5. Розгорнути застосунок

Одна команда з каталогу:

```bash
kubectl apply -f k8s/
```

Перелік створених об'єктів:

```bash
kubectl get pods,deploy,rs,svc -n taskmanager
kubectl get ingress -n taskmanager
```

Зачекай, поки всі поди стануть `Running`/`READY 2/2`:

```bash
kubectl get pods -n taskmanager -w
```

### Відкрити застосунок у браузері

Через NodePort:
```bash
minikube service api -n taskmanager --url
```
Відкрий виведену адресу + `/apidocs/` у браузері.

Або через Ingress (додай у `/etc/hosts` або
`C:\Windows\System32\drivers\etc\hosts` рядок
`<minikube ip> taskmanager.local`, IP бери з `minikube ip`):
```bash
minikube ip
curl http://taskmanager.local/api/health
```

### Показати, що ConfigMap і Secret реально в контейнері

```bash
kubectl exec -n taskmanager-zankovskiy deploy/api -- env | Select-String -Pattern "MONGO_DB|LOG_LEVEL|MONGO_URI"
```
Побачиш живі значення з ConfigMap (`MONGO_DB`, `LOG_LEVEL`) і зі
Secret (`MONGO_URI`) — саме це і є доказом для пункту 5d.

---

## 6. Керування життєвим циклом

### a) Самовідновлення

```bash
kubectl get pods -n taskmanager -l app=api
kubectl delete pod <ім'я-одного-з-подів-api> -n taskmanager
kubectl get pods -n taskmanager -l app=api -w
```
Побачиш, що видалений под зникає, а ReplicaSet одразу створює новий —
кількість реплік знову стає 2.

### b) Масштабування

```bash
kubectl scale deployment api -n taskmanager --replicas=4
kubectl get pods -n taskmanager -l app=api
```
Щоб показати розподіл трафіку між репліками, зроби кілька запитів і
подивись, який под відповідає (hostname можна додати в лог gunicorn,
або просто показати `kubectl get endpoints api -n taskmanager` — буде
видно 4 IP-адреси подів за одним Service).

Поверни назад:
```bash
kubectl scale deployment api -n taskmanager --replicas=2
```

### c) Оновлення (rolling update)

В окремому терміналі запусти безперервні запити, щоб довести, що
застосунок не падає під час оновлення (пункт 6e):
```bash
while true; do curl -s -o /dev/null -w "%{http_code}\n" http://$(minikube ip):30500/health; sleep 1; done
```

В іншому терміналі:
```bash
kubectl set image deployment/api api=taskmanager-api:1.1.0 -n taskmanager
kubectl rollout status deployment/api -n taskmanager
```
Поки це триває — дивись на перший термінал: коди відповіді мають
лишатись `200` (можливо, з поодинокими короткими збоями, якщо
readinessProbe налаштована туго — це нормально показати і пояснити).

### d) Історія оновлень і відкат

```bash
kubectl rollout history deployment/api -n taskmanager
kubectl rollout undo deployment/api -n taskmanager
kubectl rollout status deployment/api -n taskmanager
```
Поверне попередню версію образу (1.0.0).

---

## 7. Діагностика

### a) Навмисна помилка — неіснуючий тег

```bash
kubectl set image deployment/api api=taskmanager-api:9.9.9-not-exist -n taskmanager
kubectl get pods -n taskmanager -l app=api
```
Побачиш `ErrImagePull` → `ImagePullBackOff`.

### b) Причина — опис пода і події

```bash
kubectl describe pod <ім'я-пода-зі-статусом-ImagePullBackOff> -n taskmanager
```
У розділі `Events` внизу буде явно видно причину
(`Failed to pull image "taskmanager-api:9.9.9-not-exist"` і т.д.).

### c) Логи та вхід у контейнер

```bash
# логи робочого (не збійного) пода
kubectl logs deploy/api -n taskmanager

# інтерактивний вхід у контейнер
kubectl exec -it deploy/api -n taskmanager -- /bin/sh
```

### d) Виправлення

```bash
kubectl set image deployment/api api=taskmanager-api:1.1.0 -n taskmanager
kubectl rollout status deployment/api -n taskmanager
kubectl get pods -n taskmanager -l app=api
```
Усі поди знову `Running`/`2/2`.

---

## 8. Оформлення результатів

- Закомітити `k8s/` у репозиторій разом з рештою проєкту.
- У головному `README.md` проєкту додати розділ "Розгортання в
  Kubernetes" з коротким описом порядку (`kubectl apply -f k8s/`) і
  переліком параметрів із ConfigMap (`MONGO_DB`, `LOG_LEVEL`) та
  Secret (`MONGO_ROOT_USERNAME`, `MONGO_ROOT_PASSWORD`, `MONGO_URI`).
- Для звіту збережи вивід команд із пунктів 5–7 (`kubectl get`,
  `rollout status`, `describe pod` з подіями) — скріншотами або
  текстом у окремий файл, наприклад `k8s/REPORT.md`.
