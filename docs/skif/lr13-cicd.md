# СКИФ ЛР13 — полный CI/CD до кластера

Задание: https://do.skif.donstu.ru/mod/assign/view.php?id=144770.
В GitHub-методичке ЛР13 — Feature Store; здесь описан CI/CD из СКИФ.

## Цепочка после merge

1. `push` в `main` запускает существующий CI: tests, Ruff, quality gates и Docker build.
2. Только успешный CI для `push main` этого репозитория запускает [Cluster delivery](../../.github/workflows/deploy.yml).
3. Checkout фиксирует именно `workflow_run.head_sha`, прошедший проверки.
4. Образ получает полный SHA-tag и OCI revision, публикуется в GHCR. Для входа используется штатный короткоживущий `GITHUB_TOKEN` с `packages:write`; отдельный пароль владельца не нужен.
5. Runner удаляет локальный tag и вновь скачивает образ из registry, затем загружает его в отдельный Minikube.
6. `deploy_k8s.sh` применяет Deployment/Service/HPA/PDB, ждёт Ready и фиксирует состояние ресурсов.
7. HTTP smoke проверяет health/readiness, настоящий `/predict`, request ID, model version и `source_commit` в метриках.
8. SHA/digest, ресурсы и smoke сохраняются в Actions artifact. Временный runner-кластер удаляется после job.

Это реальный deploy в отдельный учебный Kubernetes на GitHub runner. Он не является постоянно работающим production-кластером; локальный профиль `mozg-mlops` используется для повторной демонстрации.

## Проверка результата

- [PR реализации и evidence](https://github.com/ESKoVV/T26_MLOps/pull/41).
- [Все CI runs](https://github.com/ESKoVV/T26_MLOps/actions/workflows/ci.yml).
- [Cluster delivery runs и artifacts](https://github.com/ESKoVV/T26_MLOps/actions/workflows/deploy.yml).
- [Локальный deployment и smoke](lr10-kubernetes.md).

У успешного delivery должны быть зелёными шаги build/push, download из registry, cluster start, deploy и HTTP smoke. Artifact `team3-delivery-<source SHA>` содержит `registry-digests.json`, `resources.json`, `smoke.json`. Ссылка на конкретный принятый run прикладывается в ответ СКИФ после его завершения.

## Воспроизведение и откат

Рабочий процесс: feature branch → PR → зелёный CI → merge в main → автоматический delivery. Секреты и kubeconfig не включаются в artifacts.

Для локального стенда можно загрузить предыдущий образ в Minikube и повторить `scripts/deploy_k8s.sh` с прежними image/source SHA; `kubectl rollout undo` применим, пока старая image доступна узлу. Для отключения автоматического delivery отключить workflow, не меняя пароли владельца.

[Состав, доли вклада и индивидуальная карточка](../evidence/skif-lr13-ESKoVV.md).

Официальные источники:
- https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images
- https://minikube.sigs.k8s.io/docs/start/
