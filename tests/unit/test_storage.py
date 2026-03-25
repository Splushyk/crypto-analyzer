import json

from freezegun import freeze_time

from src.storage import JsonStorage


@freeze_time("2026-03-16 10:00:00")
def test_json_storage_content_logic(sample_coin, sample_results, mocker):
    """Проверка содержимого JSON в классе JsonStorage."""
    # Создаем мок для файла
    m = mocker.patch("builtins.open", mocker.mock_open())

    storage = JsonStorage("test.json")
    storage.save([sample_coin], sample_results)

    # Собираем всё, что было записано в файл
    handle = m()
    written_data = "".join(call.args[0] for call in handle.write.call_args_list)
    data = json.loads(written_data)

    assert data["total_market_cap_usd"] == sample_results["total_market_cap"]
    assert data["generated_at"] == "2026-03-16 10-00-00"
    assert data["top_gainers"][0]["symbol"] == sample_coin.symbol


def test_json_storage_custom_filenames(sample_coin, sample_results, mocker):
    """Проверка, что JsonStorage открывает правильный файл."""
    m = mocker.patch("builtins.open", mocker.mock_open())

    # Проверяем инициализацию с кастомным именем
    JsonStorage("custom_report.json").save([sample_coin], sample_results)

    # Проверяем, что open был вызван именно с этим именем
    m.assert_any_call("custom_report.json", "w", encoding="utf-8")
