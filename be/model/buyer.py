from pymongo.errors import PyMongoError
import uuid
import logging
from be.model import db_conn
from be.model import error
from datetime import datetime

unpaid_orders = {}


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)
        self.time_limit = 300
        self.page_size = 25

    def new_order(
        self, user_id:  str, store_id:  str, id_and_count:  [(str, int)]
    ) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))
            order_id = uid
            total_price = 0

            for book_id, count in id_and_count:
                store_col = self.db['store']
                row = store_col.find({'$and':  [{'store_id':  store_id}, {'book_id':  book_id}]},
                                     {'_id':  0, 'book_id':  1, 'stock_level':  1, 'price':  1})

                row = list(row)
                if not row:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                row = row[0]
                stock_level = row['stock_level']
                price = row['price']

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                cursor = store_col.update_one({'$and':  [{'store_id':  store_id},
                                                         {'book_id':  book_id},
                                                         {'stock_level':  {'$gte':  count}}]},
                                              {'$inc':  {'stock_level': -count}})

                if cursor.modified_count == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)

                new_order_detail_col = self.db['new_order_detail']
                new_order_detail_col.insert_one({'order_id':  order_id, 'book_id':  book_id, 'count':  count,
                                                 'price':  price})

                total_price += price * count

            unpaid_orders[order_id] = int(datetime.now().timestamp())
            new_order_col = self.db['new_order']
            new_order_col.insert_one({'order_id': order_id,
                                      'store_id': store_id,
                                      'user_id': user_id,
                                      'status': 1,
                                      'total_price': total_price,
                                      'order_time': unpaid_orders[order_id]})

            history_order_col = self.db['history_order']
            history_order_col.insert_one({'order_id': order_id,
                                          'user_id': user_id,
                                          'store_id': store_id,
                                          'status': 1,
                                          'total_price': total_price,
                                          'order_time': unpaid_orders[order_id],
                                          'books': id_and_count})

        except PyMongoError as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    def payment(self, user_id:  str, password:  str, order_id:  str) -> (int, str):
        try:
            new_order_col = self.db['new_order']
            row = new_order_col.find({'order_id':  order_id}, {'_id': 0, 'order_id': 1, 'user_id': 1, 'store_id': 1,
                                                               'status': 1, 'total_price': 1})

            row = list(row)
            if not row:
                return error.error_invalid_order_id(order_id)

            row = row[0]
            order_id = row['order_id']
            buyer_id = row['user_id']
            store_id = row['store_id']
            status = row['status']
            total_price = row['total_price']

            if status != 1:
                return error.error_invalid_order_id(order_id)

            if buyer_id != user_id:
                return error.error_authorization_fail()

            cur_time = int(datetime.now().timestamp())
            time_diff = cur_time - unpaid_orders[order_id]
            if time_diff > self.time_limit:
                try:
                    unpaid_orders.pop(order_id)
                    result_cursor = self.db['new_order_detail'].find({'order_id': order_id},
                                                              {'_id': 0, 'book_id': 1, 'count': 1})
                    result_list = list(result_cursor)
                    if not result_list:
                        return error.error_invalid_order_id(order_id)
                    for row in result_list:
                        book_id = row['book_id']
                        count = row['count']
                        self.db['store'].update_one({'store_id': store_id,
                                                     'book_id': book_id},
                                                    {'$inc': {'stock_level': count}})
                    cursor = self.db['history_order'].update_one({'order_id': order_id}, {'$set': {'status': 0}})
                    if cursor.modified_count == 0:
                        return error.error_invalid_order_id(order_id)

                    self.db['new_order'].delete_one({'order_id': order_id})

                    self.db['new_order_detail'].delete_many({'order_id': order_id})
                except PyMongoError as e:
                    return 529, "{}".format(str(e))
                except BaseException as e:
                    return 530, "{}".format(str(e))
                return error.error_order_timelimit_exceeded(order_id)

            user_col = self.db['user']
            row = user_col.find({'user_id':  buyer_id}, {'_id':  0, 'balance':  1, 'password':  1})

            row = list(row)
            if not row:
                return error.error_non_exist_user_id(buyer_id)
            row = row[0]

            balance = row['balance']

            if password != row['password']:
                return error.error_authorization_fail()

            """         
            user_store_col = self.db['user_store']
            row = user_store_col.find({'store_id':  store_id}, {'_id':  0, 'store_id':  1, 'user_id':  1})

            row = list(row)
            if not row:
                return error.error_non_exist_store_id(store_id)

            row = row[0]
            seller_id = row['user_id']

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id) 
            """

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            cursor = user_col.update_one({'$and':  [{'user_id':  buyer_id}, {'balance':  {'$gte':  total_price}}]},
                                         {'$inc':  {'balance': -total_price}})

            if cursor.modified_count == 0:
                return error.error_not_sufficient_funds(order_id)

            cursor = new_order_col.update_one({'order_id':  order_id}, {'$set':  {'status':  2}})

            if cursor.modified_count == 0:
                return error.error_invalid_order_id(order_id)

            history_order_col = self.db['history_order']
            cursor = history_order_col.update_one({'order_id': order_id}, {'$set': {'status': 2}})

            if cursor.modified_count == 0:
                return error.error_invalid_order_id(order_id)

        except PyMongoError as e:
            return 528, "{}".format(str(e))

        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            user_col = self.db['user']
            row = user_col.find({'user_id':  user_id}, {'_id':  0, 'password':  1})
            row = list(row)

            if not row:
                return error.error_authorization_fail()

            row = row[0]
            if row['password'] != password:
                return error.error_authorization_fail()

            cursor = user_col.update_one({'user_id':  user_id}, {'$inc':  {'balance':  add_value}})

            if cursor.modified_count == 0:
                return error.error_non_exist_user_id(user_id)

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def manual_cancel_orders(self, order_id, user_id):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.order_id_exist(order_id):
                return error.error_invalid_order_id(order_id)
            
            unpaid_orders.pop(order_id)
            row = self.db['new_order'].find({'order_id': order_id}, {'_id': 0})
            row = list(row)
            if not row:
                return error.error_invalid_order_id(order_id)
            row = row[0]
            order_id = row['order_id']
            buyer_id = row['user_id']
            store_id = row['store_id']
            status = row['status']

            if buyer_id != user_id:
                return error.error_authorization_fail
            if status != 2:
                return error.error_invalid_order_status(order_id)

            #result = self.db['user_store'].find({'store_id': store_id}, {'_id': 0})
            #result = list(result)
            #if not result:
                #return error.error_non_exist_store_id(store_id)
            #result = result[0]
            #seller_id = result['user_id']
            #if not self.user_id_exist(seller_id):
                #return error.error_non_exist_user_id(seller_id)

            #self.db['users'].update_one({'user_id': user_id}, {'$inc': {"balance": total_price}})
            #self.db['users'].update_one({'user_id': seller_id}, {'$inc': {"balance": -total_price}})
            self.db['history_order'].update_one({'order_id': order_id}, {'$set': {'status': 0}})

            result_cursor = self.db['new_order_detail'].find({'order_id': order_id}, {'_id': 0, 'book_id': 1, 'count': 1})
            result_list = list(result_cursor)
            if not result_list:
                return error.error_invalid_order_id(order_id)
            for row in result_list:
                book_id = row['book_id']
                count = row['count']
                self.db['store'].update_one({'store_id': store_id,
                                             'book_id': book_id},
                                            {'$inc': {'stock_level': count}})

            self.db['new_order'].delete_one({'order_id': order_id})

            self.db['new_order_detail'].delete_one({'order_id': order_id})

        except PyMongoError as e:
            return 529, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "manual cancelled"

    def confirm_delivery(self, order_id:  str, user_id:  str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.order_id_exist(order_id):
                return error.error_invalid_order_id(order_id)

            delivery = self.db['new_order'].find({'order_id': order_id}, {'_id': 0})
            delivery = list(delivery)
            if not delivery:
                return error.error_invalid_order_id(order_id)

            delivery = delivery[0]
            buyer_id = delivery['user_id']
            status = delivery['status']
            store_id = delivery['store_id']
            total_price = delivery['total_price']

            if buyer_id != user_id:
                return error.error_authorization_fail()
            if status != 3:
                return error.error_invalid_order_status(order_id)
            seller = self.db['user_store'].find({'store_id': store_id}, {'_id': 0})
            seller = list(seller)
            if not seller:
                return error.error_non_exist_store_id(store_id)
            seller = seller[0]
            seller_id = seller['user_id']
            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            self.db['user'].update_one({'user_id': seller_id}, {'$inc': {'balance': total_price}})
            cursor = self.db['history_order'].update_one({'order_id': order_id}, {'$set': {'status': 4}})
            if cursor.modified_count == 0:
                return error.error_invalid_order_id(order_id)

            self.db['new_order'].delete_one({'order_id': order_id})
            self.db['new_order_detail'].delete_one({'order_id': order_id})

        except PyMongoError as e:
            return 529, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "delivery confirmed"

    def auto_cancel_orders(self, order_id, user_id):
        if not self.user_id_exist(user_id):
            return error.error_non_exist_user_id(user_id)
        if not self.order_id_exist(order_id):
            return error.error_invalid_order_id(order_id)
        cur_time = int(datetime.now().timestamp())
        time_diff = cur_time - unpaid_orders[order_id]
        if time_diff > self.time_limit:
            try:
                unpaid_orders.pop(order_id)
                store_id = self.db['order_detail'].find({'order_id': order_id},
                                                        {'_id': 0, 'store_id': 1})
                result_cursor = self.db['new_order_detail'].find({'order_id': order_id},
                                                          {'_id': 0, 'book_id': 1, 'count': 1})
                result_list = list(result_cursor)
                if not list(result_list):
                    return error.error_invalid_order_id(order_id)
                for row in result_list:
                    book_id = row['book_id']
                    count = row['count']
                    self.db['store'].update_one({'store_id': store_id,
                                                 'book_id': book_id},
                                                {'$inc': {'stock_level': count}})
                    cursor = self.db['history_order'].update_one({'order_id': order_id}, {'$set': {'status': 0}})
                    if cursor.modified_count == 0:
                        return error.error_invalid_order_id(order_id)

                    self.db['new_order'].delete_one({'order_id': order_id})

                    self.db['new_order_detail'].delete_many({'order_id': order_id})
            except PyMongoError as e:
                return 529, "{}".format(str(e))
            except BaseException as e:
                return 530, "{}".format(str(e))
            return error.error_order_timelimit_exceeded(order_id)
        return 200, "auto cancel"

    def search(self, search_key, page=0) -> (int, str, list):
        try:
            inverted_index_col = self.db['inverted_index']
            if page > 0:
                page_start = self.page_size * (page - 1)
                rows = inverted_index_col.find(
                    {'search_key': search_key},
                    {'_id': 0,
                    'book_id': 1,
                    'book_title': 1,
                    'book_author': 1}
                ).sort({'search_id': 1}).limit(self.page_size).skip(page_start)
            else:
                rows = inverted_index_col.find({'search_key': search_key},
                                               {'_id': 0,
                                                'book_id': 1,
                                                'book_title': 1,
                                                'book_author': 1}).sort({'search_id': 1})
            rows = list(rows)
            result = []
            store_col = self.db['store']
            for row in rows:
                book_id = row['book_id']
                if not store_col.find_one({'book_id': book_id}):
                    continue
                book = {
                    'id': book_id,
                    'title': row['book_title'],
                    'author': row['book_author']
                }
                result.append(book)

        except PyMongoError as e:
            return 529, '{}'.format(str(e)), []
        except BaseException as e:
            return 530, '{}'.format(str(e)), []
        return 200, 'ok', result

    def search_multi_words(self, key_words) -> (int, str, list):
        try:
            result = []
            for word in key_words:
                code, message, cur_res = self.search(word, 0)
                if code == 200:
                    result += cur_res

            unique_dict = {}
            for record in result:
                if record['id'] in unique_dict.keys():
                    continue
                unique_dict[record['id']] = record
            result = list(unique_dict.values())
        except PyMongoError as e:
            return 529, '{}'.format(str(e)), []
        except BaseException as e:
            return 530, '{}'.format(str(e)), []
        return 200, 'ok', result

    def search_in_store(self, store_id, search_key, page=0) -> (int, str, list):
        try:
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + ([],)

            inverted_index_col = self.db['inverted_index']

            if page > 0:
                page_start = self.page_size * (page - 1)
                rows = inverted_index_col.aggregate([{'$lookup': {
                                                    'from': 'store',
                                                    'localField': 'book_id',
                                                    'foreignField': 'book_id',
                                                    'as': 'search_doc'}},
                                                     {'$project': {
                                                         'search_doc.store_id': 1,
                                                         'search_key': 1,
                                                         'search_id': 1,
                                                         'book_id': 1,
                                                         'book_title': 1,
                                                         'book_author': 1,
                                                         '_id': 0
                                                     }},
                                                     {'$match': {
                                                         'search_key': search_key,
                                                         'search_doc.store_id': store_id
                                                     }},
                                                     {'$sort': {'search_id': 1}},
                                                     {'$skip': page_start},
                                                     {'$limit': self.page_size}])
            else:
                rows = inverted_index_col.aggregate([{'$lookup': {
                                                    'from': 'store',
                                                    'localField': 'book_id',
                                                    'foreignField': 'book_id',
                                                    'as': 'search_doc'}},
                                                    {'$project': {
                                                        'search_doc.store_id': 1,
                                                        'search_key': 1,
                                                        'search_id': 1,
                                                        'book_id': 1,
                                                        'book_title': 1,
                                                        'book_author': 1,
                                                        '_id': 0
                                                    }},
                                                    {'$match': {
                                                        'search_key': search_key,
                                                        'search_doc.store_id': store_id
                                                    }},
                                                    {'$sort': {'search_id': 1}}])

            rows = list(rows)
            result = []
            for row in rows:
                book = {
                    'id': row['book_id'],
                    'title': row['book_title'],
                    'author': row['book_author']
                }
                result.append(book)
        except PyMongoError as e:
            return 529, '{}'.format(str(e)), []
        except BaseException as e:
            return 530, '{}'.format(str(e)), []
        return 200, 'ok', result
