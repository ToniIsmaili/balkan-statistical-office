from pyaxis import pyaxis
from pathlib import Path
from sqlalchemy import create_engine, MetaData, Table, select, insert, delete
from sqlalchemy.orm import Session
import pandas as pd
import json
from tqdm import tqdm
from dotenv import load_dotenv
import os

from Config import Config

load_dotenv()
engine = create_engine(os.getenv("DB_URL"))

configs = []

for json_file in Path("configs/mkstat").glob("*.json"):
    print("Loading [MKSTAT]:", json_file.name)
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        configs.append(Config(json_file.name, data))

for json_file in Path("configs/instat").glob("*.json"):
    print("Loading [INSTAT]:", json_file.name)
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        configs.append(Config(json_file.name, data))

print(f"Loaded {len(configs)} JSON files.")

def createDf(config:Config) -> pd.DataFrame:
    px = pyaxis.parse(config.url, encoding=config.encoding)
    dataDict = {}
    for column in config.columns:
        if column.fieldName is not None:
            series = px["DATA"][column.fieldName]
        else:
            series = column.defaultValue
        if column.map is not None:
            series = pd.Series(series).replace(column.map)
        dataDict[column.columnName] = series
    dataDict["value"] = pd.to_numeric(px["DATA"]["DATA"], errors="coerce")
    return pd.DataFrame(dataDict).dropna(subset=["value"])

def getOrCreate(session: Session, table_name: str, field_name: str, field_value) -> int:
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=session.bind)

    stmt = select(table.c.id).where(table.c[field_name] == field_value)
    result = session.execute(stmt).scalar_one_or_none()
    if result:
        return result

    ins = insert(table).values(**{field_name: field_value})
    result = session.execute(ins)
    session.commit()

    return result.inserted_primary_key[0]

def prepareForDb(df:pd.DataFrame, config:Config) -> pd.DataFrame:
    with Session(engine) as session:
        for column in config.columns:
            uniqueValues = df[column.columnName].unique()
            mapping = {}
            for value in uniqueValues:
                valueId = getOrCreate(session, column.tableName, column.columnName, value)
                mapping[value] = valueId
            df[column.columnName] = df[column.columnName].map(mapping).astype(int)
    if config.exchangeRate is not None:
        df["value"] = df["value"].astype(float).apply(lambda x: x / config.exchangeRate)
    return df

def insertDfIntoDb(tableName:str, df: pd.DataFrame):
    country_ids = df["country"].unique().tolist()
    with Session(engine) as session:
        metadata = MetaData()
        table = Table(tableName, metadata, autoload_with=session.bind)
        try:
            session.begin()
            session.execute(delete(table).where(table.c.country.in_(country_ids)))
            rows = df.to_dict(orient="records")
            session.execute(insert(table), rows)
            session.commit()
        except Exception as e:
            session.rollback()
            print("Error inserting data:", e)
            raise

for config in tqdm(configs):
    df = createDf(config)
    df = prepareForDb(df, config)
    insertDfIntoDb(config.tableName, df)