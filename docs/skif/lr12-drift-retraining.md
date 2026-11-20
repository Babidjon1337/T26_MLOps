# СКИФ ЛР12 — drift и автоматическая реакция

Задание: https://do.skif.donstu.ru/mod/assign/view.php?id=144769.
Отчёт дополняет [исследование drift на BTS](../monitoring/lr12.md) реальным автоматическим retraining.

## Выполненный сценарий

1. PSI сравнивает reference и текущее окно для `DepHour` и `IsWeekend`.
2. При отсутствии drift обучение не вызывается.
3. При `alert` отдельная лабораторная policy автоматически запускает `train_model` на явно указанном размеченном training snapshot.
4. Создаются bundle, SHA-256, validation metrics и manifest кандидата; MLflow регистрирует candidate v1 в отдельном `team3-skif-drift-candidates`.
5. Повтор с теми же входами переиспользует bundle с проверкой его SHA-256 и не создаёт новую Registry version.
6. Автоматической замены serving/champion нет. Обычная monitoring policy с human review сохранена; новая policy относится к изолированному учебному кандидату.

Обучение не использует неразмеченные production features как целевую переменную. Допуск и временные ограничения зрелых меток в прежнем мониторинге не ослаблены.

## Реальные результаты

- Reference = current: PSI обоих признаков 0, `action=no_retraining`.
- Смещённое окно: `drift.status=alert`, `action=candidate_trained` и MLflow candidate version 1.
- Повтор: `action=candidate_reused`, та же версия Registry 1.
- Тесты также подтверждают policy-off и отказ при неразмеченном training snapshot.

24-строчный sample используется для воспроизводимой проверки механики trigger/register, с явно учебным gate ROC AUC 0.0. Его качество не выдаётся за качество BTS-модели. Реальные BTS-метрики и delayed-label coverage остаются в исходных отчётах ЛР12.

## Запуск и расписание

```bash
python -m pip install -c requirements.lock -e '.[tracking]'
bash scripts/run_drift_cycle.sh
```

Отчёт `reports/drift-retraining/drift_report.json` создаётся автоматически. Для контрольного запуска без drift:

```bash
REFERENCE_DATA=data/monitoring/reference.csv \
CURRENT_DATA=data/monitoring/reference.csv \
DRIFT_OUTPUT_DIR=reports/drift-baseline bash scripts/run_drift_cycle.sh
```

Workflow [Drift candidate training](../../.github/workflows/drift-retraining.yml) работает ежедневно в 03:17 UTC и по `workflow_dispatch`. Учебный schedule проверяет versioned snapshots из Git, а не подключённый внешний production stream. На GitHub runner каждый запуск имеет изолированный candidate store, bundle и отчёты сохраняются в Actions artifacts на 30 дней; локально повтор использует постоянный каталог моделей.

## Evidence

- [Baseline без drift](../../reports/drift-retraining/baseline.json).
- [Автоматический trigger](../../reports/drift-retraining/triggered.json).
- [MLflow registration](../../reports/drift-retraining/registry-candidate.json).
- [Повтор без нового обучения/версии](../../reports/drift-retraining/idempotence.json).
- [Тесты](../../tests/test_drift_retrain.py).

Откат: отключить schedule workflow; serving model не изменялась. Удаление локального `models/drift-candidates/` затрагивает только новые учебные кандидаты.

[Состав, доли вклада и индивидуальная карточка](../evidence/skif-lr12-ESKoVV.md).
