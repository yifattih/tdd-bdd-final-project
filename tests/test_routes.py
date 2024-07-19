######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
  codecov --token=$CODECOV_TOKEN

  While debugging just these tests it's convenient to use this:
    nosetests --stop tests/test_service.py:TestProductService
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from urllib.parse import quote_plus
from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory

# Disable all but critical errors during normal test run
# uncomment for debugging failing tests
# logging.disable(logging.CRITICAL)

# DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///../db/test.db')
DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    ############################################################
    # Utility function to bulk create products
    ############################################################
    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code, status.HTTP_201_CREATED, "Could not create test product"
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ############################################################
    #  T E S T   C A S E S
    ############################################################
    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    # ----------------------------------------------------------
    # TEST CREATE
    # ----------------------------------------------------------
    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Product: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["description"], test_product.description)
        self.assertEqual(Decimal(new_product["price"]), test_product.price)
        self.assertEqual(new_product["available"], test_product.available)
        self.assertEqual(new_product["category"], test_product.category.name)

        #
        # Uncomment this code once READ is implemented
        #

        # # Check that the location header was correct
        # response = self.client.get(location)
        # self.assertEqual(response.status_code, status.HTTP_200_OK)
        # new_product = response.get_json()
        # self.assertEqual(new_product["name"], test_product.name)
        # self.assertEqual(new_product["description"], test_product.description)
        # self.assertEqual(Decimal(new_product["price"]), test_product.price)
        # self.assertEqual(new_product["available"], test_product.available)
        # self.assertEqual(new_product["category"], test_product.category.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        logging.debug("Product no name: %s", new_product)
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    #
    # ADD YOUR TEST CASES HERE
    #
    def test_get_product(self):
        """It should Read a Product"""
        test_product = self._create_products(count=1)[0]
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)

    def test_get_product_list(self):
        """It should Get a list of Products"""

        # create products list
        self._create_products(count=5)

        # get response
        response = self.client.get(BASE_URL)

        # check if created
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # store response data
        data = response.get_json()

        # check length of data is equal number of products created
        self.assertEqual(len(data), 5)

    def test_get_product_not_found(self):
        """It should not Read a Product that is not found"""
        product_id = 0
        response = self.client.get(f"{BASE_URL}/{product_id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        self.assertIn("was not found", data["message"])

    def test_update_product(self):
        """It should Update an existing Product entry"""
        # create product
        test_product = ProductFactory()

        # send post request
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # update product
        new_product = response.get_json()
        new_product["description"] = "Unknown"
        response = self.client.put(f"{BASE_URL}/{new_product['id']}", json=new_product)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # assert if product was updated
        updated_product = response.get_json()
        self.assertEqual(updated_product["description"], "Unknown")

        # update product that dont exist
        response = self.client.put(f"{BASE_URL}/0", json=new_product)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_product(self):
        """It should Delete a Product"""
        # create list of products
        products = self._create_products(count=5)

        # get count of products created
        products_count = self.get_product_count()

        # first test product
        test_product = products[0]

        # delete test product
        response = self.client.delete(f"{BASE_URL}/{test_product.id}")

        # assert status code 204
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # check response data empty
        self.assertEqual(len(response.data), 0)

        # retrieve deleted product
        response = self.client.get(f"{BASE_URL}/{test_product.id}")

        # confirm product deletion
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # get product count again
        new_count = self.get_product_count()

        # check product count is one less than initial count
        self.assertEqual(new_count, products_count - 1)

    def test_query_by_name(self):
        """It should Query Products by its name"""

        # create 5 products
        products = self._create_products(count=5)

        # extract name of first product
        test_name = products[0].name

        # count products with same name
        name_count = len([product for product in products if product.name == test_name])

        # get request
        response = self.client.get(BASE_URL, query_string=f"name={quote_plus(test_name)}")

        # check request was successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # retrieve json data
        data = response.get_json()

        # check length data list is same as name count
        self.assertEqual(len(data), name_count)

        # check if products in data list match test name
        for product in data:
            self.assertEqual(product["name"], test_name)

    def test_query_by_category(self):
        """It should Query Products by category"""

        # create products
        products = self._create_products(10)

        # retrieve category of first product in the list
        category = products[0].category

        # create list with products matching category
        found = [product for product in products if product.category == category]

        # count found products matching category
        found_count = len(found)

        # debug message products found
        logging.debug("Found Products [%d] %s", found_count, found)

        # get request for category
        response = self.client.get(BASE_URL, query_string=f"category={category.name}")

        # check successful request
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # retrieve response data
        data = response.get_json()

        # check if length of data is same as found count
        self.assertEqual(len(data), found_count)

        for product in data:
            self.assertEqual(product["category"], category.name)

    def test_query_by_availability(self):
        """It should Query Products by availability"""

        # create products
        products = self._create_products(10)

        # initialize list to store available products
        available_products = [product for product in products if product.available is True]

        # count available products
        available_count = len(available_products)

        # debug message products avaiable
        logging.debug("Available Products [%d] %s", available_count, available_products)

        # send get request
        response = self.client.get(BASE_URL, query_string="available=true")

        # check request success
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # retrieve data
        data = response.get_json()

        # check is length of data is same as available count
        self.assertEqual(len(data), available_count)

        # check if products in data is available
        for product in data:
            self.assertEqual(product["available"], True)

    ######################################################################
    # Utility functions
    ######################################################################

    def get_product_count(self):
        """save the current number of products"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        # logging.debug("data = %s", data)
        return len(data)
