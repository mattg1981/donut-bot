from unittest import TestCase
import commands.database as db


class Test(TestCase):
    def test_get_address_for_registered_user(self):
        user = db.get_address_for_user("mattg1981")
        expected_output = {'address': '0xd762e68a2d30ab4d836683c421121AbB5b3e1DcC', 'username': 'mattg1981'}
        self.assertEqual(user, expected_output)
        self.assertEqual(user["address"], '0xd762e68a2d30ab4d836683c421121AbB5b3e1DcC')
        self.assertEqual(user["username"], 'mattg1981')


    def test_get_address_for_unregistered_user(self):
        user = db.get_address_for_user("NonRegisteredUser#1981")
        self.assertEqual(user, None)

    def test_get_addresses_for_registered_users(self):
        author_name = "carlslarson"
        commenter_name = "mattg1981"
        users_result = db.get_address_for_users([author_name, commenter_name])
        expected_output = [
            {'address': '0x95D9bED31423eb7d5B68511E0352Eae39a3CDD20', 'username': 'carlslarson'},
            {'address': '0xd762e68a2d30ab4d836683c421121AbB5b3e1DcC', 'username': 'mattg1981'}
        ]
        self.assertEqual(users_result, expected_output)
        self.assertEqual(len(users_result), 2)

        author = next(item for item in users_result if item["username"] == author_name)
        self.assertEqual(author["address"], '0x95D9bED31423eb7d5B68511E0352Eae39a3CDD20')
        self.assertEqual(author["username"], 'carlslarson')

        commenter = next(item for item in users_result if item["username"] == commenter_name)
        self.assertEqual(commenter["address"], '0xd762e68a2d30ab4d836683c421121AbB5b3e1DcC')
        self.assertEqual(commenter["username"], 'mattg1981')

    def test_get_addresses_for_users_author_not_registered(self):
        author_name = "NonRegisteredUser#1981"
        commenter_name = "mattg1981"
        users_result = db.get_addresses_for_users([author_name, commenter_name])
        expected_output = [
            {'address': '0xd762e68a2d30ab4d836683c421121AbB5b3e1DcC', 'username': 'mattg1981'}
        ]
        self.assertEqual(users_result, expected_output)
        self.assertEqual(len(users_result), 1)

        try:
            author = next(item for item in users_result if item["username"] == author_name)
        except Exception as e:
            author = None

        self.assertEqual(author, None)
