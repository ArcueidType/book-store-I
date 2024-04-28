import os

import numpy as np
import pymongo
import random
import base64
import simplejson as json


class Book:
    id: str
    title: str
    author: str
    publisher: str
    original_title: str
    translator: str
    pub_year: str
    pages: int
    price: int
    currency_unit: str
    binding: str
    isbn: str
    author_intro: str
    book_intro: str
    content: str
    tags: [str]
    pictures: [bytes]

    def __init__(self):
        self.tags = []
        self.pictures = []


class BookDB:
    def __init__(self, large: bool = False):
        parent_path = os.path.dirname(os.path.dirname(__file__))
        # self.db_s = 'mongodb://localhost:27017/'
        # self.db_l = 'mongodb://localhost:27017/'
        # if large:
        self.database = 'mongodb://localhost:27017/'
        client = pymongo.MongoClient(self.database)
        self.book_db = client['book_store']
        # else:
        #     self.book_db = self.db_s

    def get_book_count(self):
        book_col = self.book_db['book']
        return book_col.count_documents({})

    def get_book_info(self, start, size) -> [Book]:
        books = []
        book_col = self.book_db['book']
        cursor = book_col.find({}, {'_id': 0}).sort('id').limit(size).skip(start)

        for row in cursor:
            book = Book()
            book.id = row['id']
            book.title = row['title']
            book.author = row['author']
            book.publisher = row['publisher']
            book.original_title = row['original_title']
            book.translator = row['translator']
            book.pub_year = row['pub_year']
            book.pages = None if np.isnan(row['pages']) else int(row['pages'])
            book.price = row['price']

            book.currency_unit = row['currency_unit']
            book.binding = row['binding']
            book.isbn = row['isbn']
            book.author_intro = row['author_intro']
            book.book_intro = row['book_intro']
            book.content = row['content']
            tags = row['tags']

            picture = row['picture']

            for tag in tags.split("\n"):
                if tag.strip() != "":
                    book.tags.append(tag)
            for i in range(0, random.randint(0, 9)):
                if picture is not None:
                    encode_str = base64.b64encode(picture).decode("utf-8")
                    book.pictures.append(encode_str)
            books.append(book)
            # print(tags.decode('utf-8'))

            # print(book.tags, len(book.picture))
            # print(book)
            # print(tags)

        return books
