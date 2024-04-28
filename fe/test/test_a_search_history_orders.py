import pytest
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer

from fe.access import auth
from fe import conf
import uuid

class TestSearchHistoryOrder: 
    @pytest.fixture(autouse=True)

    def pre_run_initialization(self):
        self.auth = auth.Auth(conf.URL)
        self.seller_id = "test_search_history_order_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_search_history_order_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_search_history_order_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.buyer_id
        self.buyer = register_new_buyer(self.buyer_id, self.password)
        self.gen_book = GenBook(self.seller_id, self.store_id)
        self.seller = self.gen_book.seller
    
    def test_search_history_orders_ok(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.buyer.add_funds(100000000000)
        code = self.buyer.payment(order_id)
        code = self.seller.deliver_book(self.store_id, order_id)
        code = self.buyer.confirm_delivery(self.buyer_id, order_id)
        code, result= self.auth.search_history_orders(self.buyer_id)
        assert code == 200 and len(result) > 0

    def test_search_history_orders_non_exist_buyer_id(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.buyer.add_funds(100000000000)
        code = self.buyer.payment(order_id)
        code = self.seller.deliver_book(self.store_id, order_id)
        code = self.buyer.confirm_delivery(self.buyer_id, order_id)
        code, _ = self.auth.search_history_orders(self.buyer_id+ "_x")
        assert code != 200