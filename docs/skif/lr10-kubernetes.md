# СКИФ ЛР10 — деплой в Kubernetes (Minikube)

Задание: https://do.skif.donstu.ru/mod/assign/view.php?id=144568.
В GitHub-методичке ЛР10 обозначает MLflow Registry; данный отчёт относится именно к СКИФ ЛР10.

## Стенд и результат

- Minikube 1.39.0, Kubernetes 1.37.0, Docker 29.9.2, отдельный профиль `mozg-mlops`.
- Namespace `mlops-team3`, Deployment `flight-delay-api`, NodePort Service, HPA CPU 60%, 2–6 replicas, PDB minAvailable=1.
- `readOnlyRootFilesystem`, non-root UID 10001, probes и отдельный writable `/tmp`.
- В маленьком учебном узле запросы CPU снижены до 100m скриптом deployment; production baseline 500m сохранён в YAML.
- `/healthz`, `/readyz`, `/predict` и `/metrics` прошли HTTP smoke; модель контейнера — учебный baseline `0.2.0`.
- Ручное масштабирование: 3/3 Ready. Для фиксации снимка временно использован HPA floor=3, затем возвращён к 2.
- Ограниченная нагрузка: 6 workers, 90 секунд, 20 830 успешных запросов, 0 ошибок; HPA сам увеличил replicas до 4.
- Удаление одного pod: Deployment создал замену и восстановил Ready за 4,476 с.

Полный исходный commit реализации: `4683724c6c470f6f81ae47527144e69a5ab6ab94`.

## Воспроизведение

Укажите отдельный локальный `KUBECONFIG`; ключи не включаются в Git.

```bash
minikube start -p mozg-mlops --driver=docker --cpus=2 --memory=3072 --kubernetes-version=v1.37.0
commit=$(git rev-parse HEAD)
image="mlops-flight-delay:$commit"
docker build --label "org.opencontainers.image.revision=$commit" -t "$image" .
minikube -p mozg-mlops image load "$image"
KUBE_CONTEXT=mozg-mlops bash scripts/deploy_k8s.sh "$image" "$commit"
minikube -p mozg-mlops -n mlops-team3 service flight-delay-api --url
kubectl --context mozg-mlops -n mlops-team3 scale deployment flight-delay-api --replicas=3
kubectl --context mozg-mlops -n mlops-team3 get pods,hpa
```

Если сеть узла пытается получить `kindnetd` через недоступный IPv6, образ можно загрузить через Docker хоста:

```bash
docker pull kindest/kindnetd:v20260820-69b56db7
minikube -p mozg-mlops image load kindest/kindnetd:v20260820-69b56db7
kubectl --context mozg-mlops -n kube-system rollout restart daemonset/kindnet
minikube -p mozg-mlops addons enable metrics-server
```

Для HPA нужны готовый metrics-server и продолжительная ограниченная нагрузка; один ручной `scale` не доказывает работу autoscaling.

## Evidence

- [HTTP smoke](../../reports/kubernetes/skif-lr10-smoke.json).
- [Три реплики](../../reports/kubernetes/skif-lr10-scale-three.json).
- [HPA во время нагрузки](../../reports/kubernetes/skif-lr10-hpa.json).
- [Состояние после нагрузки](../../reports/kubernetes/skif-lr10-after-load.json).
- [Восстановление pod](../../reports/kubernetes/skif-lr10-recovery.json).

Откат: `minikube stop -p mozg-mlops`; для полного удаления только учебного стенда — `minikube delete -p mozg-mlops`.
Локальный адрес NodePort не публикуется в интернет и меняется при пересоздании профиля.

[Состав, доли вклада и индивидуальная карточка](../evidence/skif-lr10-ESKoVV.md).
