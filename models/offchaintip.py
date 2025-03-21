class OffchainTip:
    def __init__(self, sender_name: str,
                 recipient_name: str,
                 amount: float,
                 weight: float,
                 token: str,
                 content_id: str,
                 parent_content_id: str,
                 submission_content_id: str,
                 community: str,
                 is_valid: bool,
                 message: str):

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