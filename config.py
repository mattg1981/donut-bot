from dataclasses import dataclass


@dataclass(frozen=True)
class ContractConfig:
    chain: str = ""
    contrib: str = ""
    staking: str = ""
    donut: str = ""
    distribute: str = ""
    multi_sig: str = ""
    lp: str = ""
    lp_manager: str = ""
    faucet: str = ""
    tipping: str = ""
    special_membership: str = ""


@dataclass(frozen=True)
class ContractConfigSection:
    contracts: list[ContractConfig]


@dataclass(frozen=True)
class CommunityFeatures:
    flair: bool
    post_bot: bool
    post_command: bool
    post_approve: bool
    faucet: bool
    tips: bool
    archive: bool
    max_posts_per_24h: bool
    post_of_the_week: bool
    topic_limiting: bool
    minimum_word_count: bool
    daily_pin: bool


@dataclass(frozen=True)
class CommunityToken:
    name: str
    icon: str
    is_default: bool
    chain: str
    chain_id: int
    contract_address: str


@dataclass(frozen=True)
class Comment2VoteConfigSection:
    max_weight: int
    update_interval_hours: int
    min_tip_to_avoid_archive: int
    min_chars_needed_to_avoid_archive: int
    archive_url: str


@dataclass(frozen=True)
class PostsConfigSection:
    removal_id: str
    max_per_24_hours: int
    approve_weight: int
    post_cooldown_in_minutes: int
    minimum_word_count: int
    minimum_word_count_excluded_flairs: list[str]
    bypass_word_count_by_title: list[str]
    pow_min_weight: int
    pow_max_weight: int


@dataclass(frozen=True)
class Community:
    name: str
    posts: PostsConfigSection
    comment2vote: Comment2VoteConfigSection
    ignore: list[str]
    features: CommunityFeatures
    tokens: list[CommunityToken]

@dataclass(frozen=True)
class MembershipConfigSection:
    members_url: str
    donut_count_in_lp: int


@dataclass(frozen=True)
class VerifiedFlair:
    user: str
    text: str
    css_class: str


@dataclass(frozen=True)
class FlairConfigSection:
    verified: list[VerifiedFlair]

class Config:
    _instance = None

    # noinspection SpellCheckingInspection
    _conf = {
        "membership": {
            "members_url": "https://raw.githubusercontent.com/EthTrader/memberships/main/members.json",
            "donut_count_in_lp": 50000
        },
        "users_location": "https://ethtrader.github.io/donut.distribution/users.json",
        "communities": [
            {
                "name": "ethtrader_test",
                "ignore": [
                    "AutoModerator",
                    "EthTraderCommunity",
                    "EthTrader_Reposter",
                    "donut-bot"
                ],
                "posts": {
                    "removal_id": "a8b91952-a441-4978-a492-2a31f1e33841",
                    "max_per_24_hours": 3,
                    "approve_weight": 60_000,
                    "post_cooldown_in_minutes": 180,
                    "minimum_word_count": 200,
                    "minimum_word_count_excluded_flairs": ["Question"],
                    "bypass_word_count_by_title": [
                        "[EthTrader Contest]",
                        "[Official]",
                        "[Announcement]"
                    ],
                    "pow_min_weight": 20_000,
                    "pow_max_weight": 500_000
                },
                "comment2vote": {
                    "max_weight": 20000,
                    "update_interval_hours": 6,
                    "min_tip_to_avoid_archive": 5,
                    "min_chars_needed_to_avoid_archive": 13,
                    "archive_url": "https://raw.githubusercontent.com/ethtrader/ethtrader-tip-archive/main/#y#/#m#/#d#/#f#"
                },
                "features": {
                    "flair": True,
                    "post_bot": True,
                    "post_command": True,
                    "post_approve": True,
                    "faucet": True,
                    "tips": True,
                    "archive": True,
                    "max_posts_per_24h": True,
                    "post_of_the_week": True,
                    "topic_limiting": True,
                    "minimum_word_count": True,
                    "daily_pin": True
                },
                "tokens": [
                    {
                        "name": "donut",
                        "icon": ":donut:",
                        "is_default": True,
                        "chain": "arb1",
                        "chain_id": 42161,
                        "contract_address": "0xF42e2B8bc2aF8B110b65be98dB1321B1ab8D44f5"
                    }
                ]
            }
        ],
        "contracts": [
            {
                "chain": "mainnet",
                "donut": "0xC0F9bD5Fa5698B6505F643900FFA515Ea5dF54A9",
                "lp": "0x718Dd8B743ea19d71BDb4Cb48BB984b73a65cE06",
                "staking": "0x813fd5A7B6f6d792Bf9c03BBF02Ec3F08C9f98B2",
                "multi_sig": "0x367b68554f9CE16A87fD0B6cE4E70d465A0C940E",
                "special_membership": "0xd1Dc1A5b56EA321A921c74F8307153A58b1EfA4D"
            },
            {
                "chain": "gnosis",
                "contrib": "0xFc24F552fa4f7809a32Ce6EE07C09Dcd7A41988F",
                "donut": "0x524B969793a64a602342d89BC2789D43a016B13A",
                "lp": "0x077240a400b1740C8cD6f73DEa37DA1F703D8c00",
                "staking": "0x84b427415A23bFB57Eb94a0dB6a818EB63E2429D",
                "multi_sig": "0x682b5664C2b9a6a93749f2159F95c23fEd654F0A",
                "tipping": "0xF40e98033eb722CC6B4a64F7b37737d56eCB17EF"
            },
            {
                "chain": "arb1",
                "contrib": "0xF28831db80a616dc33A5869f6F689F54ADd5b74C",
                "donut": "0xF42e2B8bc2aF8B110b65be98dB1321B1ab8D44f5",
                "distribute": "0xf4d6a6585BDaebB6456050Ae456Bc69ea7f51838",
                "multi_sig": "0x439ceE4cC4EcBD75DC08D9a17E92bDdCc11CDb8C",
                "lp": "0x65f7a98d87bc21a3748545047632fef4d3ff9a67",
                "lp_manager": "0xf0cbce1942a68beb3d1b73f0dd86c8dcc363ef49",
                "faucet": "",
                "tipping": "0x403EB731A37cf9e41d72b9A97aE6311ab44bE7b9"
            }
        ]
    }

    def __new__(cls, json_data=None):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    # @property
    # def flair(self) -> FlairConfigSection:
    #     verified = self._conf.get('flair', {}).get('verified')
    #     return FlairConfigSection([VerifiedFlair(**v) for v in verified])

    @property
    def membership(self) -> MembershipConfigSection:
        return MembershipConfigSection(**self._conf['membership'])

    # @property
    # def posts(self) -> PostsConfigSection:
    #     return PostsConfigSection(**self._conf.get('posts', {}))

    # @property
    # def comment2vote(self) -> Comment2VoteConfigSection:
    #     return Comment2VoteConfigSection(**self._conf.get('comment2vote', {}))

    @property
    def users_location(self):
        return self._conf.get('users_location', "")

    @property
    def communities(self) -> list[Community]:
        communities = []
        for community in self._conf.get('communities', []):
            name = community["name"]
            ignore = community.get("ignore", [])
            features = CommunityFeatures(**community.get('features', {}))
            posts = PostsConfigSection(**community.get('posts', {}))
            comment2vote = Comment2VoteConfigSection(**community.get('comment2vote', {}))
            tokens = []
            for token in community.get('tokens', []):
                tokens.append(CommunityToken(**token))

            communities.append(Community(name, posts, comment2vote, ignore, features, tokens))

        return communities

    @property
    def contracts(self):
        contracts = [ContractConfig(**c) for c in self._conf['contracts']]
        return ContractConfigSection(contracts)
