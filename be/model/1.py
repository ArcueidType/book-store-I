    def history_order(self, user_id):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)

            result = []
            orders = self.mongo['history_order'].find({'user_id': user_id}, {'_id': 0})
            for order in orders:
                result.append(order)

        except PyMongoError as e:
            return 529, "{}".format(str(e)), []
        except BaseException as e:
            return 530, "{}".format(str(e)), []
        return 200, "ok", result

   def recommend(self, user_id):
        try:
            code, message, orders = self.history_order(user_id)
            if code != 200:
                return error.error_non_exist_user_id(user_id)

            reco = {}
            labels = []
            for order in orders:
                boughtbooks = order['books']
                for boughtbook in boughtbooks:
                    eachbook = self.mongo['book'].find_one({'id': boughtbook['book_id']},
                                                           {'_id': 0, 'id': 1, 'title': 1, 'author': 1, 'tags': 1, 'publisher':1})
                    labels += eachbook['tags']
                    reco[eachbook['id']] = eachbook
                    reco[eachbook['id']]['tags'] = []
                    books = self.mongo['book'].find({'$or': [{'author': eachbook['author']},
                                                             {'publisher': eachbook['publisher']},
                                                             {'tags': {'$elemMatch': {'$in': eachbook['tags']}}}]},
                                                    {'_id': 0, 'id': 1, 'title': 1, 'author': 1, 'tags': 1})
                    for book in books:
                        if book['id'] not in reco.keys():
                            reco[book['id']] = book
            labels = list(set(labels))
            for book in reco.values():
                book['sim'] = jarcard_sim(labels, book['tags'])
                book.pop('tags')
            result = sorted(reco.values(), key=lambda k:k['sim'], reverse=True)
            result = result[:5]
        except PyMongoError as e:
            return 529, "{}".format(str(e)), []
        except BaseException as e:
            return 530, "{}".format(str(e)), []
        return 200, "ok", result


    def jarcard_sim(a, b):
        i = set(a).intersection(set(b))
        u = set(a + b)
        if len(u) == 0:
            return 0
        return len(i)/len(u)