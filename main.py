import io
import json
from pathlib import Path

import boto3
import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import requests


BUCKET_NAME = "nbu-currency-lab2-2026"
REGION = "us-east-1"

API_URL = "https://bank.gov.ua/NBU_Exchange/exchange_site"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CHARTS_DIR = BASE_DIR / "charts"

JSON_FILE = DATA_DIR / "exchange_rates_2022.json"
CSV_FILE = DATA_DIR / "exchange_rates_2022.csv"
CHART_FILE = CHARTS_DIR / "exchange_rates_2022.png"


def fetch_exchange_rates():
    data = {}

    for currency in ["USD", "EUR"]:
        params = {
            "start": "20220101",
            "end": "20221231",
            "valcode": currency,
            "sort": "exchangedate",
            "order": "asc",
            "json": ""
        }

        response = requests.get(
            API_URL,
            params=params,
            timeout=60
        )
        response.raise_for_status()

        data[currency] = response.json()

        print(
            f"{currency}: отримано "
            f"{len(data[currency])} записів"
        )

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("JSON збережено:", JSON_FILE)

    return data


def convert_to_csv(data):
    records = []

    for currency, entries in data.items():
        for entry in entries:
            records.append({
                "date": entry["exchangedate"],
                "currency": currency,
                "rate": entry["rate_per_unit"]
            })

    df = pd.DataFrame(records)

    if df.empty:
        raise ValueError("API НБУ не повернув даних.")

    df["date"] = pd.to_datetime(
        df["date"],
        format="%d.%m.%Y"
    )

    df = df.pivot(
        index="date",
        columns="currency",
        values="rate"
    ).sort_index()

    df = df[["USD", "EUR"]]

    df.to_csv(CSV_FILE)

    print("CSV збережено:", CSV_FILE)
    print("Кількість днів:", len(df))
    print(df.head())


def upload_csv(s3):
    s3.upload_file(
        str(CSV_FILE),
        BUCKET_NAME,
        "data/exchange_rates_2022.csv"
    )

    response = s3.head_object(
        Bucket=BUCKET_NAME,
        Key="data/exchange_rates_2022.csv"
    )

    print("CSV завантажено в S3.")
    print("Розмір:", response["ContentLength"], "байтів")


def read_csv_from_s3(s3):
    response = s3.get_object(
        Bucket=BUCKET_NAME,
        Key="data/exchange_rates_2022.csv"
    )

    df = pd.read_csv(
        io.BytesIO(response["Body"].read()),
        parse_dates=["date"]
    )

    df = df.sort_values("date")

    print("CSV прочитано з S3.")
    print(df.head())

    return df


def create_chart(df):
    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(
        df["date"],
        df["USD"],
        label="USD"
    )

    ax.plot(
        df["date"],
        df["EUR"],
        label="EUR"
    )

    ax.set_title("USD and EUR Exchange Rates in 2022")
    ax.set_xlabel("Date")
    ax.set_ylabel("UAH per Currency Unit")

    ax.legend()
    ax.grid(True, alpha=0.3)

    fig.autofmt_xdate()
    fig.tight_layout()

    fig.savefig(
        CHART_FILE,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close(fig)

    print("Графік збережено:", CHART_FILE)


def upload_chart(s3):
    s3.upload_file(
        str(CHART_FILE),
        BUCKET_NAME,
        "charts/exchange_rates_2022.png",
        ExtraArgs={"ContentType": "image/png"}
    )

    print("Графік успішно завантажено в S3!")


def main():
    DATA_DIR.mkdir(exist_ok=True)
    CHARTS_DIR.mkdir(exist_ok=True)

    s3 = boto3.client("s3", region_name=REGION)

    print("=== Отримання курсів валют ===")
    data = fetch_exchange_rates()

    print("\n=== Конвертація JSON у CSV ===")
    convert_to_csv(data)

    print("\n=== Завантаження CSV у S3 ===")
    upload_csv(s3)

    print("\n=== Читання CSV із S3 ===")
    df = read_csv_from_s3(s3)

    print("\n=== Побудова графіка ===")
    create_chart(df)

    print("\n=== Завантаження графіка в S3 ===")
    upload_chart(s3)

    print("\nЛабораторну №2 успішно виконано!")


if __name__ == "__main__":
    main()
