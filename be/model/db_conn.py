from be.model import store


class DBConn:
    def __init__(self):
        self.db = store.get_db_conn()

    def user_id_exist(self, user_id):
        user_col = self.db['user']
        row = user_col.find({'user_id': user_id}, {'_id': 0, 'user_id': 1})

        if list(row):
            return True
        else:
            return False

    def book_id_exist(self, store_id, book_id):
        store_col = self.db['store']
        row = store_col.find({'$and': [{'store_id': store_id}, {'book_id': book_id}]}, {'_id': 0, 'book_id': 1})

        if list(row):
            return True
        else:
            return False

    def store_id_exist(self, store_id):
        user_store_col = self.db['user_store']
        row = user_store_col.find({'store_id': store_id}, {'_id': 0, 'store_id': 1})
        if list(row):
            return True
        else:
            return False
