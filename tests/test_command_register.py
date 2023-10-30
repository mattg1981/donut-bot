from unittest import TestCase

from commands.command_register import RegisterCommand


class TestRegisterCommand(TestCase):

    def test_config_is_available(self):
        reg = RegisterCommand()
        config = reg.config
        self.assertIsNotNone(config)

    def test_process_command(self):
        command1 = "!register status"
        command2 = "!register 0x...."
        command3 = "!register"
        command4 = """
        !register \n
        status
        """
        self.fail()
