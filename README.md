# Подготовка виртуальной машины

## Склонируйте репозиторий

```bash
git clone https://github.com/yandex-praktikum/mle-project-sprint-4-v001.git
cd mle-project-sprint-4-v001
```

## Активируйте виртуальное окружение

```bash
python3 -m venv env_recsys_start
source env_recsys_start/bin/activate
pip install -r requirements.txt
```

## Скачайте исходные данные

Для работы с ноутбуком и офлайн-рекомендациями нужны 3 файла:
- [tracks.parquet](https://storage.yandexcloud.net/mle-data/ym/tracks.parquet)
- [catalog_names.parquet](https://storage.yandexcloud.net/mle-data/ym/catalog_names.parquet)
- [interactions.parquet](https://storage.yandexcloud.net/mle-data/ym/interactions.parquet)

Скачивание:

```bash
wget https://storage.yandexcloud.net/mle-data/ym/tracks.parquet
wget https://storage.yandexcloud.net/mle-data/ym/catalog_names.parquet
wget https://storage.yandexcloud.net/mle-data/ym/interactions.parquet
```

## Запуск Jupyter Lab

```bash
jupyter lab --ip=0.0.0.0 --no-browser
```

# Расчёт рекомендаций (часть 1)

Выполнение части 1 находится в ноутбуке:
- `recommendations.ipynb`

После выполнения ноутбука в проекте должны быть сформированы:
- `items.parquet`
- `events.parquet`
- `top_popular.parquet`
- `personal_als.parquet`
- `similar.parquet`
- `recommendations.parquet`

# Сервис рекомендаций (часть 2)

Файл сервиса:
- `recommendations_service.py`

## Запуск сервиса

```bash
uvicorn recommendations_service:app --reload --port 8000
```

Проверка:
- [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## API сервиса

- `POST /event` — добавить событие прослушивания в онлайн-историю пользователя.
  - body:
    ```json
    {
      "user_id": 123,
      "track_id": 456
    }
    ```
- `GET /recommendations?user_id=<id>&k=<n>` — получить `k` рекомендаций для пользователя.

## Стратегия смешивания онлайн- и офлайн-рекомендаций

Сервис использует 3 сценария:
1. Если у пользователя нет персональных офлайн-рекомендаций, возвращается `top_popular`.
2. Если персональные офлайн-рекомендации есть, но онлайн-истории нет, возвращаются офлайн-рекомендации (`recommendations.parquet`, fallback — `personal_als.parquet`).
3. Если есть и персональные офлайн-рекомендации, и онлайн-история, офлайн-рекомендации смешиваются с онлайн i2i-кандидатами из `similar.parquet` по последним прослушиваниям пользователя.

Дополнительно:
- треки из онлайн-истории пользователя исключаются из выдачи;
- при нехватке кандидатов результат дополняется популярными треками.

# Тестирование сервиса

Файл теста:
- `test_service.py`

Тест покрывает 3 обязательных кейса:
1. Пользователь без персональных рекомендаций.
2. Пользователь с персональными рекомендациями, но без онлайн-истории.
3. Пользователь с персональными рекомендациями и онлайн-историей.

Запуск теста:

```bash
python test_service.py
```

Запуск теста с сохранением лога:

```bash
python test_service.py | tee test_service.log
```

Результат работы теста сохраняется в:
- `test_service.log`
