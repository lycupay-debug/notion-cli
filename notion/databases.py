from .client import notion


def query_data_source(data_source_id: str):
    response = notion.data_sources.query(
        data_source_id=data_source_id,
    )
    return response["results"]


def get_database(database_id: str):
    response = notion.databases.retrieve(
        database_id=database_id,
    )
    return response