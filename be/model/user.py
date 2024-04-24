import jwt
import time
import logging
from pymongo.errors import PyMongoError
from be.model import error
from be.model import db_conn

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
