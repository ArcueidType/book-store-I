import logging
import os
import pymongo
import threading
from pymongo.database import Database
from pymongo.errors import PyMongoError


class Store:
    database: str

    def __init__(self, db_path):
        self.database = db_path
        self.init_indexes()

    def init_indexes(self):
        try:
            db = self.get_db_conn()
            new_order_col = db['new_order']
            new_order_detail_col = db['new_order_detail']
            store_col = db['store']
            user_col = db['user']
            user_store_col = db['user_store']
            inverted_index_col = db['inverted_index']

            new_order_ii = new_order_col.index_information()
            if 'new_order_index' not in new_order_ii.keys():
                new_order_col.create_index([('order_id', 1)], unique=True, name='new_order_index')

            new_order_detail_ii = new_order_detail_col.index_information()
            if 'new_order_detail_index' not in new_order_detail_ii.keys():
                new_order_detail_col.create_index([('order_id', 1), ('book_id', 1)], unique=True,
                                                  name='new_order_detail_index')

            store_ii = store_col.index_information()
            if 'store_index' not in store_ii.keys():
                store_col.create_index([('store_id', 1), ('book_id', 1)], unique=True, name='store_index')

            user_ii = user_col.index_information()
            if 'user_index' not in user_ii.keys():
                user_col.create_index([('user_id', 1)], unique=True, name='user_index')

            user_store_ii = user_store_col.index_information()
            if 'user_store_index' not in user_store_ii.keys():
                user_store_col.create_index([('store_id', 1)], unique=True, name='user_store_index')

            inverted_index_ii = inverted_index_col.index_information()
            if 'inverted_index_index' not in inverted_index_ii.keys():
                inverted_index_col.create_index([('search_key', 1), ('search_id', 1)],
                                                unique=True, name='inverted_index_index')

        except PyMongoError as e:
            logging.error(e)

    def get_db_conn(self) -> Database:
        client = pymongo.MongoClient(self.database)
        db = client['book_store']
        return db


database_instance: Store = None
# global variable for database sync
init_completed_event = threading.Event()


def init_database(db_path):
    global database_instance
    database_instance = Store(db_path)


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()
