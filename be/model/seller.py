import json
from be.model import error
from be.model import db_conn
from pymongo.errors import PyMongoError


class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_book(
        self,
        user_id: str,
        store_id: str,
        book_id: str,
        book_json_str: str,
        stock_level: int,
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            book_json = json.loads(book_json_str)
            price = book_json.get('price')
            store_col = self.db['store']
            store_col.insert_one({'store_id': store_id, 'book_id': book_id, 'price': price,
                                  'stock_level': stock_level})

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def add_stock_level(
        self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            store_col = self.db['store']
            store_col.update_one({'$and': [{'store_id': store_id}, {'book_id': book_id}]},
                                 {'$inc': {'stock_level': add_stock_level}})

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)

            user_store_col = self.db['user_store']
            user_store_col.insert_one({'store_id': store_id, 'user_id': user_id})

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def deliver_book(self, order_id: str, store_id: str) -> (int, str):
        try:
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.order_id_exist(order_id):
                return error.error_invalid_order_id(order_id)
            status = self.db['new_order'].find_one({'order_id': order_id}, {'_id': 0})
            if status['status'] != 2:
                return error.error_invalid_order_status(order_id)

            self.db['new_order'].update_one({'order_id': order_id}, {'$set': {'status': 3}})
            cursor = self.db['history_order'].update_one({'order_id': order_id}, {'$set': {'status': 3}})
            if cursor.modified_count == 0:
                return error.error_invalid_order_id(order_id)

        except PyMongoError as e:
            return 529, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"
