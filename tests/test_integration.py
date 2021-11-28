import unittest
import requests


class TestWrappingApiBasic(unittest.TestCase):
    def test_single_call(self):
        response = requests.get('http://localhost:5000/crypto/sign?message=test')
        self.assertEqual(response.status_code, requests.codes.ok)
        self.assertTrue('success' in response.json())
        self.assertTrue('last_status_code' in response.json())
        self.assertTrue('value' in response.json())


if __name__ == "__main__":
    unittest.main()