class Column:
    columnName:str
    defaultValue:str
    fieldName:str
    tableName:str
    map:dict

    def __init__(self, columnName, defaultValue, fieldName, tableName, map):
        self.columnName = columnName
        self.defaultValue = defaultValue
        self.fieldName = fieldName
        self.tableName = tableName
        self.map = map


class Config:
    fileName:str
    url:str
    encoding:str
    tableName:str
    exchangeRate:float
    columns:list[Column]

    def __init__(self, fileName:str, data:dict):
        self.fileName = fileName
        self.url = data["url"]
        self.encoding = data["encoding"]
        self.tableName = data["table_name"]
        self.exchangeRate = data["exchange_rate"]
        self.columns = []
        for column in data["columns"]:
            self.columns.append(Column(column["column_name"], column["default_value"], column["field_name"], column["table_name"], column["map"]))

    def __str__(self):
        return f"File: {self.fileName}"

    def printColumns(self):
        for column in self.columns:
            print(f"Column Name: {column.columnName}, Default Value: {column.defaultValue}, Field Name: {column.fieldName}")