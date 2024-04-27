from pymongo.errors import PyMongoError
import uuid
import logging
from be.model import db_conn
from be.model import error
from datetime import datetime

unpaid_orders = {}
time_limit = 20


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)
        self.time_limit = 300

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

            new_order_col = self.db['new_order']
            new_order_col.insert_one({'order_id':  order_id, 'store_id':  store_id, 'user_id':  user_id,
                                      'status':  1, 'total_price':  total_price,
                                      'order_time':  int(datetime.now().timestamp())})
            unpaid_orders[order_id] = int(datetime.now().timestamp())

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
                                                               'status': 1, 'total_price': 1, 'order_time': 1})

            row = list(row)
            if not row:
                return error.error_invalid_order_id(order_id)

            row = row[0]
            order_id = row['order_id']
            buyer_id = row['user_id']
            store_id = row['store_id']
            status = row['status']
            total_price = row['total_price']
            order_time = row['order_time']

            if status != 1:
                return error.error_invalid_order_id(order_id)

            if buyer_id != user_id:
                return error.error_authorization_fail()

            cur_time = int(datetime.now().timestamp())
            time_diff = cur_time - unpaid_orders[order_id]
            if time_diff > time_limit:
                try:
                    unpaid_orders.pop(order_id)
                    result = self.db['new_order_detail'].find({'order_id': order_id}, {'_id': 0, 'book_id': 1, 'count': 1})
                    if not list(result):
                        return error.error_invalid_order_id(order_id)
                    for row in result:
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
                return error.error_order_timelimit_exceeded(order_id)

            duration = int(datetime.now().timestamp()) - order_time
            if duration > self.time_limit:
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

            user_store_col = self.db['user_store']
            row = user_store_col.find({'store_id':  store_id}, {'_id':  0, 'store_id':  1, 'user_id':  1})

            row = list(row)
            if not row:
                return error.error_non_exist_store_id(store_id)

            row = row[0]
            seller_id = row['user_id']

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            cursor = user_col.update_one({'$and':  [{'user_id':  buyer_id}, {'balance':  {'$gte':  total_price}}]},
                                         {'$inc':  {'balance': -total_price}})

            if cursor.modified_count == 0:
                return error.error_not_sufficient_funds(order_id)

            cursor = new_order_col.update_one({'order_id':  order_id}, {'$set':  {'status':  2}})

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

            row = self.db['new_order'].find({'order_id': order_id}, {'_id': 0})
            if not list(row):
                return error.error_invalid_order_id(order_id)
            order_id = row['order_id']
            buyer_id = row['user_id']
            store_id = row['store_id']
            total_price = row['total_price']
            status = row['status']
            order_time = row['order_time']
            if buyer_id != user_id:
                return error.error_authorization_fail
            if status != 2:
                return error.error_invalid_order_status(order_id)

            result = self.db['user_store'].find({'store_id': store_id}, {'_id': 0})
            if not list(result):
                return error.error_non_exist_store_id(store_id)
            seller_id = result['user_id']
            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            self.db['users'].update_one({'user_id': user_id}, {'$inc': {"balance": total_price}})

            self.db['users'].update_one({'user_id': seller_id}, {'$inc': {"balance": -total_price}})

            self.db['history_order'].insert_one({'order_id': order_id,
                                                 'user_id': user_id,
                                                 'store_id': store_id,
                                                 'status': 0,
                                                 'total_price': total_price,
                                                 'order_time': order_time})

            result = self.db['new_order_detail'].find({'order_id': order_id}, {'_id': 0, 'book_id': 1, 'count': 1})
            if not list(result):
                return error.error_invalid_order_id(order_id)
            for row in result:
                book_id = row['book_id']
                count = row['count']
                self.db['store'].update_one({'store_id': store_id,
                                             'book_id': book_id},
                                            {'$inc': {'stock_level': count}})

            self.db['new_order'].delete_one({'order_id': order_id})

            self.db['new_order_detail'].delete_one({'order_id': order_id})

        except PyMongoError as e:
            return 529, "{}".format(str(e)), []
        except BaseException as e:
            return 530, "{}".format(str(e)), []
        return 200, "ok", result

    def confirm_delivery(self, order_id:  str, user_id:  str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.order_id_exist(order_id):
                return error.error_invalid_order_id(order_id)

            delivery = self.db['new_order'].find({'order_id': order_id}, {'_id': 0})

            buyer_id = delivery['user_id']
            status = delivery['status']
            store_id = delivery['store_id']
            total_price = delivery['total_price']
            order_time = delivery['order_time']

            if buyer_id != user_id:
                return error.error_authorization_fail()
            if status != 3:
                return error.error_invalid_order_status(order_id)
            seller = self.db['user_store'].find({'store_id': store_id}, {'_id': 0})
            if not list(seller):
                return error.error_non_exist_store_id(store_id)
            seller_id = seller['user_id']
            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            self.db['user'].update_one({'user id': seller_id}, {'$inc': {'balance': total_price}})
            self.db['history_order'].insert_one({
                'order_id': order_id,
                'user_id': user_id,
                'store_id': store_id,
                'status': 4,
                'total_price': total_price,
                'order_time': order_times
            })
            self.db['new_order'].delete_one({'order_id': order_id})
            self.db['new_order_detail'].delete_one({'order_id': order_id})

        except PyMongoError as e:
            return 529, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"
