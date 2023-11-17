class Tip:
    def __init__(self, sender_name, sender_address, recipient_name,
                 recipient_address, amount, token, content_id, parent_content_id,
                 submission_content_id, community, is_valid, message):

        self.sender_name = sender_name
        self.sender_address = sender_address
        self.recipient_name = recipient_name
        self.recipient_address = recipient_address
        self.amount = amount
        self.token = token
        self.content_id = content_id
        self.parent_content_id = parent_content_id
        self.submission_content_id = submission_content_id
        self.community = community
        self.is_valid = is_valid
        self.message = message

    def __str__(self):
        return f"[valid]: {self.is_valid} [sender]: {self.sender_name} [recipient]: {self.recipient_name} [amount]: {self.amount} [token]: {self.token}"