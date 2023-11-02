from unittest import TestCase
import commands.database as db


class Test(TestCase):

    def test_add_unregistered_user(self):
        user="def_not_a_valid_user";
        content_id = "some_id"
        result = db.add_unregistered_user(user, content_id)
        if result:
            return
        self.fail()

    def test_get_user_by_address(self):
        address = "0xd762e68a2d30ab4d836683c421121AbB5b3e1DcC"
        result = db.get_user_by_address(address)
        if not result:
            self.fail()

        address2 = "not_in_database"
        result2 = db.get_user_by_address(address2)
        if result2:
            self.fail()

    def test_get_address_for_registered_user(self):
        user = db.get_user_by_name("mattg1981")
        expected_output = {'address': '0xd762e68a2d30ab4d836683c421121AbB5b3e1DcC', 'username': 'mattg1981'}
        self.assertEqual(user, expected_output)
        self.assertEqual(user["address"], '0xd762e68a2d30ab4d836683c421121AbB5b3e1DcC')
        self.assertEqual(user["username"], 'mattg1981')

    def test_has_processed_content(self):
        result = db.has_processed_content("t1_k782jvi")
        self.assertIsNotNone(result)

        result = db.has_processed_content("t1_NOT-IN-DB")
        self.assertIsNone(result)

    def test_set_processed_content(self):
        content_id = "SOME_ID_NOT_IN_DB"

        # cleanup (in case a prior test failed and failed to cleanup)
        db.remove_processed_content(content_id)

        result = db.set_processed_content(content_id)

        self.assertIsNotNone(result)
        self.assertIsNotNone(db.has_processed_content(content_id))

        # cleanup
        db.remove_processed_content(content_id)


    def test_get_address_for_unregistered_user(self):
        user = db.get_user_by_name("@Non.Registered.User#1981")
        self.assertEqual(user, None)

    def test_get_addresses_for_registered_users(self):
        author_name = "carlslarson"
        commenter_name = "mattg1981"
        users_result = db.get_users_by_name([author_name, commenter_name])
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
        users_result = db.get_users_by_name([author_name, commenter_name])
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

    def test_get_tip_status_for_current_round(self):
        author = "Honey_-_Badger"
        result = db.get_tip_status_for_current_round_new(author)
        self.assertIsNotNone(result)

    def test_get_sub_status_for_current_round(self):
        community = "EthTrader_Test"
        result = db.get_sub_status_for_current_round(community)
        self.assertIsNotNone(result)

    def test_process_earn2tip(self):
        user_address = "0xd762e68a2d30ab4d836683c421121AbB5b3e1DcC"
        author_address = "0xa8C8c9e18C763805c91bcB720B2320aDe16a0BBf"
        amount = 10
        token = 'donut'
        content_id = 't1_kajdfkaj'