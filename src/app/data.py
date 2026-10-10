"""Create synthetic sales and derive only information available before each day."""

import numpy as np
import pandas as pd

from src.app.settings import (
    DATA_DIR,
    END_DATE,
    HISTORY_DAYS,
    PRODUCTS,
    SEED,
    START_DATE,
    BRANCHES,
)


def generate_sales(start=START_DATE, end=END_DATE, seed=SEED):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, end, freq="D")
    records = []

    weekday_factors = [1.15, 1.10, 1.00, 0.95, 1.05, 1.20, 0.55]

    branch_factors = {
        "SUC_01_CENTRO": 1.30,
        "SUC_02_NORTE": 1.10,
        "SUC_03_SUR": 0.95,
        "SUC_04_ESTE": 0.85,
        "SUC_05_OESTE": 0.80,
    }

    for branch_id in BRANCHES:
        branch_mult = branch_factors[branch_id]

        for product_id, product in PRODUCTS.items():
            base_price = product["price"]

            for day_number, date in enumerate(dates):
                seasonal_factor = 1 + 0.15 * np.sin(2 * np.pi * date.dayofyear / 365.25)

                trend_factor = 1 + day_number * 0.00012

                expected_sales = (
                    product["base_demand"]
                    * branch_mult
                    * weekday_factors[date.dayofweek]
                    * seasonal_factor
                    * trend_factor
                )

                units_sold = int(rng.poisson(expected_sales))

                if rng.random() < product["zero_prob"]:
                    units_sold = 0

                price_factor = rng.uniform(0.97, 1.03)
                effective_price = round(base_price * price_factor, 2)
                effective_price = float(effective_price)

                records.append(
                    {
                        "date": date,
                        "branch_id": branch_id,
                        "product_id": product_id,
                        "category": product["category"],
                        "unit_price": effective_price,
                        "units_sold": units_sold,
                    }
                )

    df = pd.DataFrame(records)

    return df.sort_values(["date", "branch_id", "product_id"]).reset_index(drop=True)


def validate_sales(sales):
    required = {"date", "branch_id", "product_id", "unit_price", "units_sold"}
    if not required.issubset(sales.columns) or sales.empty:
        raise ValueError(
            "Sales must contain date, branch_id, product_id, unit_price and units_sold."
        )

    if sales[list(required)].isna().any().any():
        raise ValueError("Missing sales records cannot be interpreted as zero demand.")

    if sales.duplicated(["branch_id", "product_id", "date"]).any():
        raise ValueError("Duplicate branch-product-date observations.")

    if not sales.branch_id.isin(BRANCHES).all():
        raise ValueError("Unknown branch.")
    if not sales.product_id.isin(PRODUCTS).all():
        raise ValueError("Unknown product.")

    if not pd.api.types.is_numeric_dtype(sales.units_sold):
        raise ValueError("Sales must be numeric.")
    if (
        not np.isfinite(sales.units_sold).all()
        or not sales.units_sold.between(0, 10000).all()
        or not (sales.units_sold % 1 == 0).all()
    ):
        raise ValueError(
            "Sales must be finite, non-negative integer units up to 10000."
        )

    for (branch_id, product_id), series in sales.groupby(["branch_id", "product_id"]):
        dates = pd.to_datetime(series.date).sort_values()

        if not dates.eq(dates.dt.normalize()).all():
            raise ValueError(
                f"Use calendar dates without a time component for {branch_id} - {product_id}."
            )

        if not dates.diff().dropna().eq(pd.Timedelta(days=1)).all():
            raise ValueError(
                f"Each branch-product pair needs a complete daily calendar, including zero-sales days. Error in {branch_id} - {product_id}."
            )

    return True


def make_features(
    branch_id: str,
    product_id: str,
    category: str,
    forecast_date: pd.Timestamp,
    unit_price: float,
    previous_sales: list | np.ndarray,
) -> dict:
    if len(previous_sales) != HISTORY_DAYS:
        raise ValueError(
            f"Se requieren exactamente {HISTORY_DAYS} días de ventas previas completas."
        )

    values = np.asarray(previous_sales, dtype=float)

    zero_days_count = np.sum(values == 0)

    return {
        "branch_id": str(branch_id),
        "product_id": str(product_id),
        "category": str(category),
        "day_of_week": int(forecast_date.dayofweek),
        "month": int(forecast_date.month),
        "is_weekend": int(forecast_date.dayofweek >= 5),
        "unit_price": float(unit_price),
        "sales_lag_1": float(values[-1]),
        "sales_lag_7": float(values[-7]),
        "sales_lag_14": float(values[-14]),
        "sales_mean_7": float(values[-7:].mean()),
        "sales_mean_14": float(values.mean()),
        "sales_std_14": float(values.std(ddof=0)),
        "zero_ratio_14": float(zero_days_count / HISTORY_DAYS),
        "sales_max_14": float(values.max()),
    }


def build_dataset(sales):
    records = []

    grouped = sales.groupby(["branch_id", "product_id"])

    for (branch_id, product_id), group in grouped:
        group = group.sort_values("date").reset_index(drop=True)
        values = group.units_sold.to_numpy()

        for index in range(HISTORY_DAYS, len(group)):
            row = group.iloc[index]
            previous_sales = values[index - HISTORY_DAYS : index]

            features = make_features(
                branch_id=branch_id,
                product_id=product_id,
                category=row.category,
                forecast_date=pd.Timestamp(row.date),
                unit_price=row.unit_price,
                previous_sales=previous_sales,
            )

            records.append(
                {"date": row.date, **features, "units_sold": int(row.units_sold)}
            )

    if not records:
        raise ValueError("Not enough history to build a training dataset.")

    df_features = pd.DataFrame(records)

    return df_features.sort_values(["date", "branch_id", "product_id"]).reset_index(
        drop=True
    )


def forecast_context(sales, branch_id, product_id, forecast_date, unit_price=None):
    date = pd.Timestamp(forecast_date)

    history = (
        sales[
            (sales.branch_id == branch_id)
            & (sales.product_id == product_id)
            & (sales.date < date)
        ]
        .sort_values("date")
        .tail(HISTORY_DAYS)
    )

    expected_dates = pd.date_range(
        date - pd.Timedelta(days=HISTORY_DAYS), periods=HISTORY_DAYS, freq="D"
    )

    if len(history) != HISTORY_DAYS or history.date.tolist() != expected_dates.tolist():
        raise ValueError(
            f"Se requieren exactamente 14 días consecutivos previos para {branch_id} - {product_id} antes de {date.date()}."
        )

    category = history.category.iloc[0]

    if unit_price is None:
        unit_price = float(history.unit_price.iloc[-1])

    features = make_features(
        branch_id=branch_id,
        product_id=product_id,
        category=category,
        forecast_date=date,
        unit_price=unit_price,
        previous_sales=history.units_sold.to_numpy(),
    )

    points = [
        {"date": str(row.date.date()), "units_sold": int(row.units_sold)}
        for row in history.itertuples()
    ]

    return features, points


def main():
    DATA_DIR.mkdir(exist_ok=True)
    sales = generate_sales()
    validate_sales(sales)
    dataset = build_dataset(sales)
    sales.to_csv(DATA_DIR / "sales.csv", index=False)
    dataset.to_csv(DATA_DIR / "features.csv", index=False)
    print(
        f"Created {len(sales):,} synthetic product-days and {len(dataset):,} forecasting examples."
    )


if __name__ == "__main__":
    main()
