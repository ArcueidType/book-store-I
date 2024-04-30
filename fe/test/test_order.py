import pytest
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer

from fe.access import auth
from fe import conf
import uuid


class TestOrder: 
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.auth = auth.Auth(conf.URL)
        self.seller_id = "test_order_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_order_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_order_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = self.buyer_id
        self.buyer = register_new_buyer(self.buyer_id, self.password)
        self.gen_book = GenBook(self.seller_id, self.store_id)
        self.seller = self.gen_book.seller

    
    def test_deliver_status_error(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        _, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.seller.deliver_book(self.store_id, order_id)
        assert code != 200
    
    def test_deliver_book_ok(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        _, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.buyer.add_funds(1000000000)
        code = self.buyer.payment(order_id)
        code = self.seller.deliver_book(self.store_id, order_id)
        assert code == 200

    def test_deliver_non_exist_order_id(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        _, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.seller.deliver_book(self.store_id, order_id+ "_x")
        assert code != 200

    def test_deliver_non_exist_store_id(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.seller.deliver_book(self.store_id+ "_x", order_id)
        assert code != 200

    def test_confirm_delivery_ok(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.buyer.add_funds(1000000000)
        code = self.buyer.payment(order_id)
        code = self.seller.deliver_book(self.store_id, order_id)
        code = self.buyer.confirm_delivery(self.buyer_id, order_id)
        assert code == 200

    def test_confirm_delivery_status_error(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.buyer.confirm_delivery(self.buyer_id, order_id)
        assert code != 200
    
    def test_confirm_delivery_non_exist_order_id(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.seller.deliver_book(self.store_id, order_id)
        code = self.buyer.confirm_delivery(self.buyer_id, order_id + "_x")
        assert code != 200

    def test_confirm_delivery_non_exist_buyer_id(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.seller.deliver_book(self.store_id, order_id)
        code = self.buyer.confirm_delivery(self.buyer_id + "_x", order_id)
        assert code != 200

    def test_confirm_delivery_non_match_buyer_id(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.seller.deliver_book(self.store_id, order_id)
        code = self.buyer.confirm_delivery(self.seller_id, order_id)
        assert code != 200


    def test_manual_cancel_orders_ok(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.buyer.add_funds(1000000000)
        code = self.buyer.payment(order_id)
        code = self.buyer.manual_cancel_orders(self.buyer_id, order_id)
        assert code == 200
    
    def test_manual_cancel_orders_status_error(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.buyer.manual_cancel_orders(self.buyer_id, order_id)
        assert code != 200

    def test_manual_cancel_orders_non_exist_buyer_id(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.buyer.add_funds(1000000000)
        code = self.buyer.payment(order_id)
        code = self.buyer.manual_cancel_orders(self.buyer_id + "_x", order_id)
        assert code != 200
    
    def test_manual_cancel_orders_non_match_buyer_id(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.buyer.add_funds(1000000000)
        code = self.buyer.payment(order_id)
        code = self.buyer.manual_cancel_orders(self.seller_id, order_id)
        assert code != 200
    
    def test_manual_cancel_orders_non_exist_order_id(self):
        ok, buy_book_id_list = self.gen_book.gen(non_exist_book_id=False, low_stock_level=False)
        assert ok
        code, order_id = self.buyer.new_order(self.store_id, buy_book_id_list)
        code = self.buyer.payment(order_id)
        code = self.buyer.manual_cancel_orders(self.buyer_id, order_id + "_x")
        assert code != 200
