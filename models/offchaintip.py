class OffchainTip:
    def __init__(self, sender_name, recipient_name, amount, weight, token, content_id, parent_content_id,
                 submission_content_id, community, is_valid, message):

        self.sender_name = sender_name
        self.recipient_name = recipient_name
        self.amount = amount
        self.weight = weight
        self.token = token
        self.content_id = content_id
        self.parent_content_id = parent_content_id
        self.submission_content_id = submission_content_id
        self.community = community
        self.is_valid = is_valid
        self.message = message

    def __str__(self):
        return f"[valid]: {self.is_valid} [sender]: {self.sender_name} [recipient]: {self.recipient_name} [amount]: {self.amount} [token]: {self.token}"