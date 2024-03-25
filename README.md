# Donut Bot

Donut bot is a reddit bot that runs in the [r/EthTrader](https://reddit.com/r/ethtrader) subreddit and performs the following functions:

- **Wallet Registration:** Allows users to register their wallets to participate in distributions.  Disttributions are held every 28 days and reward users with the [Donut](https://arbiscan.io/token/0xf42e2b8bc2af8b110b65be98db1321b1ab8d44f5) crypto token based on their contribution within the community.
- **Faucet:** Perfoms a drip to help users cover gas costs
- **Tipping:** Allows users to tip Donut tokens to each other.  This is performed off chain and the tips are deducted from the users next distribution.
- **Data Retrieval:** Performs data retrieval and outputs to the [Donut-Bot-Output](https://github.com/mattg1981/donut-bot-output) repository.  This data is used during distribution time to calculate the amount a user will receive.

# Adapting this bot
To adapt this bot for use within other subreddits:
- Build the database using the scripts provided in ad_hoc > setup
- Populate the .env.sample file with your secrets.  Then rename this file to .env
- Update the config.json file with settings that are correct for your subreddit
- Run the `donut-bot.sh` shell script

Many of the ad_hoc scripts will need to be modified with correct addresses as well - or will not be applicable to your subreddit.  These scripts are run as ad_hoc processes on a schedule, so you will need to add them to whichever process scheduler you use (e.g. cron)

# Updating the bot
Run the `update.sh` script within the utils directory.  This script will stop the running python processes, pull down the latest commits and then starts the individual python bots again. 

# Notes
I am not a python developer professionally.  As a matter of fact, this was my very first python project I wrote, in large part due to the PRAW reddit python library.  As such, this code is not shared as a great example of python code, rather hopefully it will help those to understand and use the praw and web3.py libraries.