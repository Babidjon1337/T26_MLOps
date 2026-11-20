# СКИФ ЛР11 — Prometheus, Grafana и метрики приложения

Задание: https://do.skif.donstu.ru/mod/assign/view.php?id=144768.
Тема совпадает с ЛР11 актуальной GitHub-методички.

## Реальный стенд

Отдельный Compose-проект `mozg-lr11`: app, Prometheus 3.15.0, Grafana OSS 13.2.6.
Порты привязаны к loopback: API 18880, Prometheus 19090, Grafana 13000.
В app смонтирован bundle LR10 A, действующий MLflow champion version 1.
`model_info`, `/predict`, Registry и SHA-256 bundle проверены и сохранены.

Метрики: bounded route/status request counter, latency histogram, prediction outcomes,
новый `prediction_probability` histogram и model identity. Ни request ID, ни входные
признаки не добавлены в metric labels.

Provisioned dashboard `Flight Delay Service` содержит 7 панелей, включая среднюю
вероятность задержки. Верифицирован не только JSON панели, но и реальный запрос
через Grafana к Prometheus, вернувший frame `up=1`.

## Измерения

200 запросов: 180 ответов 200, 20 ожидаемых 422, ни одного 5xx.
Client latency: p95 6,42 мс, max 19,22 мс; это конечный локальный sample,
а не доказательство долгосрочного production SLO.

PromQL сохранены вместе с временем/окном/результатами:

```promql
sum(rate(http_requests_total[5m]))
histogram_quantile(0.95, sum by(le)(rate(http_request_duration_seconds_bucket[5m])))
sum(rate(prediction_probability_sum[5m]))
  / clamp_min(sum(rate(prediction_probability_count[5m])), 0.000001)
```

## Контролируемый инцидент

Остановлен только `app` нашего Compose-проекта. `FlightDelayServiceDown` прошёл
pending → firing. После запуска app target стал UP, alert разрешился.

UTC: остановка 12:31:09, restart 12:32:19, resolved 12:32:32 (2026-11-20).
Порог `for: 1m` не сокращался. Prometheus/Grafana продолжали работать.
Выполнены шаги [runbook](../runbooks/flight-delay-api.md).

## Исправленные дефекты исходной конфигурации

- `grafana/grafana-oss:13.2.4` не существует: официальный OSS repository после12.4
  переехал на `grafana/grafana`; закреплён доступный 13.2.6.
- Installer Grafana 13 требовал writable `/tmp`; добавлен ограниченный tmpfs.
- Обновление bundled plugins конфликтовало с read-only image и оставляло
  Prometheus plugin незарегистрированным. `GF_PLUGINS_PREINSTALL_AUTO_UPDATE=false`
  оставляет подписанную bundled-версию из закреплённого образа.
- После restart histogram series создаётся первым успешным `/predict`;
  отсутствие этой ленивой series до запросов не означает неисправность scrape.

## Повторный запуск

Случайный локальный пароль Grafana хранится только в отдельном файле параметров
вне Git (600). Для стандартных портов и встроенного model bundle:

```bash
docker compose --env-file /path/to/private-lab.env -p mozg-lr11 up --build -d
python scripts/observability_load.py --base-url http://127.0.0.1:8080 \
  --requests 200 --invalid-every 10 --student-id ESKoVV-lr11 \
  --output reports/observability/repeated-load.json
```

Для exact champion1 требуется смонтировать локальный `models/lr10-a.joblib` в
`/app/models/model.joblib:ro` и задать model name/version из Registry.
Без этого контейнер использует свой sample baseline, что необходимо явно обозначить.

## Evidence

- [Локальная нагрузка](../../reports/observability/skif-lr11-load.json).
- [Prometheus targets](../../reports/observability/skif-lr11-targets.json).
- [PromQL с результатами](../../reports/observability/skif-lr11-promql.json).
- [Grafana dashboard и настоящий datasource query](../../reports/observability/skif-lr11-grafana.json).
- [Полный lifecycle алерта](../../reports/observability/skif-lr11-alert-lifecycle.json).
- [Связь с bundle](../../reports/observability/skif-lr11-model-link.json).
- [Наблюдаемая Registry identity](../../reports/observability/skif-lr11-registry-identity.json).

Откат: остановить только `docker compose ... -p mozg-lr11 down`. Не удалять чужие
volumes и не публиковать Grafana с локальным паролем в интернет.

[Карточка и доли команды](../evidence/skif-lr11-ESKoVV.md).

Официальный источник по OSS image:
https://grafana.com/docs/grafana/latest/setup-grafana/installation/docker/
