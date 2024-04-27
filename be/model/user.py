import jwt
import time
import logging
from pymongo.errors import PyMongoError
from be.model import error
from be.model import db_conn
from collections import defaultdict
import math
from operator import itemgetter

# encode a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }


def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal, "timestamp": time.time()},
        key=user_id,
        algorithm="HS256",
    )
    return encoded


# decode a JWT to a json string like:
#   {
#       "user_id": [user name],
#       "terminal": [terminal code],
#       "timestamp": [ts]} to a JWT
#   }
def jwt_decode(encoded_token, user_id: str) -> dict:
    decoded = jwt.decode(encoded_token, key=user_id, algorithms="HS256")
    return decoded


class User(db_conn.DBConn):
    token_lifetime: int = 3600  # 3600 second

    def __init__(self):
        db_conn.DBConn.__init__(self)

    def __check_token(self, user_id, db_token, token) -> bool:
        try:
            if db_token != token:
                return False
            jwt_text = jwt_decode(encoded_token=token, user_id=user_id)
            ts = jwt_text["timestamp"]
            if ts is not None:
                now = time.time()
                if self.token_lifetime > now - ts >= 0:
                    return True
            return False
        except jwt.exceptions.InvalidSignatureError as e:
            logging.error(str(e))
            return False

    def register(self, user_id: str, password: str) -> (int, str):
        try:
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            user_col = self.db['user']

            if self.user_id_exist(user_id):
                return error.error_exist_user_id(user_id)

            user_col.insert_one({'user_id': user_id, 'password': password, 'balance': 0, 'token': token,
                                 'terminal': terminal})

        except PyMongoError:
            return error.error_exist_user_id(user_id)
        return 200, "ok"

    def check_token(self, user_id: str, token: str) -> (int, str):
        user_col = self.db['user']
        row = user_col.find({'user_id': user_id}, {'_id': 0, 'token': 1})
        row = list(row)
        if not row:
            return error.error_authorization_fail()
        row = row[0]
        db_token = row['token']
        if not self.__check_token(user_id, db_token, token):
            return error.error_authorization_fail()
        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> (int, str):
        user_col = self.db['user']
        row = user_col.find({'user_id': user_id}, {'_id': 0, 'password': 1})

        row = list(row)
        if not row:
            return error.error_authorization_fail()

        row = row[0]
        if password != row['password']:
            return error.error_authorization_fail()

        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""

            token = jwt_encode(user_id, terminal)
            user_col = self.db['user']
            cursor = user_col.update_one({'user_id': user_id}, {'$set': {'token': token, 'terminal': terminal}})

            if cursor.modified_count == 0:
                return error.error_authorization_fail() + ("",)

        except PyMongoError as e:
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            return 530, "{}".format(str(e)), ""
        return 200, "ok", token

    def logout(self, user_id: str, token: str) -> (int, str):
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            dummy_token = jwt_encode(user_id, terminal)

            user_col = self.db['user']
            cursor = user_col.update_one({'user_id': user_id}, {'$set': {'token': dummy_token, 'terminal': terminal}})

            if cursor.modified_count == 0:
                return error.error_authorization_fail()

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message

            user_col = self.db['user']
            cursor = user_col.delete_one({'user_id': user_id})
            if cursor.deleted_count != 1:
                return error.error_authorization_fail()

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> (int, str):
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            user_col = self.db['user']
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            cursor = user_col.update_one({'user_id': user_id}, {'$set': {'password': new_password,
                                                                         'token': token,
                                                                         'terminal': terminal}})

            if cursor.modified_count == 0:
                return error.error_authorization_fail()

        except PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def search_history_orders(self, user_id):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            result = []
            orders = self.db['history_order'].find({'user_id': user_id}, {'_id': 0})
            for _ in orders:
                result.append(_)
            
        except PyMongoError as e:
            return 529, "{}".format(str(e)), []
        except BaseException as e:
            return 530, "{}".format(str(e)), []
        return 200, "ok", result

    # ItemCF-IUF物品协同过滤推荐算法
    def recommend_generate(self, user_id: str) -> (int, str, list):
        try:
            users_tags = defaultdict(set)
            users_books = defaultdict(set)
            all_books_tags = defaultdict(set)
            target_user_history = set()
            history_orders = self.db['history_order']

            for history_order in history_orders.find({'status': 4}, {'_id': 0}):
                books = history_order['books']
                user = history_orders['user_id']
                for book in books:
                    if book[0] in users_books[user]:
                        continue
                    if user == user_id:
                        target_user_history.add(book[0])

                    users_books.setdefault(user, []).append(book[0])
                    each_book = self.db['book'].find_one({'id': book[0]},
                                                         {'_id': 0, 'id': 1, 'title': 1, 'author': 1, 'tags': 1})
                    tags = set(each_book['tags'].split("\n"))
                    tags = tags.add(each_book['author'])
                    all_books_tags[book[0]] = tags
                    users_tags.setdefault(user, set()).update(tags)

            for _, user_tags in users_tags.items():
                user_tags.remove('')

            tag_total_matched = defaultdict(int)   # 每个tag被所有user购买过book的tags的匹配次数总和
            tag_sim_matrix = defaultdict(dict)      # tag的共现矩阵

            # 以二维字典形式计算共现矩阵
            for user, tags in users_tags.items():
                for tag in tags:
                    tag_sim_matrix.setdefault(tag, dict())
                    tag_total_matched[tag] += 1
                    for tag_k in tags:
                        if tag == tag_k:
                            continue
                        tag_sim_matrix[tag].setdefault(tag_k, 0)
                        tag_sim_matrix[tag][tag_k] += (1. / math.log1p(len(tags) * 1.))

            # 计算相似度矩阵
            tagSimMatrix = defaultdict(dict)
            for tag, related_tags in tag_sim_matrix.items():
                for tag_k, value in related_tags.items():
                    tagSimMatrix[tag][tag_k] = value / math.sqrt(tag_total_matched[tag] * tag_total_matched[tag_k])

            # 相似度矩阵标准化
            for tag, related_degrees in tag_sim_matrix.items():
                max_degree = max(related_degrees.values())
                tagSimMatrix[tag] = {k: v / max_degree for k, v in related_degrees.items()}

            # 寻找相似度最高的10个tag
            recommend_tags = dict()
            target_user_tags = users_tags[user_id]
            for tag in target_user_tags:
                for i, sim in sorted(tagSimMatrix[tag].items(), key=itemgetter(1), reverse=True)[:20]:
                    # 这里筛选的结果保留user购买过的书籍包含的tags
                    # if i in target_user_tags:
                    #     continue
                    recommend_tags.setdefault(i, 0.)
                    recommend_tags[i] += sim
            recommend_tags = dict(sorted(recommend_tags.items(), key=itemgetter(1), reverse=True)[:10])

            # 寻找相似度最高的书籍并推荐
            recommends = []
            key_tags = set(recommend_tags.keys())
            for book_id, tags in all_books_tags.items():
                intersection = tags.intersection(key_tags)
                if intersection:
                    sim_value = sum(recommend_tags[tag] for tag in intersection)
                    recommends.append([book_id, tags, sim_value])

            recommends = sorted(recommends, key=lambda x: x[2], reverse=True)[:20]
            recommend_books = []
            for book_info in recommends:
                if book_info[0] in target_user_history:
                    continue
                book = self.db['book'].find_one({'id': book_info[0]}, {'_id': 0, 'id': 1, 'title': 1, 'author': 1})
                recommend_books.append(list(book.values()) + book_info[1:])

        except PyMongoError as e:
            return 529, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok", recommend_books
