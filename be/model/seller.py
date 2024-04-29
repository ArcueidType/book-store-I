import json
from be.model import error
from be.model import db_conn
from pymongo.errors import PyMongoError
from be.model.utils import parse_country_author
from be.model.utils import parse_name
from be.model.utils import get_keywords
from be.model.utils import get_prefix
from be.model.utils import get_words_suffix


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
            book_json.pop('price')

            inverted_index_col = self.db['inverted_index']
            cursor = inverted_index_col.find_one({'book_id': book_id})
            if not cursor:
                country, author = '', ''
                if 'author' in book_json.keys():
                    author = book_json.get('author')
                    country, author = parse_country_author(author)
                tags = []
                if 'tags' in book_json.keys():
                    tags = book_json.get('tags')
                # if 'author_intro' in book_json.keys():
                #     tags += get_keywords(book_json.get('author_intro'))
                # if 'book_intro' in book_json.keys():
                #     tags += get_keywords(book_json.get('book_intro'))
                # if 'content' in book_json.keys():
                #     tags += get_keywords(book_json.get('content'))
                # tags = list(set(tags))

                prefixes = []
                title = book_json.get('title')
                prefixes += get_words_suffix(title)

                if author != '':
                    names = parse_name(author)
                    for i in range(1, len(names)):
                        prefixes += get_prefix(names[i])
                    prefixes += get_prefix(author)
                if 'original_title' in book_json.keys():
                    prefixes += get_prefix(book_json.get('original_title'))
                if 'translator' in book_json.keys():
                    translator = book_json.get('translator')
                    names = parse_name(translator)
                    for i in range(1, len(names)):
                        prefixes += get_prefix(names[i])
                    prefixes += get_prefix(translator)
                if country != '':
                    prefixes += [country]
                if tags:
                    prefixes += tags
                prefixes = list(set(prefixes))

                for prefix in prefixes:
                    cur_search_id = self.db['inverted_index'].count_documents({}) + 1
                    inverted_index_col.insert_one({'search_key': prefix,
                                                   'search_id': cur_search_id,
                                                   'book_id': book_id,
                                                   'book_title': title,
                                                   'book_author': author})

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
