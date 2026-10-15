# Helm-чарт Task Manager (лабораторна робота №4)

Чарт описує той самий застосунок, що й `k8s/` з лабораторної №3: сервіси
`api` і `stats` та базу MongoDB. Набір об'єктів у кластері такий самий:
ConfigMap, Secret, PVC, 3 Deployment, 3 Service, Ingress. Namespace в чарті
не описується: його задає `helm install -n <ns> --create-namespace`.

## version і appVersion

| Поле | Значення | Що означає для цього проєкту |
|---|---|---|
| `version` | `0.1.0` | Версія **самого чарта**: шаблонів, `values.yaml`, структури. Збільшується, коли змінюється чарт (новий прапорець, новий шаблон), навіть якщо код застосунку не змінився. |
| `appVersion` | `1.0.0` | Версія **застосунку**, який пакує чарт (теги образів `taskmanager-api` і `taskmanager-stats`). Збільшується, коли виходить нова версія коду. |

Приклад: якщо я додав у чарт новий прапорець для Ingress, змінюється `version`,
а `appVersion` лишається. Якщо вийшов образ `1.1.0` без змін у шаблонах,
змінюється `appVersion`, а `version` можна підняти лише на patch.

## Параметри values.yaml

| Параметр | За замовчуванням | Опис |
|---|---|---|
| `nameOverride`, `fullnameOverride` | `""` | Перевизначення імені чарта / повного імені об'єктів |
| `api.replicaCount` | `1` | Кількість реплік api |
| `api.image.repository` / `tag` / `pullPolicy` | `taskmanager-api` / `1.0.0` / `IfNotPresent` | Образ api |
| `api.containerPort` | `5000` | Порт контейнера api |
| `api.service.type` / `port` / `nodePort` | `NodePort` / `5000` / `null` | Service api |
| `api.resources` | requests 50m/96Mi, limits 200m/256Mi | Ресурси api |
| `stats.*` | ті самі ключі, порт `5001`, тип `ClusterIP` | Налаштування stats |
| `mongo.replicaCount` | `1` | Кількість реплік MongoDB |
| `mongo.image.repository` / `tag` | `mongo` / `7` | Образ MongoDB |
| `mongo.service.port` | `27017` | Порт Service MongoDB |
| `mongo.persistence.enabled` | `true` | Чи створювати PVC (інакше `emptyDir`) |
| `mongo.persistence.size` / `storageClass` | `1Gi` / `""` | Розмір і клас сховища |
| `mongo.resources` | requests 100m/256Mi, limits 500m/512Mi | Ресурси MongoDB |
| `ingress.enabled` | `false` | Чи створювати Ingress |
| `ingress.className` / `host` | `nginx` / `taskmanager.local` | Параметри Ingress |
| `config.mongoDb` | `taskmanager` | Назва бази (ConfigMap) |
| `config.logLevel` | `info` | Рівень логування (ConfigMap) |
| `secret.mongoRootUsername` | `taskmanager_admin` | Користувач MongoDB (Secret) |
| `secret.mongoRootPassword` | `dev-only-password` | Пароль MongoDB (Secret). Навчальний пароль лише для dev. Для prod порожній, передається через `--set` |

Відмінності середовищ:

| | values-dev.yaml | values-prod.yaml |
|---|---|---|
| Репліки api / stats | 1 / 1 | 3 / 2 |
| Тег образів | 1.0.0 | 1.1.0 |
| Ресурси api, stats | requests 50m/96Mi | requests 100m/128Mi, limits 300m/384Mi |
| Ingress | вимкнений | увімкнений |
| Розмір PVC | 1Gi | 2Gi |

## Команди встановлення

Спільне для PowerShell:

```powershell
$ns = "taskmanager-zankovskiy"
```

dev:
```powershell
helm install taskmanager ./chart -n $ns --create-namespace -f chart/values-dev.yaml
```

prod (пароль обов'язково передається ззовні):
```powershell
helm install taskmanager-prod ./chart -n $ns --create-namespace -f chart/values-prod.yaml --set secret.mongoRootPassword=ТВІЙ_ПАРОЛЬ
```

Образи мають бути завантажені в minikube заздалегідь (`minikube image load`,
теги `1.0.0` і `1.1.0` для api і stats), реєстр не використовується.

---

# Покроковий runbook

## 1. Підготовка середовища

```powershell
winget install Helm.Helm
```
Закрий і знову відкрий PowerShell, далі:
```powershell
helm version
minikube start --driver=docker
kubectl get nodes
$ns = "taskmanager-zankovskiy"
kubectl get pods -n $ns
```
(Останнє показує, що розгортання з лаби №3 працює.)

Видали реліз з лабораторної №3, щоб не було конфліктів:
```powershell
kubectl delete -f k8s/
kubectl get namespace $ns
```
Дочекайся `NotFound` (namespace видаляється разом з об'єктами лаби №3).

## 2–5. Структура чарта

```powershell
Get-ChildItem chart -Recurse | Select-Object FullName
```
Що де лежить:

* `Chart.yaml`: метадані (name, description, version, appVersion)
* `values.yaml`: значення за замовчуванням (dev)
* `templates/_helpers.tpl`: іменовані шаблони `taskmanager.fullname` (повне ім'я з імені релізу) і `taskmanager.labels` / `taskmanager.selectorLabels` (набір міток)
* `templates/*.yaml`: по одному файлу на об'єкт, усі імена й мітки через `include`
* `templates/NOTES.txt`: підказка, яку Helm друкує після встановлення
* `templates/secret.yaml`: значення беруться з `.Values.secret.*`, у шаблоні паролів немає

## 6. Два середовища

Різниця без встановлення в кластер:
```powershell
helm template demo ./chart -f chart/values-dev.yaml | Out-File dev.yaml -Encoding utf8
helm template demo ./chart -f chart/values-prod.yaml --set secret.mongoRootPassword=x | Out-File prod.yaml -Encoding utf8
git diff --no-index dev.yaml prod.yaml
```

Пріоритет значень (від найнижчого до найвищого):

1. `values.yaml` чарта (значення за замовчуванням)
2. файли `-f` (якщо їх кілька, пізніший перекриває ранній)
3. прапорці `--set` (найвищий пріоритет)

Демонстрація:
```powershell
helm template demo ./chart | Select-String "replicas:"
helm template demo ./chart -f chart/values-prod.yaml --set secret.mongoRootPassword=x | Select-String "replicas:"
helm template demo ./chart -f chart/values-prod.yaml --set secret.mongoRootPassword=x --set api.replicaCount=5 | Select-String "replicas:"
```
У першому випадку реплік по одній, у другому 3 / 2 з prod-файлу, у третьому
api стає 5, бо `--set` сильніший за `-f`.

## 7. Перевірка і встановлення

```powershell
helm lint ./chart
helm lint ./chart -f chart/values-prod.yaml --set secret.mongoRootPassword=x
helm template taskmanager ./chart -f chart/values-dev.yaml | Select-String "^kind:"
Get-ChildItem k8s
```
Порівняй список `kind:` з файлами `k8s/` (лаба №3): ті самі об'єкти, окрім Namespace.

Встановлення:
```powershell
helm install taskmanager ./chart -n $ns --create-namespace -f chart/values-dev.yaml
helm list -n $ns
helm status taskmanager -n $ns
helm get values taskmanager -n $ns
helm get values taskmanager -n $ns --all
kubectl get pods -n $ns
```

Де Helm зберігає стан релізу: у Secret типу `helm.sh/release.v1` у namespace релізу
(по одному Secret на ревізію):
```powershell
kubectl get secrets -n $ns
kubectl get secret sh.helm.release.v1.taskmanager.v1 -n $ns -o jsonpath='{.type}'
```

## 8. Життєвий цикл релізу

**Увага про пароль.** MongoDB читає початковий пароль лише при першому старті
на порожньому томі. Тому при оновленні існуючого релізу dev на prod-значення
пароль має **лишитися тим самим**, інакше api не зможе автентифікуватися.

a) оновлення тега через `--set` (ревізія 2):
```powershell
helm upgrade taskmanager ./chart -n $ns -f chart/values-dev.yaml --set api.image.tag=1.1.0
```
У другому вікні під час оновлення видно под pre-upgrade хука:
```powershell
kubectl get pods -n $ns -w
```

b) оновлення з файлом іншого середовища (ревізія 3):
```powershell
helm upgrade taskmanager ./chart -n $ns -f chart/values-prod.yaml --set secret.mongoRootPassword=dev-only-password
kubectl get pods -n $ns
```

c) історія і що змінювалося:
```powershell
helm history taskmanager -n $ns
helm get manifest taskmanager -n $ns --revision 1 | Out-File rev1.yaml -Encoding utf8
helm get manifest taskmanager -n $ns --revision 2 | Out-File rev2.yaml -Encoding utf8
git diff --no-index rev1.yaml rev2.yaml
```
Ревізія 1 це встановлення, 2 змінює тег образу api на 1.1.0, 3 переводить
на prod-значення (реплік більше, ресурси, Ingress).

d) відкат:
```powershell
helm rollback taskmanager 2 -n $ns
helm history taskmanager -n $ns
```
З'явиться ревізія 4 з описом `Rollback to 2`: відкат не стирає історію,
а створює нову ревізію зі старим вмістом.

e) видалення і перевірка, що нічого не лишилось:
```powershell
helm uninstall taskmanager -n $ns
kubectl get all,pvc,cm,secret,ingress -n $ns
```
Залишається лише службовий `kube-root-ca.crt`, його створює сам Kubernetes.

## 9. Завдання на вибір: хук і тест релізу

* `templates/pre-upgrade-job.yaml`: Job з анотацією `helm.sh/hook: pre-upgrade`. Перед кожним `helm upgrade` він перевіряє, що MongoDB відповідає на ping. Якщо ні, оновлення зупиняється.
* `templates/tests/test-connection.yaml`: Pod з анотацією `helm.sh/hook: test`, перевіряє `/health` в api і stats.

```powershell
helm install taskmanager ./chart -n $ns --create-namespace -f chart/values-dev.yaml
kubectl get pods -n $ns
helm test taskmanager -n $ns --logs
```
Очікується `Phase: Succeeded` і рядок `OK: api and stats are healthy`.
Хук запускається під час `helm upgrade` (див. п. 8a).

## 10. Git

```powershell
git checkout main
git pull
git checkout -b lab4-helm
git add chart/
git commit -m "Lab 4: Helm chart for taskmanager"
git push -u origin lab4-helm
```
Далі створи Pull Request у `main`.
