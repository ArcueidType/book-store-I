import pytest
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer

from fe.access import auth
from fe import conf
import uuid
import time

class TestAutoCancel: 
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.auth = auth.Auth(conf.URL)
        self.seller_id = "test_auto_cancel_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_auto_cancel_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_auto_cancel_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.buyer_id
        self.buyer = register_new_buyer(self.buyer_id, self.password)
        self.gen_book = GenBook(self.seller_id, self.store_id)
        self.seller = self.gen_book.seller
    
    def test_auto_cancel_ok(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        _, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        time.sleep(31)
        code = self.buyer.auto_cancel_orders(self.buyer_id, order_id)
        assert code == 200
    
    def test_auto_cancel_not_timeout(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        _, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.buyer.auto_cancel_orders(self.buyer_id, order_id)
        assert code == 531

    def test_auto_cancel_non_exist_order_id(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        _, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        time.sleep(31)
        code = self.buyer.auto_cancel_orders(self.buyer_id, order_id + "_x")
        assert code != 200

    def test_auto_cancel_non_exist_user_id(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        _, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        time.sleep(31)
        code = self.buyer.auto_cancel_orders(self.buyer_id + "_x", order_id)
        assert code != 200