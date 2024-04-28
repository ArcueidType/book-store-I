import pytest
from fe.access.new_seller import register_new_seller
from fe.access import book
from fe.access import auth
from fe import conf
import uuid

class TestSearch: 
    @pytest.fixture(autouse=True)

    def pre_run_initialization(self):
        self.auth = auth.Auth(conf.URL)
        self.seller_id="test_point_search_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_point_search_store_id_{}".format(str(uuid.uuid1()))
        self.password = self.seller_id
        self.seller = register_new_seller(self.seller_id, self.password)
        code = self.seller.create_store(self.store_id)
        assert code == 200
        book_db = book.BookDB()
        self.books = book_db.get_book_info(0, 1)
        for bk in self.books:
            self.title=bk.title
            self.author=bk.author
            code = self.seller.add_book(self.store_id, 0, bk)
            assert code == 200 
        yield
    
    def test_search_ok(self):
        code, result = self.auth.search_title(self.title, 0)
        assert code==200 and len(result) > 0

    def test_search_multi_words_ok(self):
        code, result = self.auth.search_multi_words([self.title, self.author])
        assert code==200 and len(result) > 0

    def test_search_in_store_ok(self):
        code, result = self.auth.search_in_store(self.store_id, self.author, 0)
        assert code==200 and len(result) > 0 

    def test_search_in_store_non_exist_store_id(self):
        code, _ = self.auth.search_in_store(self.store_id+ "_x", self.author, 0)
        assert code != 200